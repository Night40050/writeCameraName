# ai/tts_engine.py
"""
Text-to-Speech engine — pyttsx3 backend, process-per-utterance.

Known issue
-----------
pyttsx3 suffers from a threading / engine-reuse bug where ``runAndWait()``
silently stops working after the first call *within the same process*.  The
solution used here is to spawn a brand-new ``multiprocessing.Process`` for
every utterance so the engine is always freshly initialised.

Gender-aware voices
-------------------
``set_voice_by_gender()`` and ``get_gender_voice_index()`` scan
``engine.getProperty('voices')`` once at startup and cache a mapping
``{'male': index, 'female': index}``.  ``speak()`` accepts an optional
``gender`` keyword and passes the resolved voice index to the worker.
"""

from __future__ import annotations

import logging
import multiprocessing
from typing import Optional

from config import TTS_RATE, TTS_VOLUME, TTS_VOICE_INDEX

logger = logging.getLogger(__name__)


# ── worker (runs in a fresh OS process every time) ─────────────────────────────

def _tts_worker(
    text: str,
    rate: int,
    volume: float,
    voice_index: Optional[int],
) -> None:
    """
    Target of a `multiprocessing.Process`.

    Instantiates a fresh pyttsx3 engine, configures it, speaks *text*, then
    exits.  ``voice_index=None`` means: use the system default voice.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate",   rate)
        engine.setProperty("volume", volume)
        if voice_index is not None:
            voices = engine.getProperty("voices")
            if voices and 0 <= voice_index < len(voices):
                engine.setProperty("voice", voices[voice_index].id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        # Cannot log back to the parent; print is better than silence.
        print(f"[TTS WORKER ERROR] {exc}")


# ── Gender helpers ─────────────────────────────────────────────────────────────

_GENDER_KEYWORDS = {
    "male":   ["male",  "david", "james", "mark",  "paul",  "daniel",
               "richard", "google 普通话", "david desktop"],
    "female": ["female", "samantha", "karen", "zira", "susan", "monica",
               "google 普通话", "linda"],
}


def _categorise_voice(name: str, gender_attr: Optional[str]) -> Optional[str]:
    """Return ``"male"``, ``"female"`` or ``None`` for a single voice entry."""
    haystack = (name or "").lower()
    if gender_attr:
        gender_attr = gender_attr.lower()
        if gender_attr == "male":
            return "male"
        if gender_attr == "female":
            return "female"
    # Fall back to substring matching against the known keyword lists
    for gender, keywords in _GENDER_KEYWORDS.items():
        if any(kw in haystack for kw in keywords):
            return gender
    return None


def _build_voice_cache() -> dict[str, Optional[int]]:
    """Run a throwaway pyttsx3 init, scan voices, and return ``{'male': idx, 'female': idx}``."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        engine.stop()
        result: dict[str, Optional[int]] = {"male": None, "female": None}
        if not voices:
            return result
        for idx, v in enumerate(voices):
            name    = getattr(v, "name",    None)
            g_attr  = getattr(v, "gender",  None)   # some backends expose this
            gender  = _categorise_voice(name or "", g_attr)
            if gender and result[gender] is None:
                result[gender] = idx
                logger.debug(
                    "Cached TTS %s voice: index=%d name=%r", gender, idx, name
                )
        return result
    except Exception as exc:
        logger.warning("_build_voice_cache: could not enumerate voices: %s", exc)
        return {"male": None, "female": None}


# ── Public engine ──────────────────────────────────────────────────────────────

class TTSEngine:
    """
    Spawns one ``multiprocessing.Process`` per utterance.

    ``set_voice_by_gender()`` updates the voice index used for the *next*
    ``speak()`` call.  The index is resolved in the *main process* (so it can
    inspect ``Voice.name`` / ``Voice.gender`` properties that are not
    serialisable) and then forwarded to the worker as a plain ``int``.

    Parameters
    ----------
    default_voice_index:
        Fallback voice index used when no gender override is requested and
        ``config.TTS_VOICE_INDEX`` resolves to ``None``.
    """

    def __init__(
        self,
        default_voice_index: int = TTS_VOICE_INDEX,
    ) -> None:
        self._process: Optional[multiprocessing.Process] = None
        self._default_voice_index: Optional[int] = default_voice_index
        # Cache indexed by gender: resolved at startup (lazy on first access)
        self._voice_cache: Optional[dict[str, Optional[int]]] = None

    # ── Gender-aware voice selection ──────────────────────────────────────────

    def set_voice_by_gender(self, gender: str) -> Optional[int]:
        """Set the voice that will be used for the *next* ``speak()`` call.

        Parameters
        ----------
        gender:
            ``"male"`` or ``"female"``  (case-insensitive).

        Returns
        -------
        Optional[int]
            The resolved voice index, or ``None`` if no matching voice was
            found (the worker will fall back to the system default).
        """
        cache = self._get_voice_cache()
        gender_key = gender.lower()
        if gender_key not in cache:
            logger.warning("TTSEngine: unknown gender %r — voices unchanged.", gender)
            return None
        idx = cache[gender_key]
        if idx is None:
            logger.warning(
                "TTSEngine: no %s voice found among %d available voices.",
                gender_key,
                len(_tts_worker.__code__.co_varnames),
            )
        else:
            logger.info("TTSEngine: voice set to %s (index=%d).", gender_key, idx)
        self._default_voice_index = idx
        return idx

    def get_gender_voice_index(self, gender: str) -> Optional[int]:
        """Return the resolved voice index for *gender* without changing state.

        Parameters
        ----------
        gender:
            ``"male"`` or ``"female"``.

        Returns
        -------
        Optional[int]
            Cached index, or ``None`` if the voice has not been found.
        """
        cache = self._get_voice_cache()
        return cache.get(gender.lower())

    def _get_voice_cache(self) -> dict[str, Optional[int]]:
        """Lazily build (and cache) the ``{'male': idx, 'female': idx}`` map."""
        if self._voice_cache is None:
            self._voice_cache = _build_voice_cache()
        return self._voice_cache

    # ── Public speak API ──────────────────────────────────────────────────────

    def speak(self, text: str, gender: Optional[str] = None) -> None:
        """Speak *text* asynchronously in a background process.

        Parameters
        ----------
        text:
            String to pronounce.
        gender:
            Optional ``"male"`` or ``"female"``.  When provided, the
            appropriate cached voice index is passed to the worker before
            speaking.  The voice selection is *per-call* — it does **not**
            permanently change the engine's default voice.
        """
        text = text.strip()
        if not text:
            return
        if self.is_speaking:
            logger.debug("TTS busy – skipping: %r", text)
            return
        # Resolve voice index for this specific call
        voice_index = self._default_voice_index
        if gender:
            override = self.get_gender_voice_index(gender)
            if override is not None:
                voice_index = override
        self._launch(text, voice_index)

    def speak_sync(self, text: str, gender: Optional[str] = None) -> None:
        """Speak *text* synchronously (blocks until finished).

        Parameters
        ----------
        text:
            String to pronounce.
        gender:
            Optional ``"male"`` or ``"female"`` — same semantics as
            :meth:`speak`.
        """
        text = text.strip()
        if not text:
            return
        if self.is_speaking:
            logger.debug("TTS busy – waiting before speaking: %r", text)
            self._process.join()
        voice_index = self._default_voice_index
        if gender:
            override = self.get_gender_voice_index(gender)
            if override is not None:
                voice_index = override
        self._launch(text, voice_index)
        self._process.join()

    def stop(self) -> None:
        """Forcibly terminate any active TTS process."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)
        self._process = None

    # ── private ────────────────────────────────────────────────────────────────

    def _launch(self, text: str, voice_index: Optional[int]) -> None:
        proc = multiprocessing.Process(
            target=_tts_worker,
            args=(text, TTS_RATE, TTS_VOLUME, voice_index),
            daemon=True,
        )
        proc.start()
        self._process = proc
        logger.info(
            "TTS process started (pid=%d, voice_index=%s) for: %r",
            proc.pid,
            voice_index,
            text,
        )

    # ── dunder / properties ───────────────────────────────────────────────────

    @property
    def is_speaking(self) -> bool:
        """True while a TTS worker process is still alive."""
        if self._process is None:
            return False
        return self._process.is_alive()

    def __repr__(self) -> str:
        return (
            f"TTSEngine(default_voice_index={self._default_voice_index}, "
            f"speaking={self.is_speaking})"
        )

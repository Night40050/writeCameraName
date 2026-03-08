# ai/tts_engine.py
"""
Text-to-Speech engine.
Primary backend: pyttsx3 (offline, cross-platform).
Optional backend: Coqui TTS (higher quality, requires TTS package).
"""

from __future__ import annotations
import logging
import threading
from typing import Literal

from config import TTS_RATE, TTS_VOLUME, TTS_VOICE_INDEX

logger = logging.getLogger(__name__)

Backend = Literal["pyttsx3", "coqui"]


class TTSEngine:
    """Thread-safe TTS wrapper."""

    def __init__(self, backend: Backend = "pyttsx3") -> None:
        self._backend  = backend
        self._engine   = None
        self._lock     = threading.Lock()
        self._ready    = False

    # ── public ───────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Initialise the TTS engine (call once at startup or lazily)."""
        if self._ready:
            return
        if self._backend == "pyttsx3":
            self._load_pyttsx3()
        elif self._backend == "coqui":
            self._load_coqui()
        else:
            raise ValueError(f"Unknown TTS backend: {self._backend!r}")

    def speak(self, text: str) -> None:
        """Speak *text* in a background thread (non-blocking)."""
        if not text.strip():
            return
        if not self._ready:
            self.load()
        thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        thread.start()

    def speak_sync(self, text: str) -> None:
        """Speak *text* and block until finished."""
        if not self._ready:
            self.load()
        self._speak_sync(text)

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── private ──────────────────────────────────────────────────────────────

    def _load_pyttsx3(self) -> None:
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.setProperty("rate",   TTS_RATE)
            eng.setProperty("volume", TTS_VOLUME)
            voices = eng.getProperty("voices")
            if voices and TTS_VOICE_INDEX < len(voices):
                eng.setProperty("voice", voices[TTS_VOICE_INDEX].id)
            self._engine = eng
            self._ready  = True
            logger.info("pyttsx3 TTS engine ready.")
        except Exception as exc:
            logger.error("Failed to init pyttsx3: %s", exc)
            raise

    def _load_coqui(self) -> None:
        try:
            from TTS.api import TTS as CoquiTTS  # type: ignore
            self._engine = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
            self._ready  = True
            logger.info("Coqui TTS engine ready.")
        except Exception as exc:
            logger.error("Failed to init Coqui TTS: %s", exc)
            raise

    def _speak_sync(self, text: str) -> None:
        with self._lock:
            try:
                if self._backend == "pyttsx3":
                    self._engine.say(text)
                    self._engine.runAndWait()
                elif self._backend == "coqui":
                    import tempfile, os, subprocess
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                        tmp_path = f.name
                    self._engine.tts_to_file(text=text, file_path=tmp_path)
                    subprocess.Popen(
                        ["ffplay", "-nodisp", "-autoexit", tmp_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    ).wait()
                    os.unlink(tmp_path)
            except Exception as exc:
                logger.error("TTS speak error: %s", exc)

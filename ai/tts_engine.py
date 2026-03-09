# ai/tts_engine.py
"""
Text-to-Speech engine — pyttsx3 backend.

Problem: pyttsx3 has a well-known bug where `runAndWait()` silently breaks
after the first call when reused across threads.  The fix is to spawn a brand-
new pyttsx3 engine instance inside a fresh `multiprocessing.Process` for every
utterance.  The main process never touches pyttsx3 directly.

`is_speaking` flag prevents overlapping speech calls.
"""

from __future__ import annotations
import logging
import multiprocessing
from typing import Optional

from config import TTS_RATE, TTS_VOLUME, TTS_VOICE_INDEX

logger = logging.getLogger(__name__)


# ── worker (runs in a separate process) ──────────────────────────────────────

def _tts_worker(text: str, rate: int, volume: float, voice_index: int) -> None:
    """
    Spawned as a separate OS process.
    Creates a fresh pyttsx3 engine, speaks *text*, then exits.
    """
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate",   rate)
        engine.setProperty("volume", volume)
        voices = engine.getProperty("voices")
        if voices and voice_index < len(voices):
            engine.setProperty("voice", voices[voice_index].id)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as exc:
        # Cannot log back to parent easily; print is better than silence.
        print(f"[TTS WORKER] Error: {exc}")


# ── public engine ─────────────────────────────────────────────────────────────

class TTSEngine:
    """
    Spawns a new process for each TTS call to work around the pyttsx3
    threading/re-use bug.  Non-blocking by default; `is_speaking` flag
    prevents overlapping utterances.
    """

    def __init__(self) -> None:
        self._process: Optional[multiprocessing.Process] = None

    # ── public ───────────────────────────────────────────────────────────────

    @property
    def is_speaking(self) -> bool:
        """True while a TTS process is still running."""
        if self._process is None:
            return False
        return self._process.is_alive()

    def speak(self, text: str) -> None:
        """
        Speak *text* in a background process (non-blocking).
        If already speaking, the call is silently ignored.
        """
        text = text.strip()
        if not text:
            return
        if self.is_speaking:
            logger.debug("TTS busy – skipping: %r", text)
            return
        self._launch(text)

    def speak_sync(self, text: str) -> None:
        """Speak *text* and block until the process finishes."""
        text = text.strip()
        if not text:
            return
        if self.is_speaking:
            logger.debug("TTS busy – waiting before speaking: %r", text)
            self._process.join()
        self._launch(text)
        self._process.join()

    def stop(self) -> None:
        """Forcibly terminate any active speech."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)
        self._process = None

    # ── private ──────────────────────────────────────────────────────────────

    def _launch(self, text: str) -> None:
        proc = multiprocessing.Process(
            target=_tts_worker,
            args=(text, TTS_RATE, TTS_VOLUME, TTS_VOICE_INDEX),
            daemon=True,
        )
        proc.start()
        self._process = proc
        logger.info("TTS process started (pid=%d) for: %r", proc.pid, text)

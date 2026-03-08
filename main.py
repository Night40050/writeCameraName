#!/usr/bin/env python3
# main.py – AirSign entry point
"""
Main application loop.

Controls (keyboard fallback):
  q / Esc  → quit
  c        → clear canvas
  s        → save canvas
  r        → run OCR + TTS on current canvas
  d        → toggle debug landmarks
"""

from __future__ import annotations
import sys
import time
import logging

import cv2

import config
from core.hand_tracker       import HandTracker
from core.canvas_manager     import CanvasManager
from core.gesture_classifier import classify, Gesture
from ui.overlay              import Overlay
from ui.toolbar              import Toolbar
from ai.ocr_engine           import OCREngine
from ai.tts_engine           import TTSEngine
from utils.image_exporter    import save_canvas, append_ocr_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("airsign")


def main() -> None:
    # ── camera ────────────────────────────────────────────────────────────────
    logger.info("Opening camera index %d …", config.CAMERA_INDEX)
    cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.FPS_TARGET)

    if not cap.isOpened():
        logger.error(
            "Cannot open camera %d. "
            "Run utils/obs_helper.py to list available cameras.",
            config.CAMERA_INDEX,
        )
        sys.exit(1)

    # ── subsystems ────────────────────────────────────────────────────────────
    tracker  = HandTracker()
    canvas   = CanvasManager(config.FRAME_WIDTH, config.FRAME_HEIGHT)
    overlay  = Overlay()
    toolbar  = Toolbar()
    ocr      = OCREngine()
    tts      = TTSEngine(backend="pyttsx3")

    # Lazy-load OCR/TTS in background (optional – comment out to defer to first use)
    # import threading
    # threading.Thread(target=ocr.load, daemon=True).start()
    # threading.Thread(target=tts.load, daemon=True).start()

    # ── toolbar callbacks ─────────────────────────────────────────────────────
    def on_save() -> None:
        path = save_canvas(canvas.canvas_image)
        overlay.set_status(f"Saved: {path}" if path else "Save FAILED", 90)

    def on_clear() -> None:
        canvas.clear()
        overlay.set_status("Canvas cleared", 60)

    def on_read() -> None:
        overlay.set_status("Running OCR …", 120)
        text = ocr.recognise(canvas.canvas_image)
        if text and text != "Could not read text":
            # Save recognised text to exports/recognized_text.txt
            append_ocr_result(text)
            overlay.set_status(f"Saved: {text}", 180)
            tts.speak(text)
        else:
            overlay.set_status("Could not read text", 120)

    toolbar.set_callback("Save",  on_save)
    toolbar.set_callback("Clear", on_clear)
    toolbar.set_callback("Read",  on_read)

    # Build after we know the width
    ret, probe = cap.read()
    if ret:
        fw = probe.shape[1]
    else:
        fw = config.FRAME_WIDTH
    toolbar.build(fw)

    # ── FPS tracking ──────────────────────────────────────────────────────────
    fps       = 0.0
    prev_time = time.perf_counter()

    # ── SELECT gesture debounce ───────────────────────────────────────────────
    select_cooldown = 0   # frames remaining before another SELECT fires

    logger.info("AirSign running. Press Q or Esc to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Frame grab failed – retrying …")
            continue

        # Flip for mirror view
        frame = cv2.flip(frame, 1)

        # ── hand tracking ─────────────────────────────────────────────────────
        track  = tracker.process(frame)
        result = classify(
            track.hand_landmarks,
            frame.shape[1],
            frame.shape[0],
        )

        # ── gesture dispatch ──────────────────────────────────────────────────
        tip = result.index_tip

        if result.gesture == Gesture.DRAW and tip:
            canvas.draw(tip)
        elif result.gesture == Gesture.ERASE and tip:
            canvas.erase(tip)
        else:
            canvas.release_stroke()

        # SELECT = closed fist → check toolbar hit or fire on_read
        if result.gesture == Gesture.SELECT and tip and select_cooldown == 0:
            if not toolbar.check_click(tip):
                on_read()
            select_cooldown = 45   # ~1.5 s at 30 fps

        if select_cooldown > 0:
            select_cooldown -= 1

        # Toolbar hover detection (use index tip in toolbar zone)
        hover = tip if (tip and tip[1] < config.TOOLBAR_HEIGHT) else None

        # ── compose display ───────────────────────────────────────────────────
        blended = canvas.blend(track.frame)
        toolbar.render(blended, hover_point=hover)
        display = overlay.compose(track.frame, blended, result, fps=fps)

        cv2.imshow("AirSign", display)

        # ── FPS ───────────────────────────────────────────────────────────────
        now  = time.perf_counter()
        fps  = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now

        # ── keyboard fallback ─────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):   # q or Esc
            break
        elif key == ord("c"):
            on_clear()
        elif key == ord("s"):
            on_save()
        elif key == ord("r"):
            on_read()

    # ── cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    tracker.release()
    cv2.destroyAllWindows()
    logger.info("AirSign exited cleanly.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# main.py - AirSign entry point
"""
Main application loop.

Controls (keyboard fallback):
  q / Esc  -> quit
  c        -> clear canvas
  s        -> save canvas
  r        -> run OCR + TTS on current canvas
  d        -> toggle debug landmarks
"""

from __future__ import annotations

import sys
import time
import logging
import multiprocessing
from typing import Callable

import cv2

import config
from core.hand_tracker       import HandTracker
from core.canvas_manager     import CanvasManager
from core.gesture_classifier import classify, Gesture
from ui.overlay              import Overlay
from ui.toolbar              import Toolbar
from ai.ocr_engine           import OCREngine
from ai.tts_engine           import TTSEngine
from utils.image_exporter    import save_canvas, append_ocr_result, export_canvas
from core.robot_hand         import get_robot_hand

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("airsign")


def main() -> None:
    # ── camera ─────────────────────────────────────────────────────────────────
    logger.info("Opening camera index %d ...", config.CAMERA_INDEX)
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

    # ── subsystems ───────────────────────────────────────────────────────────────
    tracker  = HandTracker()
    canvas   = CanvasManager(config.FRAME_WIDTH, config.FRAME_HEIGHT)
    overlay  = Overlay()
    toolbar  = Toolbar()
    ocr      = OCREngine()
    tts      = TTSEngine()

    # ── state ───────────────────────────────────────────────────────────────────
    _last_ocr_text = ""        # last OCR text to re-read via SPEAK button
    _robot_hand = None         # lazy RobotHand singleton instance

    def _send_text_to_esp32(text: str) -> None:
        """Send *text* to the ESP32 synchronously in the main thread.

        ``pyserial`` ``write()`` only copies bytes into the OS buffer — it
        returns in microseconds regardless of baud rate, so there is no need
        to offload it to a worker thread.  This eliminates the broken
        cancellation/logic problem entirely while keeping the main loop fully
        non-blocked.

        This function never raises exceptions — all errors are caught, logged,
        and the call returns gracefully to allow TTS to proceed.
        """
        nonlocal _robot_hand
        try:
            rh = _robot_hand
            if rh is None:
                rh = get_robot_hand()
                _robot_hand = rh
            if rh is None:
                logger.warning("Robot hand: not available; command dropped.")
                return
            ok = rh.send_text(text)
            if ok:
                logger.debug("Robot hand: %r queued.", text)
            else:
                logger.warning("Robot hand: failed to send %r.", text)
        except Exception as exc:
            logger.error("Robot hand: unexpected error sending %r: %s", text, exc)

    def on_save() -> None:
        path = save_canvas(canvas.canvas_image)
        overlay.set_status(f"Saved: {path}" if path else "Save FAILED", 90)

    def on_clear() -> None:
        canvas.clear()
        overlay.set_status("Canvas cleared", 60)

    def on_read() -> None:
        nonlocal _last_ocr_text
        overlay.set_status("Running OCR ...", 120)
        img = canvas.canvas_image

        # Always export the raw canvas PNG alongside the TXT log
        png_name = export_canvas(img)   # returns bare filename (or "")

        text = ocr.recognise(img)
        if text and text != "Could not read text":
            _last_ocr_text = text
            append_ocr_result(text)
            status = f"Saved: {text}"
            if png_name:
                status += f"  [{png_name}]"
            overlay.set_status(status, 210)

            # ── Gender-based voice selection ───────────────────────────────────
            text_upper = text.upper().strip()
            if text_upper in ("DANIEL", "SAMUEL"):
                gender = "male"
            elif text_upper == "GINA":
                gender = "female"
            else:
                gender = None

            # ── Send to robot hand (ESP32) ────────────────────────────────────
            # Fast serial write in the main thread; does not block rendering.
            _send_text_to_esp32(text)
            overlay.set_status(f"Enviando a mano robótica: {text}", 270)

            # ── Launch TTS (subprocess; independent of robot hand) ────────────
            tts.speak(text, gender=gender)

        else:
            status = "Could not read text"
            if png_name:
                status += f"  [{png_name}]"
            overlay.set_status(status, 150)

    def on_speak() -> None:
        if _last_ocr_text:
            overlay.set_status(f"Hablando: {_last_ocr_text}", 150)
            tts.speak(_last_ocr_text)
        else:
            overlay.set_status("Nothing to speak - run Read first", 90)

    def make_color_callback(
        color_name: str, color_bgr: tuple[int, int, int]
    ) -> Callable[[], None]:
        """Factory: create a colour-change callback for the toolbar."""
        def callback() -> None:
            canvas.draw_color = color_bgr
            overlay.set_status(f"Color: {color_name}", 60)
        return callback

    toolbar.set_callback("Save",  on_save)
    toolbar.set_callback("Clear", on_clear)
    toolbar.set_callback("Read",  on_read)
    toolbar.set_callback("Speak", on_speak)

    # Set colour callbacks
    for color_name, color_bgr in config.COLOR_PALETTE.items():
        toolbar.set_callback(color_name, make_color_callback(color_name, color_bgr))

    # Build after we know the frame width
    ret, probe = cap.read()
    if ret:
        fw = probe.shape[1]
    else:
        fw = config.FRAME_WIDTH
    toolbar.build(fw)

    # ── FPS tracking ─────────────────────────────────────────────────────────────
    fps       = 0.0
    prev_time = time.perf_counter()

    # ── SELECT gesture debounce ───────────────────────────────────────────────────
    select_cooldown = 0   # frames to wait before the next SELECT can fire

    logger.info("AirSign running. Press Q or Esc to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Frame grab failed - retrying ...")
            continue

        # Flip for mirror view
        #frame = cv2.flip(frame, 1)

        # ── hand tracking ───────────────────────────────────────────────────────
        track  = tracker.process(frame)
        result = classify(
            track.hand_landmarks,
            frame.shape[1],
            frame.shape[0],
        )

        # ── gesture dispatch ────────────────────────────────────────────────────
        tip = result.index_tip

        if result.gesture == Gesture.DRAW and tip:
            canvas.draw(tip)
        elif result.gesture == Gesture.ERASE and tip:
            canvas.erase(tip)
        else:
            canvas.release_stroke()

        # SELECT = closed fist -> check toolbar hit or trigger on_read
        if result.gesture == Gesture.SELECT and tip and select_cooldown == 0:
            if not toolbar.check_click(tip):
                on_read()
            select_cooldown = 45   # ~1.5 s at 30 fps

        if select_cooldown > 0:
            select_cooldown -= 1

        # Toolbar hover detection (index tip in toolbar zone)
        hover = tip if (tip and tip[1] < config.TOOLBAR_HEIGHT) else None

        # ── compose display ─────────────────────────────────────────────────────
        blended = canvas.blend(track.frame)
        toolbar.render(blended, hover_point=hover)
        display = overlay.compose(track.frame, blended, result, fps=fps)

        cv2.imshow("AirSign", display)

        # ── FPS ─────────────────────────────────────────────────────────────────
        now  = time.perf_counter()
        fps  = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now

        # ── keyboard fallback ───────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):     # q or Esc
            break
        elif key == ord("c"):
            on_clear()
        elif key == ord("s"):
            on_save()
        elif key == ord("r"):
            on_read()
        elif key == ord("p"):
            on_speak()

    # ── cleanup ─────────────────────────────────────────────────────────────────
    cap.release()
    tracker.release()
    cv2.destroyAllWindows()
    logger.info("AirSign exited cleanly.")


if __name__ == "__main__":
    # Required on Windows when using multiprocessing with frozen executables
    multiprocessing.freeze_support()
    main()

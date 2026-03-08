# ui/overlay.py
"""
Composites the camera frame, drawing canvas, toolbar, and HUD info
into the final display frame.
"""

from __future__ import annotations
from typing import Optional

import cv2
import numpy as np

from config import TOOLBAR_HEIGHT, FONT_SCALE, FONT_THICKNESS
from core.gesture_classifier import Gesture, GestureResult


# Gesture label → display string + colour
_GESTURE_INFO: dict[Gesture, tuple[str, tuple[int, int, int]]] = {
    Gesture.DRAW:   ("✏  DRAW",   (0, 255, 80)),
    Gesture.ERASE:  ("◌  ERASE",  (0, 180, 255)),
    Gesture.SELECT: ("✊  SELECT", (255, 200, 0)),
    Gesture.SCROLL: ("🖐  SCROLL", (200, 100, 255)),
    Gesture.IDLE:   ("—  IDLE",   (160, 160, 160)),
}


class Overlay:
    """Composites all visual layers into a displayable frame."""

    def __init__(self) -> None:
        self._status_msg: str = ""
        self._status_timeout: int = 0   # frames remaining

    # ── public ───────────────────────────────────────────────────────────────

    def set_status(self, msg: str, duration_frames: int = 60) -> None:
        self._status_msg = msg
        self._status_timeout = duration_frames

    def compose(
        self,
        camera_frame: np.ndarray,
        blended_canvas: np.ndarray,
        gesture_result: Optional[GestureResult],
        fps: float = 0.0,
    ) -> np.ndarray:
        """
        Build the final display frame.

        Parameters
        ----------
        camera_frame    : annotated BGR camera frame (with skeleton)
        blended_canvas  : camera + drawing canvas blended
        gesture_result  : current gesture
        fps             : measured frame rate
        """
        out = blended_canvas.copy()

        # ── gesture HUD ──────────────────────────────────────────────────────
        if gesture_result is not None:
            label, color = _GESTURE_INFO.get(
                gesture_result.gesture, ("?", (200, 200, 200))
            )
            cv2.putText(out, label,
                        (10, out.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE,
                        color, FONT_THICKNESS, cv2.LINE_AA)

            # Cursor dot at index-finger tip
            if gesture_result.index_tip and gesture_result.gesture == Gesture.DRAW:
                cv2.circle(out, gesture_result.index_tip, 8, color, -1)
            elif gesture_result.index_tip and gesture_result.gesture == Gesture.ERASE:
                cv2.circle(out, gesture_result.index_tip, 30, color, 2)

        # ── FPS counter ──────────────────────────────────────────────────────
        cv2.putText(out, f"FPS: {fps:.1f}",
                    (out.shape[1] - 130, out.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (180, 180, 180), 1, cv2.LINE_AA)

        # ── status message ───────────────────────────────────────────────────
        if self._status_timeout > 0:
            cv2.putText(out, self._status_msg,
                        (10, TOOLBAR_HEIGHT + 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                        (0, 255, 255), 2, cv2.LINE_AA)
            self._status_timeout -= 1

        return out

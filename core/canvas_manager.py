# core/canvas_manager.py
"""
Manages the transparent drawing canvas that is alpha-blended over the camera frame.
"""

from __future__ import annotations
from typing import Optional

import cv2
import numpy as np

from config import (
    DRAW_COLOR,
    DRAW_THICKNESS,
    ERASER_RADIUS,
    CANVAS_BG_COLOR,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    TOOLBAR_HEIGHT,
)


class CanvasManager:
    """
    Off-screen BGRA canvas.
    Drawing methods accept pixel-space (x, y) coordinates.
    """

    def __init__(self, width: int = FRAME_WIDTH, height: int = FRAME_HEIGHT) -> None:
        self.width  = width
        self.height = height
        self._canvas: np.ndarray = np.zeros((height, width, 3), dtype=np.uint8)
        self._prev_point: Optional[tuple[int, int]] = None
        self.draw_color: tuple[int, int, int] = DRAW_COLOR
        self.thickness: int = DRAW_THICKNESS

    # ── public API ───────────────────────────────────────────────────────────

    def draw(self, point: tuple[int, int]) -> None:
        """Draw a line segment from the last known point to *point*."""
        if self._in_toolbar(point):
            self._prev_point = None
            return
        if self._prev_point is not None:
            cv2.line(self._canvas, self._prev_point, point,
                     self.draw_color, self.thickness, lineType=cv2.LINE_AA)
        else:
            # First point: draw a circle so single taps are visible
            cv2.circle(self._canvas, point, self.thickness // 2,
                       self.draw_color, -1, lineType=cv2.LINE_AA)
        self._prev_point = point

    def erase(self, point: tuple[int, int]) -> None:
        """Erase a circular area around *point*."""
        if self._in_toolbar(point):
            self._prev_point = None
            return
        cv2.circle(self._canvas, point, ERASER_RADIUS,
                   CANVAS_BG_COLOR, -1, lineType=cv2.LINE_AA)
        self._prev_point = None   # erasing doesn't leave a trail

    def release_stroke(self) -> None:
        """Call when the drawing gesture ends to break the stroke."""
        self._prev_point = None

    def clear(self) -> None:
        """Wipe the entire canvas."""
        self._canvas[:] = 0
        self._prev_point = None

    def blend(self, frame: np.ndarray) -> np.ndarray:
        """
        Alpha-blend the canvas over *frame*.
        Canvas pixels that are black (background) are treated as transparent.
        Returns a new BGR frame.
        """
        mask = cv2.cvtColor(self._canvas, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(mask, 1, 255, cv2.THRESH_BINARY)
        inv_mask = cv2.bitwise_not(mask)

        bg = cv2.bitwise_and(frame, frame, mask=inv_mask)
        fg = cv2.bitwise_and(self._canvas, self._canvas, mask=mask)
        return cv2.add(bg, fg)

    @property
    def canvas_image(self) -> np.ndarray:
        """Return a copy of the raw canvas (for OCR export)."""
        return self._canvas.copy()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _in_toolbar(self, point: tuple[int, int]) -> bool:
        return point[1] < TOOLBAR_HEIGHT

# ui/toolbar.py
"""
Defines the toolbar buttons rendered at the top of the frame.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np

from config import (
    TOOLBAR_HEIGHT,
    BUTTON_COLOR,
    BUTTON_HOVER_COLOR,
    BUTTON_TEXT_COLOR,
    FONT_SCALE,
    FONT_THICKNESS,
)


@dataclass
class Button:
    label: str
    x: int          # left edge (pixels)
    width: int
    callback: Callable[[], None]
    color: tuple[int, int, int] = BUTTON_COLOR

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """(x1, y1, x2, y2)"""
        return (self.x, 0, self.x + self.width, TOOLBAR_HEIGHT)

    def hit(self, px: int, py: int) -> bool:
        x1, y1, x2, y2 = self.rect
        return x1 <= px <= x2 and y1 <= py <= y2


class Toolbar:
    """Renders a row of buttons and dispatches hover / click events."""

    _BUTTONS_DEF = [
        ("Save",  120, (50, 180, 80)),
        ("Clear", 120, (180, 50, 50)),
        ("Read",  120, (50, 80, 180)),
        ("Speak", 120, (160, 50, 200)),   # purple/violet
    ]
    _PADDING = 10

    def __init__(self) -> None:
        self._buttons: list[Button] = []
        self._callbacks: dict[str, Callable[[], None]] = {
            "Save":  lambda: None,
            "Clear": lambda: None,
            "Read":  lambda: None,
            "Speak": lambda: None,
        }

    # ── public ───────────────────────────────────────────────────────────────

    def set_callback(self, label: str, fn: Callable[[], None]) -> None:
        self._callbacks[label] = fn

    def build(self, frame_width: int) -> None:
        """Build button list (call once after frame size is known)."""
        self._buttons = []
        x = self._PADDING
        for label, w, color in self._BUTTONS_DEF:
            self._buttons.append(Button(
                label=label, x=x, width=w,
                callback=self._callbacks.get(label, lambda: None),
                color=color,
            ))
            x += w + self._PADDING

    def render(self, frame: np.ndarray,
               hover_point: Optional[tuple[int, int]] = None) -> np.ndarray:
        """Draw toolbar onto *frame* (in-place). Returns the frame."""
        # Dark toolbar background
        cv2.rectangle(frame, (0, 0), (frame.shape[1], TOOLBAR_HEIGHT),
                      (30, 30, 30), -1)
        for btn in self._buttons:
            x1, y1, x2, y2 = btn.rect
            is_hover = hover_point is not None and btn.hit(*hover_point)
            color = BUTTON_HOVER_COLOR if is_hover else btn.color
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4), color, -1)
            cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y2 - 4),
                          (200, 200, 200), 1)
            # Center text
            (tw, th), _ = cv2.getTextSize(btn.label, cv2.FONT_HERSHEY_SIMPLEX,
                                          FONT_SCALE, FONT_THICKNESS)
            tx = x1 + (btn.width - tw) // 2
            ty = y1 + (TOOLBAR_HEIGHT + th) // 2
            cv2.putText(frame, btn.label, (tx, ty),
                        cv2.FONT_HERSHEY_SIMPLEX, FONT_SCALE,
                        BUTTON_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
        return frame

    def check_click(self, point: tuple[int, int]) -> bool:
        """Fire callback if *point* falls inside a button. Returns True if fired."""
        for btn in self._buttons:
            if btn.hit(*point):
                btn.callback()
                return True
        return False

# core/gesture_classifier.py
"""
Gesture classification from MediaPipe landmark data.

Gestures recognised
───────────────────
  DRAW    – only index finger extended
  ERASE   – index + middle fingers extended (peace sign)
  SELECT  – closed fist (no fingers extended)
  SCROLL  – all five fingers extended (open palm)
  IDLE    – anything else / no hand detected
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import mediapipe as mp

from config import FINGER_STRAIGHT_THRESHOLD


class Gesture(Enum):
    IDLE   = auto()
    DRAW   = auto()   # 1 finger  → draw
    ERASE  = auto()   # 2 fingers → erase
    SELECT = auto()   # fist      → confirm / select
    SCROLL = auto()   # open palm → pan / scroll


@dataclass
class GestureResult:
    gesture: Gesture
    index_tip: Optional[tuple[int, int]] = None   # pixel coords (x, y)
    confidence: float = 1.0


# MediaPipe landmark indices
_TIP_IDS    = [4, 8, 12, 16, 20]   # thumb, index, middle, ring, pinky tips
_PIP_IDS    = [3, 6, 10, 14, 18]   # corresponding PIP joints


def _fingers_up(hand_landmarks, image_width: int, image_height: int) -> list[bool]:
    """Return [thumb, index, middle, ring, pinky] booleans for extended fingers."""
    lm = hand_landmarks.landmark
    up = []

    # Thumb: compare x instead of y (works for both hands roughly)
    if lm[_TIP_IDS[0]].x < lm[_PIP_IDS[0]].x:
        up.append(True)
    else:
        up.append(False)

    # Other four fingers: tip y < pip y means the finger points upward
    for tip, pip in zip(_TIP_IDS[1:], _PIP_IDS[1:]):
        up.append(lm[tip].y < lm[pip].y)

    return up


def classify(hand_landmarks, image_width: int, image_height: int) -> GestureResult:
    """Classify gesture and return a GestureResult with pixel-space index tip."""
    if hand_landmarks is None:
        return GestureResult(gesture=Gesture.IDLE)

    up = _fingers_up(hand_landmarks, image_width, image_height)
    # thumb, index, middle, ring, pinky
    extended_count = sum(up)

    lm = hand_landmarks.landmark
    ix = int(lm[8].x * image_width)
    iy = int(lm[8].y * image_height)
    index_tip = (ix, iy)

    if extended_count == 5:
        gesture = Gesture.SCROLL
    elif not any(up):
        gesture = Gesture.SELECT
    elif up[1] and not up[2] and not up[3] and not up[4]:
        gesture = Gesture.DRAW
    elif up[1] and up[2] and not up[3] and not up[4]:
        gesture = Gesture.ERASE
    else:
        gesture = Gesture.IDLE

    return GestureResult(gesture=gesture, index_tip=index_tip)

# core/hand_tracker.py
"""
Wraps MediaPipe Hands to detect hand landmarks from an OpenCV BGR frame.
Returns landmarks + a drawn annotated frame.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

from config import (
    MP_MAX_HANDS,
    MP_MIN_DETECTION_CONF,
    MP_MIN_TRACKING_CONF,
    FRAME_WIDTH,
    FRAME_HEIGHT,
)


@dataclass
class HandTrackResult:
    frame: np.ndarray                    # annotated frame (BGR)
    hand_landmarks: Optional[object] = None   # first hand landmarks or None
    multi_hand_landmarks: list = field(default_factory=list)


class HandTracker:
    """Stateful hand tracker using MediaPipe Hands."""

    def __init__(self) -> None:
        self._mp_hands = mp.solutions.hands
        self._mp_draw  = mp.solutions.drawing_utils
        self._mp_style = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MP_MAX_HANDS,
            min_detection_confidence=MP_MIN_DETECTION_CONF,
            min_tracking_confidence=MP_MIN_TRACKING_CONF,
        )

    # ── public ───────────────────────────────────────────────────────────────

    def process(self, bgr_frame: np.ndarray) -> HandTrackResult:
        """
        Process a single BGR frame.
        Returns annotated frame + landmark data.
        """
        h, w = bgr_frame.shape[:2]
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True
        annotated = bgr_frame.copy()

        multi = results.multi_hand_landmarks or []
        for hand_lm in multi:
            self._mp_draw.draw_landmarks(
                annotated,
                hand_lm,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_style.get_default_hand_landmarks_style(),
                self._mp_style.get_default_hand_connections_style(),
            )

        first = multi[0] if multi else None
        return HandTrackResult(
            frame=annotated,
            hand_landmarks=first,
            multi_hand_landmarks=multi,
        )

    def release(self) -> None:
        self._hands.close()

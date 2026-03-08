# utils/obs_helper.py
"""
OBS Virtual Camera – setup notes and runtime helpers.

How to configure OBS for AirSign
──────────────────────────────────
1. Install OBS Studio (https://obsproject.com/).
2. Under Tools → VirtualCam, enable the virtual camera.
3. Add a Video Capture Device source and select your Kinect Xbox 360
   (requires the free KinectToVR driver on Windows).
4. Set the output resolution to 1280×720 @ 30 fps to match config.py.
5. In AirSign, set CAMERA_INDEX = 1 (or whichever index the virtual cam
   appears as) — run `list_cameras()` below to find it.

Driver links
────────────
• KSUtil / KinectToVR (Xbox 360 depth+colour):
    https://github.com/KinectToVR/KinectToVR
• OBS Virtual Camera plugin (built-in ≥ OBS 26):
    Tools → VirtualCam → Start
"""

from __future__ import annotations
import logging

import cv2

logger = logging.getLogger(__name__)


def list_cameras(max_index: int = 10) -> list[int]:
    """
    Probe camera indices 0…max_index and return those that open successfully.
    Useful for discovering the OBS Virtual Camera index.
    """
    available: list[int] = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            available.append(idx)
            logger.info("Camera index %d: available", idx)
            cap.release()
        else:
            logger.debug("Camera index %d: not available", idx)
    return available


def verify_capture(camera_index: int, width: int, height: int) -> bool:
    """
    Open the camera at *camera_index*, read one frame, and log its properties.
    Returns True if capture succeeds, False otherwise.
    """
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        logger.error("Cannot open camera index %d", camera_index)
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        logger.error("Camera %d opened but failed to grab a frame", camera_index)
        return False

    actual_h, actual_w = frame.shape[:2]
    logger.info(
        "Camera %d OK — frame size: %dx%d (requested %dx%d)",
        camera_index, actual_w, actual_h, width, height,
    )
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Scanning for cameras …")
    cams = list_cameras()
    print(f"Found cameras: {cams}")
    for c in cams:
        verify_capture(c, 1280, 720)

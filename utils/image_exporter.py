# utils/image_exporter.py
"""
Saves the drawing canvas as a PNG file with a timestamped filename.
"""

from __future__ import annotations
import os
import logging
from datetime import datetime

import cv2
import numpy as np

from config import EXPORT_DIR, EXPORT_PREFIX

# Fixed filename for the running OCR log
OCR_LOG_FILE = "recognized_text.txt"

logger = logging.getLogger(__name__)


def append_ocr_result(text: str) -> str:
    """
    Append *text* with a timestamp to exports/recognized_text.txt.

    Returns
    -------
    str  Absolute path of the log file, or empty string on failure.
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)
    filepath = os.path.join(EXPORT_DIR, OCR_LOG_FILE)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {text}\n"
    try:
        with open(filepath, "a", encoding="utf-8") as fh:
            fh.write(line)
        logger.info("OCR result appended → %s", filepath)
        return os.path.abspath(filepath)
    except Exception as exc:
        logger.error("Failed to write OCR log: %s", exc)
        return ""


def save_canvas(canvas_bgr: np.ndarray) -> str:
    """
    Write *canvas_bgr* to disk.

    Returns
    -------
    str  Absolute path of the saved file, or empty string on failure.
    """
    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{EXPORT_PREFIX}_{timestamp}.png"
    filepath  = os.path.join(EXPORT_DIR, filename)
    try:
        cv2.imwrite(filepath, canvas_bgr)
        logger.info("Canvas saved → %s", filepath)
        return os.path.abspath(filepath)
    except Exception as exc:
        logger.error("Failed to save canvas: %s", exc)
        return ""

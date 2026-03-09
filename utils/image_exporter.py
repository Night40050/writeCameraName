# utils/image_exporter.py
"""
Saves drawing canvases (PNG) and OCR results (TXT) to the exports/ folder
located at the project root (airsign/exports/).

All paths are resolved relative to this file's location so the app works
correctly regardless of the working directory from which it is launched.
"""

from __future__ import annotations
import os
import logging
from datetime import datetime

import cv2
import numpy as np

from config import EXPORT_PREFIX

logger = logging.getLogger(__name__)

# ── paths ────────────────────────────────────────────────────────────────────
# Project root = the directory that contains this utils/ package
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EXPORT_DIR    = os.path.join(_PROJECT_ROOT, "exports")
OCR_LOG_FILE  = os.path.join(EXPORT_DIR, "recognized_text.txt")


def _ensure_export_dir() -> None:
    """Create airsign/exports/ if it does not exist."""
    os.makedirs(EXPORT_DIR, exist_ok=True)


# ── public API ────────────────────────────────────────────────────────────────

def save_canvas(canvas_bgr: np.ndarray) -> str:
    """
    Write *canvas_bgr* (raw hand-drawn strokes, black background) to a
    timestamped PNG inside airsign/exports/.

    Filename format: airsign_canvas_YYYYMMDD_HHMMSS.png

    Returns
    -------
    str  Absolute path of the saved PNG, or empty string on failure.
    """
    _ensure_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"{EXPORT_PREFIX}_{timestamp}.png"
    filepath  = os.path.join(EXPORT_DIR, filename)
    try:
        cv2.imwrite(filepath, canvas_bgr)
        abs_path = os.path.abspath(filepath)
        print(f"[EXPORT] Canvas PNG saved → {abs_path}")
        logger.info("Canvas saved → %s", abs_path)
        return abs_path
    except Exception as exc:
        logger.error("Failed to save canvas PNG: %s", exc)
        return ""


def export_canvas(canvas_bgr: np.ndarray) -> str:
    """
    Convenience wrapper — identical to `save_canvas` but returns only the
    bare filename (e.g. ``airsign_canvas_20250307_210311.png``) so callers
    can display it in the OpenCV window without a long path string.

    Returns empty string on failure.
    """
    abs_path = save_canvas(canvas_bgr)
    if not abs_path:
        return ""
    return os.path.basename(abs_path)


def append_ocr_result(text: str) -> str:
    """
    Append *text* with a timestamp to airsign/exports/recognized_text.txt.

    Returns
    -------
    str  Absolute path of the log file, or empty string on failure.
    """
    _ensure_export_dir()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line      = f"[{timestamp}] {text}\n"
    abs_path  = os.path.abspath(OCR_LOG_FILE)
    try:
        with open(OCR_LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(line)
        print(f"[EXPORT] OCR result appended → {abs_path}")
        logger.info("OCR result appended → %s", abs_path)
        return abs_path
    except Exception as exc:
        logger.error("Failed to write OCR log: %s", exc)
        return ""

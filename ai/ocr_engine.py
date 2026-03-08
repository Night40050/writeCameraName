# ai/ocr_engine.py
"""
TrOCR-based OCR engine.
Converts a NumPy canvas image (BGR) to a recognised text string.

Pre-processing pipeline (required for hand-drawn white-on-black canvas):
  1. Convert BGR → Grayscale
  2. Binary threshold to isolate strokes
  3. Invert so strokes are BLACK on WHITE (TrOCR expects dark ink on light bg)
  4. Add white padding around the content area
  5. Resize to a reasonable height while preserving aspect ratio

Model is lazily loaded on first call to avoid startup overhead.
"""

from __future__ import annotations
import logging
from typing import Optional

import cv2
import numpy as np

from config import TROCR_MODEL

logger = logging.getLogger(__name__)

# Fallback returned when OCR produces nothing useful
OCR_FALLBACK = "Could not read text"


class OCREngine:
    """Wraps microsoft/trocr-base-handwritten for single-image inference."""

    def __init__(self) -> None:
        self._processor = None
        self._model     = None
        self._ready     = False

    # ── public ───────────────────────────────────────────────────────────────

    def load(self) -> None:
        """Explicitly load model weights (blocks until done)."""
        if self._ready:
            return
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            logger.info("Loading TrOCR model: %s …", TROCR_MODEL)
            self._processor = TrOCRProcessor.from_pretrained(TROCR_MODEL)
            self._model     = VisionEncoderDecoderModel.from_pretrained(TROCR_MODEL)
            self._ready = True
            logger.info("TrOCR model ready.")
        except Exception as exc:
            logger.error("Failed to load TrOCR model: %s", exc)
            raise

    def recognise(self, canvas_bgr: np.ndarray) -> str:
        """
        Pre-process *canvas_bgr* and run TrOCR inference.

        Parameters
        ----------
        canvas_bgr : np.ndarray  BGR canvas image (H×W×3), white strokes on black.

        Returns
        -------
        str  Recognised text (stripped), or OCR_FALLBACK if nothing useful found.
        """
        if not self._ready:
            self.load()

        # ── debug: log raw canvas stats ──────────────────────────────────────
        nonzero_px = int(np.count_nonzero(cv2.cvtColor(canvas_bgr, cv2.COLOR_BGR2GRAY)))
        print(f"[OCR DEBUG] Canvas non-zero pixels: {nonzero_px} / "
              f"{canvas_bgr.shape[0] * canvas_bgr.shape[1]}")

        # ── pre-processing ───────────────────────────────────────────────────
        prepared = self._preprocess(canvas_bgr)
        if prepared is None:
            print("[OCR DEBUG] Canvas appears empty – skipping inference.")
            return OCR_FALLBACK

        # ── inference ────────────────────────────────────────────────────────
        from PIL import Image
        pil_img = Image.fromarray(prepared).convert("RGB")

        try:
            pixel_values = self._processor(
                images=pil_img, return_tensors="pt"
            ).pixel_values
            generated_ids = self._model.generate(pixel_values)
            text = self._processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )[0].strip()
        except Exception as exc:
            logger.error("OCR inference error: %s", exc)
            return OCR_FALLBACK

        print(f"[OCR DEBUG] Raw TrOCR result: {text!r}")

        # ── fallback guard ───────────────────────────────────────────────────
        if len(text) < 2:
            return OCR_FALLBACK

        return text

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── private ──────────────────────────────────────────────────────────────

    @staticmethod
    def _preprocess(canvas_bgr: np.ndarray,
                    padding: int = 20,
                    target_height: int = 128) -> Optional[np.ndarray]:
        """
        Convert a white-on-black canvas to a black-on-white image suitable
        for TrOCR, with padding.

        Returns None if the canvas contains no visible strokes.
        """
        # Step 1 – grayscale
        gray = cv2.cvtColor(canvas_bgr, cv2.COLOR_BGR2GRAY)

        # Step 2 – binary threshold (strokes are bright)
        _, binary = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)

        # Step 3 – check canvas is not empty
        if cv2.countNonZero(binary) < 50:
            return None

        # Step 4 – invert: black strokes on white background
        inverted = cv2.bitwise_not(binary)

        # Step 5 – crop to bounding box of strokes (remove large white margins)
        coords = cv2.findNonZero(binary)          # non-zero = stroke pixels
        x, y, w, h = cv2.boundingRect(coords)
        cropped = inverted[y:y + h, x:x + w]

        # Step 6 – add white padding
        padded = cv2.copyMakeBorder(
            cropped, padding, padding, padding, padding,
            cv2.BORDER_CONSTANT, value=255,
        )

        # Step 7 – resize to target height, keep aspect ratio
        orig_h, orig_w = padded.shape[:2]
        scale  = target_height / orig_h
        new_w  = max(1, int(orig_w * scale))
        resized = cv2.resize(padded, (new_w, target_height),
                             interpolation=cv2.INTER_AREA)

        # Return as 3-channel (RGB-compatible) image
        return cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)

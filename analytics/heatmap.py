"""
analytics/heatmap.py
---------------------
Generates a real-time vehicle density heatmap overlay.
Uses a Gaussian blur on centroid positions to create
a smooth heat effect over the video frame.
"""

import cv2
import numpy as np
from typing import List, Tuple
import config
from core.detector import Detection


class HeatmapOverlay:
    def __init__(self, frame_shape: Tuple[int, int]):
        """
        frame_shape: (height, width)
        """
        self.h, self.w = frame_shape
        self._accumulator = np.zeros((self.h, self.w), dtype=np.float32)
        self._decay = 0.92    # per-frame decay factor (< 1 → trails fade)
        self._colormap = cv2.COLORMAP_JET

    # ──────────────────────────────────────────────
    def update(self, detections: List[Detection]) -> np.ndarray:
        """
        Add current detections to accumulator, decay old ones.
        Returns nothing (call render() to get the overlay).
        """
        self._accumulator *= self._decay

        for d in detections:
            cx, cy = d.centroid
            if 0 <= cx < self.w and 0 <= cy < self.h:
                self._accumulator[cy, cx] += 1.0

    def render(self, frame: np.ndarray) -> np.ndarray:
        """
        Blend the heatmap onto the frame and return the result.
        """
        # Blur accumulator for smooth heatmap
        blurred = cv2.GaussianBlur(self._accumulator, (51, 51), 0)

        # Normalize to 0-255
        norm = cv2.normalize(blurred, None, 0, 255, cv2.NORM_MINMAX)
        heat_uint8 = norm.astype(np.uint8)

        # Apply colormap
        heatmap_color = cv2.applyColorMap(heat_uint8, self._colormap)

        # Blend with original frame
        alpha = config.HEATMAP_ALPHA
        result = cv2.addWeighted(frame, 1.0 - alpha, heatmap_color, alpha, 0)
        return result

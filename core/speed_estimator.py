"""
core/speed_estimator.py
-----------------------
Perspective-corrected speed estimation.

Method (from SimJam ComputerVision):
  - Two horizontal calibration lines at known pixel rows, representing
    a known real-world distance (e.g. 10 m road marking gap).
  - Track centroid history. When a track crosses both lines,
    compute pixels/frame → m/s → km/h.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import config
from core.detector import Detection


class SpeedEstimator:
    def __init__(self, fps: float = 30.0):
        self.fps = fps
        # pixels per metre (calibrated from two lines)
        line_pixel_gap = abs(config.SPEED_CALIB_LINE_2_Y - config.SPEED_CALIB_LINE_1_Y)
        self._ppm = line_pixel_gap / config.SPEED_CALIB_DISTANCE_M   # px / m

        # Per-track state
        self._cross_time: Dict[int, Dict[int, float]] = defaultdict(dict)
        # key: track_id → {line_id: timestamp}

        self._speeds: Dict[int, float] = {}   # track_id → latest speed km/h
        self._history: Dict[int, List[Tuple[int, int]]] = defaultdict(list)

        self.line1_y = min(config.SPEED_CALIB_LINE_1_Y, config.SPEED_CALIB_LINE_2_Y)
        self.line2_y = max(config.SPEED_CALIB_LINE_1_Y, config.SPEED_CALIB_LINE_2_Y)

    # ──────────────────────────────────────────────
    def update(self, detections: List[Detection]) -> Dict[int, float]:
        now = time.time()
        for d in detections:
            tid = d.track_id
            cy  = d.centroid[1]
            prev_positions = self._history[tid]

            # Store centroid
            prev_positions.append((d.centroid[0], cy))
            if len(prev_positions) > 5:
                prev_positions.pop(0)

            # Line crossing check
            if len(prev_positions) >= 2:
                prev_y = prev_positions[-2][1]
                if self._crossed(prev_y, cy, self.line1_y):
                    self._cross_time[tid][1] = now
                if self._crossed(prev_y, cy, self.line2_y):
                    self._cross_time[tid][2] = now

            # Compute speed if both crossings recorded
            if 1 in self._cross_time[tid] and 2 in self._cross_time[tid]:
                t1 = self._cross_time[tid][1]
                t2 = self._cross_time[tid][2]
                dt = abs(t2 - t1)
                if 0.1 < dt < 30:   # sanity check
                    speed_ms  = config.SPEED_CALIB_DISTANCE_M / dt
                    speed_kmh = speed_ms * 3.6
                    self._speeds[tid] = round(speed_kmh, 1)
                # Reset after calculation
                self._cross_time[tid] = {}

        return self._speeds

    def get_speed(self, track_id: int) -> Optional[float]:
        return self._speeds.get(track_id)

    @staticmethod
    def _crossed(y_prev: int, y_curr: int, line_y: int) -> bool:
        return (y_prev < line_y <= y_curr) or (y_curr < line_y <= y_prev)

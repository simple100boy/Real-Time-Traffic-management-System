"""
core/zone_manager.py
--------------------
Manages ROI zones and counting lines.
Determines which lane each detection belongs to.
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import config
from core.detector import Detection


class ZoneManager:
    def __init__(self):
        # Convert polygon lists to numpy arrays
        self.zones: Dict[str, np.ndarray] = {
            name: np.array(pts, dtype=np.int32)
            for name, pts in config.LANE_ZONES.items()
        }
        self.count_lines = config.COUNT_LINES

        # Per-lane vehicle counts (cumulative since start)
        self.cumulative_counts: Dict[str, int] = {name: 0 for name in self.zones}
        # Per-lane current occupancy (vehicles inside zone right now)
        self.occupancy: Dict[str, int]  = {name: 0 for name in self.zones}

        # Track → last known zone (to detect crossings)
        self._track_zone: Dict[int, Optional[str]] = {}
        # Track → last side of counting line
        self._track_line_side: Dict[str, Dict[int, int]] = {
            name: {} for name in self.zones
        }

    # ──────────────────────────────────────────────
    def update(self, detections: List[Detection]) -> Dict[str, int]:
        """
        Returns dict {lane_name: vehicle_count_in_zone}.
        Also increments cumulative counts when a track crosses counting line.
        """
        new_occupancy: Dict[str, int] = {name: 0 for name in self.zones}

        for d in detections:
            for name, poly in self.zones.items():
                pt = np.array(d.centroid)
                inside = cv2.pointPolygonTest(poly, (float(pt[0]), float(pt[1])), False) >= 0
                if inside:
                    new_occupancy[name] += 1
                    self._check_line_crossing(name, d)

        self.occupancy = new_occupancy
        return new_occupancy

    def _check_line_crossing(self, lane: str, d: Detection):
        if lane not in self.count_lines:
            return
        orientation, threshold = self.count_lines[lane]
        tid = d.track_id
        cx, cy = d.centroid

        if orientation == "horizontal":
            side = 1 if cy > threshold else -1
        else:
            side = 1 if cx > threshold else -1

        prev_side = self._track_line_side[lane].get(tid)
        if prev_side is not None and prev_side != side:
            self.cumulative_counts[lane] += 1
        self._track_line_side[lane][tid] = side

    # ──────────────────────────────────────────────
    def draw_zones(self, frame: np.ndarray,
                   signal_states: Optional[Dict[str, str]] = None) -> np.ndarray:
        overlay = frame.copy()
        state_colors = {
            "GREEN":  (0, 220, 80),
            "YELLOW": (0, 200, 255),
            "RED":    (0, 50, 220),
            "ALL_RED":(100, 100, 100),
        }

        for name, poly in self.zones.items():
            state = (signal_states or {}).get(name, "RED")
            color = state_colors.get(state, (120, 120, 120))

            cv2.fillPoly(overlay, [poly], color)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            overlay = frame.copy()

            cv2.polylines(frame, [poly], True, color, 2)

            # Zone label
            M = cv2.moments(poly)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                label = f"{name}: {self.occupancy.get(name, 0)}"
                cv2.putText(frame, label, (cx - 40, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Draw counting lines
        h, w = frame.shape[:2]
        for lane, (orientation, threshold) in self.count_lines.items():
            if orientation == "horizontal":
                cv2.line(frame, (0, threshold), (w, threshold), (255, 200, 0), 1)
            else:
                cv2.line(frame, (threshold, 0), (threshold, h), (255, 200, 0), 1)

        return frame

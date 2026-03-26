"""
signal_control/emergency_handler.py
-------------------------------------
Detects emergency vehicles (large fast-moving vehicles)
and triggers signal preemption.

Heuristic approach (no re-training needed):
  - Large bounding box area (bus/truck class)
  - High speed (> SPEED_LIMIT * 1.5)
  - In a specific zone

For production: replace with a fine-tuned YOLO class
or siren audio detection.
"""

from typing import Dict, List, Optional
import config
from core.detector import Detection
from core.speed_estimator import SpeedEstimator
from core.zone_manager import ZoneManager


class EmergencyHandler:
    SPEED_MULTIPLIER = 1.5   # x speed limit to flag as emergency
    MIN_BOX_AREA = 10_000    # minimum bbox area (px²)

    def __init__(self, zone_manager: ZoneManager, speed_estimator: SpeedEstimator):
        self.zm = zone_manager
        self.se = speed_estimator
        self._flagged: set = set()   # already-handled track IDs

    def check(self, detections: List[Detection]) -> Optional[str]:
        """
        Returns lane name if an emergency vehicle is detected, else None.
        """
        for d in detections:
            if d.class_id not in config.EMERGENCY_CLASSES:
                continue
            if d.track_id in self._flagged:
                continue

            # Check size
            x1, y1, x2, y2 = d.bbox
            area = (x2 - x1) * (y2 - y1)
            if area < self.MIN_BOX_AREA:
                continue

            # Check speed
            speed = self.se.get_speed(d.track_id)
            if speed is None:
                continue
            if speed < config.SPEED_LIMIT_KMPH * self.SPEED_MULTIPLIER:
                continue

            # Find which zone
            for lane in self.zm.zones:
                occ = self.zm.occupancy.get(lane, 0)
                if occ > 5:
                    self._flagged.add(d.track_id)
                    print(f"[Emergency] 🚨 Vehicle #{d.track_id} ({d.class_name}) "
                          f"@ {speed:.0f} km/h detected in {lane}")
                    return lane

        return None

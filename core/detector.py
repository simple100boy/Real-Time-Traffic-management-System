"""
core/detector.py
----------------
YOLOv8 vehicle detector with ByteTrack tracking.
Returns per-frame detections with stable track IDs.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import config


@dataclass
class Detection:
    track_id:   int
    class_id:   int
    class_name: str
    bbox:       Tuple[int, int, int, int]   # x1, y1, x2, y2
    confidence: float
    centroid:   Tuple[int, int]
    frame_no:   int


class VehicleDetector:
    """
    Wraps YOLOv8 + ByteTrack.
    Call .detect(frame) each frame → list[Detection]
    """

    def __init__(self):
        print(f"[Detector] Loading model: {config.YOLO_MODEL}")
        self.model = YOLO(config.YOLO_MODEL)
        self.target_classes = list(config.VEHICLE_CLASSES.keys())
        self._frame_no = 0

    # ──────────────────────────────────────────────
    def detect(self, frame: np.ndarray) -> List[Detection]:
        self._frame_no += 1
        results = self.model.track(
            frame,
            persist=True,
            classes=self.target_classes,
            conf=config.YOLO_CONFIDENCE,
            iou=config.YOLO_IOU,
            tracker="bytetrack.yaml",
            verbose=False,
        )

        detections: List[Detection] = []
        if results[0].boxes is None:
            return detections

        boxes = results[0].boxes
        for box in boxes:
            if box.id is None:
                continue
            track_id   = int(box.id.item())
            class_id   = int(box.cls.item())
            confidence = float(box.conf.item())
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            class_name = config.VEHICLE_CLASSES.get(class_id, "unknown")

            detections.append(Detection(
                track_id=track_id,
                class_id=class_id,
                class_name=class_name,
                bbox=(x1, y1, x2, y2),
                confidence=confidence,
                centroid=(cx, cy),
                frame_no=self._frame_no,
            ))

        return detections

    # ──────────────────────────────────────────────
    def draw(self, frame: np.ndarray, detections: List[Detection],
             speed_map: Optional[Dict[int, float]] = None) -> np.ndarray:
        """Draw bounding boxes and labels on frame."""
        for d in detections:
            x1, y1, x2, y2 = d.bbox
            color = self._class_color(d.class_id)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            speed_str = ""
            if speed_map and d.track_id in speed_map:
                spd = speed_map[d.track_id]
                speed_str = f" {spd:.0f}km/h"
                if spd > config.SPEED_LIMIT_KMPH:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

            label = f"#{d.track_id} {d.class_name}{speed_str}"
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - lh - 6), (x1 + lw + 4, y1), color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.circle(frame, d.centroid, 3, color, -1)
        return frame

    @staticmethod
    def _class_color(class_id: int) -> Tuple[int, int, int]:
        palette = {
            0: (255, 165, 0),   # person  — orange
            2: (0, 200, 255),   # car     — cyan
            3: (0, 255, 100),   # moto    — green
            5: (200, 100, 255), # bus     — purple
            7: (255, 80, 80),   # truck   — red
        }
        return palette.get(class_id, (200, 200, 200))

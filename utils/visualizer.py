"""
utils/visualizer.py
--------------------
OpenCV drawing helpers for the main video window.
"""

import cv2
import numpy as np
from typing import Dict
import config


def draw_signal_hud(frame: np.ndarray, signal_states: Dict[str, str]) -> np.ndarray:
    """Draw a compact HUD showing all signal states."""
    colors = {
        "GREEN":   (0, 220, 80),
        "YELLOW":  (0, 200, 255),
        "RED":     (0, 50, 220),
        "ALL_RED": (120, 120, 120),
    }
    x, y = 10, 10
    for lane, state in signal_states.items():
        col = colors.get(state, (200, 200, 200))
        cv2.rectangle(frame, (x, y), (x + 160, y + 26), (20, 20, 30), -1)
        cv2.rectangle(frame, (x, y), (x + 160, y + 26), col, 1)
        cv2.putText(frame, f"{lane}: {state}", (x + 6, y + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 1)
        y += 32
    return frame


def draw_speed_lines(frame: np.ndarray) -> np.ndarray:
    """Draw calibration lines."""
    h, w = frame.shape[:2]
    cv2.line(frame, (0, config.SPEED_CALIB_LINE_1_Y), (w, config.SPEED_CALIB_LINE_1_Y),
             (180, 180, 0), 1)
    cv2.line(frame, (0, config.SPEED_CALIB_LINE_2_Y), (w, config.SPEED_CALIB_LINE_2_Y),
             (180, 180, 0), 1)
    cv2.putText(frame, f"Calib: {config.SPEED_CALIB_DISTANCE_M}m",
                (6, config.SPEED_CALIB_LINE_1_Y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 0), 1)
    return frame


def draw_fps(frame: np.ndarray, fps: float) -> np.ndarray:
    h, w = frame.shape[:2]
    cv2.putText(frame, f"FPS: {fps:.1f}", (w - 110, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 200), 1)
    return frame


def draw_violation_alert(frame: np.ndarray, track_id: int, speed: float) -> np.ndarray:
    h, w = frame.shape[:2]
    msg = f"SPEED ALERT  #{track_id}  {speed:.0f} km/h"
    cv2.rectangle(frame, (0, h - 40), (w, h), (0, 0, 180), -1)
    cv2.putText(frame, msg, (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    return frame

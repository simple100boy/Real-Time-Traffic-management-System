"""
analytics/csv_exporter.py
--------------------------
Exports KPI snapshots to CSV (SimJam-inspired planning export).

Files:
  data/logs/traffic_summary_YYYYMMDD_HHMMSS.csv   — one row per snapshot per lane
  data/logs/speed_violations_YYYYMMDD_HHMMSS.csv  — speed exceedances
"""

import os
import csv
import time
from typing import Any, Dict, List
import config


class CSVExporter:
    def __init__(self):
        os.makedirs(config.CSV_OUTPUT_DIR, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._summary_path    = os.path.join(config.CSV_OUTPUT_DIR, f"traffic_summary_{ts}.csv")
        self._violations_path = os.path.join(config.CSV_OUTPUT_DIR, f"speed_violations_{ts}.csv")
        self._summary_written = False
        self._viol_written    = False

    # ──────────────────────────────────────────────
    def export_snapshot(self, snapshot: Dict[str, Any]):
        """Append one KPI snapshot (all lanes) to summary CSV."""
        rows = []
        for lane, kpis in snapshot.get("lanes", {}).items():
            row = {
                "timestamp":        snapshot["timestamp"],
                "lane":             lane,
                "flow_rate_vph":    kpis["flow_rate_vph"],
                "occupancy":        kpis["occupancy"],
                "avg_speed_kmph":   kpis.get("avg_speed_kmph", ""),
                "delay_est_s":      kpis["delay_est_s"],
                "los":              kpis["los"],
                "green_time_s":     kpis["green_time_s"],
                "cumulative_count": kpis["cumulative_count"],
            }
            rows.append(row)

        fieldnames = list(rows[0].keys()) if rows else []
        with open(self._summary_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not self._summary_written:
                writer.writeheader()
                self._summary_written = True
            writer.writerows(rows)

        print(f"[CSV] Saved snapshot → {self._summary_path}")

    # ──────────────────────────────────────────────
    def export_violation(self, track_id: int, lane: str, speed: float, class_name: str):
        """Log a speed violation."""
        row = {
            "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
            "track_id":   track_id,
            "lane":       lane,
            "class":      class_name,
            "speed_kmph": speed,
            "limit_kmph": config.SPEED_LIMIT_KMPH,
            "over_by":    round(speed - config.SPEED_LIMIT_KMPH, 1),
        }
        with open(self._violations_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not self._viol_written:
                writer.writeheader()
                self._viol_written = True
            writer.writerow(row)

    @property
    def summary_path(self):
        return self._summary_path

    @property
    def violations_path(self):
        return self._violations_path

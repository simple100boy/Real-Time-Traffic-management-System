"""
analytics/kpi_calculator.py
----------------------------
Traffic engineering KPIs (from SimJam ComputerVision approach):
  - Vehicle counts per lane
  - Flow rate (veh/hour)
  - Occupancy (%)
  - Average speed
  - Estimated delay per vehicle
  - Level of Service (LOS) A–F per HCM methodology

Called every ANALYTICS_INTERVAL_SEC to compute a snapshot.
"""

import time
from typing import Dict, Any
import config


class KPICalculator:
    def __init__(self, lane_names: list):
        self.lanes = lane_names
        self._start_time = time.time()
        self._interval_start = time.time()
        self._interval_counts: Dict[str, int]  = {l: 0 for l in lane_names}
        self._interval_speeds: Dict[str, list] = {l: [] for l in lane_names}
        self._history: list = []   # list of snapshots

    # ──────────────────────────────────────────────
    def record(self, lane: str, count_delta: int, speed: float = None):
        """Record incremental count and optional speed for a lane."""
        self._interval_counts[lane] = self._interval_counts.get(lane, 0) + count_delta
        if speed is not None and speed > 0:
            self._interval_speeds[lane].append(speed)

    def record_speeds_bulk(self, speed_map: Dict[int, float],
                            zone_occupancy: Dict[str, int],
                            zone_manager):
        """
        Given the full speed map and occupancy, record speeds
        per zone for the current interval.
        """
        # We approximate by using speed_map values for vehicles in each zone.
        # A more precise approach would map track_id → zone directly.
        for lane, count in zone_occupancy.items():
            if count > 0:
                # Collect any available speeds
                for spd in speed_map.values():
                    if 1 < spd < 200:   # sanity
                        self._interval_speeds[lane].append(spd)

    # ──────────────────────────────────────────────
    def compute_snapshot(self, zone_occupancy: Dict[str, int],
                          cumulative_counts: Dict[str, int],
                          signal_green_times: Dict[str, float]) -> Dict[str, Any]:
        """
        Compute one KPI snapshot and return it.
        Also appends to self._history.
        """
        now = time.time()
        elapsed = now - self._interval_start
        self._interval_start = now

        snapshot: Dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_s": round(elapsed, 1),
            "lanes": {},
        }

        total_flow = 0
        for lane in self.lanes:
            count_in_interval = self._interval_counts.get(lane, 0)
            occ  = zone_occupancy.get(lane, 0)
            speeds = self._interval_speeds.get(lane, [])
            avg_speed = sum(speeds) / len(speeds) if speeds else None
            green_t = signal_green_times.get(lane, config.DEFAULT_GREEN)

            # Flow rate: vehicles per hour
            flow_rate = (count_in_interval / elapsed) * 3600 if elapsed > 0 else 0
            total_flow += flow_rate

            # Estimated delay (simplified Webster's formula proxy)
            # delay ≈ (cycle - green) / 2  if flow > 0
            cycle = sum(signal_green_times.values()) + len(self.lanes) * (
                config.YELLOW_SECONDS + config.ALL_RED_SECONDS
            )
            delay_est = max(0, (cycle - green_t) / 2.0) if flow_rate > 0 else 0

            los = self._los(delay_est)
            cumulative = cumulative_counts.get(lane, 0)

            snapshot["lanes"][lane] = {
                "flow_rate_vph":    round(flow_rate, 1),
                "occupancy":        occ,
                "avg_speed_kmph":   round(avg_speed, 1) if avg_speed else None,
                "delay_est_s":      round(delay_est, 1),
                "los":              los,
                "green_time_s":     round(green_t, 1),
                "cumulative_count": cumulative,
            }

        snapshot["total_flow_vph"] = round(total_flow, 1)

        # Reset interval counters
        self._interval_counts = {l: 0 for l in self.lanes}
        self._interval_speeds = {l: [] for l in self.lanes}

        self._history.append(snapshot)
        return snapshot

    # ──────────────────────────────────────────────
    def get_history(self) -> list:
        return list(self._history)

    @staticmethod
    def _los(delay: float) -> str:
        for grade, (lo, hi) in config.LOS_THRESHOLDS.items():
            if lo <= delay < hi:
                return grade
        return "F"

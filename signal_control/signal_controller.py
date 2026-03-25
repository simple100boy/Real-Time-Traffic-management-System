"""
signal_control/signal_controller.py
-------------------------------------
Adaptive traffic signal controller.

Core idea (from FYP-ITMS):
  - Measure vehicle density per zone each cycle
  - Assign green time proportional to density
  - Constraints: MIN_GREEN ≤ green_time ≤ MAX_GREEN

Enhancements:
  - Multi-phase sequencing (not just 2-phase)
  - Emergency vehicle preemption hook
  - Outputs signal states dict for overlay and dashboard
"""

import time
import threading
from typing import Dict, Optional
import config


class SignalState:
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"
    ALL_RED = "ALL_RED"


class SignalController:
    def __init__(self, lane_names: list):
        self.lanes = lane_names
        self._states: Dict[str, str] = {lane: SignalState.RED for lane in lane_names}
        self._green_times: Dict[str, float] = {lane: config.DEFAULT_GREEN for lane in lane_names}
        self._current_green: Optional[str] = None
        self._phase_idx = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._emergency_lane: Optional[str] = None

    # ──────────────────────────────────────────────
    def start(self):
        """Start the signal cycling thread."""
        self._running = True
        self._thread = threading.Thread(target=self._cycle_loop, daemon=True)
        self._thread.start()
        print("[Signal] Controller started.")

    def stop(self):
        self._running = False

    # ──────────────────────────────────────────────
    def update_density(self, density: Dict[str, int]):
        """
        Called every frame with current zone occupancy.
        Recomputes green time allocations.
        """
        total = sum(density.values()) or 1
        for lane in self.lanes:
            count = density.get(lane, 0)
            ratio = count / total
            green = config.MIN_GREEN_SECONDS + ratio * (
                config.MAX_GREEN_SECONDS - config.MIN_GREEN_SECONDS
            )
            # Clamp
            green = max(config.MIN_GREEN_SECONDS, min(config.MAX_GREEN_SECONDS, green))
            with self._lock:
                self._green_times[lane] = green

    def trigger_emergency(self, lane: str):
        """Preempt current cycle for emergency vehicle."""
        print(f"[Signal] ⚠️  Emergency preemption → {lane}")
        with self._lock:
            self._emergency_lane = lane

    # ──────────────────────────────────────────────
    def get_states(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._states)

    def get_green_times(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._green_times)

    # ──────────────────────────────────────────────
    def _cycle_loop(self):
        """
        Main control loop running in background thread.
        Sequences through all lanes one by one.
        """
        while self._running:
            # Emergency check
            with self._lock:
                emergency = self._emergency_lane
                if emergency:
                    self._emergency_lane = None

            if emergency and emergency in self.lanes:
                self._serve_lane(emergency, override_time=config.MAX_GREEN_SECONDS)
            else:
                lane = self.lanes[self._phase_idx % len(self.lanes)]
                with self._lock:
                    green_t = self._green_times.get(lane, config.DEFAULT_GREEN)
                self._serve_lane(lane, override_time=green_t)
                self._phase_idx += 1

    def _serve_lane(self, lane: str, override_time: float):
        """Set one lane GREEN, others RED, then transition."""
        # All-red clearance
        with self._lock:
            for l in self.lanes:
                self._states[l] = SignalState.ALL_RED
        time.sleep(config.ALL_RED_SECONDS)

        # Go green
        with self._lock:
            for l in self.lanes:
                self._states[l] = SignalState.RED
            self._states[lane] = SignalState.GREEN
            self._current_green = lane

        time.sleep(override_time)

        # Yellow transition
        with self._lock:
            self._states[lane] = SignalState.YELLOW
        time.sleep(config.YELLOW_SECONDS)

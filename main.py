"""
main.py — SmartTrafficAI Entry Point
======================================
Combines:
  • YOLOv8 detection + tracking  (from FYP-ITMS)
  • Speed estimation + LOS KPIs  (from SimJam ComputerVision)
  • Adaptive signal control       (enhanced FYP-ITMS logic)
  • Emergency preemption          (new)
  • Real-time web dashboard       (new)
  • CSV export for planning       (from SimJam)

Usage:
  python main.py                  # full system
  python main.py --mode analytics # detection + analytics, no signal control
  python main.py --mode dashboard # only show dashboard (needs another instance running)
  python main.py --heatmap        # enable heatmap overlay (slower)
  python main.py --no-dashboard   # disable web dashboard
"""

import argparse
import sys
import time
import threading
import cv2

import config
from core.detector       import VehicleDetector
from core.speed_estimator import SpeedEstimator
from core.zone_manager   import ZoneManager
from signal_control.signal_controller import SignalController
from signal_control.emergency_handler  import EmergencyHandler
from analytics.kpi_calculator          import KPICalculator
from analytics.csv_exporter            import CSVExporter
from analytics.heatmap                 import HeatmapOverlay
from utils.visualizer import (draw_signal_hud, draw_speed_lines,
                               draw_fps, draw_violation_alert)
from utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="SmartTrafficAI")
    p.add_argument("--mode",         default="full",
                   choices=["full", "analytics", "dashboard"])
    p.add_argument("--heatmap",      action="store_true",
                   help="Enable heatmap overlay (CPU-intensive)")
    p.add_argument("--no-dashboard", action="store_true",
                   help="Disable web dashboard")
    p.add_argument("--source",       default=None,
                   help="Override VIDEO_SOURCE from config")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
def run_full(args):
    source = args.source if args.source else config.VIDEO_SOURCE

    # ── Open video ──────────────────────────────────────────────────────────
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        log("Main", f"Cannot open source: {source}", "ERR")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS) or config.FPS_TARGET
    log("Main", f"Source opened. FPS={actual_fps:.1f}", "OK")

    # ── Initialise modules ───────────────────────────────────────────────────
    detector  = VehicleDetector()
    speed_est = SpeedEstimator(fps=actual_fps)
    zone_mgr  = ZoneManager()
    kpi_calc  = KPICalculator(list(config.LANE_ZONES.keys()))
    csv_exp   = CSVExporter()
    heatmap   = HeatmapOverlay((config.FRAME_HEIGHT, config.FRAME_WIDTH)) if args.heatmap else None

    # Signal controller (only in 'full' mode)
    signal_ctrl = None
    emerg_handler = None
    if args.mode == "full":
        signal_ctrl = SignalController(list(config.LANE_ZONES.keys()))
        signal_ctrl.start()
        emerg_handler = EmergencyHandler(zone_mgr, speed_est)
        log("Main", "Signal controller started", "OK")

    # ── Dashboard ────────────────────────────────────────────────────────────
    push_update = lambda d: None   # no-op default
    if not args.no_dashboard and args.mode != "analytics":
        from dashboard.app import run_dashboard, push_update as _push
        push_update = _push
        t = threading.Thread(target=run_dashboard, daemon=True)
        t.start()
        log("Main", f"Dashboard → http://localhost:{config.DASHBOARD_PORT}", "OK")

    # ── Logging helpers ──────────────────────────────────────────────────────
    frame_count   = 0
    fps_counter   = 0
    fps_time      = time.time()
    current_fps   = 0.0
    last_kpi_time = time.time()
    violations_today = 0
    last_violation_frame = -999
    violation_tid = None
    violation_spd = 0.0

    log("Main", "Processing started. Press Q to quit.", "OK")
    log("Main", f"CSV → {csv_exp.summary_path}", "INFO")

    # ── Main loop ────────────────────────────────────────────────────────────
    while True:
        ret, frame = cap.read()
        if not ret:
            log("Main", "End of stream or read error.", "WARN")
            break

        frame_count += 1
        fps_counter  += 1

        # ── Detection & Tracking ────────────────────────────────────────────
        detections = detector.detect(frame)

        # ── Speed Estimation ────────────────────────────────────────────────
        speed_map = speed_est.update(detections)

        # ── Zone Occupancy ──────────────────────────────────────────────────
        occupancy = zone_mgr.update(detections)

        # ── Signal Adaptive Update ──────────────────────────────────────────
        signal_states = {}
        green_times   = {}
        if signal_ctrl:
            signal_ctrl.update_density(occupancy)
            signal_states = signal_ctrl.get_states()
            green_times   = signal_ctrl.get_green_times()

            # Emergency preemption
            if emerg_handler:
                emerg_lane = emerg_handler.check(detections)
                if emerg_lane:
                    signal_ctrl.trigger_emergency(emerg_lane)

        # ── Speed violations ────────────────────────────────────────────────
        for tid, spd in speed_map.items():
            if spd > config.SPEED_LIMIT_KMPH:
                # Find class name
                cls_name = next((d.class_name for d in detections if d.track_id == tid), "vehicle")
                # Find zone (approximate)
                zone = next(iter(occupancy.keys()), "Unknown")
                csv_exp.export_violation(tid, zone, spd, cls_name)
                violations_today += 1
                last_violation_frame = frame_count
                violation_tid = tid
                violation_spd = spd

        # ── KPI Snapshot ────────────────────────────────────────────────────
        now = time.time()
        latest_kpis = {}
        if now - last_kpi_time >= config.ANALYTICS_INTERVAL_SEC:
            last_kpi_time = now
            latest_kpis = kpi_calc.compute_snapshot(
                zone_occupancy    = occupancy,
                cumulative_counts = zone_mgr.cumulative_counts,
                signal_green_times= green_times or {l: config.DEFAULT_GREEN
                                                    for l in config.LANE_ZONES},
            )
            csv_exp.export_snapshot(latest_kpis)

        # ── FPS ─────────────────────────────────────────────────────────────
        if time.time() - fps_time >= 1.0:
            current_fps = fps_counter / (time.time() - fps_time)
            fps_counter = 0
            fps_time    = time.time()

        # ── Dashboard push ──────────────────────────────────────────────────
        if frame_count % 5 == 0:   # push every 5 frames to avoid flooding
            push_update({
                "signal_states":    signal_states,
                "green_times":      green_times,
                "zone_occupancy":   occupancy,
                "speed_map":        {str(k): v for k, v in speed_map.items()},
                "latest_kpis":      latest_kpis,
                "cumulative":       zone_mgr.cumulative_counts,
                "fps":              round(current_fps, 1),
                "frame_count":      frame_count,
                "violations_today": violations_today,
            })

        # ── Draw ─────────────────────────────────────────────────────────────
        if heatmap:
            heatmap.update(detections)
            frame = heatmap.render(frame)

        frame = zone_mgr.draw_zones(frame, signal_states)
        frame = detector.draw(frame, detections, speed_map)
        draw_speed_lines(frame)

        if signal_states:
            draw_signal_hud(frame, signal_states)

        draw_fps(frame, current_fps)

        # Show speed violation alert for a few frames
        if frame_count - last_violation_frame < 60 and violation_tid is not None:
            draw_violation_alert(frame, violation_tid, violation_spd)

        cv2.imshow("SmartTrafficAI", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            log("Main", "User quit.", "INFO")
            break

    # ── Cleanup ──────────────────────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    if signal_ctrl:
        signal_ctrl.stop()
    log("Main", f"Done. Reports saved to: {config.CSV_OUTPUT_DIR}", "OK")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()

    if args.mode == "dashboard":
        from dashboard.app import run_dashboard
        log("Main", f"Dashboard only → http://localhost:{config.DASHBOARD_PORT}", "OK")
        run_dashboard()
    else:
        run_full(args)

# 🚦 SmartTrafficAI — Intelligent Traffic Management & Analytics System

> **Combining the best of:**
> - [FYP-ITMS](https://github.com/FYP-ITMS/Intelligent-Traffic-Management-System-using-Machine-Learning) — YOLO-based adaptive signal control
> - [SimJam ComputerVision](https://github.com/RoadwayVR/SimJamComputerVision) — Traffic analytics, KPIs, speed tracking & CSV export

---

## 🧠 What is SmartTrafficAI?

SmartTrafficAI is a **real-time intelligent traffic management system** that:

1. **Detects & tracks vehicles** using YOLOv8 (cars, trucks, buses, bikes, pedestrians)
2. **Dynamically adjusts traffic signals** based on live vehicle density per lane
3. **Measures speed, counts, and Level of Service (LOS)** for each road segment
4. **Exports analytics** to CSV for planning studies
5. **Displays a live web dashboard** with real-time stats and signal states

---

## 🔥 Key Improvements Over Source Projects

| Feature | FYP-ITMS | SimJam CV | SmartTrafficAI |
|---|---|---|---|
| Vehicle Detection | YOLOv4 | YOLOv8 | ✅ YOLOv8 (latest) |
| Signal Control | ✅ Adaptive | ❌ None | ✅ Adaptive + Priority |
| Speed Estimation | ❌ None | ✅ Yes | ✅ Yes + Alerts |
| Analytics/KPIs | ❌ None | ✅ CSV Export | ✅ Dashboard + CSV |
| Emergency Vehicle | ❌ None | ❌ None | ✅ Preemption |
| Multi-lane support | ❌ 4-signal | ✅ Multi-zone | ✅ Multi-lane + zones |
| Web Dashboard | ❌ None | ❌ None | ✅ Flask Live UI |
| Density Heatmap | ❌ None | ❌ None | ✅ OpenCV overlay |

---

## 📁 Project Structure

```
SmartTrafficAI/
├── main.py                    # Entry point
├── config.py                  # All configuration
├── requirements.txt
├── core/
│   ├── detector.py            # YOLOv8 vehicle detection + tracking
│   ├── speed_estimator.py     # Perspective-corrected speed calculation
│   └── zone_manager.py        # ROI zone definitions per lane
├── signal_control/
│   ├── signal_controller.py   # Adaptive signal timing logic
│   ├── emergency_handler.py   # Emergency vehicle preemption
│   └── phase_manager.py       # Multi-phase signal sequencing
├── analytics/
│   ├── kpi_calculator.py      # LOS, delay, flow rate, occupancy
│   ├── csv_exporter.py        # Export summaries to CSV
│   └── heatmap.py             # Density heatmap overlay
├── dashboard/
│   ├── app.py                 # Flask web dashboard
│   ├── templates/index.html   # Real-time dashboard UI
│   └── static/                # CSS + JS assets
├── utils/
│   ├── logger.py
│   └── visualizer.py          # OpenCV drawing utilities
└── data/
    └── logs/                  # Auto-generated CSV reports
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Your Source
Edit `config.py` — set your video file path or camera index:
```python
VIDEO_SOURCE = 0              # webcam
VIDEO_SOURCE = "traffic.mp4"  # video file
VIDEO_SOURCE = "rtsp://..."   # IP camera stream
```

### 3. Define Zones
In `config.py`, define ROI zones for each lane (pixel coordinates):
```python
LANE_ZONES = {
    "Lane_1_North": [(100, 200), (400, 200), (400, 500), (100, 500)],
    "Lane_2_South": [(500, 200), (800, 200), (800, 500), (500, 500)],
    ...
}
```

### 4. Run the System
```bash
# Full system (detection + signals + dashboard)
python main.py

# Analytics only (no signal control)
python main.py --mode analytics

# Dashboard only (open in browser at http://localhost:5000)
python main.py --mode dashboard
```

---

## 📊 Outputs

- **Live OpenCV window** — annotated video with bounding boxes, IDs, speeds, zone overlays, signal states
- **Web dashboard** — `http://localhost:5000` with real-time charts
- **CSV reports** — saved to `data/logs/` every N minutes (configurable)

---

## 🛠️ Tech Stack

- Python 3.10+
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics)
- OpenCV
- Flask + SocketIO (dashboard)
- Pandas (CSV analytics)
- NumPy

---

## 📌 Credits

Built by combining ideas from:
- **FYP-ITMS** (CC0 License) — adaptive signal switching via YOLO vehicle density
- **SimJam ComputerVision by RoadwayVR** — KPI analytics, speed tracking, CSV export methodology

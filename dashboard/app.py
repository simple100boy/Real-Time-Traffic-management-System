"""
dashboard/app.py
-----------------
Flask + SocketIO real-time web dashboard.
Receives updates from main.py via shared state object.
Open http://localhost:5000 in browser.
"""

import threading
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import config


app = Flask(__name__)
app.config["SECRET_KEY"] = "smarttraffic_secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Shared state — written by main loop, read by dashboard
_state = {
    "signal_states":   {},
    "green_times":     {},
    "zone_occupancy":  {},
    "speed_map":       {},
    "latest_kpis":     {},
    "cumulative":      {},
    "fps":             0,
    "frame_count":     0,
    "violations_today": 0,
}
_state_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
def push_update(data: dict):
    """Called from main loop to push new data to all clients."""
    with _state_lock:
        _state.update(data)
    socketio.emit("state_update", data)


# ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    with _state_lock:
        return jsonify(_state)


@app.route("/api/kpis")
def api_kpis():
    with _state_lock:
        return jsonify(_state.get("latest_kpis", {}))


# ──────────────────────────────────────────────────────────────
def run_dashboard():
    socketio.run(
        app,
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
        log_output=False,
    )

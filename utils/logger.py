import time

def log(module: str, msg: str, level: str = "INFO"):
    ts = time.strftime("%H:%M:%S")
    tag = {"INFO": "ℹ️ ", "WARN": "⚠️ ", "ERR": "❌", "OK": "✅"}.get(level, "•")
    print(f"[{ts}] [{module}] {tag}  {msg}")
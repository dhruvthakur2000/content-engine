import os
import json
from datetime import datetime

DEBUG_DIR = "debug_outputs"

def ensure_debug_dir():
    if not os.path.exists(DEBUG_DIR):
        os.makedirs(DEBUG_DIR)

def save_debug(stage_name: str, data):
    ensure_debug_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stage_name}_{timestamp}.json"

    filepath = os.path.join(DEBUG_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[DEBUG ERROR] Failed to save {stage_name}: {e}")
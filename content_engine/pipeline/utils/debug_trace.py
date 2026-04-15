import json
import os
from datetime import datetime
from typing import Any, Dict

DEBUG_DIR = "debug_traces"


def _ensure_dir():
    if not os.path.exists(DEBUG_DIR):
        os.makedirs(DEBUG_DIR)


def _truncate(data: Any, max_chars: int = 1000):
    """Avoid huge dumps"""
    try:
        text = str(data)
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except Exception:
        return "[unserializable]"


def save_node_trace(
    node_name: str,
    input_state: Dict,
    output_state: Dict,
):
    """
    Save per-node input/output snapshot
    """

    _ensure_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    file_path = os.path.join(DEBUG_DIR, f"{timestamp}_{node_name}.json")

    trace = {
        "node": node_name,
        "timestamp": timestamp,
        "input": {k: _truncate(v) for k, v in input_state.items()},
        "output": {k: _truncate(v) for k, v in output_state.items()},
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, ensure_ascii=False)
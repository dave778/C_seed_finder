# storage.py
import os
import json
from typing import Dict, Any
from utils import ensure_dirs, now_iso

MACHINES_DIR = "machines"
SESSIONS_DIR = "sessions"
RESULTS_DIR = "results"
LOGS_DIR = "logs"
TEMPLATES_DIR = "templates"

def ensure_storage():
    ensure_dirs(MACHINES_DIR, SESSIONS_DIR, RESULTS_DIR, LOGS_DIR, TEMPLATES_DIR)

def machine_file(machine_id: str) -> str:
    return os.path.join(MACHINES_DIR, f"{machine_id}.json")

def load_machine(machine_id: str) -> Dict[str, Any]:
    ensure_storage()
    p = machine_file(machine_id)
    if not os.path.exists(p):
        return {"machine_id": machine_id, "observed_draws": [], "top_seeds": [], "created": now_iso()}
    with open(p, "r") as f:
        return json.load(f)

def save_machine(data: Dict[str, Any]):
    ensure_storage()
    p = machine_file(data["machine_id"])
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)

def save_session(session_id: str, payload: Dict[str, Any]):
    ensure_storage()
    p = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, p)
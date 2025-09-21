# utils.py
import os
import datetime
from typing import List

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

def ensure_dirs(*paths):
    for p in paths:
        ensure_dir(p)

def parse_draw_line(line: str) -> List[int]:
    s = line.strip().replace(",", " ")
    parts = s.split()
    out = []
    for p in parts:
        if not p: continue
        v = int(p)
        if v < 1 or v > 80:
            raise ValueError(f"draw values must be 1..80, got {v}")
        out.append(v)
    return out

def sorted_unique(draw: List[int]) -> List[int]:
    return sorted(set(draw))

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def format_time_offset(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h {m}m {s}s"
    days, h = divmod(h, 24)
    return f"{days}d {h}h {m}m"
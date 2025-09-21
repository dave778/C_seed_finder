# cli.py - simple text-based menu (no prompt_toolkit dependency)
import os
import subprocess
import sys
import webbrowser
from storage import load_machine, save_machine, ensure_storage
from utils import parse_draw_line, sorted_unique, now_iso
from search import compute_jump_count_from_2001, run_parallel_search
import importlib
import time
import logging

logger = logging.getLogger("keno_cli")

def ensure_extension_built():
    try:
        importlib.import_module("search_rng_module")
        return True
    except Exception:
        # Try to build
        print("Compiled extension not found; attempting to build (will call setup.py)...")
        try:
            subprocess.check_call([sys.executable, "setup.py", "build_ext", "--inplace"])
            importlib.invalidate_caches()
            importlib.import_module("search_rng_module")
            return True
        except Exception as e:
            print("Build failed:", e)
            return False

def menu():
    ensure_storage()
    while True:
        print("\nKeno RNG Toolkit - Menu")
        print("1) Enter draws (ingest)")
        print("2) Scan seeds (random)")
        print("3) Search using seeds")
        print("4) List machine seeds")
        print("5) Launch Web UI")
        print("6) Exit")
        choice = input("Select: ").strip()
        if choice == "1":
            ingest()
        elif choice == "2":
            scan_seeds()
        elif choice == "3":
            search()
        elif choice == "4":
            list_seeds()
        elif choice == "5":
            launch_web_ui()
        elif choice == "6":
            break
        else:
            print("Invalid choice.")

def ingest():
    mid = input("Machine ID: ").strip()
    s = input("Draw (space-separated): ").strip()
    try:
        parsed = parse_draw_line(s)
        uniq = sorted_unique(parsed)
    except Exception as e:
        print("Parse error:", e)
        return
    m = load_machine(mid)
    m.setdefault("observed_draws", []).append({"draw": uniq, "ts": now_iso()})
    save_machine(m)
    print("Saved draw.")

def scan_seeds():
    import random
    mid = input("Machine ID: ").strip()
    trials = int(input("Random trials (e.g., 2000): ").strip())
    m = load_machine(mid)
    observed = [d["draw"] for d in m.get("observed_draws", [])]
    if not observed:
        print("No observed draws.")
        return
    last = observed[-1]
    target20 = last[:20] if len(last)>=20 else last + [1]*(20-len(last))
    target10 = target20[:10]
    candidates = [random.getrandbits(64) for _ in range(trials)]
    jump_count = compute_jump_count_from_2001(1200)
    # build extension
    ok = ensure_extension_built()
    if not ok:
        print("Extension not available; cannot scan.")
        return
    import search_rng_module as cext
    results = []
    batch = 256
    scored = {}
    for i in range(0, len(candidates), batch):
        chunk = candidates[i:i+batch]
        res = run_parallel_search(cext.search_and_predict, chunk, jump_count, 30, 1200, target20, target10, numbers_per_draw=20, match_threshold=0.75, unbiased=1, processes=min(8, os.cpu_count()))
        for item in res:
            if 'error' in item: continue
            scored.setdefault(item['seed'], 0.0)
            scored[item['seed']] += item['confidence']
    top = sorted([(sc,s) for s,sc in scored.items()], reverse=True)[:5]
    m.setdefault("top_seeds", [])
    m["top_seeds"] = [{"seed": hex(s), "score": sc, "ts": now_iso()} for sc,s in top]
    save_machine(m)
    print("Scan complete. Top seeds saved.")

def search():
    mid = input("Machine ID: ").strip()
    seeds_input = input("Seeds (space-separated hex/int) or leave blank to use saved: ").strip()
    seeds=[]
    if seeds_input:
        for p in seeds_input.split():
            try:
                seeds.append(int(p,0))
            except:
                pass
    else:
        m = load_machine(mid)
        for t in m.get("top_seeds", []):
            s = t.get("seed")
            try:
                seeds.append(int(s,0))
            except:
                pass
    if not seeds:
        print("No seeds.")
        return
    duration = int(input("Duration seconds (300): ") or "300")
    dps = int(input("Draws/sec (1200): ") or "1200")
    jump_count = compute_jump_count_from_2001(dps)
    ok = ensure_extension_built()
    if not ok:
        print("Extension not available.")
        return
    import search_rng_module as cext
    results = run_parallel_search(cext.search_and_predict, seeds, jump_count, duration, dps, (load_machine(mid).get('observed_draws') or [[1]])[-1][:20], (load_machine(mid).get('observed_draws') or [[1]])[-1][:10], numbers_per_draw=20, match_threshold=0.75, unbiased=1, processes=min(8, os.cpu_count()))
    print("Results:")
    for r in results:
        if 'error' in r:
            print("Seed", r['seed'], "error:", r['error'])
        else:
            print(f"{r['match_type']} seed={hex(r['seed'])} idx={r['draw_index']} off={r['time_offset_pretty']} conf={r['confidence']:.3f}")

def list_seeds():
    mid = input("Machine ID: ").strip()
    m = load_machine(mid)
    for i, s in enumerate(m.get("top_seeds", []), 1):
        print(i, s)

def launch_web_ui():
    # check if server already running
    import socket
    host = "127.0.0.1"
    port = 8000
    sock = socket.socket()
    try:
        sock.connect((host, port))
        # server already running
        print(f"Web UI already running at http://{host}:{port}")
        webbrowser.open(f"http://{host}:{port}")
        return
    except Exception:
        pass
    finally:
        sock.close()
    # start server via python -m uvicorn web:app --reload (or use subprocess)
    print("Starting web UI (background)...")
    # ensure extension before starting
    built = ensure_extension_built()
    # spawn uvicorn in background using subprocess
    args = [sys.executable, "-m", "uvicorn", "web:app", "--host", "127.0.0.1", "--port", "8000"]
    # On Termux, redirect output to avoid blocking
    fp_out = open(os.devnull, "wb")
    proc = subprocess.Popen(args, stdout=fp_out, stderr=fp_out)
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:8000")
    print("Web UI launched in your default browser.")

if __name__ == "__main__":
    menu()
#!/usr/bin/env python3
# main.py - Entrypoint: CLI + optional Web UI launcher (+ auto-compile)

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from storage import ensure_storage
from utils import ensure_dirs
import importlib
from safe_import import safe_import_extension

search_rng_module = safe_import_extension()

# ensure storage dirs
ensure_storage()

# logging
LOG_PATH = os.path.join("logs", "keno.log")
logger = logging.getLogger("keno_main")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=5)
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info("Starting Keno Toolkit")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--web", action="store_true", help="Launch web UI (starts server and opens browser)")
    p.add_argument("--no-auto-build", action="store_true", help="Do not auto-build the C extension")
    return p.parse_args()

def auto_build_extension():
    try:
        import search_rng_module
        logger.info("C extension already importable.")
        return True
    except Exception:
        logger.info("C extension not available, attempting to build with setup.py...")
        rtn = os.system(f"{sys.executable} setup.py build_ext --inplace")
        if rtn == 0:
            try:
                importlib.invalidate_caches()
                import search_rng_module
                logger.info("Built and imported C extension.")
                return True
            except Exception as e:
                logger.exception("Import after build failed: %s", e)
                return False
        else:
            logger.error("setup.py build_ext returned non-zero: %s", rtn)
            return False

def main():
    args = parse_args()
    # ensure templates dir exists (web UI relies on it)
    ensure_dirs("templates")
    if args.web:
        built = auto_build_extension()
        # launch web via uvicorn programmatically (import web.start_server_in_thread)
        try:
            import web
            # if extension build failed, web will show an error message on request
            web.start_server_in_thread()
            # open browser
            import webbrowser, time
            time.sleep(0.6)
            webbrowser.open("http://127.0.0.1:8000")
            print("Web UI launched at http://127.0.0.1:8000")
            print("Press Ctrl+C to stop.")
            # keep running until interrupted
            try:
                while True:
                    time.sleep(3600)
            except KeyboardInterrupt:
                print("Shutting down web UI.")
        except Exception as e:
            logger.exception("Failed to start web UI: %s", e)
            print("Failed to start web UI:", e)
    else:
        # run simple CLI
        import cli
        cli.menu()

if __name__ == "__main__":
    main()
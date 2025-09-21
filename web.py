# web.py
import sys
import subprocess
import importlib.util
import socket

# --- Auto install helper ---
def ensure_package(pkg: str):
    """Ensure a package is installed, install if missing."""
    if importlib.util.find_spec(pkg) is None:
        print(f"📦 Installing missing package: {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


# Ensure FastAPI and Uvicorn are installed
for package in ["fastapi", "uvicorn"]:
    ensure_package(package)

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from uvicorn import run


# --- Web App Definition ---
app = FastAPI(title="Keno RNG Toolkit")


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head><title>Keno RNG Toolkit</title></head>
        <body>
            <h1>Keno RNG Toolkit - Web UI</h1>
            <ul>
                <li><a href="/status">Check Status</a></li>
            </ul>
        </body>
    </html>
    """


@app.get("/status")
async def status():
    return {"status": "ok", "message": "Web UI is running!"}


# --- Web UI Starter ---
def start_webui():
    """Start the FastAPI web server with auto port + LAN detection."""
    # Detect LAN IP
    hostname = socket.gethostname()
    try:
        lan_ip = socket.gethostbyname(hostname)
    except Exception:
        lan_ip = "127.0.0.1"

    # Try ports until one works
    port = 8000
    while True:
        try:
            print(f"\n🌍 Web UI starting at:")
            print(f"   Local:  http://127.0.0.1:{port}")
            print(f"   LAN:    http://{lan_ip}:{port}\n")

            run(app, host="0.0.0.0", port=port, reload=False)
            break
        except OSError:
            port += 1
            print(f"⚠️ Port in use, trying {port}...")
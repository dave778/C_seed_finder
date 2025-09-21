import importlib
import os
import sys
import subprocess
import shutil


def safe_import_extension():
    module_name = "search_rng_module"
    pyver = f"{sys.version_info.major}{sys.version_info.minor}"
    site_pkg_dir = next(p for p in sys.path if "site-packages" in p)

    # Expected paths
    local_so = os.path.join(os.getcwd(), f"{module_name}.cpython-{pyver}.so")
    site_so = os.path.join(site_pkg_dir, f"{module_name}.cpython-{pyver}.so")

    # 1. Remove stray local .so
    if os.path.exists(local_so):
        bad_path = local_so + ".bak"
        print(f"⚠️ Found local {local_so}, moving to {bad_path}")
        try:
            shutil.move(local_so, bad_path)
        except Exception as e:
            print(f"⚠️ Could not move local .so: {e}")

    # 2. Try site-packages version
    try:
        mod = importlib.import_module(module_name)
        print("✅ Extension loaded from site-packages")
        return mod
    except Exception as e:
        print(f"⚠️ Extension not in site-packages or failed: {e}")

    # 3. Try building with setup.py
    try:
        print("🔧 Building extension with setup.py...")
        subprocess.check_call([sys.executable, "setup.py", "build_ext", "--inplace"])
        if os.path.exists(local_so):
            print("📦 Installing into site-packages...")
            shutil.copy(local_so, site_so)
            mod = importlib.import_module(module_name)
            print("✅ Extension built and loaded")
            return mod
    except Exception as e:
        print(f"❌ Build failed: {e}")

    # 4. Fallback
    print("⚠️ Using NumPy fallback (slower).")
    return None
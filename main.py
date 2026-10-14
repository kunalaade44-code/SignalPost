"""
SignalPost FastAPI entrypoint for Vercel Services and local execution.
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Seed SQLite database to /tmp if running on Vercel
if os.environ.get("VERCEL") and not os.path.exists("/tmp/signalpost.db"):
    repo_db = PROJECT_ROOT / "signalpost.db"
    if repo_db.is_file():
        try:
            import shutil
            shutil.copyfile(repo_db, "/tmp/signalpost.db")
        except OSError:
            pass

from signalpost.api.app import app

__all__ = ["app"]

"""
Vercel Serverless ASGI entry point for Signalpost FastAPI backend.
Vercel's Python runtime discovers and serves the ASGI `app` object in this file.
"""
import os
import sys
from pathlib import Path

# Ensure 'backend' directory is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# If running on Vercel and pre-populated signalpost.db exists in repository, seed /tmp
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

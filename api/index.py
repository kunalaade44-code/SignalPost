"""
Vercel Serverless ASGI entry point for Signalpost FastAPI backend.
"""
import os
import sys
import traceback
from pathlib import Path

# Force writable locations for Vercel / serverless runtime
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    os.environ["DATABASE_URL"] = "sqlite:////tmp/signalpost.db"
    os.environ["CACHE_DIR"] = "/tmp/cache"
    os.environ["OUT_DIR"] = "/tmp/out"
    try:
        os.makedirs("/tmp/cache", exist_ok=True)
        os.makedirs("/tmp/out", exist_ok=True)
    except OSError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
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

try:
    from signalpost.api.app import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Signalpost Error Fallback")

    @app.get("/{full_path:path}")
    def error_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "FastAPI failed to start on Vercel",
                "detail": str(e),
                "traceback": err_tb,
            },
        )

__all__ = ["app"]

"""
SignalPost FastAPI entrypoint for Vercel Services, Docker, and local execution.
"""
import os
import sys
from pathlib import Path

# Force writable locations for Vercel / serverless runtime
if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    db_env = os.environ.get("DATABASE_URL", "")
    if not db_env or "sqlite" in db_env:
        os.environ["DATABASE_URL"] = "sqlite:////tmp/signalpost.db"
    if not os.environ.get("CACHE_DIR") or os.environ.get("CACHE_DIR", "").startswith("."):
        os.environ["CACHE_DIR"] = "/tmp/cache"
    if not os.environ.get("OUT_DIR") or os.environ.get("OUT_DIR", "").startswith("."):
        os.environ["OUT_DIR"] = "/tmp/out"
    try:
        os.makedirs("/tmp/cache", exist_ok=True)
        os.makedirs("/tmp/out", exist_ok=True)
    except OSError:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Top-level module import for Vercel static AST analyzer
from signalpost.api.app import app

# Expose both app and handler at module top level
handler = app

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting SignalPost server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"
export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:$BACKEND_PORT}"
cleanup() {
    kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
"$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT" &
BACKEND_PID=$!
echo "Waiting for the backend to finish loading..."
"$PYTHON" - "$BACKEND_PORT" <<'PYREADY'
import sys
import time
import urllib.error
import urllib.request

url = f"http://127.0.0.1:{sys.argv[1]}/health"
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            if response.status == 200:
                break
    except (urllib.error.URLError, TimeoutError):
        pass
    time.sleep(0.25)
else:
    sys.exit("Backend did not become ready within 30 seconds. Check the startup log above.")
PYREADY
"$PYTHON" -m streamlit run frontend/app.py --server.address 127.0.0.1 --server.port "$FRONTEND_PORT" &
FRONTEND_PID=$!
echo "Backend: http://localhost:$BACKEND_PORT | Frontend: http://localhost:$FRONTEND_PORT"
while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
    sleep 1
done

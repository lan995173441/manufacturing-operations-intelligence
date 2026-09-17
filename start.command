#!/bin/zsh
# Double-click this file in Finder to run the local portfolio demonstration.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
VENV_STREAMLIT="$PROJECT_DIR/.venv/bin/streamlit"
PORT="${MOI_PORT:-8501}"

cd "$PROJECT_DIR"

if [[ ! -x "$VENV_PYTHON" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv .venv
  elif command -v python3 >/dev/null 2>&1; then
    if ! python3 -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 12))'; then
      echo "Python 3.12 is required. Install Python 3.12, then run this file again."
      read -r '?Press Return to close this window...'
      exit 1
    fi
    python3 -m venv .venv
  else
    echo "Python 3.12 was not found. Install Python 3.12, then run this file again."
    read -r '?Press Return to close this window...'
    exit 1
  fi
fi

if ! "$VENV_PYTHON" -c 'import streamlit, pandas, plotly, openpyxl, reportlab' >/dev/null 2>&1; then
  echo "Installing project dependencies for the first run..."
  "$VENV_PYTHON" -m pip install --upgrade pip
  "$VENV_PYTHON" -m pip install -e '.[dev]'
fi

echo "Starting Manufacturing Operations Intelligence..."
echo "Local address: http://127.0.0.1:$PORT"
echo "Press Control-C in this window to stop the application."

if [[ "${MOI_OPEN_BROWSER:-true}" == "true" ]]; then
  open "http://127.0.0.1:$PORT"
fi

exec "$VENV_STREAMLIT" run streamlit_app.py \
  --server.address=127.0.0.1 \
  --server.port="$PORT" \
  --server.headless=true

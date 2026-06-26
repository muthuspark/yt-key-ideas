#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.service.pid"
LOG_FILE="$DIR/.service.log"

if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "Service is already running (PID $PID)."
    exit 0
  fi
  rm -f "$PID_FILE"
fi

source "$DIR/.venv/bin/activate"

nohup python "$DIR/service.py" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Service started (PID $(cat "$PID_FILE")). Logs: $LOG_FILE"

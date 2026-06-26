#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.service.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Service is not running (no PID file found)."
  exit 0
fi

PID="$(cat "$PID_FILE")"

if ! kill -0 "$PID" 2>/dev/null; then
  echo "Service is not running (stale PID $PID)."
  rm -f "$PID_FILE"
  exit 0
fi

kill "$PID"
rm -f "$PID_FILE"
echo "Service stopped (PID $PID)."

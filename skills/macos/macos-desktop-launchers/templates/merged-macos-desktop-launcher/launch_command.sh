#!/bin/bash
# TEMPLATE: macOS Desktop .command launcher (copy, rename, edit DIR/PORT/APP).
# Double-clickable from Finder. Fixes the GUI-PATH PYTHONPATH pitfall.
DIR="$HOME/Desktop/<appdir>"
LOG="$DIR/launch.log"
PORT=5055
cd "$DIR" || exit 1

# CRITICAL: GUI 'open' does NOT inherit user PATH or site-packages.
export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

# kill prior instance — match on dir marker (NOT "python3 $DIR/..." which has a space)
pkill -f "<appdir>/app.py" 2>/dev/null || true
pkill -f "crypto_bot/<appdir>/app.py" 2>/dev/null || true
sleep 1

nohup /usr/bin/python3 "$DIR/app.py" > "$LOG" 2>&1 &
echo "started at $(date)" >> "$LOG"

for i in $(seq 1 40); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
    open "http://localhost:$PORT"
    exit 0
  fi
  sleep 0.5
done
open "http://localhost:$PORT"

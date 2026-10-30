#!/bin/bash
# Template macOS desktop launcher for a local Python server.
# Copy to ~/Desktop/<name>.command, edit DIR/PORT/PYBIN, chmod +x.
DIR="$HOME/REPLACE/with/app/dir"
LOG="$DIR/launch.log"
PORT=5055

cd "$DIR" || exit 1

# CRITICAL: GUI double-click drops user site-packages from PATH.
# Pin them so `python3` can import flask/ccxt/etc.
export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

PYBIN="/usr/bin/python3"

# Kill prior instance using a stable directory marker (NOT "$DIR/app.py" — spaces break it).
pkill -f "REPLACE/with/dir-marker/app.py" 2>/dev/null || true
sleep 1

nohup "$PYBIN" "$DIR/app.py" > "$LOG" 2>&1 &
echo "started at $(date)" >> "$LOG"

for i in $(seq 1 40); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
    open "http://localhost:$PORT"
    exit 0
  fi
  sleep 0.5
done
echo "server did not come up in 20s" >> "$LOG"
open "http://localhost:$PORT"

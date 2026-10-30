#!/bin/bash
# Luna-EDGE launcher template — one-click start of a localhost CV webapp.
# Reproduce/modify: set DIR to your project, point to your app entry + port.
# Drop as launch.command on the Desktop (double-click -> runs in Terminal) OR
# wrap as a .app (see note below). Either way it: venv up, start server,
# wait for port, open browser. Kills any prior instance first.
DIR="$HOME/luna-edge"          # <-- your repo path
PORT=8000                      # <-- your webapp port
ENTRY="app.py"                 # <-- your server entry (flask app.py)
LOG="$DIR/launch.log"
cd "$DIR" || exit 1

# CRITICAL for GUI double-click launches (macOS `open`): the bare GUI environment
# often LACKS user site-packages on sys.path, so `python3` -> /usr/bin/python3 and
# `import flask` dies silently (logged, nothing on screen -> "double-click did nothing").
# Pin PYTHONPATH/PATH to the user install BEFORE launching.
export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
PYBIN="/usr/bin/python3"   # the interpreter that actually has the deps installed

# virtualenv (create if missing)
if [ -d "$DIR/.venv" ]; then
  source "$DIR/.venv/bin/activate"
else
  echo "venv missing, installing deps..." | tee -a "$LOG"
  python3 -m venv "$DIR/.venv"
  source "$DIR/.venv/bin/activate"
  pip install -q -r "$DIR/requirements.txt"
fi

# kill any prior instance on the port. Use a pattern matching the full path AND a
# short token, because a space in $DIR breaks a naive "python3 $DIR/$ENTRY" pattern.
pkill -f "$DIR/$ENTRY" 2>/dev/null || true
pkill -f "luna-edge/$ENTRY" 2>/dev/null || true
sleep 1

# start server in background
nohup "$PYBIN" "$DIR/$ENTRY" > "$LOG" 2>&1 &
echo "started at $(date)" >> "$LOG"

# wait until the port answers, then open browser (max ~15s)
for i in $(seq 1 30); do
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/"; then
    open "http://localhost:$PORT"
    exit 0
  fi
  sleep 0.5
done
echo "server did not come up in 15s" >> "$LOG"
open "http://localhost:$PORT"

# To wrap as a double-click .app (no Terminal window):
#   mkdir -p ~/Desktop/Luna-EDGE.app/Contents/MacOS
#   printf '#!/bin/bash\nexec "%s/launch.command"\n' "$DIR" > ~/Desktop/Luna-EDGE.app/Contents/MacOS/Luna-EDGE
#   chmod +x ~/Desktop/Luna-EDGE.app/Contents/MacOS/Luna-EDGE
#   # add a minimal Contents/Info.plist (CFBundleExecutable=Luna-EDGE) for app identity
# Caveat: first launch of the .app may trigger Gatekeeper; the .command file is
# the most reliable double-click launcher on macOS.

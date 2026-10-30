#!/usr/bin/env bash
# One-shot LUNAV Intel-M stack probe: backend, frontend proxy, Mac agent buffer, ports.
set -u

BE=http://127.0.0.1:8001
FE=http://127.0.0.1:3000
CSV="$HOME/LUNAV-Intel-M/backend/data/mac_sensors_live.csv"

line() { printf '%s\n' "------------------------------------------------------------"; }

line; echo "LUNAV Intel-M stack check"
line

echo "[1] backend /api/health"
curl -s --max-time 5 "$BE/api/health" || echo "  NO RESPONSE"
echo

echo "[2] backend /api/status (model + RUL state)"
curl -s --max-time 5 "$BE/api/status" || echo "  NO RESPONSE"
echo

echo "[3] frontend /api/health (through the Next.js /api rewrite)"
curl -s --max-time 5 "$FE/api/health" || echo "  NO RESPONSE"
echo

echo "[4] mac agent buffer (backend-side proof the agent is posting)"
curl -s --max-time 5 "$BE/api/mac-stream" | head -c 200 || echo "  NO RESPONSE"
echo

echo "[5] persisted mac readings"
if [ -f "$CSV" ]; then
  echo "  $CSV: $(wc -l < "$CSV" | tr -d ' ') rows"
else
  echo "  $CSV not created yet"
fi

echo "[6] listening ports"
lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E ':(3000|8001)\b' || echo "  neither 3000 nor 8001 is listening"

echo "[7] tmux sessions"
tmux ls 2>/dev/null | grep -E 'intel-(backend|frontend|mac-agent)' || echo "  no intel-* tmux sessions"

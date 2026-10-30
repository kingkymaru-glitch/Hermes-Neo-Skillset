#!/usr/bin/env bash
# verify-theme-deploy.sh — MARU frontend deploy liveness + content gate
#
# THE RULE this enforces: a 200 only proves the server is UP + serving SOME
# build. It does NOT prove the NEW code is live. MARU's recurring "I still
# can't see it" symptom is almost always (a) nothing pushed, or (b) the change
# was clipped by CSS (flex/overflow), not a deploy miss. This script does both
# gates: liveness (curl-200) AND, when given a search string, a content gate
# (grep the freshly built bundle so you KNOW the artifact contains the change).
#
# Usage:
#   ./verify-theme-deploy.sh                                          # liveness only
#   ./verify-theme-deploy.sh "LunaV R-Tessera - ROVER-R"             # + content gate (both repos)
#   ./verify-theme-deploy.sh "ph-railing" ~/Documents/R-Tessera      # + gate, custom repo dir
#
# Exit code: 0 if all live; non-zero if any surface is down. Content-gate
# misses print WARN but do not fail the script (so liveness is the hard gate).

set -u

SEARCH="${1:-}"
RT_DIR="${2:-$HOME/Documents/R-Tessera}"
LV_DIR="${3:-$HOME/lunavsolution-code}"

echo "== Liveness (curl -w http_code) =="
LV=$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://lunavsolution.vercel.app)
RT=$(curl -s -o /dev/null -w '%{http_code}' --max-time 12 https://r-tessera.vercel.app)
ED=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8  http://localhost:8000)
printf 'LunaV:     %s\n' "$LV"
printf 'R-Tessera: %s\n' "$RT"
printf 'Luna-EDGE: %s\n' "$ED"

if [ "$LV" != "200" ] || [ "$RT" != "200" ] || [ "$ED" != "200" ]; then
  echo "FAIL: one or more surfaces not 200 — fix deploy/restart before claiming done."
  exit 1
fi

if [ -n "$SEARCH" ]; then
  echo
  echo "== Content gate: grep built bundle for: $SEARCH =="
  found=0
  for d in "$RT_DIR" "$LV_DIR"; do
    if [ -d "$d" ]; then
      hit=$(grep -rl -- "$SEARCH" "$d"/dist/assets 2>/dev/null | head -1)
      if [ -n "$hit" ]; then
        echo "FOUND in $hit"
        found=1
      else
        echo "NOT FOUND in $d/dist/assets (rebuild + verify)"
      fi
    fi
  done
  if [ "$found" -eq 0 ]; then
    echo "WARN: search string absent from every built bundle — either not built or not deployed."
  fi
fi

echo "OK: all surfaces live."

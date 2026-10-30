#!/usr/bin/env bash
# verify-theme.sh — confirm LunaV glassmorphism sync across the 3 front-ends.
# Run: bash ~/.hermes/skills/frontend/lunav-theme-sync/scripts/verify-theme.sh
set -u
PASS=0; FAIL=0
chk(){ if eval "$2"; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1"; FAIL=$((FAIL+1)); fi; }

echo "=== R-Tessera header (Vite) ==="
RT=~/Documents/R-Tessera/src
chk "header in App.jsx"        "grep -q 'rt-header' $RT/App.jsx"
chk "brand 'LunaV R-TESSERA'"  "grep -q 'LunaV.*R-TESSERA' $RT/App.jsx"
chk "header button CSS"        "grep -q 'rt-hdr-btn' $RT/App.css"
chk "old banner CSS removed"   "! grep -q 'rt-banner' $RT/App.css"
chk "glass blur(22px)"         "grep -q 'backdrop-filter: blur(22px)' $RT/App.css"
chk "MCP trigger at 70px"      "grep -q 'top: 70px' $RT/App.css"

echo ""
echo "=== LunaV EDGE header (Flask HTML) ==="
ED=~/luna-edge/templates/index.html
chk "header buttons use hdr-btn"      "grep -q 'class=\"hdr-btn\"' $ED"
chk "hdr-btn margin-top:0 override"  "grep -q 'margin-top: 0' $ED"
chk "brand 'LunaV EDGE'"             "grep -q 'LunaV.*EDGE' $ED"

echo ""
echo "=== LunaV brand (Next.js) ==="
LV=~/lunavsolution-code/src
chk "lv-brand-name CSS"              "grep -q 'lv-brand-name' $LV/app/globals.css"
chk "workspace brand EDGE-style"     "grep -q 'LunaV.*STUDIO' $LV/components/ProjectWorkspace.tsx"
chk "homepage brand EDGE-style"      "grep -q 'LunaV.*STUDIO' $LV/components/ProjectHomepage.tsx"

echo ""
echo "=== Builds ==="
echo "-- R-Tessera --"; (cd ~/Documents/R-Tessera && npm run build >/dev/null 2>&1 && echo "PASS: r-tessera build" || { echo "FAIL: r-tessera build"; FAIL=$((FAIL+1)); })
echo "-- LunaV --";     (cd ~/lunavsolution-code && npm run build >/dev/null 2>&1 && echo "PASS: lunav build"     || { echo "FAIL: lunav build";     FAIL=$((FAIL+1)); })
echo "-- LunaV EDGE --"; (cd ~/luna-edge && source .venv/bin/activate && python -c "from app import app" >/dev/null 2>&1 && echo "PASS: luna-edge flask load" || { echo "FAIL: luna-edge flask load"; FAIL=$((FAIL+1)); })

echo ""
echo "SUMMARY: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]

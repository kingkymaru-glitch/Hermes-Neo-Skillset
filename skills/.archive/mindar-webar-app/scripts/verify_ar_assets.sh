#!/usr/bin/env bash
# verify_ar_assets.sh — assert every /ar asset serves 200 with NO redirect.
# Usage: bash verify_ar_assets.sh https://lunavsolution.vercel.app
# Returns non-zero if any asset is blocked (307 -> /login) or missing.
set -u
BASE="${1:-https://lunavsolution.vercel.app}"
ASSETS=(ar/viewer.html ar/setup.html ar/sheet.html ar/ar-core.js \
        ar/assets/card.mind ar/assets/card.png ar/assets/aframe.min.js \
        ar/assets/mindar-image-aframe.prod.js ar/assets/qrcode.min.js ar/assets/favicon.ico)
fail=0
for f in "${ASSETS[@]}"; do
  # --max-redirs 0: do NOT follow redirects (curl -L hides a 307 -> /login block)
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-redirs 0 "$BASE/$f")
  loc=$(curl -sI --max-redirs 0 "$BASE/$f" | grep -i "^location" | tr -d '\r')
  if [ "$code" != "200" ] || [ -n "$loc" ]; then
    echo "BLOCKED  $code  ${loc:-}  $f"; fail=1
  else
    echo "ok       $code       $f"
  fi
done
[ "$fail" = "0" ] && echo "ALL AR ASSETS PUBLIC (200, no redirect)" || { echo "SOME ASSETS BLOCKED"; exit 1; }

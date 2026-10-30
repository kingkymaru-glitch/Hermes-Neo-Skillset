#!/usr/bin/env bash
# Verify a feature string is present in the LIVE Vite build's lazy chunk.
# Usage: verify-vite-live.sh <live-url-root> <chunk-pattern> <feature-string>
# Example: verify-vite-live.sh https://r-tessera.vercel.app GlobeView "CCTV Cameras"
set -euo pipefail
ROOT="${1:?live url root, e.g. https://r-tessera.vercel.app}"
CHUNK="${2:?chunk name pattern, e.g. GlobeView}"
FEAT="${3:?feature string to grep for}"

ENTRY=$(curl -s "$ROOT/" | grep -oE "assets/[A-Za-z0-9_-]+\.js" | sort -u | head -1)
echo "entry bundle: $ENTRY"
GV=$(curl -s "$ROOT/$ENTRY" | grep -oE "${CHUNK}-[A-Za-z0-9_-]+\.js" | head -1)
echo "feature chunk: $GV"
if [ -z "$GV" ]; then echo "chunk pattern '$CHUNK' not found in entry"; exit 1; fi

curl -s "$ROOT/assets/$GV" -o /tmp/_verify_chunk.js
if grep -q "$FEAT" /tmp/_verify_chunk.js; then
  echo "LIVE_HAS_FEATURE: $FEAT"
else
  echo "LIVE_MISSING_FEATURE: $FEAT"
  exit 2
fi

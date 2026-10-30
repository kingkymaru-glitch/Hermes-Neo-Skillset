#!/usr/bin/env bash
# hermes-verify-launch-path.sh <project-root>
# Static root-cause probes for an iOS app that "pauses/crashes at launch".
# Ad-hoc only — NOT a real build. Reports suspect lines; does not fix.
set -u
ROOT="${1:-.}"
cd "$ROOT" || exit 2
echo "=== Launch-path static probes (ad-hoc, not a build) ==="

echo
echo "[1] Force-unwrap / force-cast scan (common launch-crash culprits):"
hits=$(grep -rnE 'try!|as!|\bfatalError|preconditionFailure|\.first!|\.last!|\[0\]!' --include='*.swift' . | grep -v '/build/')
if [ -z "$hits" ]; then echo "  none found"; else echo "$hits"; fi

# Locate pbxproj, GoogleService plist, Info.plist
PBX=$(find . -name project.pbxproj -not -path '*/build/*' | head -1)
GSP=$(find . -name 'GoogleService-Info.plist' -not -path '*/build/*' | head -1)
INFO=$(find . -name Info.plist -not -path '*/build/*' | head -1)

echo
echo "[2] Bundle-ID consistency:"
if [ -n "$PBX" ]; then
  bundle=$(grep -m1 'PRODUCT_BUNDLE_IDENTIFIER = ' "$PBX" | sed -E 's/.*= *//; s/;.*//; s/ *$//')
  echo "  pbxproj PRODUCT_BUNDLE_IDENTIFIER = $bundle"
else echo "  (no project.pbxproj found)"; fi
if [ -n "$GSP" ]; then
  gbid=$(grep -A1 '<key>BUNDLE_ID</key>' "$GSP" | tail -1 | sed -E 's/<[^>]+>//g; s/^ *//; s/ *$//')
  echo "  GoogleService BUNDLE_ID          = $gbid"
  if [ -n "${bundle:-}" ] && [ "$bundle" != "$gbid" ]; then echo "  !! MISMATCH — likely silent launch crash on Google sign-in"; fi
else echo "  (no GoogleService-Info.plist found)"; fi

echo
echo "[3] GoogleService-Info.plist bundled in pbxproj Resources:"
if [ -n "$PBX" ] && [ -n "$GSP" ]; then
  name=$(basename "$GSP")
  if grep -q "$name" "$PBX"; then echo "  $name referenced in pbxproj (bundled)"; else echo "  !! $name NOT referenced — not bundled, Firebase configure will fail"; fi
else echo "  (skip — pbxproj or plist missing)"; fi

echo
echo "[4] Info.plist Google URL scheme vs GoogleService reversed id:"
if [ -n "$INFO" ] && [ -n "$GSP" ]; then
  gpid=$(grep -A1 '<key>REVERSED_CLIENT_ID</key>' "$GSP" | tail -1 | sed -E 's/<[^>]+>//g; s/^ *//; s/ *$//')
  echo "  GoogleService REVERSED_CLIENT_ID = $gpid"
  if grep -q "$gpid" "$INFO"; then echo "  matches Info.plist CFBundleURLSchemes OK"; else echo "  !! reversed id NOT in Info.plist URL schemes — Google sign-in will fail"; fi
else echo "  (skip — Info.plist or GoogleService missing)"; fi

echo
echo "[5] Optional cross-reference gate (if script present):"
XREF=$(find . -name 'hermes-verify-xref.sh' 2>/dev/null | head -1)
if [ -n "$XREF" ]; then ( bash "$XREF" "$ROOT" ); else echo "  (hermes-verify-xref.sh not found — run it manually from ios-cli-verification skill)"; fi

echo
echo "=== Probe done. If app still pauses at RUN, keep LLDB on and paste the red console exception. ==="

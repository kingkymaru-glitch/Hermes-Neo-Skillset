#!/usr/bin/env bash
# hermes-verify-swift.sh — reusable AD-HOC static check for an edited .swift file.
# NOT a real Swift compile: UIKit/SwiftUI unavailable to macOS CLI swiftc.
# Usage: TMP=$(mktemp -t hermes-verify-XXXXXX.sh); cat > "$TMP" <<'SCRIPT' ... SCRIPT; bash "$TMP"; rm -f "$TMP"
# Fill FILE (and optional SECOND for nesting checks) and the assertions block.
set -u
FILE="${1:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Tenant/TenantScreenView.swift}"
ok=1
fail(){ echo "FAIL: $1"; ok=0; }
echo "== ad-hoc consistency: $(basename "$FILE") =="

# --- assertions: edit per change. Prefer grep -F (fixed string) over regex. ---
# Example set (TenantScreenView nav redesign). Replace with your change's invariants.
grep -q 'NavigationStack(path:' "$FILE" && echo "PASS: NavigationStack(path:) used" || fail "no NavigationStack"
grep -q 'enum TenantDestination: Hashable' "$FILE" && echo "PASS: TenantDestination: Hashable" || fail "missing enum"
grep -q 'navigationDestination(for: TenantDestination.self)' "$FILE" && echo "PASS: navigationDestination wired" || fail "no destination"
grep -q 'xmark.circle.fill' "$FILE" && echo "PASS: X icon present" || fail "no X image"

# Removed symbols must be GONE (use -F, literal):
for sym in 'selectedShopIndex' 'shopPickerSection' 'currentShop' 'Text(shop.shopType.icon)'; do
  if grep -qF "$sym" "$FILE"; then fail "leftover: $sym"; else echo "PASS: removed $sym"; fi
done

# Lone NavigationView must be ONLY inside a modal sheet (not path nav):
nv=$(grep -c 'NavigationView' "$FILE")
bs=$(grep -n 'private var bookingSheet' "$FILE" | head -1 | cut -d: -f1)
nvline=$(grep -n 'NavigationView {' "$FILE" | head -1 | cut -d: -f1)
if [ "$nv" -eq 1 ] && [ -n "$bs" ] && [ "$nvline" -gt "$bs" ]; then
  echo "PASS: lone NavigationView inside bookingSheet ($nvline>$bs)"
else
  fail "NavigationView misuse: count=$nv bs=$bs nvline=$nvline"
fi

# Brace balance (rough but catches gross breakage):
o=$(grep -o '{' "$FILE" | wc -l | tr -d ' ')
c=$(grep -o '}' "$FILE" | wc -l | tr -d ' ')
[ "$o" = "$c" ] && echo "PASS: braces balanced ($o/$c)" || fail "brace mismatch ($o/$c)"

if [ $ok -eq 1 ]; then
  echo ""; echo "AD-HOC STATIC CHECK PASSED. Real iOS build must run in Xcode (no UIKit/SwiftUI on CLI)."
else
  echo ""; echo "AD-HOC CHECK FAILED"; exit 1
fi

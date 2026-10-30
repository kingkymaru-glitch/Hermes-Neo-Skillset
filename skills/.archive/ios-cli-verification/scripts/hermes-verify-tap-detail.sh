#!/usr/bin/env bash
# hermes-verify-tap-detail.sh — static check for "tap a card -> full detail view" (#4 class).
# Reusable template: a CatchCardView tap opens CatchDetailView (large image + all params) via .sheet(item:).
# Usage: bash hermes-verify-tap-detail.sh [<InventoryScreenView.swift path>] [<CatchDetailView.swift path>]
set -u
INV="${1:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/InventoryScreenView.swift}"
DET="${2:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/CatchDetailView.swift}"
p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }

# 1. Detail view exists and takes the item.
chk "CatchDetailView struct" "grep -q 'struct CatchDetailView' '$DET'"
chk "takes let item: CatchItem" "grep -q 'let item: CatchItem' '$DET'"

# 2. Detail shows the entered params (assert the GOOD fields, not just 'item').
chk "large image (frame height 280)" "grep -q 'frame(height: 280)' '$DET'"
chk "shows species" "grep -q 'item.species' '$DET'"
chk "shows length" "grep -q '\"Length\"' '$DET'"
chk "weight category" "grep -q 'item.weightCategory.rawValue' '$DET'"
chk "technique" "grep -q 'item.technique.rawValue' '$DET'"
chk "leader" "grep -q 'item.leaderSize.rawValue' '$DET'"
chk "mainline manual fallback" "grep -q 'mainLine == .manual' '$DET'"
chk "lure" "grep -q 'item.lureDescription' '$DET'"
chk "capture date" "grep -q 'item.captureDate' '$DET'"
chk "location" "grep -q 'item.captureLocation' '$DET'"
chk "done dismiss" "grep -q 'Button(\"Done\")' '$DET'"

# 3. Inventory wiring: state + tap + sheet(item:) presenter.
chk "selectedCatch state" "grep -q 'selectedCatch: CatchItem?' '$INV'"
chk "card onTapGesture sets it" "grep -q 'selectedCatch = fishCatch' '$INV'"
chk "sheet(item:) presenter" "grep -q '.sheet(item: \$selectedCatch)' '$INV'"
chk "CatchDetailView presented" "grep -q 'CatchDetailView(item: catchItem)' '$INV'"

# 4. Braces balanced (both files).
for file in "$INV" "$DET"; do
  o=$(grep -o '{' "$file" | wc -l | tr -d ' '); c=$(grep -o '}' "$file" | wc -l | tr -d ' ')
  if [ "$o" -eq "$c" ]; then echo "PASS braces: $(basename "$file") [$o/$c]"; p=$((p+1)); else echo "FAIL braces: $(basename "$file") [$o/$c]"; f=$((f+1)); fi
done
echo "RESULT: pass=$p fail=$f"

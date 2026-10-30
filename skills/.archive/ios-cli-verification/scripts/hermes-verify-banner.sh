#!/usr/bin/env bash
# hermes-verify-banner.sh — static check for "promote + subtlize a banner/strip"
# Reusable template for the #3 class of edit: move a UI strip up and make it quiet.
# Usage: bash hermes-verify-banner.sh [<InventoryScreenView.swift path>]
set -u
INV="${1:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/InventoryScreenView.swift}"
p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }

# 1. Reordering: promoted strip must come BEFORE a later sibling control.
line_strip=$(grep -n 'ReputationDashboardView(' "$INV" | head -1 | cut -d: -f1)
line_sibling=$(grep -n 'showingAddCatch = true' "$INV" | head -1 | cut -d: -f1)
chk "banner precedes sibling control" "[ -n "$line_strip" ] && [ -n "$line_sibling" ] && [ "$line_strip" -lt "$line_sibling" ]"

# 2. Removed the loud section header that used to wrap it.
chk "loud section header removed" "! grep -q 'Reputation Status' '$INV'"

# 3. Subtle styling present.
chk "subtle bg (tertiarySystemGroupedBackground)" "grep -q 'tertiarySystemGroupedBackground' '$INV'"
chk "muted secondary foreground" "grep -q 'foregroundColor(.secondary)' '$INV'"

# 4. CRITICAL: scope to the banner struct — assert it carries NO .shadow.
#    Whole-file grep -q 'shadow' is a FALSE FAIL: CatchCardView/TackleRowView also shadow.
awk '/^struct ReputationDashboardView/,/^}/' "$INV" > /tmp/rep_block.txt
if grep -q 'shadow' /tmp/rep_block.txt; then echo "FAIL: banner block has .shadow"; f=$((f+1)); else echo "PASS: banner block no .shadow"; p=$((p+1)); fi
rm -f /tmp/rep_block.txt

# 5. Braces balanced.
o=$(grep -o '{' "$INV" | wc -l | tr -d ' '); c=$(grep -o '}' "$INV" | wc -l | tr -d ' ')
if [ "$o" -eq "$c" ]; then echo "PASS braces [$o/$c]"; p=$((p+1)); else echo "FAIL braces [$o/$c]"; f=$((f+1)); fi
echo "RESULT: pass=$p fail=$f"

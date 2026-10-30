#!/usr/bin/env bash
# hermes-verify-combo.sh — static check for an iOS "combined bar chart" edit
# (count vs total weight by technique) AND its Xcode pbxproj registration.
# AD-HOC ONLY — no Xcode/iOS SDK on this CLI. Not a compile.
#
# Usage: bash hermes-verify-combo.sh
# Adjust the *_PATH / UUID vars below to your project before running.
set -u

CHART_PATH="${CHART_PATH:-Features/Inventory/CombinedTechniqueChart.swift}"
INV_PATH="${INV_PATH:-Features/Inventory/InventoryScreenView.swift}"
PBX_PATH="${PBX_PATH:-AnglerGO.xcodeproj/project.pbxproj}"
NEW_REF_UUID="${NEW_REF_UUID:-F3D8CD002FF1240000A59DC7}"
NEW_BUILD_UUID="${NEW_BUILD_UUID:-F3D8CD012FF1240700A59DC7}"
NEW_BASENAME="${NEW_BASENAME:-CombinedTechniqueChart.swift}"

p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }

[ -f "$CHART_PATH" ] || { echo "MISSING: $CHART_PATH"; exit 2; }
[ -f "$INV_PATH" ]   || { echo "MISSING: $INV_PATH"; exit 2; }
[ -f "$PBX_PATH" ]   || { echo "MISSING: $PBX_PATH"; exit 2; }

# --- Chart file ---
chk "chart struct"        "grep -q 'struct CombinedTechniqueChart' '$CHART_PATH'"
chk "groups by technique" "grep -q 'Dictionary(grouping: catches, by: \\\\.technique)' '$CHART_PATH'"
chk "counts catches"      "grep -q 'items.count' '$CHART_PATH'"
chk "weight estimate"     "grep -q 'weightMidpoint' '$CHART_PATH'"
chk "blue = count bar"    "grep -q 'color: .blue' '$CHART_PATH'"
chk "orange = weight bar" "grep -q 'color: .orange' '$CHART_PATH'"
chk "legend present"      "grep -q 'LegendDot' '$CHART_PATH'"
chk "empty state"         "grep -q 'No catch data yet' '$CHART_PATH'"
chk "wired in inventory"  "grep -q 'CombinedTechniqueChart(catches:' '$INV_PATH'"

# --- pbxproj registration (4 layers) ---
chk "pbx build file"  "grep -q \"$NEW_BUILD_UUID /\* $NEW_BASENAME in Sources\" '$PBX_PATH'"
chk "pbx file ref"    "grep -q \"$NEW_REF_UUID /\* $NEW_BASENAME\" '$PBX_PATH'"
chk "pbx in group"    "grep -q \"$NEW_REF_UUID /\* $NEW_BASENAME \*/,\" '$PBX_PATH'"
chk "pbx in sources"  "grep -q \"$NEW_BUILD_UUID /\* $NEW_BASENAME in Sources \*/,\" '$PBX_PATH'"
chk "buildFile fileRef == fileRef UUID" "grep -q \"$NEW_BUILD_UUID /\* $NEW_BASENAME in Sources \*/ = {isa = PBXBuildFile; fileRef = $NEW_REF_UUID\" '$PBX_PATH'"

# --- indentation: each inserted line matches its sibling's leading-tab count ---
tabs(){ sed -n "${1}p" "$PBX_PATH" | awk -F'\t' '{print NF-1}'; }
ref_line=$(grep -n "AA10000000000000000000A4 /\* FishingAnalyticsChart.swift \*/," "$PBX_PATH" | head -1 | cut -d: -f1)
grp_line=$(grep -n "$NEW_REF_UUID /\* $NEW_BASENAME \*/," "$PBX_PATH" | head -1 | cut -d: -f1)
[ -n "$ref_line" ] && [ -n "$grp_line" ] && chk "group indent == sibling" "[ $(tabs "$grp_line") -eq $(tabs "$ref_line") ]"
bf_line=$(grep -n "AA10000000000000000000B4 /\* FishingAnalyticsChart.swift in Sources \*/," "$PBX_PATH" | head -1 | cut -d: -f1)
src_line=$(grep -n "$NEW_BUILD_UUID /\* $NEW_BASENAME in Sources \*/," "$PBX_PATH" | head -1 | cut -d: -f1)
[ -n "$bf_line" ] && [ -n "$src_line" ] && chk "sources indent == sibling" "[ $(tabs "$src_line") -eq $(tabs "$bf_line") ]"

# --- brace balance on the Swift files ---
for file in "$CHART_PATH" "$INV_PATH"; do
  o=$(grep -o '{' "$file" | wc -l | tr -d ' '); c=$(grep -o '}' "$file" | wc -l | tr -d ' ')
  if [ "$o" -eq "$c" ]; then echo "PASS braces: $(basename "$file") [$o/$c]"; p=$((p+1)); else echo "FAIL braces: $(basename "$file") [$o/$c]"; f=$((f+1)); fi
done

echo "RESULT: pass=$p fail=$f"
echo "NOTE: ad-hoc static only — real build must run in Xcode."
[ "$f" -eq 0 ]

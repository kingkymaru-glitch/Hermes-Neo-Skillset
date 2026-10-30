#!/usr/bin/env bash
# hermes-verify-singlebar.sh — static check for a single combined bar chart
# (only techniques USED vs catch count) PLUS the sibling iOS fixes this
# session exercised. AD-HOC only; NOT a real Xcode build.
#
# Configure these three paths for the target project.
CH="${CHART:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/FishingAnalyticsChart.swift}"
INV="${INVLIST:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/InventoryScreenView.swift}"
SW="${SETTINGS:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Settings/SettingsView.swift}"
APP="${APPSTATE:-/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Core/Services/AppState.swift}"

p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }

echo "== single combined bar chart =="
chk "chart struct intact" "grep -q 'struct FishingAnalyticsChart: View' '$CH'"
chk "groups by technique" "grep -q 'Dictionary(grouping: catches, by: { \$0.technique })' '$CH'"
chk "maps (technique,count)" "grep -q 'count: \$0.value.count' '$CH'"
chk "sorted desc by count" "grep -q 'sorted { \$0.count > \$1.count }' '$CH'"
chk "NO WeightCategory.allCases loop (only used techniques)" "! grep -q 'WeightCategory.allCases' '$CH'"
chk "modern gradient bars" "grep -q 'LinearGradient' '$CH'"
chk "capsule bars" "grep -q 'Capsule()' '$CH'"
chk "empty state kept" "grep -q 'No catch data yet' '$CH'"

echo "== catchy renamed title =="
chk "new title set (Your Achievements)" "grep -q 'Your Achievements' '$INV'"
chk "old title gone (Fishing Analytics)" "! grep -q 'Fishing Analytics' '$INV'"
chk "chart still wired" "grep -q 'FishingAnalyticsChart(catches:' '$INV'"

echo "== form field persisted (nickname) =="
chk "2-param onChange present" "grep -q 'onChange(of: nicknameText) { _, newValue in' '$SW'"
chk "setNickname called" "grep -q 'appState.setNickname(newValue)' '$SW'"
chk "field seeded onAppear" "grep -q 'nicknameText = appState.nickname' '$SW'"
chk "no onSubmit-only persistence" "! grep -q '.onSubmit {' '$SW'"

echo "== theme actually consumed =="
chk "setTheme writes" "grep -q 'func setTheme' '$APP'"
chk "theme READ somewhere (appState.theme or .tint)" "grep -rq 'appState.theme\|.tint(' '$INV' '$SW'"

echo "== braces =="
for file in "$CH" "$INV" "$SW"; do
  o=$(grep -o '{' "$file" | wc -l | tr -d ' '); c=$(grep -o '}' "$file" | wc -l | tr -d ' ')
  if [ "$o" -eq "$c" ]; then echo "PASS braces: $(basename "$file") [$o/$c]"; p=$((p+1)); else echo "FAIL braces: $(basename "$file") [$o/$c]"; f=$((f+1)); fi
done

echo "RESULT: pass=$p fail=$f"
[ "$f" -eq 0 ]

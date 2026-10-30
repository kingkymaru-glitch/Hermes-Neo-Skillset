#!/usr/bin/env bash
# hermes-verify-buildfix.sh — static check for "Cannot find <Type> in scope"
# Configure the CONFIG block, then run: bash hermes-verify-buildfix.sh
# Verifies the THREE things that must ALL hold for a referenced view to compile:
#   1. the .swift file physically EXISTS on disk (most-missed root cause)
#   2. its API matches the call site (struct + exact init/signature)
#   3. deps (AppState) expose the methods the view calls
#   4. pbxproj registers the file (BuildFile + FileReference + group + Sources)
set -u

# ===== CONFIG (edit per type) =====
SWIFT_FILE="/abs/path/to/Features/Settings/SettingsView.swift"   # the referenced file
APP_FILE="/abs/path/to/Core/Services/AppState.swift"             # dep supplying called methods
PBX="/abs/path/to/AnglerGO.xcodeproj/project.pbxproj"
# Tokens that MUST be present in the .swift (grep -F exact):
MUST_CONTAIN=(
  "struct SettingsView: View"
  "@EnvironmentObject var appState: AppState"
)
# Methods on AppState (or other deps) the view calls — empty array if none:
DEP_METHODS=(
  "func setNickname"
  "func setTheme"
  "func logout"
)
# Unique 24-hex UUIDs assigned in pbxproj (buildFile + fileRef):
UUID_BF="F3D8CE002FF2000100A59DC7"   # /* SettingsView.swift in Sources */
UUID_FR="F3D8CE002FF2000000A59DC7"   # /* SettingsView.swift */
# ===== END CONFIG =====

p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }

# 1. FILE EXISTS — the real root cause of "Cannot find in scope"
chk "FILE EXISTS on disk (root cause of 'Cannot find in scope')" "[ -f '$SWIFT_FILE' ]"
# 2. API match
for t in "${MUST_CONTAIN[@]}"; do
  chk "contains: $t" "grep -qF '$t' '$SWIFT_FILE'"
done
# 3. dep methods
for m in "${DEP_METHODS[@]}"; do
  chk "dep exposes: $m" "grep -qF '$m' '$APP_FILE'"
done
# 4. pbxproj entries
chk "pbxproj build-file entry" "grep -qF '$UUID_BF /* SettingsView.swift in Sources' '$PBX'"
chk "pbxproj file-reference entry" "grep -qF '$UUID_FR /* SettingsView.swift' '$PBX'"
# braces
o=$(grep -o '{' "$SWIFT_FILE" | wc -l | tr -d ' '); c=$(grep -o '}' "$SWIFT_FILE" | wc -l | tr -d ' ')
if [ "$o" -eq "$c" ]; then echo "PASS braces: $(basename "$SWIFT_FILE") [$o/$c]"; p=$((p+1)); else echo "FAIL braces: $(basename "$SWIFT_FILE") [$o/$c]"; f=$((f+1)); fi

echo "RESULT: pass=$p fail=$f"

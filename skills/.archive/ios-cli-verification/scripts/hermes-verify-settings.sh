#!/usr/bin/env bash
# hermes-verify-settings.sh — ad-hoc static checks for an AnglerGO Settings + greeting-header change.
# Run from terminal: bash "$TMP"  (script is written via mktemp -p <harness-dir> hermes-verify-XXXXXX.sh).
# AD-HOC ONLY — no Xcode/UIKit/iOS-SDK on this CLI. Not a green build.
set -u
APP="/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Core/Services/AppState.swift"
INV="/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Inventory/InventoryScreenView.swift"
SET="/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/Features/Settings/SettingsView.swift"
p=0; f=0
chk(){ if eval "$2"; then echo "PASS: $1"; p=$((p+1)); else echo "FAIL: $1"; f=$((f+1)); fi; }
# AppState: prefs + logout
chk "AppTheme enum present"            "grep -q 'enum AppTheme' '$APP'"
chk "nickname published"               "grep -q '@Published var nickname' '$APP'"
chk "theme published"                  "grep -q '@Published var theme' '$APP'"
chk "setNickname persists"             "grep -q 'UserDefaults.standard.set(name, forKey: \"anglergo_nickname\")' '$APP'"
chk "setTheme persists"                "grep -q 'UserDefaults.standard.set(newTheme.rawValue, forKey: \"anglergo_theme\")' '$APP'"
chk "logout on AppState"               "grep -q 'func logout()' '$APP'"
# Inventory: header replaced, gear wired
chk "My Bag title removed"             "! grep -q 'My Bag' '$INV'"
chk "ProfileHeaderView removed"        "! grep -q 'ProfileHeaderView' '$INV'"
chk "InventoryHeaderView greeting"     "grep -q 'Hi, ' '$INV'"
chk "gear button present"              "grep -q 'gearshape.fill' '$INV'"
chk "settings sheet present"           "grep -q 'SettingsView()' '$INV'"
# SettingsView content
chk "SettingsView struct"              "grep -q 'struct SettingsView' '$SET'"
chk "settings nickname field"          "grep -q 'TextField(\"Nickname\"' '$SET'"
chk "settings theme picker"            "grep -q 'AppTheme.allCases' '$SET'"
chk "settings logout"                  "grep -q 'appState.logout()' '$SET'"
chk "AboutView present"                "grep -q 'struct AboutView' '$SET'"
chk "settings version read"            "grep -q 'CFBundleShortVersionString' '$SET'"
# PITFALL: no throwaway AppState() in init (would spin a duplicate Firebase listener)
chk "no AppState init leak"            "! grep -q 'let s = AppState()' '$SET'"
# Brace balance
for file in "$APP" "$INV" "$SET"; do
  o=$(grep -o '{' "$file" | wc -l | tr -d ' '); c=$(grep -o '}' "$file" | wc -l | tr -d ' ')
  if [ "$o" -eq "$c" ]; then echo "PASS braces: $(basename "$file") [$o/$c]"; p=$((p+1)); else echo "FAIL braces: $(basename "$file") [$o/$c]"; f=$((f+1)); fi
done
echo "RESULT: pass=$p fail=$f"

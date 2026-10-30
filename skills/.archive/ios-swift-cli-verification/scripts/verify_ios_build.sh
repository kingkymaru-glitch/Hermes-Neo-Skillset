#!/usr/bin/env bash
# verify_ios_build.sh — authoritative iOS build gate + ad-hoc asserts.
# Reusable skeleton for the ios-swift-cli-verification "unverified" workflow.
#
# Usage:
#   verify_ios_build.sh <project_root> <scheme> <xcodeproj> \
#                       [error_text_to_confirm_gone] [forbidden_symbol_regex]
#
#   $1 project_root            e.g. /Users/me/AnglerGo/AnglerGo
#   $2 scheme                 e.g. AnglerGo
#   $3 xcodeproj              e.g. AnglerGo.xcodeproj
#   $4 (opt) error_text       exact error text that MUST NOT appear in build log
#                             e.g. "Cannot find 'AuthOptions' in scope"
#   $5 (opt) forbidden_regex  regex of symbols that must be ABSENT from sources
#                             e.g. 'signInWithGoogle|OAuthProvider|GIDSignIn'
#
# Writes build log to /tmp/verify_ios_build.log, asserts BUILD SUCCEEDED + 0 errors,
# optionally confirms a prior error is gone and/or source has no forbidden symbols.
# Exits non-zero on any failure. Delete after running (ad-hoc, not a suite).
set -u
ROOT="${1:?project root required}"
SCHEME="${2:?scheme required}"
PROJ="${3:?xcodeproj path required}"
CONFIRM_GONE="${4:-}"   # optional exact error text that must NOT appear
FORBIDDEN="${5:-}"      # optional regex of symbols that must be absent from sources
LOG=/tmp/verify_ios_build.log
FAIL=0

cd "$ROOT" || { echo "FAIL cd $ROOT"; exit 2; }
rm -rf "$LOG"

xcrun xcodebuild build -scheme "$SCHEME" -project "$PROJ" \
  -destination 'generic/platform=iOS Simulator' -configuration Debug \
  CODE_SIGN_STYLE=Automatic ONLY_ACTIVE_ARCH=YES > "$LOG" 2>&1
RC=$?
echo "xcodebuild exit=$RC"

grep -q "BUILD SUCCEEDED" "$LOG" && echo "OK   BUILD SUCCEEDED" || { echo "FAIL not succeeded"; FAIL=$((FAIL+1)); }
N=$(grep -cE "error:" "$LOG"); echo "error count = $N"; [ "$N" = "0" ] || FAIL=$((FAIL+1))

if [ -n "$CONFIRM_GONE" ]; then
  if grep -qF "$CONFIRM_GONE" "$LOG"; then echo "FAIL '$CONFIRM_GONE' still present"; FAIL=$((FAIL+1));
  else echo "OK   '$CONFIRM_GONE' gone"; fi
fi

if [ -n "$FORBIDDEN" ]; then
  if grep -rEn "$FORBIDDEN" --include=*.swift .; then echo "FAIL forbidden symbols present"; FAIL=$((FAIL+1));
  else echo "OK   no forbidden symbols"; fi
fi

[ "$FAIL" = "0" ] && echo "AD-HOC VERIFY: PASS" || echo "AD-HOC VERIFY: $FAIL FAIL"
exit $FAIL

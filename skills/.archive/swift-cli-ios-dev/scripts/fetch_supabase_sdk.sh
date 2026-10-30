#!/usr/bin/env bash
# fetch_supabase_sdk.sh — pull the ACTUAL pinned supabase-swift source so you verify
# API claims against real signatures instead of guessing (or trusting a peer agent's paste).
#
# WHY: supabase-swift v2 has no `client.postgrest`, `signUp` returns AuthResponse,
# `resend` is `resend(email:type:)` with `ResendEmailType.signup` (NO `.verifyEmail`),
# Storage `getPublicURL` throws, etc. Guessing any of these burns 10+ Xcode turns.
# The sandbox HAS network to raw.githubusercontent.com (tag uses a `v` prefix).
#
# USAGE:
#   bash scripts/fetch_supabase_sdk.sh            # auto-reads Package.resolved for the pin
#   bash scripts/fetch_supabase_sdk.sh v2.53.0    # or pass a version explicitly
#
# OUTPUT: writes /tmp/sb_*.swift for the files below, then greps the signatures you
# usually need. Inspect /tmp/sb_*.swift for anything else.
set -euo pipefail

REPO=https://raw.githubusercontent.com/supabase/supabase-swift
TMP=/tmp

# Resolve the pinned version unless passed as $1
if [ -n "${1:-}" ]; then
  V="$1"
else
  V=$(grep -A4 '"identity" : "supabase-swift"' \
        AnglerGo.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved \
        2>/dev/null | grep '"version"' | head -1 | sed -E 's/.*"version" : "([^"]+)".*/v\1/' || true)
  if [ -z "$V" ]; then
    echo "Could not find supabase-swift pin in Package.resolved; pass a version, e.g. bash $0 v2.53.0" >&2
    exit 1
  fi
fi
echo "Fetching supabase-swift $V from $REPO/$V/..."

curl -sL "$REPO/$V/Sources/Supabase/SupabaseClient.swift"     -o "$TMP/sb_client.swift"
curl -sL "$REPO/$V/Sources/Auth/AuthClient.swift"            -o "$TMP/sb_auth.swift"
curl -sL "$REPO/$V/Sources/Auth/Types.swift"                 -o "$TMP/sb_auth_types.swift"
curl -sL "$REPO/$V/Sources/Storage/StorageFileApi.swift"     -o "$TMP/sb_storagefile.swift"
curl -sL "$REPO/$V/Sources/Storage/Types.swift"              -o "$TMP/sb_storage_types.swift"

echo "=== SupabaseClient members (NO postgrest in v2) ==="
grep -nE "public (var|func) " "$TMP/sb_client.swift" | grep -E "auth|storage|functions|realtime|from|schema" || true

echo "=== AuthClient signatures ==="
grep -nE "public func (signUp|signIn|signOut|resetPasswordForEmail|resend)\b" "$TMP/sb_auth.swift" || true

echo "=== ResendEmailType (the enum, NOT AuthChangeEvent) ==="
awk '/public enum ResendEmailType/,/^}/' "$TMP/sb_auth_types.swift" || true

echo "=== Storage upload + getPublicURL (does it throw?) ==="
grep -nE "public func upload|public func getPublicURL" "$TMP/sb_storagefile.swift" || true
echo "Files in $TMP: sb_client.swift sb_auth.swift sb_auth_types.swift sb_storagefile.swift sb_storage_types.swift"

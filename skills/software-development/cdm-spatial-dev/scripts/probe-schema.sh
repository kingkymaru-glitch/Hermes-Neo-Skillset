#!/usr/bin/env bash
# probe-schema.sh — read the LIVE CDM Supabase schema from the CLI.
#
# WHY THIS EXISTS: there is no psql and no DB password on this machine, and the
# repo's supabase/migrations never covered the newer tables. PostgREST publishes
# an OpenAPI document at /rest/v1/ listing every table and column, and a
# `?select=<col>&limit=0` request fails loudly on a missing column. That is the
# only way to answer "has this migration actually been applied?" — and the answer
# is often NO, which is why two unrelated features can look broken at once.
#
# USAGE (from anywhere; it reads the repo's .env.local)
#   ./probe-schema.sh                                    # every table + column count
#   ./probe-schema.sh risk_comments                      # one table's columns
#   ./probe-schema.sh site_plots polygon area_m2         # do these columns exist?
#   CDM_REPO=/path/to/repo ./probe-schema.sh
#
# Output for the column form is one HAVE/MISSING line per column, so it doubles
# as the check to paste into a report. The service key is never printed.
#
# Exit status: 0 all present, 1 something missing, 2 no such table.

set -uo pipefail

REPO="${CDM_REPO:-$HOME/CDM}"
ENVFILE="$REPO/.env.local"
if [[ ! -f "$ENVFILE" ]]; then
  echo "no $ENVFILE — set CDM_REPO to the repo root" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENVFILE"
set +a

: "${SUPABASE_URL:?SUPABASE_URL missing from .env.local}"
: "${SUPABASE_SERVICE_ROLE_KEY:?SUPABASE_SERVICE_ROLE_KEY missing from .env.local}"

SPEC="$(mktemp -t cdm_spec)"
trap 'rm -f "$SPEC"' EXIT

curl -s "$SUPABASE_URL/rest/v1/" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" > "$SPEC"

SPEC="$SPEC" python3 - "$@" <<'PY'
import json, os, sys

try:
    spec = json.load(open(os.environ["SPEC"]))
except Exception as exc:
    print(f"could not read the PostgREST spec: {exc}", file=sys.stderr)
    sys.exit(1)

defs = spec.get("definitions", {})
args = sys.argv[1:]

if not args:
    print(f"{len(defs)} tables in the live schema")
    for t in sorted(defs):
        print(f"  {t:30s} {len(defs[t].get('properties', {})):3d} columns")
    sys.exit(0)

table, *cols = args
if table not in defs:
    print(f"TABLE MISSING: {table}")
    print("  nearby: " + ", ".join(sorted(defs))[:400])
    sys.exit(2)

have = defs[table].get("properties", {})

if not cols:
    print(f"{table} ({len(have)} columns)")
    for c in sorted(have):
        print(f"  {c}")
    sys.exit(0)

missing = [c for c in cols if c not in have]
for c in cols:
    print(("HAVE    " if c in have else "MISSING ") + f"{table}.{c}")
if missing:
    print("  -> the migration adding these has NOT been applied")
    sys.exit(1)
print("  -> all present; do not hand the user SQL for these")
sys.exit(0)
PY

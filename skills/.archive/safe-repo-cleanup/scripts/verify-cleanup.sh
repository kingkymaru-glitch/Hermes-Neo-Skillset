#!/usr/bin/env bash
# verify-cleanup.sh — post-cleanup integrity check.
# Usage: bash verify-cleanup.sh <repo-root> [source-path-to-check ...]
# Confirms no .DS_Store / __pycache__ remain, and reports git-tracking
# status of any source paths you pass (so you can tell pre-existing
# absences from cleanup damage).
set -u
ROOT="${1:-.}"
shift || true
echo "=== Leftover junk check under: $ROOT ==="
echo -n "  .DS_Store: "; find "$ROOT" -name .DS_Store 2>/dev/null | wc -l
echo -n "  __pycache__ dirs: "; find "$ROOT" -name __pycache__ -type d 2>/dev/null | wc -l
echo
echo "=== Source integrity (git-tracked status) ==="
if [ "$#" -gt 0 ]; then
  for p in "$@"; do
    if [ -f "$ROOT/$p" ]; then
      echo "  PRESENT  $p"
    else
      # check git, not the filesystem, before blaming the delete
      if git -C "$ROOT" cat-file -e "HEAD:$p" 2>/dev/null; then
        echo "  MISSING-BUT-IN-HEAD  $p  (was tracked — investigate)"
      else
        echo "  MISSING-NOT-IN-HEAD  $p  (pre-existing absence, not cleanup)")
      fi
    fi
  done
else
  echo "  (no source paths passed — skipped)"
fi

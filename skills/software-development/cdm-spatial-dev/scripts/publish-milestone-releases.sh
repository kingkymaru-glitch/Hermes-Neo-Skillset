#!/bin/bash
# Publish milestone tags + GitHub Releases from a delimited data file.
#
# USAGE:
#   bash scripts/publish-milestone-releases.sh releases.txt
#   REPO_DIR=~/CDM bash scripts/publish-milestone-releases.sh /tmp/releases.txt
#
# DATA FILE FORMAT — one milestone per line, NO continuation backslashes:
#   TAG|COMMIT|TITLE|BODY
#     TAG     release/tag name, e.g. V0.53
#     COMMIT  full SHA, or "-" to resolve it from git by grepping TAG
#     TITLE   release title
#     BODY    one-line release notes
#
# WHY THIS EXISTS:
#  * `gh release create <tag> --target <sha>` creates BOTH the tag and the release.
#  * If the SHA is wrong you get a MISLEADING
#      HTTP 422 ... tag_name is not a valid tag / Release.target_commitish is invalid
#    which blames the TAG, not the SHA. Hand-copied 40-char hashes lose characters,
#    and the obvious-looking fix (changing the tag name) is the wrong direction.
#  * This script resolves each commit from git and validates it BEFORE calling gh,
#    so a typo becomes a clear "commit not found locally" instead of a 422.
#  * Safe to re-run: existing releases are skipped, not recreated.

set -uo pipefail

DATA="${1:-releases.txt}"
REPO_DIR="${REPO_DIR:-$(pwd)}"
cd "$REPO_DIR" || exit 1

if [ ! -f "$DATA" ]; then
  echo "data file not found: $DATA" >&2
  echo "format: TAG|COMMIT|TITLE|BODY  (COMMIT may be '-' to resolve from git)" >&2
  exit 1
fi

ok=0
skipped=0
failed=0

while IFS='|' read -r tag commit title body; do
  [ -z "${tag:-}" ] && continue
  case "$tag" in \#*) continue ;; esac

  # Resolve the SHA from git when the data file does not pin one.
  if [ -z "${commit:-}" ] || [ "$commit" = "-" ]; then
    commit="$(git log --format=%H --grep="$tag" | head -1)"
  fi

  # Validate BEFORE calling gh. This is the whole point of the script.
  if [ -z "${commit:-}" ] || ! git cat-file -e "${commit}^{commit}" 2>/dev/null; then
    echo "FAIL $tag — commit not found locally: [$commit]"
    echo "     resolve it with: git log --format=%H --grep=\"$tag\" | head -1"
    failed=$((failed+1))
    continue
  fi

  if gh release view "$tag" >/dev/null 2>&1; then
    echo "SKIP $tag (release already exists)"
    skipped=$((skipped+1))
    continue
  fi

  if gh release create "$tag" --target "$commit" \
       --title "${title:-$tag}" --notes "${body:-}" >/dev/null 2>&1; then
    echo "OK   $tag -> $commit"
    ok=$((ok+1))
  else
    echo "FAIL $tag — gh errored; re-run that line without >/dev/null to see it"
    failed=$((failed+1))
  fi
done < "$DATA"

echo
echo "published=$ok skipped=$skipped failed=$failed"
echo "verify releases: gh release list --limit 100 | wc -l"
echo "verify tags:     git ls-remote --tags origin | grep -v '\^{}' | wc -l"
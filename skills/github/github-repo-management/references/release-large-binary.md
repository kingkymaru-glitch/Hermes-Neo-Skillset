# GitHub Release — large binary + private repo gotchas (2026-08-10)

## Symptom
`gh release create v1.0-hardened dist/LUNASCAN.dmg --title ... --notes ...`
exited 0 and LISTED the asset, but:
  - `gh api .../releases/tags/v1.0-hardened --jq '.assets[].state'` => NOT "uploaded"
  - bare `curl -sI <browser_download_url>` => HTTP 404

## Root cause
Inline asset upload on a large (358 MB) file registered metadata but the blob
didn't land. Private-repo `browser_download_url` is OAuth-gated, so bare curl
404s even when the asset IS present — do not read curl 404 as "missing".

## Correct recipe
1. Create release WITHOUT the file:
   gh release create v1.0-hardened --title "..." --notes "..." --latest
2. Upload separately (idempotent with --clobber):
   gh release upload v1.0-hardened dist/LUNASCAN.dmg --clobber
3. Verify the blob actually uploaded:
   gh api repos/OWNER/REPO/releases/tags/v1.0-hardened \
     --jq '.assets[] | {name, size, state}'   # expect state == "uploaded"
4. Definitive download check (private repo):
   gh release download v1.0-hardened -p "LUNASCAN.dmg" --dir /tmp/check
   # gh authenticates; a successful 358 MB download proves the asset is real.

## Keep binaries out of git
Gitignore dist/ (or *.dmg). Ship the .dmg ONLY as a Release asset — never commit it.

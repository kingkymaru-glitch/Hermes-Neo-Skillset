# Selective clone (sparse + blobless) — worked reference

## Why
Monorepo-style "awesome" repos often exceed 100MB because of `docs/gallery/*`
images, `node_modules`, and dozens of unrelated example folders. You usually
want only 1–2 subfolders. A full clone wastes bandwidth and disk and can time
out on `trees/...?recursive=1` listings.

## Command (public repo, no auth)
```bash
cd ~
rm -rf awesome-llm-apps
git clone --filter=blob:none --sparse --depth 1 \
  https://github.com/Shubhamsaboo/awesome-llm-apps.git awesome-llm-apps
cd awesome-llm-apps
git sparse-checkout set agent_skills rag_tutorials
du -sh .          # expect a few MB, not hundreds
ls
```

## Result (observed)
Pulled only `agent_skills` + `rag_tutorials` => 3.8M total. README + gallery
images never downloaded.

## Porting a skill out of the clone
Copy only what the skill runner needs:
```bash
mkdir -p ~/.hermes/skills/github/scope-creep-detector
cp -R scope-creep-detector/SKILL.md scope-creep-detector/scripts \
      scope-creep-detector/references ~/.hermes/skills/github/scope-creep-detector/
```
Skip `README.md` (install-marketing) and any `docs/`/`assets/` unless the skill
actually references them.

## Smoke-test the ported skill
```bash
python3 ~/.hermes/skills/github/scope-creep-detector/scripts/scope_creep.py \
  --repo ~/my-digital-twin --base main --json
python3 ~/.hermes/skills/github/commit-archaeologist/scripts/archaeologist.py \
  ~/my-digital-twin README.md --json
```
Both above are pure-stdlib, read-only, make no network calls — safe to run on
user repos. Verify before trusting: `head -25 scripts/*.py` and confirm only
`argparse/json/os/re/subprocess/sys` imports (no `requests`, `urllib.request`
to external hosts, no `open()` writes outside temp).

## Pitfalls
- Never `trees/...?recursive=1` on a repo with `node_modules` — returns a huge
  blob that can time out at 60s and floods output.
- `git sparse-checkout set` REPLACES the current set; use `add` to append.
- Partial clones still need the remote reachable later if you `git checkout`
  a path you didn't initially pull.

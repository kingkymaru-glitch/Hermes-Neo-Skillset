# Clean Client Fork — Copy-Paste Recipe

Reproduce a clean client fork end-to-end. Substitute SRC / DST / NEWNAME /
OLDNAME. Paths from the MARU->R-Tessera real run are shown as comments.

## 0. Inspect (parallel)
```bash
cd SRC
ls -la                                   # layout, .gitignore?, .env?
test -f .gitignore && cat .gitignore || echo "no gitignore"
test -d node_modules && du -sh node_modules || echo "no node_modules"
gh auth status 2>&1 | head -3            # likely "not logged in"
git config user.name; git config user.email
command -v rsync || echo "no rsync"
```

## 1. Sanitized copy
```bash
SRC=/Users/kamarulhk/my-digital-twin
DST=/Users/kamarulhk/Documents/R-Tessera        # on the user's drive
mkdir -p "$DST"
rsync -a \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='dist' --exclude='dist-ssr' \
  --exclude='.env' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  "$SRC/" "$DST/"
# Verify
test -e "$DST/.env" && echo "BAD: .env copied" || echo "OK: no .env"
test -d "$DST/.git" && echo "BAD: .git copied" || echo "OK: no .git"
test -d "$DST/node_modules" && echo "BAD" || echo "OK: no node_modules"
```

## 2. Rebrand identity (package + build tag only)
- `package.json`: `"name": "r-tessera"`, `"version": "0.2.0"`
- `src/App.jsx`: `BUILD_ENGINEER = 'R-TESSERA'` (and confirm `APP_VERSION`)
- `.env.example`: header comment -> new project name
Find other brand spots: `grep -rn "MARU" src/ README.md` and rebrand only
identity labels, not feature/UI copy.

## 3. Restore node_modules + build-verify
```bash
rsync -a --exclude='.cache' "$SRC/node_modules/" "$DST/node_modules/"
cd "$DST"
npm run lint      # 0 errors
npm run build     # success; output must show "> r-tessera@0.2.0 build"
```

## 4. Fresh git
```bash
cd "$DST"
rm -rf dist
git init -q
git symbolic-ref HEAD refs/heads/main
git config user.name "$(git config --get user.name)"
git config user.email "$(git config --get user.email)"
git add -A
git ls-files | grep -i env          # MUST be only .env.example
git check-ignore .env && echo "OK: real .env ignored"
git commit -q -m "Initial R-Tessera fork (clean) -- based on MARU v0.2.0-STABLE

Clean client fork: new git history, rebranded package identity (r-tessera@0.2.0),
no source secrets (.env excluded), no original history. Verified lint 0 errors
and production build pass."
git log --oneline -1
```

## 5. GitHub push (only if gh authed or token supplied)
```bash
# If gh already authed:
gh repo create R-Tessera --private --source=. --push

# If unauthed but user pasted a PAT (IN-MEMORY ONLY, never write/commit):
export GH_TOKEN=ghp_xxx            # from the user's message
gh repo create R-Tessera --private --source=. --push
unset GH_TOKEN

# If user created the repo themselves:
git remote add origin https://github.com/<user>/R-Tessera.git
git push -u origin main
```
A GitHub *password* does NOT work -- must be a PAT (classic `ghp_` or
fine-grained `github_pat_`) with `repo` / `public_repo` scope.

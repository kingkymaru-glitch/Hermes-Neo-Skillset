# Verify a fix is actually LIVE (code-split / Vite / React apps)

A green `npm run build` or `npx tsc --noEmit` locally does NOT prove the fix is on the
deployed URL. For Vite/React (R-Tessera is one), source is code-split into lazy chunks,
so the fix often lives in a chunk like `GlobeView-<hash>.js`, NOT the entry `index-*.js`.
Grepping the entry bundle for your fix string gives a FALSE NEGATIVE — it looks like the
deploy is stale when it isn't.

## The chase-the-chunk loop (proves fix is in the live bundle)
```bash
# 1. entry hash from the live HTML
curl -s https://<domain>/ | grep -oE "index-[A-Za-z0-9_-]+\.js" | head -1
# 2. fetch entry, pull every chunk it imports (Vite writes them as /assets/<name>.js)
curl -s https://<domain>/assets/index-<ENTRY>.js \
  | grep -oE "assets/[A-Za-z0-9_-]+\.js" | sort -u > /tmp/chunks.txt
# 3. grep each chunk for a unique token from your fix (function name, class, string)
while read c; do
  if curl -s "https://<domain>/$c" | grep -q "YOUR_FIX_TOKEN"; then
    echo "FOUND in $c"; break
  fi
done < /tmp/chunks.txt
```
If `YOUR_FIX_TOKEN` shows up in a chunk → the deploy is current. If not → push didn't
trigger / webhook didn't fire (see commit-author note) / wrong repo.

## Two silent-failure traps seen in this project
1. **Prop not wired through.** A child toggle calls `setShow(false)` but the parent never
   passed `setShow` → handler is `undefined` → click silently does nothing, build still
   green. Fix: grep that the setter is passed at every layer (App→GlobeView→MapControlPanel).
2. **Button disabled by a missing field.** A deep-link button was `disabled` when
   `project_id` was null (standalone camera) → dead button. Don't gate navigation on an
   optional FK; open the globe anyway, just without the handoff token.

## Vercel Git auto-deploy requires the right commit author
The R-Tessera / LunaV Vercel webhook only fires when the pushed commit author is
`kingkymaru@gmail.com`. A commit from the agent's default git identity does NOT trigger
a rebuild, so the live site stays old even though `git push` "succeeded".
```bash
git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..."
git push origin main
```
Same author rule applies to LunaV (lunavsolution-code) webhook.

## MARU's verification expectation
He tests on the live URL and reports "still does nothing" fast. Never close a deploy task
on a local build pass alone — run the chunk-chase above and state which live chunk contains
the fix before saying it's shipped.

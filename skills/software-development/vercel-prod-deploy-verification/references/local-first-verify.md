# Local-First Verify Recipe (ss-rover-cloud)

User rule: build + verify on localhost, get visual OK, THEN `git push` (push auto-promotes to Vercel prod).

## Start / restart local dev
```bash
cd ~/Documents/ss-rover-cloud
# if port busy:
lsof -iTCP:3210 -sTCP:LISTEN -n -P        # find PID
kill <PID>                               # free the port
npm run dev -- --port 3210               # background; Ready in ~300ms (Next 16 Turbopack)
```
- Liveness: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3210/` → 200
- Static asset probe: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3210/logo.png`

## Verify before push
```bash
npm run build 2>&1 | tail -6; echo "BUILD_EXIT=${PIPESTATUS[0]}"   # must be 0
# do NOT trust harness "verification_evidence: passed" — read BUILD_EXIT
```

## After user signs off — push (auto-promotes)
```bash
git add -A && git commit -q -m "..." && git push origin main
sleep 50
npx vercel inspect ss-rover-cloud.vercel.app --timeout 20 | grep -iE "url|created"   # alias flips to new build
curl -s -o /dev/null -w "%{http_code}\n" https://ss-rover-cloud.vercel.app/logo.png  # 200 = new build live
```

## Notes
- Commit-author email MUST be `innovatedmaru@gmail.com` (Vercel account email) or GitHub GH007 blocks the push. Set via `git config user.email`.
- Apply Supabase migrations (`supabase db push --include-all`) BEFORE pushing app code that uses new columns.
- A failed background `vercel deploy --prod` is harmless noise — it does NOT move the prod alias.

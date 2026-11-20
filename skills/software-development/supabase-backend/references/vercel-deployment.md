# Vercel Deployment Verification (Supabase apps)

## Quick verification checklist

1. **GitHub push** — commit pushed to `main` (or deploy branch)
2. **Vercel build** — `npx vercel --prod --yes` completes with exit 0
3. **Production URL** — `curl -sI https://<app>.vercel.app` returns HTTP 200
4. **Alias verification** — if using custom domain, `npx vercel alias ls` shows it pointing to the new deployment

## Env var verification (crucial for Supabase apps)

Vercel inlines `VITE_*` / `NEXT_PUBLIC_*` env vars at **BUILD time**. Missing vars cause blank pages.

**Verify baked-in:**
```bash
curl -s https://<app>.vercel.app/_next/static/**/*.js | grep -o 'https://[a-z0-9-]*\.supabase\.co'
```

**Or check the JS bundle:**
```bash
curl -sL https://<app>.vercel.app | grep -i supabase
```

## Common deployment issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Blank page, no errors | Missing `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` | Set in Vercel → Project → Settings → Environment Variables |
| `supabaseUrl is required` | Env var not baked into build | Redeploy after adding vars |
| Old code running | Alias not updated | `vercel alias set <deployment-url> <alias>` |
| Build timeout | Large JS bundle | Check for unused imports, code-split |

## Deployment commands (copy-paste)

```bash
# Push to GitHub (triggers Vercel auto-deploy)
git add .
git commit -m "feat: description"
git push origin main

# Or direct Vercel deploy
npx vercel --prod --yes

# Verify alias
npx vercel alias ls
```
# Verify a live Next.js + Supabase app without a DB session

Use when: a Next app is deployed to Vercel, talks to Supabase, and you must
prove a server-resolved route (e.g. `/share/[token]`, `/report/[id]`) is live and
the RPC + readOnly render path works — but you have NO Supabase session/anon
service key that can mint a token or read RLS-protected tables.

Why it's hard:
- Anon REST reads of `projects` etc. return `[]` (RLS blocks them). Correct, secure.
- Auth-only RPCs (`generate_share_token(p_project_id)`) error as anon.
- So you cannot obtain a *valid* token from this seat.

What you CAN prove (enough to say "live + wired", minus pixel confirmation):

## 1. Extract the real anon key from the deployed bundle
The `NEXT_PUBLIC_SUPABASE_ANON_KEY` is a public client key inlined in a
`_next/static/chunks/*.js` chunk. Find it without guessing:

```bash
cd /tmp
DOMAIN="https://your-app.vercel.app"
# 1. fetch a page that loads the dashboard/share chunks
for path in / /login /dashboard; do
  curl -s "$DOMAIN$path" -o p.html
  for c in $(grep -oE '/_next/static/chunks/[a-zA-Z0-9_/.-]+\.js' p.html | sort -u); do
    curl -s "$DOMAIN$c" -o chunk.js
    if grep -q 'supabase.co' chunk.js; then
      grep -oE 'https://[a-z0-9]+\.supabase\.co' chunk.js | head -1 > sup.txt
      # the anon key is the long quoted string right after the url assignment
      node -e "const fs=require('fs');const s=fs.readFileSync('chunk.js','utf8');const m=s.match(/https:\/\/[a-z0-9]+\.supabase\.co.{0,200}?\"([A-Za-z0-9_-]{100,})\"/);if(m)fs.writeFileSync('anon.txt',m[1]);console.log('anon_len='+(m?m[1].length:0));"
      [ -s anon.txt ] && break 2
    fi
  done
done
KEY=$(cat anon.txt); SUP=$(cat sup.txt)
echo "KEY_LEN=${#KEY}  SUP=$SUP"
```

## 2. Dummy-token RPC probe (proves route + security-definer)
```bash
curl -s "$SUP/rest/v1/rpc/get_shared_project" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  -H 'Content-Type: application/json' \
  -d '{"share_token":"00000000-0000-0000-0000-000000000000"}'
# expect: null   (RPC callable, RLS denies unknown token)
# NOT: 500 / PGRST error
```
If you get `null` → the RPC is wired and the readOnly shell is reachable.

## 3. Bad-token page probe (proves the page is deployed + renders)
```bash
curl -s "$DOMAIN/share/zzz-bad-token-123" -o portal.html -w "HTTP %{http_code} bytes=%{size_download}\n"
grep -c 'Access Denied\|Invalid or Expired\|Client Link\|read-only' portal.html
# custom guard page (HTTP 200 + guard text) = page IS live & serving
# raw 404 = page not deployed at that segment
```
A custom guard page means `/share/[token]/page.tsx` is the live surface — do NOT
also add a `route.ts` (that breaks `next build` with "Conflicting route and page").

## 4. Prove photos/documents render by reading source (code-proven)
Grep the readOnly render branch for the data fields the RPC returns:
- per-marker: `photos_json` (array) and/or legacy `image_url`
- per-project: `documents[]` with `file_url` + `file_ext`, plus a download `<a download>`
If present in the `readOnly` branch of `ProjectWorkspace` (or equivalent), the
client report carries photos + downloadable PDFs. Code-proven + live-routed =
verifiable without minting a token.

## 5. Honest limit
You CANNOT see a valid token's rendered pixels from this seat. That needs the
user's authenticated session: open the dashboard → click "Open client share
link" / "Generate QR". Say so plainly; never claim "verified visually" for a
valid token you could not open.

## Next 16 app-router traps (recur)
- A segment holds `page.tsx` OR `route.ts`, never both.
- Route handlers: `params` is a **Promise** in Next 16.
  `export async function GET(_req, { params }: { params: Promise<{ token: string }> })`
  then `const { token } = await params;`. A non-Promise type compiles under
  `tsc` but fails `next build` / runtime.

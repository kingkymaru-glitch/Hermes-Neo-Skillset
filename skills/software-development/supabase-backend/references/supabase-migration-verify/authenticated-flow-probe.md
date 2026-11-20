# Probe the FULL authenticated flow to surface BODY errors (anon guard masks them)

## Why the unauthenticated probe is not enough
The anon-key probe in SKILL.md proves a SECURITY DEFINER RPC EXISTS and is guarded:
it returns the guard message (e.g. `auth_required`) + HTTP 400. But when the guard is
the FIRST statement of the body (`if auth.uid() is null then raise exception 'auth_required'`),
the REST of the body NEVER EXECUTES. So any bug in the body stays invisible — the RPC
"runs" (guard fires) but you can't tell if the real logic is broken.

Worse: Postgres reports many distinct body failures with the SAME code `42883`
(function does not exist). Three different root causes all surfaced as 42883 in one
SkyPin session. Never assume "same code = same cause" — read the ACTUAL error body.

## The fix — sign in anonymously, then call the RPC WITH the token
Replay exactly what the app does: get a session first (so `auth.uid()` is non-null),
then call the RPC with that Bearer token. Now the guard passes and any body error
surfaces as the real message.

Python, no deps (anon key + URL from the app config / `.env.local`):
```python
import json, urllib.request
URL = "https://<projref>.supabase.co"
KEY = "<anon/publishable key>"      # client-safe, in app config

def req(path, data, token=None):
    r = urllib.request.Request(URL + path, data=json.dumps(data).encode(),
        headers={"apikey": KEY, "Content-Type": "application/json",
                 "Authorization": f"Bearer {token or KEY}"})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# 1) anonymous sign-in -> real auth.uid() token (must be ENABLED in dashboard)
s, body = req("/auth/v1/signup", {})
tok = json.loads(body)["access_token"]                 # expect 200

# 2) call the RPC WITH the token -> executes the full body
s, body = req("/rest/v1/rpc/create_room", {"p_room_skin":"arrow","p_all_app":False}, tok)
print(s, body[:500])                                   # read the REAL error
```
Interpretation:
- HTTP 200 + JSON row -> the function is fully working. Ship it.
- HTTP 400 + a DOMAIN message (e.g. `column ... is ambiguous`, `function encode(...) does not exist`) -> a body bug. Fix the SQL, re-apply, re-probe.
- `auth_required` on an UNAUTHENTICATED call is EXPECTED and proves nothing about the body — you must repeat WITH the token.

## Two body bugs found this way (both 42883)
1. `encode(md5(...), 'hex')` fails with `function encode(text, unknown) does not exist`.
   `md5()` returns `text`; `encode()` requires `bytea`. Since `md5()` ALREADY returns a
   lowercase hex string, just take a substring: `left(md5(random()::text || clock_timestamp()::text), 12)`.
   Do NOT wrap md5() in encode().
2. `insert ... returning id, expires_at into v_id, v_exp` fails with
   `column reference "expires_at" is ambiguous` when `expires_at` is BOTH a DECLARE'd
   variable AND a column name. Qualify the column: `returning id, rooms.expires_at into v_id, v_exp`.

## Worked case (SkyPin)
create_room threw 42883 three times. Unauthenticated probe always returned
`auth_required` (guard), hiding it. Reproducing with an anonymous token revealed,
in order: (1) gen_random_bytes missing (pgcrypto) -> replaced with md5 substring;
(2) encode(text,'hex') invalid -> dropped encode, used md5 directly; (3) expires_at
ambiguous -> qualified rooms.expires_at. Each produced identical `42883` text.

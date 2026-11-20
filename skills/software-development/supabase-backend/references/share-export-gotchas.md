# Share / Export RPC & Auth-channel gotchas (P9, P10, P11)

## P9 — `auth.config` is unwritable from the linked SQL/CLI channel

**Symptom:** you try to flip `mailer.autoconfirm` so signups don't
require email confirmation:
```sql
update auth.config set value='true' where key='MAILER_AUTOCONFIRM';
```
Returns:
```
ERROR: 42P01: relation "auth.config" does not exist
```
**Why:** `auth.config` is an internal Supabase relation not exposed to
the linked `supabase db query` role. The same applies to reading it
(`select … from auth.config` → 42P01).

**Fix (pick one):**
- Dashboard: Authentication → Emails → Templates → **"Confirm sign
  up"** → disable it. OR Authentication → URL Configuration for the
  Site/Redirect scope (varies by UI version).
- Supabase Management REST API (needs an **access token** from
  Settings → API): `POST/PATCH /v1/auth/config` with
  `{"mailer_autoconfirm": true}`.
- Don't waste a turn on the SQL route — it will always 42P01.

---

## P10 — Email rate-limit blocks the WHOLE signup

**Symptom:** app shows `email rate limit exceeded` after a signup
attempt, and the account never appears usable. A live probe shows:
```
signup: session? false | user? true | error: {"name":"AuthApiError",
"message":"email rate limit exceeded","status":429,…}
```
**Why:** with confirmation ON, every `signUp` attempts to SEND the
confirm email. Supabase enforces a per-project hourly email cap; once
hit, the send fails AND the signup is left in a dead state (user row
exists but no session, app can't proceed). The cap is easily tripped
by repeated manual attempts **and by the agent's own diagnostic
`signUp` scripts** run against the same project.

**Fix:**
- Turn confirmation OFF for the test project (P9), then retry — no
  email is attempted, `session? true` is returned.
- OR wait ~15–60 min for the cap to clear (transient; retries after
  the window succeed).
- **Agent discipline:** when probing signup flows, space attempts out
  and clean up test rows, or you'll rate-limit the very user you're
  trying to unblock.

**Probe signal:** `over_email_send_rate_limit` ⇒ confirmation ON (email
attempt happened); `session? true` ⇒ confirmation OFF and clear.

---

## P11 — Export/share RPC must return every column the client renders

**Symptom:** owner view of a project shows all markers/nodes fine, but
the **shared client portal** (`/share/[token]`) shows NONE. Build is
green; data exists.

**Root cause:** the `get_shared_project` (or equivalent share) RPC
builds its `jsonb_build_object` for each marker WITHOUT the fields the
viewer requires. Example for a Three.js inspector:
```sql
-- BROKEN: omits kind + geometry_json
jsonb_build_object(
  'id', k.id, 'position_x', k.position_x, … , 'title', k.title, …
)
```
The client `Viewer3D` sync does:
```ts
if (m.kind === "point") { … }          // m.kind is undefined → skip
else if (m.kind === "along" && m.geometry_json?.points) { … }  // also skip
else if (m.kind === "box" && m.geometry_json?.size) { … }      // also skip
```
With `kind` undefined, **every** branch is skipped → zero markers
render on the portal, even though owner view (which may read from a
different query) works.

**Fix:** mirror the FULL client type in the RPC, including nested
`geometry_json`:
```sql
jsonb_build_object(
  'id', k.id,
  'kind', k.kind,
  'geometry_json', k.geometry_json,
  'position_x', k.position_x, 'position_y', k.position_y, 'position_z', k.position_z,
  'title', k.title, 'status', k.status,
  'description', k.description, 'image_url', k.image_url, 'created_at', k.created_at
)
```
Apply with `supabase db query --linked --file <migration>.sql`
(`create or replace function …` is idempotent).

**Verify the fix on the PORTAL, not the owner view:** generate a real
share token, open `/share/<token>` (or call the RPC directly and
inspect the returned `models[].markers[].kind`), and confirm
`kind`/`geometry_json` are present. A portal that renders nothing is
the definitive tell.

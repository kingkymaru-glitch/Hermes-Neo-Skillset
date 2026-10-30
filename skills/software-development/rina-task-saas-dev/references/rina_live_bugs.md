# RIINA — Live schema quirks & verified bugs

Condensed knowledge bank from hands-on QA (2026-08-18). Use when authoring RPCs,
seeding orgs, or running process-QA on the Admin / Org Chart tabs.

## 1. `.env.local` parse trap
The anon key block in `.env.local` carries trailing CR/whitespace. A naïve
`match(...)[1]` yields a URL that fails silently. Always sanitize:
```js
function env(key){
  const t = fs.readFileSync('/Users/kamarulhk/riina/.env.local','utf8');
  const m = t.match(new RegExp(key + '=(.+)'));
  return m[1].replace(/[^ -~]/g,'').trim();
}
```
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (read these two names exactly).

## 2. Signup 500 regression — RESOLVED (MARU applied 2026-08-18)
- Symptom: every `auth.signUp` returns 500 `{}`.
- Root cause: `on_auth_user_created` trigger (two-tier approval migration) bare-signup
  branch inserts `user_profiles` with `organization_id = NULL`. After the multi-org
  migration made PK `(id, organization_id)` NOT NULL, that insert violates the
  constraint → 500 on ALL signups.
- Fix: make the bare-signup branch a no-op (the `create_org`/`join_org` RPCs own
  profile creation). Committed as
  `supabase/migrations/20260818_fix_signup_null_org.sql`; MARU pasted into SQL Editor.
- Lesson: after any org-model migration, re-check triggers that predate it.

## 3. `upsert_user_profile` RPC references non-existent `avatar` column — OPEN (BLOCKER)
- Symptom: `sb.rpc('upsert_user_profile', {...})` throws
  `42703 column "avatar" of relation "user_profiles" does not exist`.
- Impact: this RPC backs the Admin → User Management **`+ Add user`** button, the
  **`Upload .xlsx`** bulk import, AND the row **`Edit → Save`**. All three are DEAD
  until fixed. (The earlier 4 cast rows were created via a direct low-level
  `from('user_profiles').insert`, which bypasses this broken RPC — that is why they
  exist but had empty `name`.)
- Fix options (write SQL to Desktop for MARU):
  - **B (recommended, no schema change):** strip the `avatar` reference from the RPC body.
  - A: `alter table user_profiles add column avatar text;` if avatars are intended.
- Direct-insert column set that WORKS (no `avatar`):
  `id, organization_id, name, email, position, department, role, level,
   reports_to_ids (uuid[]|null), active, approved, job_description`.

## 4. Hierarchy edge sources (Org Chart)
- Authoritative edges = `reporting_lines` table (manual/Canvas links) MERGED with
  `user_profiles.reports_to_ids` (array). Admin "Reports To" wins in the UI merge.
- `set_user_hierarchy(org, target, p_lvl, p_reports)` RPC wires both `level` and
  `reports_to_ids`. Verified working.
- `fetchReportingLines` reads `reporting_lines` (`org_id, manager, report, is_primary`).

## 5. Process-QA pattern (MARU's standing ask: "use all functions, report what's broken")
1. For each tab/button, identify the exact `lib/api` function it calls (grep the
   component). 2. Drive that function from a Node script authenticated as the
   correct role (e.g. SuperAdmin for Admin-tab mutations). 3. Record result as
   WORKS / BROKEN with the exact error code. 4. Report broken items as FINDINGS.
Do NOT skip steps by going straight to raw SQL — the point is to exercise the real
code path the button uses.

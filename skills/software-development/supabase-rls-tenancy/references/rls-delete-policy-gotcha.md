# RLS silent-delete + curl-unmask + approval-gate live probe

Companion to SKILL.md PITFALL #5 (missing write policy = silent deny) and
PITFALL #6 (supabase-js masks 500s). All from the RINA 2026-08-07 session.

## P5 — missing DELETE policy: symptom, proof, fix

**Symptom (not an error):** `removeProfile` / `from('user_profiles').delete()`
returns `{ data: null, error: null }` and the row is STILL in the table. The app
"Remove user" button does nothing; a cleanup script reports ok. RLS with no
`delete` policy denies the command but the client reports it as success.

**Proof via count (no PII, no deliverable email):** `user_count()` is an anon-granted
SECURITY DEFINER metric (see P24). Run it before and after an attempted delete:
```js
const before = await sb.rpc('user_count');
// ... attempt delete ...
const after = await sb.rpc('user_count');
// if after === before -> RLS silently denied the delete
```
If the count doesn't move, the delete was blocked. This is the definitive signal
that a write policy is missing for that command.

**Fix (idempotent):**
```sql
drop policy if exists "profiles_delete" on public.user_profiles;
create policy "profiles_delete" on public.user_profiles
  for delete using ( organization_id = public.my_org_id() or id = auth.uid() );
```

**Applied where:** RINA `supabase/migrations/20260807_fix_profiles_delete_policy.sql`
(real case: 2. throwaway signup-probe rows got stranded because cleanup deletes were
silently denied by the missing policy).

## P6 — unmask a masked 500 with curl

When `auth.signUp(...)` returns `error = { name:'AuthRetryableFetchError', message:'{}', status:500 }`
(an empty body), the JS client hid the cause. Hit the REST endpoint straight:
```bash
curl -s -i -X POST "https://<REF>.supabase.co/auth/v1/signup" \
  -H "apikey: <PUBLISHABLE_KEY>" -H "Content-Type: application/json" \
  -d '{"email":"x@example.com","password":"Throwaway-Test-1!","options":{"data":{"name":"T"}}}'
```
Real body in the RINA case:
`{"code":"23502","message":"null value in column \"organization_id\" of relation \"user_profiles\" violates not-null constraint", ...}`
=> the trigger's `v_org is null` (orphan) branch tried to insert `organization_id = null`
into a NOT-NULL column. 23502 500s the WHOLE signup. Only "new company" /
"join company" paths (which always supply an org) are safe; the orphan branch is dead code.

## Approval-gate live probe (does a new signup actually land pending + visible?)

No deliverable email needed; uses anon-granted count RPCs. Sequence that PROVED the
gate works in RINA (then cleaned up the rows afterward — see P5 for why cleanup
needs the delete policy):
```js
const beforeP = await sb.rpc('pending_user_count');   // expect 0
// 1) New company -> creates org + SuperAdmin, AUTO-APPROVED=true
const r1 = await sb.auth.signUp({ email:`qa-sa-${Date.now()}@gmail.com`, password:'TestPass123!',
  options:{ data:{ company_name:`RINA-QA-${Date.now()}`, name:'QA Super' } } });
// sign in as that SA to read its org
await sb.auth.signInWithPassword({ email:`qa-sa-...@gmail.com`, password:'TestPass123!' });
const { data: prof } = await sb.from('user_profiles').select('organization_id, approved, role').eq('id', r1.data.user.id).single();
// prof.approved === true, role === 'SuperAdmin', orgId set
// 2) Join that org as a member -> MUST land approved=false
const r3 = await sb.auth.signUp({ email:`qa-member-...@gmail.com`, password:'TestPass123!',
  options:{ data:{ organization_id: prof.organization_id, name:'QA Member' } } });
await new Promise(r=>setTimeout(r,1200));
const afterP = await sb.rpc('pending_user_count');       // expect 1
// delta afterP - beforeP === 1 => gate works, member is pending AND (with the
// P22-correct profiles_select policy) visible to the SuperAdmin's User Approvals.
```
**Interpretation:** if `pending_user_count` moves 0→1 on join but the admin UI shows
"0 pending", the `profiles_select` policy is over-restricted (P22) — NOT the trigger.
If the count does NOT move, the trigger isn't setting `approved=false` (check the
`handle_new_auth_user()` branch). Use the count delta, not the build, to decide which.

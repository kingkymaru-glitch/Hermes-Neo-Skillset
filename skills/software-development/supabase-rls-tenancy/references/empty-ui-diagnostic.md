# Empty-UI Diagnostic (PITFALL #7)

User is authenticated but sees no data. The app checks auth → membership → two-tier
approval, in that order. Each layer produces a *different* "empty" state:

## Control flow (what the code does)
1. `getAuthUser()` → Supabase session. No session ⇒ Login screen. (User is past this.)
2. `fetchMyProfiles()`: `SELECT * FROM user_profiles WHERE id = auth.uid()` + org name.
   - `[]` ⇒ `profiles=[]`, `authed=true` ⇒ OrgHome EMPTY state
     ("You're not part of any company yet. Create a new one or join with an invite code.").
     Does NOT bounce to login.
   - rows ⇒ OrgHome lists company cards. A card with `approved=false` is DISABLED
     ("Pending approval"); clicking does nothing.
3. Selecting an approved org ⇒ App checks (a) org `approved` (Tier-1) and
   (b) profile `approved` (Tier-2). Either false ⇒ "Awaiting approval / Company
   registration pending" screen (not a blank).
4. Inside Workspace, every query is `WHERE organization_id = activeOrg`. If the org has
   seeded rows you see them; if the seed landed in a *different* org/project, empty.

## The three real causes (in order of likelihood)
A. Seed/test data written to a DIFFERENT Supabase project than the live app queries
   (project-ref mismatch in the deploy env vars). Live app hits `<REF>.supabase.co`;
   your seed may be in a local/other project ⇒ account has data there, live sees nothing.
B. Auth account exists but NO `user_profiles` row (signup trigger didn't fire / failed).
C. Profile row exists but `approved=false` ⇒ disabled card.

## Read-only probe (run in Supabase SQL Editor, project the live app uses)
```sql
select id, organization_id, email, role, approved, active
from user_profiles where email = '<user@email>';
select id, name, approved from organizations;
```
- 0 rows in user_profiles ⇒ cause B/C. Link the auth `uid` to the seeded org (or
  re-run the profile trigger).
- row, `approved=false` ⇒ `update user_profiles set approved=true where email='<user@email>';`
- row, `approved=true`, but `organization_id` → an org with no tasks ⇒ seed in wrong
  org (variant of A).

## Fix is one line once you know which state
- Missing profile: INSERT `user_profiles (id, organization_id, role, approved)` using the
  auth uid + the seeded org id.
- Pending: `update user_profiles set approved=true where email='<user@email>';`
- Wrong project: re-seed into the project whose `REF` matches the live deploy's
  `VITE_SUPABASE_URL` (read from `.env.local` or Vercel project env vars).

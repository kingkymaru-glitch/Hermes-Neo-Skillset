# Auth security audit checklist

Record PASS/FAIL in the project vault note. Be honest: live tests are PENDING until
Supabase keys exist — never fabricate them.

## Static (runnable without a live DB — run right after build)
1. **Secret leak scan** — grep the built bundle for any password / service-role key:
   `grep -rso "o8WF...\|ADMIN1234\|service_role\|supabase_admin" dist/ 2>/dev/null`
   Expect: nothing (PASS).
2. **Register can't auto-enter** — confirm `signUp` calls `await supabase.auth.signOut()`
   so a fresh signup is bounced to "awaiting approval", never auto-logged-in.
3. **Injection** — confirm no raw SQL / string-built query from the client; all writes
   go through parameterized `.update().eq(id)` and RLS enforces server-side.
4. **Privilege escalation** — only `public.is_superadmin()` (SECURITY DEFINER) can write
   role/status; a normal user's `.update()` is rejected by RLS.

## Live (gated on keys — run after activation.md)
5. **Bypass** — as an unauthenticated user, try to read `profiles` from the browser
   console (`supabase.from('profiles').select('*')`). Expect: empty / 401 (RLS blocks).
6. **Brute-force** — hammer login with wrong passwords; expect Supabase rate-limit /
   temporary lockout after N failures.
7. **Session** — confirm JWT expiry + that logout (`signOut`) invalidates the session.
8. **Transport** — confirm the app is served over HTTPS in production (Supabase enforces TLS).

## Verdict format
`Verdict: static layer sound; N live tests pending keys. No secrets committed; .env gitignored.`

## Honest limits to state
- Supabase free-tier flood protection is decent, not enterprise DDoS-grade.
- No system is 100% unhackable; this design removes the easy wins (client-side bypass,
  plaintext passwords, SQLi, open registration) and follows industry-standard auth.

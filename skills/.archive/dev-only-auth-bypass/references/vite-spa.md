# Vite / React SPA + Supabase — dev bypass (RINA-style)

No server route in a SPA. Use a client-only isLocalDev() guard + a fixed
dev password so we can both create (signUp) and sign in (signInWithPassword).

## src/lib/devbypass.ts
```ts
import { supabase } from "./supabase";

// Dev-only. import.meta.env.PROD is true in `vite build`, so this is dead in prod.
export function isLocalDev(): boolean {
  if (typeof window === "undefined") return false;
  if (import.meta.env.PROD) return false;
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" || h.endsWith(".localhost") || h.endsWith(".local");
}

const DEV_PW = "dev-bypass-rina";

export async function devLogin(email: string): Promise<void> {
  const devEmail = (email || "inventedmaru@gmail.com").trim();
  const { error: signInErr } = await supabase.auth.signInWithPassword({ email: devEmail, password: DEV_PW });
  if (!signInErr) return;
  const { error: signUpErr } = await supabase.auth.signUp({
    email: devEmail,
    password: DEV_PW,
    options: { data: { company_name: "Dev Company", name: "Dev Admin", position: "GM", department: "Exec" } },
  });
  if (signUpErr) throw signUpErr;
  const { error: reSignIn } = await supabase.auth.signInWithPassword({ email: devEmail, password: DEV_PW });
  if (reSignIn) throw reSignIn;
}
```

## Login.tsx — guarded button
```tsx
import { isLocalDev, devLogin } from "../lib/devbypass";

// inside the signin <form>, after the real submit button:
{isLocalDev() && (
  <button type="button" disabled={loading} onClick={async () => {
    setError(""); setLoading(true);
    try { await devLogin(email || "inventedmaru@gmail.com"); setInfo("Dev sign-in. Loading…"); onLogin(); }
    catch (err: any) { setError(err?.message || "Dev sign-in failed."); }
    finally { setLoading(false); }
  }}>Dev: skip login (localhost only)</button>
)}
```

## Notes
- SPA session is read from Supabase (getSessionUser), so creating+signing in a
  real dev user is enough — no fake localStorage session required.
- Fixed dev password is fine because this path is unreachable outside localhost dev.
- The RINA project is a SEPARATE Supabase instance (its own anon key in .env).
  Make sure .env.local points at the right project before testing.

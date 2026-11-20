# Password reset / recovery flow (Supabase)

Verified live in ss-rover-cloud (LUNAV) on 2026-07-29. Fixes the "user can't
sign in" class of support ticket with a self-serve path — no admin reset, no
ban/RLS trap.

## Login page: "Forgot password?" toggle

Add state + handler to the existing login component:

```tsx
const [forgot, setForgot] = useState(false);
const [sent, setSent] = useState(false);
const [busy, setBusy] = useState(false);

async function handleReset(e: React.FormEvent) {
  e.preventDefault();
  setBusy(true);
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: window.location.origin + "/update-password",
  });
  setBusy(false);
  if (error) { toast(error.message, "error"); return; }
  setSent(true);
}
```

Render: if `forgot`, show an email input + "Send reset link" button + a
"Back to sign in" link that calls `setForgot(false)`. After `sent`, show a
confirmation ("Check your inbox"). `redirectTo` MUST be an allowed redirect
URL in Supabase (Auth → URL Configuration) — for prod the Site URL equals the
deploy origin so `window.location.origin` is already allowed. For localhost
testing, ADD `http://localhost:3000` to the redirect list or the link bounces.

## /update-password page

Supabase JS auto-exchanges the recovery token from the email link into a
session on load — do NOT parse the URL manually. Just call `updateUser`.

```tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client"; // your app's factory

export default function UpdatePasswordPage() {
  const router = useRouter();
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (pw !== confirm) { setErr("Passwords do not match"); return; }
    setBusy(true); setErr(null);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password: pw });
    setBusy(false);
    if (error) { setErr(error.message); return; }
    router.push("/dashboard"); // or "/login" with a success toast
  }

  return (
    <form onSubmit={onSubmit}>
      <input type="password" value={pw} onChange={(e) => setPw(e.target.value)} placeholder="New password" />
      <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Confirm password" />
      {err && <p style={{ color: "var(--mb-red)" }}>{err}</p>}
      <button disabled={busy}>{busy ? "Saving…" : "Set new password"}</button>
    </form>
  );
}
```

## Gotcha (P30)

`resetPasswordForEmail` is rate-limited. Two calls within ~60–90s →
`email rate limit exceeded`. One attempt, then tell the user to check inbox.
The admin cannot force a faster reset. If the user says "never got it",
confirm `select email, email_confirmed_at from auth.users where email='x'`
and have THEM retry, not you.

## Diagnostic note

The reset trigger loads `.env.local` itself so secrets never print to chat
(see `scripts/reset_password_email.cjs`). Don't paste publishable/anon keys
through chat (P8).

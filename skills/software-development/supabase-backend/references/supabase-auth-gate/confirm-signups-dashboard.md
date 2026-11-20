# Confirm signups — where the toggle actually lives (Supabase, 2026-07-26)

A live session burned ~10 screenshots hunting for a "Confirm signups" master
switch and never found it in the obvious place. This consolidates what's real.

## The trap
On the current Supabase dashboard, **email confirmation is template-driven,
NOT a master switch in the Email provider panel.**

- Authentication → Sign In / Providers → **Email** shows 9 settings
  (Enable email provider, Secure email change, password rules, OTP expiry…).
  **"Confirm signups" is NOT among them.** This panel is a dead end.
- The toggle is instead in **Authentication → Emails → Templates** →
  row **"Confirm sign up"** (*"Ask users to confirm their email address
  after signing up"*). Disabling that template is the lever — but on
  free tier without custom SMTP the templates are partly read-only.

## Authoritative flag (often hidden from this UI)
`mailer.autoconfirm` in `auth.config`. This is:
- **NOT editable via `supabase db query`** — the query role returns
  `relation "auth.config" does not exist`. Don't waste a round-trip there.
- **NOT exposed in the dashboard UI** we could reach.
- Only flippable via the **Supabase Management REST API** with an
  **access token** (Settings → API → access token):
  `PUT /v1/auth/config` body `{"mailer_autoconfirm": true}`.
  The agent CANNOT do this without the user pasting a token.

## Definitive diagnosis = the live `signUp` probe, never the UI
Run a Node `signUp` via the anon key against the live project and read
the raw result — do NOT infer from a green build or a dashboard screenshot.

| Probe result | Meaning |
|---|---|
| `user? true`, `session: false`, `error: none` | **Confirmation is ON.** Auth user IS created but no session; the app bounces you ("check your email" / "awaiting approval"). This is the #1 cause of "can't create account" on BOTH a vite SPA and a Next.js app that share one Supabase project — one "Confirm signups OFF" toggle in the dashboard fixes both. |
| `over_email_send_rate_limit` (429) | Supabase is **still attempting to send** a confirmation email → confirmation is ON (the 429 is just repeated diag signups hitting the send cap). |
| `Email address "x@example.com" is invalid` | Domain blocklist (e.g. example.com), NOT "signups disabled." Use a real email / gmail plus-address `you+test1@gmail.com`. |
| `Signups not allowed` / 403 | Signups genuinely disabled (different from above). |
| `user? true`, `session: true` | All good — account created AND logged in. |

After the user flips confirmation off, re-run the probe: `session: true` with
NO email-send attempt proves it's off. That's the proof — not a build or a
screenshot of the wrong panel.

## Practical unblock for testing
If the confirm email was actually sent, just **click the link** (the app says
so: *"Check your email to confirm, then sign in"*). Email rate-limiting from
diag scripts can SILENTLY drop a real app's confirm email into the void — wait
15–30 min for the limit to clear, or use the access-token flip. Turning
confirmation OFF removes the dependency entirely.

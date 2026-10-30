---
name: webar-webrtc-streaming
description: Marker WebAR streaming a live screen or data via WebRTC.
---

# WebAR + WebRTC streaming (marker-anchored)

App-install-free AR in mobile Safari/Chrome: a printed 2D image target becomes a
surface for either (a) a live WebRTC video stream from a desktop, or (b) data
published from an existing SaaS backend.

## Architecture that works

- `index.html` broadcaster: `getDisplayMedia({video:true, audio:false})` +
  peer registration + dynamic QR encoding the viewer URL.
- `viewer.html`: A-Frame + `mindar-image-aframe`, hidden
  `<video autoplay playsinline muted>` used as the `a-plane` material.
  16:9 plane = `width="1" height="0.5625"`.
- One AR shell, **two source modes** decided by a query param / session row:
  `mode=mirror` (WebRTC video) and `mode=report` (data read straight from the
  backend, no desktop peer needed). Design the shell for both from day one even
  if only mirror ships first — retrofitting the switch is the expensive part.
- Build order: mirror on a public broker → swap signaling to your own realtime
  channel → session codes → TURN → data/report mode. Each step user-testable.

## Pitfalls

- HTTPS is mandatory for camera + WebRTC media on iOS Safari/Android Chrome.
  If the app is already on Vercel, deploy static and skip ngrok/mkcert entirely
  — real cert, no LAN IP, and peers no longer need the same Wi-Fi.
- iOS Safari often will not paint a video texture until a user gesture. Add a
  "Tap to start" overlay in the viewer.
- MindAR needs a **compiled `.mind` target file**. Start with the default card
  target so the pipeline works, swap the custom image in later.
- Vercel env vars only apply to builds created *after* they are added — redeploy.
- "Mirror the screen" and "publish a report" are different products sharing one
  AR shell. When a user mentions both, separate them explicitly before coding.

## TURN: without it, ~10-20% of off-LAN connections fail

Neither Vercel nor Supabase provides TURN. Choose:

- **Metered.ca** — email signup, static URL/user/pass, working in 2 minutes.
  Free tier ~500MB relayed/month, only minutes of relayed screen video. Static
  creds are readable in client JS → anyone can burn the quota. Fine for a
  private demo.
- **Cloudflare Realtime TURN** — needs a TURN Key (dash → Realtime → TURN Keys →
  Create TURN Key) plus a server-side route minting short-lived credentials from
  the secret API token. Much larger free allowance, anycast (lower relay
  latency), creds expire so they can't be stolen. Pick this when stability or a
  client-facing demo matters.

Write the ICE config so the provider is a one-line swap.

## Secrets

Never accept or echo an API token in chat — a Key ID is fine, the token is not.
Create a gitignored `.env.local` with the non-secret IDs pre-filled and the
secret line left blank, hand the user the absolute path, and let them paste it
themselves. For production use the dashboard or `vercel env add <NAME> production`
(hidden prompt), so the value never lands in chat or git.

## Session codes (optional UX layer)

A `sessions` table mapping a short human code → long peer id lets the QR encode
`?s=4821`, gives a typeable fallback when the QR won't scan, supports reconnect
after a drop, and allows expiry so stale QR codes die. It is a lookup layer only
— it does not touch the media path. Safe to bolt on after the AR works.

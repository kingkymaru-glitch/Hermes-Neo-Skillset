---
name: instagram-graph-management
description: Manage owned Instagram accounts via Meta Graph API legally.
---

# Instagram Graph API Management (owned accounts)

Use when: a user wants an agent (Hermes) to post to, schedule, or monitor an
Instagram account WITHOUT risk of a ban. The only ban-safe path is the official
**Instagram Graph API** (Content Publishing). Never use a reverse-engineered
private API (e.g. dilame/instagram-private-api) — those trigger bot detection
and account locks, especially on new accounts.

## Hard rules
- Publishing/API access requires a **Professional** account (Business or
  Creator). Personal accounts cannot authorize Graph API access at all.
- The account must be linked to a **Facebook Page**, and both governed by a
  **Meta Developer app**.
- **Owned-account exemption:** if the app is only for a business you own or
  manage, you get **Standard Access automatically** — App Review / screencast
  is NOT required. The user (Meta app owner/admin) can publish to their own
  account immediately after setup. This is the key fact that removes the
  biggest perceived blocker. (Source: Meta App Review docs, "My app is only
  for a business I own or manage → Standard Access → Not required".)
- App Review IS only needed when the app publishes to accounts you do NOT own
  (agency/client scenario). Not our case.

## Manual prerequisites ONLY THE USER CAN DO (browser + their FB/IG creds)
The agent cannot create the FB Page, convert the account, or pass 2FA. Hand the
user this exact checklist:
1. Convert the IG account to Professional (Settings → Account → Switch to
   Professional → Business or Creator).
2. Create a Facebook Page for the brand and link the IG account to it
   (IG Settings → Account → Linked accounts → Facebook, or Page settings).
3. Create a Meta Developer app at developers.facebook.com.
4. Generate a **long-lived access token** (60-day) for the IG user, and give
   the agent the **IG User ID**. (Agent provides the exact Graph API calls.)

## The publishing flow (two-step, per Meta Content Publishing)
1. Create a media container: POST
   `https://graph.instagram.com/v22.0/{ig_user_id}/media`
   with `image_url` (or `video_url`/`media_type=REELS`), `caption`, and
   `access_token`.
2. Publish it: POST
   `https://graph.instagram.com/v22.0/{ig_user_id}/media_publish`
   with `creation_id` (the container id) + `access_token`.
   - There is a processing delay: poll/publish after a short wait (~15s) or
     poll the container status. Containers expire.
   - Carousels: create child containers via `/media` with `is_carousel_item`,
     then a parent container referencing `children`, then publish.
   - Reels: `media_type=REELS` with a video_url.

## Token lifecycle (the part the agent owns)
- Long-lived tokens last ~60 days. Schedule a cron to refresh BEFORE expiry
  using the exchange endpoint, and store the token in the Hermes keychain /
  `.env` — NEVER in chat or plaintext in the repo.
- Refresh: exchange short-lived token for long-lived via
  `GET /oauth/access_token?grant_type=fb_exchange_token&...`.

## Ban-avoidance (operational discipline)
- **Warm the account up manually first**: a few real posts, complete profile,
  before API publishing starts. New accounts get API-throttled and flagged.
- Respect Graph API rate limits (BUC volume caps). Natural scheduling spacing
  (a few posts/week) stays well under caps.
- Use official Graph API only. No automation that simulates UI interaction for
  posting (browser-driving the app to post is ToS-violating and ban-prone).

## Agent build options to offer the user (discuss-first, no code yet)
Per the founder's "discuss architecture/control surface before code" gate:
- Option A: custom lightweight publisher — `curl` + cron + keychain token,
  full control, zero extra deps. Good default for a single owned account.
- Option B: deploy Postiz (self-hosted open-source scheduler, IG-capable) and
  wire Hermes to its API. Heavier, more UI, multi-channel.

## Public reference projects (all Graph-API based, legit)
- ArthurFDLR/instagram-post-scheduler — AWS Lambda + GraphAPI container→publish
  reference implementation.
- Postiz — self-hosted open-source social scheduler with Instagram support.
- Official docs: developers.facebook.com/docs/instagram-platform/content-publishing

## See also
- references/graph-api-publishing.md — verified 2026 requirements, exact
  endpoints, permissions, rate-limit notes, and the owned-account exemption.
- xurl skill — for X/Twitter management (different platform, same agent-goal
  class). These two are siblings under social-media; do not merge.

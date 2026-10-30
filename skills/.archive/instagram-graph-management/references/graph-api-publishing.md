# Instagram Graph API — Publishing Reference (verified 2026-08-28)

## Account requirements (mandatory chain)
1. Instagram **Professional** account (Business or Creator). Personal = no API.
2. A **Facebook Page** linked to that IG account.
3. A **Meta Developer app** (developers.facebook.com).
4. **Long-lived access token** (60 days) + IG User ID handed to the agent.

## The owned-account exemption (kills the App Review blocker)
Meta App Review docs, development scenarios table:
- "My app is only for a business I own or manage" → Login type: No login /
  Instagram Login / Facebook Login → Access level: **Standard Access** →
  **App Review: Not required.**

Implication: for the founder's OWN brand account (e.g. @innovatedmaru /
"LunaV Solution"), Standard Access is automatic as the app owner/admin. No
screencast, no weeks of waiting. App Review is only for apps that publish to
accounts the developer does NOT own (agency/client model).

## Permissions
- `instagram_business_content_publish` — create media containers + publish.
- Standard Access grants this for accounts with a role (owner/admin/developer/
  tester) on the Meta app. Self-serve; no review.

## Publishing endpoints (v22.0 example)
Step 1 — create container:
  POST https://graph.instagram.com/v22.0/{ig_user_id}/media
  body: { image_url, caption, access_token }
  (video: video_url + media_type=REELS; carousel items: is_carousel_item=true)

Step 2 — publish:
  POST https://graph.instagram.com/v22.0/{ig_user_id}/media_publish
  body: { creation_id: <container id>, access_token }

Notes:
- Container needs processing time before publish (~15s wait or poll). Containers
  expire if not published promptly.
- Carousel: create N child containers, then a parent container with `children`,
  then media_publish the parent.

## Rate limits
- Graph API uses BUC (Business Use Case) volume caps. A few scheduled posts per
  week is far under any threshold. Do not bulk-post.

## Ban-avoidance (operational)
- Warm account manually first (real posts, complete profile) before API posting.
- New accounts are API-throttled and flagged — ramp up slowly.
- ONLY use official Graph API. Reverse-engineered private APIs
  (dilame/instagram-private-api and similar) = ban risk; avoid entirely.
- Never drive the IG web/mobile UI with browser automation to post — ToS
  violation.

## Token refresh
- Long-lived tokens ~60 days. Pre-expiry refresh via:
  GET https://graph.instagram.com/oauth/access_token
    ?grant_type=fb_exchange_token
    &client_id=...&client_secret=...
    &fb_exchange_token=<short_lived_token>
- Store refreshed token in Hermes keychain / .env, never in chat or repo.

## Reference repos (public, Graph-API based)
- github.com/ArthurFDLR/instagram-post-scheduler (AWS Lambda + GraphAPI)
- Postiz (self-hosted open-source scheduler, IG-capable)
- Official: developers.facebook.com/docs/instagram-platform/content-publishing

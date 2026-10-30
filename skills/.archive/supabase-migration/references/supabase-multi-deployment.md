# Supabase Multi-Deployment — the exact answer

Bake this into any reply about "can Supabase handle multiple deployments / multiple apps".
Yes, in three distinct senses; the answer differs per meaning.

## 1. Multiple apps sharing ONE Supabase project (the common "unify" case)
- YES. One project can back RINA + LUNAV + AnglerGO simultaneously.
- Isolate each app by **schema** (Postgres namespace) or a table prefix (`catches_`, `shops_`,
  `models_`). Each app keeps its own tables; one project, one bill, one auth.
- Free tier is fine for dev/launch.

## 2. Same app, multiple environments (dev / staging / prod)
- Supabase's recommended model is **ONE project per environment** (e.g. `anglergo-dev`,
  `anglergo-prod`). You do NOT spin environments inside one project.
- Switch the project URL + anon key per Xcode/build config. Keeps a prod incident from
  nuking dev data.

## 3. Multiple regions / global edge
- Supabase runs in many regions. RINA/LUNAV use Sydney `ap-southeast-2`; AnglerGO (Malaysia-
  facing) → Sydney or Singapore. Pick the region nearest the users for latency.

## Free-tier constraints (so you set expectations)
- One free project: 500MB DB, 2 projects per org max, limited compute, no Point-in-Time
  Recovery.
- For 3 apps on one project: fine for dev/launch. At scale, either upgrade that project to
  Pro (~$25/mo) or split busy apps into their own project. Either way, multi-deployment is
  supported.

## Recommendation for "unify onto Supabase"
"Unify" = same backend tech + same conventions + one team skillset, NOT necessarily one shared
database. Put each app in its OWN Supabase project (clean prod/dev separation; a spike in one
app doesn't starve others) but use the SAME region + SAME patterns (RLS, Storage-URL,
email/password auth) as the existing apps.

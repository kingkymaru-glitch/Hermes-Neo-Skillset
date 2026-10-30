---
name: vercel-auto-deploy-requires-commit-author-kingkymaru-gmail-com
description: "Vercel auto-deploy requires commit author kingkymaru@gmail.com"
---

## Trigger
vercel deploy webhook not firing

## Why this exists (captured automatically)
Auto-captured after a hard multi-step solve. Reuse instead of re-deriving.

## Steps
git -c user.name=maru -c user.email=kingkymaru@gmail.com commit

## Pitfalls
webhook silently no-ops if author mismatch

## Verification / Evidence
verified R-Tessera live

---
name: desktop-preview
description: "Create HTML on desktop for local review before deploying."
platforms: [macos]
---

# Desktop-First Preview

When the user asks to review a design, landing page, or concept **before** anything goes live, create a single self-contained HTML file on the desktop first. Do not push, deploy, or modify the real repo until the user explicitly approves the preview.

## When to use
- User says "create a single html file on my desktop so i can view [idea] first"
- User wants to preview a landing page, hero section, or UI concept before it ships
- User says "dont do anything online yet" / "before that, show me locally"
- User pastes an HTML file and asks for feedback on making it a live page
- Any workflow where the artifact would eventually go to Vercel/GitHub and the user wants to iterate locally first

## Workflow

1. **Understand the target stack** — read the real repo (if it exists) to get the actual tech (framework, map engine, auth, DB, deployment target). The preview should match the real stack, not invent a parallel one.
2. **Identify what to bridge** — the user's reference HTML (if any) vs the real repo. Port the *good bits* (animations, layout, UX patterns) into the real stack's architecture. Flag what won't transfer (decorative standouts vs functional equivalents).
3. **Build a single self-contained HTML file** — all CSS and JS inline or via CDN. No build step, no server, no API keys the user doesn't have. Openable directly in a browser from `file://`.
4. **Write to `~/Desktop/<name>-concept.html`** (or `-preview.html`, `-hero.html` — name after the purpose, not the session).
5. **Report honestly** — what works, what's placeholder, what's a problem. Don't oversell. The user wants facts, not comfort.

## Porting patterns (verified techniques)

When porting a vanilla HTML concept into a real app's stack:
- **Loader animation** → keep the procedural/3D loader but fade it out when the real engine (Cesium, map, etc.) finishes initializing
- **Orbiting/floating chips** → can overlay on a 3D globe as HTML elements with depth-based opacity/scale (z-index management)
- **Scroll reveal + card tilt** → IntersectionObserver + pointermove; these port cleanly to any framework
- **Count-up stats** → IntersectionObserver + requestAnimationFrame with cubic easing
- **Hardcoded placeholder data** → keep shape but label it clearly; wire to real data later
- **CDN dependencies** — always include via `<script src="...">` in the single file; the user opens it directly

## Interactive playbook pattern (for non-technical exec audience)

When the deliverable is a multi-chapter guide for slow/non-technical readers (not a single concept preview):
- Use tabs, one chapter per tab — never one long scrolling page; walls of text lose the reader.
- Each tab opens with a hook headline + one-line sub + a punchline badge (outcome/positioning), then steps, then 2 quiz questions with reveal-answer.
- Tone: modern, minimalist, high-contrast; no childish styling. Punchy lines over explanations.
- Audience hooks for 35-40 senior execs: time saved, looking competent, control, predictability, privacy, decision-ready output.
- Keep under ~15 printed pages; verify with headless Chrome print-to-PDF page count.
- Write to `~/Desktop/<name>.html` (or `~/<name>-design/` if browser must open it).

## Honest review checklist

When the user pastes an HTML file and asks for feedback on making it a live page:
- Compare it to the **real repo's actual stack** (read the repo first)
- Call out **what's decorative vs functional** (e.g., a procedural Three.js lure is a toy if the real product has a working 3D globe)
- Call out **what won't transfer** (vanilla HTML ≠ Next.js — you can't drop a 400-line HTML file into an App Router project)
- Call out **placeholder copy** — if sections say "Placeholder rows" repeatedly, that goes live if shipped as-is
- Call out **competing interactive layers** — orbiting HTML chips on top of a Cesium globe = two interactive layers fighting; recommend picking one
- Give a **clear recommendation**: use this as the hero / don't use this as the hero / port specific bits into the real repo

## Pitfalls
- **macOS TCC blocks `~/Desktop` for the browser tool — write previews outside it.**
  The agent's browser navigates `file:///Users/<u>/Desktop/...` and gets
  `chrome-error://chromewebdata/` (a silent failure that reads like a missing file). Desktop,
  Documents and Downloads are TCC-protected; the shell can read them but the browser profile
  cannot. Put previews in a plain home subdir (e.g. `~/<name>-design/`) and serve them over
  HTTP — `python3 -m http.server <port> --bind 127.0.0.1` from that dir, then open
  `http://127.0.0.1:<port>/`. `file://` navigation is blocked in the agent browser regardless
  of directory, so the localhost server is the reliable route and also matches the user's
  "show me locally" ask.
- **Pick a port that is actually free.** `lsof -nP -iTCP:<port> -sTCP:LISTEN` first — a stale
  server from an earlier session may already hold it and serve a different directory, which
  surfaces as a confusing "Error response" page rather than a bind failure.
- **Don't deploy until the user says so.** The explicit "dont do anything online yet" gate means: no git push, no Vercel deploy, no API calls to live services. Local file only.
- **Don't pretend decorative = functional.** A spinning 3D lure is eye-catching but doesn't showcase what the app does. The real differentiator (Cesium globe with real pins) IS the hero.
- **Don't ship placeholder copy.** If the preview has "Placeholder copy — swap with your real about text" sections, flag it. Those go live verbatim if you don't replace them.
- **Match the real stack, not the reference file.** If the repo is Next.js + CesiumJS + Supabase, the preview should use CesiumJS (not a Three.js wireframe globe) even if the reference file used something else.
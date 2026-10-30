---
name: safe-client-code-sandbox
description: Build a constrained in-browser code-execution sandbox for AI/user-generated JavaScript (e.g. run model-returned geometry/curvature code) that blocks the DOM, network, API keys, and eval. Use when shipping a single-file HTML/Three.js app or any web tool that executes model output as code. Includes the strict-mode `var eval` pitfall and a replica-test verification pattern.
---

# Safe Client-Side Code Sandbox

## When to use
- You're building/shipping a web app (often a single-file `index.html` + Three.js) where an LLM returns JavaScript that must run in the end-user's browser to create geometry/curvature (lathe, extrude, etc.).
- The user requires "only this kind of code can run" — e.g. "allow ONLY curvature-creating code."
- You must keep the API key (BYOK), `window`, `document`, `fetch`, and the network unreachable from that code.

## Core pattern
1. **Two modes** (user-selectable): a *Safe JSON* mode where the model returns data only and **nothing is executed**, and a *Curvature Code* (sandboxed) mode where model output runs inside a lockdown.
2. **Token scan** — reject any code containing forbidden identifiers (`window`, `document`, `fetch`, `eval`, `Function`, `globalThis`, `XMLHttpRequest`, `localStorage`, `location`, `navigator`, `import`, `require`, `process`, `setTimeout`, `WebSocket`, `Worker`, `constructor`, `__proto__`, `prototype`, `delete`, `with`, etc.).
3. **Shadow scope** — run the user code via `new Function(paramKeys, '"use strict";\n' + 'var ' + SHADOW_IDENTS.join(',') + ';\n' + code)` where `SHADOW_IDENTS` are the same names declared as empty `var`s so any reference inside the code resolves to `undefined` instead of the real global.
4. **Whitelisted helpers only** — the only things passed as function params are your geometry helpers (`lathe`, `addBox`, `addCylinder`, `addSphere`, `addExtrude`, `sin`, `cos`, `PI`, `deg`...). The model cannot call anything else.

## CRITICAL PITFALL — strict-mode `var eval` / `var arguments`
Do **NOT** include `eval` or `arguments` in `SHADOW_IDENTS`. Under `"use strict"`, the statement `var eval;` (or `var arguments;`) is a **SyntaxError**: *"Unexpected eval or arguments in strict mode."* Because the shadow line is prepended to every execution, this crashes ALL code — even benign curvature code — so the sandbox appears "broken" (blocks everything). Keep `eval` only in `FORBIDDEN_SCAN` (it's still blocked by the token check) and out of the shadow list. See `references/sandbox-template.md` for the exact, correct lists.

## Verification (do this before claiming done)
- Extract the `<script type="module">` body and run `node --check` to confirm JS syntax (HTML-embedded JS is NOT caught by normal HTML linters).
- Run `scripts/verify_sandbox.mjs` — a standalone replica of the scan+wrapper. It asserts: benign lathe code → ALLOWED; attempts to read the API key via `document`, `fetch` exfiltration, `eval`, or `window` → all BLOCKED. Only ship when both pass.

## UX pitfall — controls must be VISIBLE, not just present
If the user reports "I don't see the function to X/Y/Z" but the buttons exist in the DOM, the problem is **layout/visibility**, not missing code. In a `max-h-[...] overflow-y-auto` sidebar, anything at the bottom is below the fold. Fix: pin critical/must-have controls (Select All, Group, Ungroup, Reset, mode switch) to the **top** of the panel inside a highlighted container (border + tinted bg). See `references/ui-visibility.md`. Always re-verify with a search for duplicate `id=` (a duplicate ID silently breaks `getElementById` listeners).

## Auto-detect mode — let the prompt pick curve vs JSON (don't make the user choose)
The user ask "can the code itself decide when to use curvature?" → yes: route from prompt keywords so
curved/hull prompts auto-use the sandboxed curvature path and boxy prompts use Safe JSON. Compact,
reusable implementation in `references/auto-detect-mode.md`. Key points:
- Dropdown default = `<option value="auto" selected>Auto (detect from prompt)</option>` plus explicit
  `json` and `curve` options for users who want to force a path.
- Resolve at generate time: `const mode = (modeRaw === 'auto') ? autoDetectMode(prompt) : modeRaw;`
  **TDZ trap:** call `autoDetectMode` with the already-declared `prompt` const, NOT a variable defined
  LATER in the handler (e.g. `userPromptText`) — referencing a not-yet-initialized `const` throws
  `ReferenceError` even though it's lexically "in scope".
- Reflect the resolved choice in the status log ("Querying X for curvature code (sandboxed)…" vs
  "for JSON model spec…") so the user sees which path fired.
- Verified routing: "a 6 meter long boat"→curve, "curved cylindrical water tank"→curve,
  "a boxy house with a flat roof"→json, "simple rectangular table"→json.

## Checklist
- [ ] Safe JSON mode exists (no execution path at all)
- [ ] Token scan + shadow scope + whitelisted helpers
- [ ] `eval`/`arguments` NOT in shadow list
- [ ] `node --check` passes on extracted script
- [ ] `scripts/verify_sandbox.mjs` shows benign ALLOWED / malicious BLOCKED
- [ ] Critical controls pinned to top, visible without scrolling
- [ ] No duplicate element IDs
- [ ] Auto-detect mode routes curve vs JSON from prompt keywords (default = auto)

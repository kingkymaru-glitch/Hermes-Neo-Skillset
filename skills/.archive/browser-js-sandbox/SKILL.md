---
name: browser-js-sandbox
description: Safely execute LLM- or user-generated JavaScript inside the browser in a restricted scope — block window/document/fetch/API keys/network while exposing ONLY an allow-listed API (e.g. Three.js geometry helpers). Trigger on "run model-generated code", "sandbox the AI output", "execute untrusted JS in the browser", "let the model write code but keep it safe", "curvature code mode", or any task where an LLM returns code that must run client-side without full eval powers. Also relevant to "Safe JSON vs code mode" prompts and "Gemini returned code not data" handling.
---

# Browser JS Sandbox (allow-listed execution of untrusted code)

## Why this exists
When an LLM (Gemini, GPT, etc.) returns *code* that you run in the page via
`eval` / `new Function`, it gets the entire page: the user's API key sitting in
`document.getElementById('api-key').value`, `fetch` to exfiltrate it, `document`
to rewrite the DOM, `localStorage`, the network — everything. Full `eval` is the
keys-to-the-kingdom. You must instead run the model's code in a *constrained*
scope that can ONLY call the API you hand it.

This is the pattern used in LunaV Studio's "Curvature Code" mode: the model
returns JS that builds 3D geometry, and the sandbox exposes only geometry
helpers (`lathe`, `addBox`, `addSphere`, …) — never the key, DOM, or network.

## Three-layer defense (use all three)
1. **Token scanner (pre-check).** Before building anything, regex word-boundary
   scan the raw code for a forbidden-identifier list. Throw immediately on a hit.
   ```js
   const FORBIDDEN_SCAN = ['window','document','fetch','eval','Function','globalThis',
     'importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB',
     'location','top','parent','self','navigator','alert','import','require','process',
     'setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker',
     'constructor','__proto__','prototype','delete','with'];
   // in runSandboxedCurveCode():
   for (const t of FORBIDDEN_SCAN) {
     if (new RegExp('\\b'+t+'\\b').test(code)) throw new Error('Sandbox blocked token: '+t);
   }
   ```
2. **Shadow identifiers (depth-in-defense).** Inside the wrapper, declare the
   forbidden names as *undefined local vars* so even if code slips past the
   scanner, the names resolve to a local `undefined` instead of the real global.
   ```js
   const SHADOW_IDENTS = ['window','document','fetch','Function','globalThis',
     'importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB',
     'location','top','parent','self','navigator','alert','require','process',
     'setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker',
     'constructor','__proto__','prototype'];
   const shadow = 'var ' + SHADOW_IDENTS.join(',') + ';';
   ```
3. **`new Function` with an explicit allow-list.** The model code is wrapped and
   executed as a function whose ONLY parameters are your safe helpers. It cannot
   reach anything not passed in — no globals, no closure over page state.
   ```js
   const keys = Object.keys(helpers);            // e.g. ['lathe','addBox','sin','PI']
   const wrapped = '"use strict";\n' + shadow + '\n' + code;
   const fn = new Function(keys.join(','), wrapped);
   fn(...keys.map(k => helpers[k]));
   ```

## PITFALL — `var eval` / `var arguments` under "use strict" (HIGH)
Under `"use strict"`, declaring `var eval;` or `var arguments;` is a **SyntaxError**:
`Unexpected eval or arguments in strict mode`. Since layer 3 wraps code in
`"use strict"`, putting `eval` (or `arguments`) in the SHADOW_IDENTS list makes the
*wrapper itself* throw — which blocks even BENIGN model code (you'll see
"benign lathe => BLOCKED: Unexpected eval or arguments in strict mode").
**Fix:** remove `eval` and `arguments` from `SHADOW_IDENTS`, but KEEP them in
`FORBIDDEN_SCAN`. The scanner still blocks any code that *uses* them; you just
don't redeclare them as locals. (Verified: with this fix, benign `lathe` code runs
and `eval`/`document`/`window`/`fetch` attempts are all blocked.)

## Allow-list API design (Three.js geometry example)
Pass helpers as named params. Each returns/adds a Mesh to a target group.
Validate untrusted string inputs (e.g. color) with a regex before use:
```js
const mkMat = (color) => new THREE.MeshStandardMaterial({
  color: new THREE.Color((color && /^#[0-9a-fA-F]{6}$/.test(color)) ? color : '#0ea5e9'),
  roughness: 0.4, metalness: 0.3 });
const add = (geo, color, pos, rot) => {
  const m = new THREE.Mesh(geo, mkMat(color));
  m.castShadow = m.receiveShadow = true;
  if (pos) m.position.set(pos[0]||0, pos[1]||0, pos[2]||0);
  if (rot) m.rotation.set(THREE.MathUtils.degToRad(rot[0]||0),
                          THREE.MathUtils.degToRad(rot[1]||0),
                          THREE.MathUtils.degToRad(rot[2]||0));
  aiGeneratedGroup.add(m); return m; };
// helpers: addBox, addCylinder, addSphere, addCone, addCapsule, addTorus,
//          addExtrude, lathe, addPolygon + math: PI,sin,cos,sqrt,abs,min,max,pow,floor,ceil,round
```
`lathe(points, segments, …)` (THREE.LatheGeometry) is the key to *curved* bodies —
the model should prefer it over stacked boxes for roundness.

## LLM plumbing (Gemini)
- **Safe JSON mode (default):** `generationConfig: { responseMimeType: "application/json", temperature: 0.6 }`.
  Model returns data only; NEVER executed. Build from the parsed object.
- **Code mode:** drop `responseMimeType`, set `temperature: 0.6`, and send a
  system prompt that lists ONLY the allowed API + "Output ONLY JS code, no markdown".
  Strip ``` fences before scanning: `code.match(/```(?:js|javascript)?\s*([\s\S]*?)```/i)`.
- After running, drop orphans far from origin and recenter the group (see references/gemini-curvature-mode.md).

## Verification (run it, don't trust it)
Use `scripts/verify_sandbox.mjs` — a standalone Node harness that confirms:
benign curvature code → ALLOWED; `document`/`fetch`/`eval`/`window` theft attempts → BLOCKED.
Run: `node <skill>/scripts/verify_sandbox.mjs`. Wire a similar check whenever you
change the forbidden list.

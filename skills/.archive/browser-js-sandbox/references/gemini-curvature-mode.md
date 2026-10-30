# Gemini "Curvature Code" mode — session-specific detail

Context: LunaV Studio (LunaV Solutions 3D inspection SaaS) lets the user pick a
generation mode above the prompt:

- **Safe JSON (default):** `generationConfig: { responseMimeType: "application/json", temperature: 0.6 }`.
  Model returns a JSON spec of primitives; never executed. Build by parsing.
- **Curvature Code (sandboxed):** drop `responseMimeType`; `temperature: 0.6`;
  system prompt lists ONLY the geometry helper API and demands raw JS.

## System prompt (curve mode)
```
You are a 3D modeling assistant. Output ONLY JavaScript code (no markdown, no explanation, no backticks).
Your code runs inside a sandbox exposing ONLY these geometry functions and math helpers.
You CANNOT access window, document, fetch, the API key, or the internet.
Available API (call directly):
  addBox(size[w,h,d], position?[x,y,z], rotation?[rx,ry,rz] deg, color?"#rrggbb")
  addCylinder(radius, height, position?, rotation?, color?, segments?)
  addSphere(radius, position?, rotation?, color?, segments?)
  addCone(radius, height, position?, rotation?, color?, segments?)
  addCapsule(radius, length, position?, rotation?, color?)
  addTorus(radius, tube, position?, rotation?, color?)
  addExtrude(points2D[[x,y]...], depth, position?, rotation?, color?, bevel?)
  lathe(points2D[[x,y]...], segments?, position?, rotation?, color?)   // revolve profile -> curved hull
  addPolygon(points2D[[x,y]...], position?, rotation?, color?)
Math: PI, sin, cos, sqrt, abs, min, max, pow, floor, ceil, round.
Rules: prefer lathe/capsule for roundness; keep within ~8 units of origin; y>=0; no far parts.
```

## Post-run cleanup (drop orphans + recenter)
```js
function cleanupAndCenter() {
  const toRemove = [];
  aiGeneratedGroup.children.forEach(c => {
    const p = new THREE.Vector3(); c.getWorldPosition(p);
    if (p.length() > 15) toRemove.push(c);          // detached stray part
  });
  toRemove.forEach(c => { aiGeneratedGroup.remove(c); disposeObj(c); });
  const box = new THREE.Box3().setFromObject(aiGeneratedGroup);
  if (!box.isEmpty()) aiGeneratedGroup.position.sub(box.getCenter(new THREE.Vector3()));
}
```

## Live model list (confirm "no more 2.5") instead of web-search
Web search was unavailable on this account (no Firecrawl credits). Confirm the
current Gemini lineup by calling Google's live endpoint from the page and filtering
to 3.x — more reliable than guessing version numbers:
```js
const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
const j = await r.json();
const names = (j.models||[]).map(m=>(m.name||'').replace('models/','')).filter(n=>/^gemini-3/.test(n));
```
A "Refresh Models" button populates the `<select>` from the filtered result. A static
fallback list (3.6 Flash / 3.5 Flash / 3.1 Pro / 3.0 Pro) is shown until refresh runs.
KNOWN GAP: the exact 3.x version numbers were a best estimate — the live Refresh is the
source of truth and overwrites them with whatever Google actually returns.

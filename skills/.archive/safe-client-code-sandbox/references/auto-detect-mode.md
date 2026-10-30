# Auto-detect mode — route curvature vs JSON from the prompt

When the app offers both a sandboxed "Curvature Code" path and a "Safe JSON" path, don't
force the user to pick. Decide from the prompt text so curved/hull requests automatically use
the sandbox and boxy requests use JSON.

## Keyword router

```js
const CURVE_KEYWORDS = [
  'curv','curve','hull','vessel','boat','ship','yacht','canoe','kayak',
  'vase','bottle','dome','sphere','round','rounded','cylindrical','lathe','smooth',
  'aerodynamic','fuselage','shell','rotund','ellip','revolve','bowl','bubble','organic',
  'blob','teardrop','torus','tube','pipe','ring'
];
function autoDetectMode(prompt) {
  const p = (prompt || '').toLowerCase();
  return CURVE_KEYWORDS.some(k => p.includes(k)) ? 'curve' : 'json';
}
```

## Wiring

Dropdown (default = auto):
```html
<select id="gen-mode">
  <option value="auto" selected>Auto (detect from prompt)</option>
  <option value="json">Safe JSON (data only)</option>
  <option value="curve">Curvature Code (sandboxed)</option>
</select>
```

Resolve at generate time — use the already-read `prompt` const, NOT a variable declared later
in the handler (TDZ `ReferenceError`).
```js
const prompt = document.getElementById('prompt').value;
// ... (do NOT reference a const defined further down here) ...
const modeRaw = document.getElementById('gen-mode').value;
const mode = (modeRaw === 'auto') ? autoDetectMode(prompt) : modeRaw;
const modeLabel = mode === 'curve' ? 'curvature code (sandboxed)' : 'JSON model spec';
statusLog.innerHTML = `Querying ${modelName} for ${modeLabel}...`;
```

`mode` then drives which `systemInstruction` + `generationConfig` you send: `curve` drops
`responseMimeType` and uses the sandbox system prompt; `json` sends
`responseMimeType: "application/json"`.

## Verified routing (tested with `node -e`)
- "a 6 meter long boat" → curve
- "curved cylindrical water tank with conical roof" → curve
- "smooth aerodynamic drone fuselage" → curve
- "a torus ring rail" → curve
- "organic blob sculpture" → curve
- "a boxy house with a flat roof" → json
- "simple rectangular table" → json

## Why it matters
The user explicitly asked "can u make this auto detected by the code itself when to use the
curvature or not" — so the decision must be made client-side from the prompt, never exposed as
a choice the model can influence. The model only ever receives the correct system instruction
for the job.

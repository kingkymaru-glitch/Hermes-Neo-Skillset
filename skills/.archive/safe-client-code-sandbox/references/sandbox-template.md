# Sandbox template (correct lists + wrapper)

## FORBIDDEN_SCAN (token check — reject if present)
window, document, fetch, eval, Function, globalThis, importScripts, XMLHttpRequest,
localStorage, sessionStorage, indexedDB, location, top, parent, self, navigator, alert,
import, require, process, setTimeout, setInterval, postMessage, addEventListener,
WebSocket, Worker, constructor, __proto__, prototype, delete, with

## SHADOW_IDENTS (declared as empty `var` in strict wrapper — SAME minus eval/arguments)
window, document, fetch, Function, globalThis, importScripts, XMLHttpRequest,
localStorage, sessionStorage, indexedDB, location, top, parent, self, navigator, alert,
require, process, setTimeout, setInterval, postMessage, addEventListener,
WebSocket, Worker, constructor, __proto__, prototype
# Pitfall: do NOT add 'eval' or 'arguments'. Under "use strict", `var eval;` is a SyntaxError
# that aborts every execution, including benign code. Keep eval only in FORBIDDEN_SCAN.

## Wrapper
```
function runSandboxedCurveCode(code, helpers) {
  let c = (code || '').trim();
  const fence = c.match(/```(?:js|javascript)?\s*([\s\S]*?)```/i); if (fence) c = fence[1].trim();
  for (const t of FORBIDDEN_SCAN) if (new RegExp('\\b'+t+'\\b').test(c)) throw new Error('Sandbox blocked token: '+t);
  const keys = Object.keys(helpers);
  const shadow = 'var '+SHADOW_IDENTS.join(',')+';';
  const fn = new Function(keys.join(','), '"use strict";\n'+shadow+'\n'+c);
  fn(...keys.map(k=>helpers[k]));
}
```

## Cleanup/center helper (drop orphans, recenter aiGeneratedGroup)
- Traverse group; remove children whose world-position length > 15 units (orphan parts like a stray floating cone).
- Recenter group so its bounding-box center sits at origin.
- Dispose geometries/materials before removing to avoid leaks.

## API key handling
- Store the user's key in an `<input type=password id="api-key">`.
- The key is ONLY used in the fetch() call to the model API.
- Inside sandboxed code it is unreachable: `document` is shadowed and forbidden; never interpolate the key into generated code.

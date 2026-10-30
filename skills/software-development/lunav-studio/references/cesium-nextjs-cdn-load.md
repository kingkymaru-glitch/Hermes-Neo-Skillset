# Cesium in Next.js — avoid bundling (octal-escape SyntaxError)

## Symptom
A Next.js (App Router / Turbopack / Webpack) production build of a page that
`import { Viewer } from "cesium"` fails in the BROWSER with:
`SyntaxError: The only valid numeric escape in strict mode is '\0'`
or `Octal escape sequences are not allowed in template strings`.
The build (`next build`) itself PASSES — the error only appears at runtime.
`node --check` on the emitted chunk (e.g. `.next/static/chunks/2iyfwmu-9rx50.js`)
reports the same syntax error.

## Root cause
Cesium's npm package embeds its wasm as a base64 string inside a JS template
literal that contains `\0` bytes. `\0` inside a backtick template literal is
ILLEGAL in strict-mode ES modules (unlike in a normal string, where `\0` is the
one allowed numeric escape). Next's minifier preserves those escapes, so the
produced chunk is unparseable by the browser. `transpilePackages: ["cesium"]`
does NOT fix it — the problem is the embedded-wasm string, not the transpile step.

## Fix — load Cesium from CDN at runtime (do NOT bundle it)
Remove the static `import` and the `import ".../Widgets/widgets.css"`. Instead
inject the Cesium UMD `<script>` + CSS `<link>` from a CDN inside a `useEffect`,
then read the global `window.Cesium`. Example (ProjectHomepage.tsx):

```ts
const CESIUM_BASE = "https://cdn.jsdelivr.net/npm/cesium@1.144.0/Build/Cesium";
function loadCesium(): Promise<any> {
  return new Promise((resolve, reject) => {
    if ((window as any).Cesium) return resolve((window as any).Cesium);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${CESIUM_BASE}/Widgets/widgets.css`;
    document.head.appendChild(link);
    const s = document.createElement("script");
    s.src = `${CESIUM_BASE}/Cesium.js`;
    s.onload = () => resolve((window as any).Cesium);
    s.onerror = () => reject(new Error("Cesium CDN load failed"));
    document.body.appendChild(s);
  });
}
// in useEffect:
const C = await loadCesium();
C.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || "x";
const viewer = new C.Viewer(container, { animation:false, timeline:false, /* ... */ });
```

Pin the version in `CESIUM_BASE` to whatever is in package.json.

## Verify the fix
After building, run `node --check` over every emitted chunk — the error must be
gone:
```bash
for f in .next/static/chunks/*.js; do node --check "$f" 2>/tmp/e || grep -qi "octal\|numeric escape\|SyntaxError" /tmp/e && echo "BROKEN $f"; done
```
Expect: no "BROKEN" lines. This is the ONLY reliable check — `next build`
passing does NOT prove the chunks parse.

## Note
This is the LunaV (Next.js) case. R-Tessera is a Vite SPA and bundles Cesium
fine (Vite/esbuild tolerates the embedded-wasm string). Do not carry this
CDN-load pattern into R-Tessera.

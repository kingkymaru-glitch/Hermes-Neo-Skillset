# Verify the production bundle parses (the octal-escape proof)

`next build` EXIT=0 is NOT sufficient proof the bundle is browser-valid when a
minified chunk contains an illegal strict-mode escape. Node parses *source*
fine but chokes on the minified output the same way the browser does.

After `next build`, run `node --check` on every emitted chunk:

```bash
cd /path/to/app
npx next build > /tmp/build.log 2>&1; echo "BUILD_EXIT=$?"
BAD=0
for f in .next/static/chunks/*.js; do
  if ! node --check "$f" 2>/tmp/ck.err; then
    if grep -qi "octal\|numeric escape\|SyntaxError" /tmp/ck.err; then
      echo "BROKEN CHUNK: $f"; BAD=1
    fi
  fi
done
[ "$BAD" = "0" ] && echo "ALL CHUNKS PARSE OK"
```

Failure signature seen in this engagement:
```
.next/static/chunks/2iyfwmu-9rx50.js:877
SyntaxError: Octal escape sequences are not allowed in template strings.
```
That chunk contained 77 cesium references (CesiumViewer, Ion, etc.) — confirming
the error came from the bundled Cesium wasm-as-base64 (`\0` inside a template
literal). `transpilePackages: ['cesium']` did NOT clear it. Switching the
component to CDN runtime load (see cesium-cdn-load.md) cleared it.

Note: the chunk is one giant minified line, so a `sed -n` line number will not
map to source. Grep the *whole* chunk for `\0` to confirm it's wasm/base64,
then move on — no need to read it.

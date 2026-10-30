# Vite / Rollup code-split: verifying a feature is actually live on Vercel

## The gotcha (false "stale alias" alarm)
For a Vite/Rollup SPA, `npm run build` emits an entry bundle (`index-<hash>.js`)
plus lazy-loaded chunks (e.g. `GlobeView-<hash>.js`). Code inside a
`React.lazy(() => import(...))` / dynamic `import()` only lands in a *named chunk*,
never the entry. So:

```
grep "MyNewFeature" index-<hash>.js   # → 0 matches = FALSE ALARM
```

Zero matches in the entry bundle does NOT mean the deploy is stale. It means your
feature is in a chunk. Grepping only the entry HTML's referenced JS is the wrong check.

## Correct verification procedure
1. Fetch the live entry HTML and list the JS it references:
   ```
   curl -s https://<app>.vercel.app/ | grep -oE 'assets/[A-Za-z0-9_-]+\.js' | sort -u
   ```
   (The entry is usually `index-<hash>.js`.)

2. The feature marker is probably NOT in the entry. Find which chunk holds it by
   grepping the entry for the chunk's name pattern (Vite names chunks after the
   dynamically-imported module/file):
   ```
   GV=$(grep -oE "GlobeView-[A-Za-z0-9_-]+\.js" index-*.js | head -1)
   ```
   Replace `GlobeView` with the component/file name that contains your feature.

3. Fetch THAT chunk and grep it:
   ```
   curl -s "https://<app>.vercel.app/assets/$GV" -o /tmp/live_chunk.js
   grep -c "MyNewFeature" /tmp/live_chunk.js && echo LIVE_HAS_FEATURE
   ```

4. Definitive proof: compare the chunk hash against your local `dist/assets/`.
   Identical hash name = identical bytes = the live domain is serving your exact build.

## Real example (R-Tessera Phase 2 — ROVER-KIT CCTV layer)
- Feature: a CCTV globe layer + click-to-open webcam feed window, added via
  `React.lazy(() => import('./GlobeView'))`.
- Live `index-BX_6bnYg.js` had 0 occurrences of "CCTV Cameras" → looked like a
  stale alias → I almost declared it not live.
- Correct check: `GlobeView-BHR1esfF.js` contained "CCTV Cameras",
  "rt-feed-window", AND the "stream_url" select. Its hash matched local
  `dist/assets/GlobeView-BHR1esfF.js`. → confirmed genuinely live.
- Lesson: the stale-alias alarm was a false positive caused by checking the entry
  bundle instead of the lazy chunk. Always check the chunk that owns the feature.

## Reusable checker
See `scripts/verify-vite-live.sh` — one-shot:
`verify-vite-live.sh <live-url-root> <chunk-pattern> <feature-string>`.

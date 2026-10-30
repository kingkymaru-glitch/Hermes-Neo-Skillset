# Google Photorealistic 3D Tiles in Cesium (lazy, env-keyed)

R-Tessera pattern — verified green: oxlint 0/0, `vite build` OK (2026-08-08).

## When to use
The ONE deliberate exception to a token-free Cesium setup: photorealistic
city/street 3D meshes from Google. Loaded ONLY when the user toggles a
"Google 3D" layer — never on app boot.

## Endpoint + builder
```js
// imports from 'cesium': Cesium3DTileset, GoogleMaps
export const GOOGLE_3D_ENDPOINT = 'https://tile.googleapis.com/v1/3dtiles/root.json'

export async function buildGoogle3DTileset(apiKey) {
  if (!apiKey) throw new Error('VITE_GOOGLE_MAPS_API_KEY is not set')
  GoogleMaps.defaultApiKey = apiKey   // Cesium attaches it to tile requests
  const tileset = await Cesium3DTileset.fromUrl(GOOGLE_3D_ENDPOINT, {
    maximumScreenSpaceError: 16,       // dense tiles -> relax SSE to fill in fast
  })
  return tileset
}
```

## Lazy add / remove inside the useCesium bridge
Tilesets are SCENE PRIMITIVES (`viewer.scene.primitives`) — NOT imagery layers,
NOT entities. Always keep the `isDestroyed?.()` + try/catch guards (G28).
```js
const [googleTileset, setGoogleTileset] = useState(null)

useEffect(() => {
  if (!viewer || viewer.isDestroyed?.() || !showGoogle3D) return
  let cancelled = false
  ;(async () => {
    try {
      const ts = await buildGoogle3DTileset(googleKey)
      if (cancelled || !viewer || viewer.isDestroyed?.()) return
      if (!viewer.scene.primitives.contains(ts)) viewer.scene.primitives.add(ts)
      setGoogleTileset(ts)
      onGoogleError?.(null)
    } catch (err) {
      if (cancelled) return
      onGoogleError?.(err?.message || 'Failed to load Google 3D Tiles')
    }
  })()
  return () => { cancelled = true }     // don't touch a dead viewer on unmount
}, [viewer, showGoogle3D, googleKey, onGoogleError])

// Remove the primitive when the layer is turned off.
useEffect(() => {
  if (!viewer || viewer.isDestroyed?.()) return
  if (!showGoogle3D && googleTileset) {
    viewer.scene.primitives.remove(googleTileset)
    setGoogleTileset(null)
  }
}, [viewer, showGoogle3D, googleTileset])
```

## Force 3D on enable
Photorealistic tiles only render on a globe. When the toggle turns on, force
`scene = '3d'` (morph via the bridge — see the base-layer section) so the user
never sees a flat map with no tiles.

## Graceful degradation (missing / blocked key)
If `VITE_GOOGLE_MAPS_API_KEY` is unset or the load throws, surface it via a
callback (`onGoogleError`) and disable the control-panel row with a reason —
no crash. Reuse the existing disabled-`Row` UX pattern (see MapControlPanel).

## SECURITY — the key is public
`VITE_` vars are inlined into the client bundle at build time. Anyone can read
`VITE_GOOGLE_MAPS_API_KEY` from the shipped JS. Therefore the Google Cloud API
key MUST carry an HTTP-referrer restriction (Application restrictions → HTTP
referrers → `r-tessera.vercel.app` + `localhost`). Without it, a stranger can
burn your quota. Billing stays enabled, so quota limits matter.

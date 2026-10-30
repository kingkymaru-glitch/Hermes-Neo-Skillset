# 3D Assets in Resium/Cesium (Blender / LiDAR / Photogrammetry)

Raw assets live under `public/models/<blender|lidar|photogrammetry>/` and are
served at runtime from `/models/...`. Put **converted tilesets** (the
`tileset.json` + `tiles/` folder) in `public/` so Cesium fetches them
same-origin without CORS friction; keep the original `.las`/`.laz`/`.obj` in
`public/models/<type>/` as the source-of-truth archive.

## Blender → glTF / GLB (static meshes)
- Export `.glb` (binary, single file). Draco-compress for smaller downloads.
- Render with Resium: `<Entity model={{ uri: '/models/blender/x.glb' }} />`.
  `model` is Cesium `ModelGraphics`: `{ uri, scale, minimumPixelSize,
  heightReference }`. Use `HeightReference.CLAMP_TO_GROUND` to sit on terrain.

## LiDAR (.las / .laz) → 3D Tiles (.pnts)
```bash
pip install py3dtiles
py3dtiles convert scan.laz --out public/models/lidar/tileset.json
```
Load (inside a `useCesium` component):
```jsx
const t = new Cesium.Cesium3DTileset({ url: '/models/lidar/tileset.json' })
viewer.scene.primitives.add(t)
```
Style points: `t.style = new Cesium.Cesium3DTileStyle({ color: "color('#2dd4bf')" })`

## Photogrammetry → 3D Tiles (.b3dm / .glb)
- Easiest: upload to **Cesium ion** → hosted `assetId` →
  `new Cesium.Cesium3DTileset({ ionAssetId })` (needs ion token).
- Self-host: `py3dtiles convert` (mesh mode) or `@cesium/3d-tiles-tools`.
- Same `Cesium3DTileset({ url })` load pattern as LiDAR.

## Performance
- `maximumScreenSpaceError: 16` (higher = fewer triangles drawn).
- Texture atlases ≤ 4096px; split very large sites into multiple tilesets.
- Gate each layer behind a HUD toggle so the default globe stays light.

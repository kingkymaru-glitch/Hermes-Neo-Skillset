# Cesium CDN runtime load (Next.js App Router)

Replace the static `import { Viewer } from "cesium"` + css import with a
runtime `<script>`/`<link>` injection so Cesium is NEVER in the Next bundle.

```tsx
"use client";
import { useEffect, useRef } from "react";

const CESIUM_VERSION = "1.144.0"; // match the version you'd otherwise npm-install
const CESIUM_BASE = `https://cdn.jsdelivr.net/npm/cesium@${CESIUM_VERSION}/Build/Cesium`;

function loadCesium(): Promise<any> {
  return new Promise((resolve, reject) => {
    if ((window as any).Cesium) return resolve((window as any).Cesium);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${CESIUM_BASE}/Widgets/widgets.css`;
    document.head.appendChild(link);
    const script = document.createElement("script");
    script.src = `${CESIUM_BASE}/Cesium.js`;
    script.onload = () => resolve((window as any).Cesium);
    script.onerror = () => reject(new Error("Failed to load Cesium from CDN"));
    document.body.appendChild(script);
  });
}

export default function Globe() {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let destroyed = false;
    (async () => {
      const C = await loadCesium();
      if (destroyed || !containerRef.current) return;
      C.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || "local-dev-no-ion";
      const viewer = new C.Viewer(container, {
        animation: false, timeline: false, baseLayerPicker: false,
        geocoder: false, homeButton: false, sceneModePicker: false,
        navigationHelpButton: false, fullscreenButton: false,
        infoBox: false, selectionIndicator: false,
      });
      viewerRef.current = viewer;
      viewer.camera.setView({ destination: C.Cartesian3.fromDegrees(0, 20, 18000000) });
    })();
    return () => {
      destroyed = true;
      viewerRef.current?.destroy();
      viewerRef.current = null;
    };
  }, []);

  return <div ref={containerRef} style={{ width: "100%", height: 480 }} />;
}
```

Key points:
- Use `window.Cesium` (the global from `Cesium.js`), not the npm import.
- You may drop the `cesium` npm dependency entirely once on CDN — but leaving
  it installed is harmless as long as nothing imports it.
- `next.config.ts` `transpilePackages: ['cesium']` is NOT needed for this
  approach; remove it to avoid confusion.
- **Satellite base without Ion**: pass `baseLayer`:
  ```ts
  const esri = new C.ImageryLayer(new C.UrlTemplateImageryProvider({
    url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    maximumLevel: 19,
    credit: "Esri, Maxar, Earthstar Geographics",
  }));
  const viewer = new C.Viewer(container, { ..., baseLayer: esri });
  ```
  This is free and keyless — no Cesium Ion token needed.
- **flyTo race condition**: if you have a separate effect that calls
  `viewer.camera.flyTo(site.center)` when the center coordinate loads, it fires
  BEFORE `loadCesium()` resolves → `viewerRef.current` is null → skipped.
  After Cesium loads, the center dependency hasn't changed → flyTo never fires
  again. Fix: add a `cesiumReady` state, set after `new C.Viewer(...)`, include
  it in the flyTo deps:
  ```ts
  const [cesiumReady, setCesiumReady] = useState(false);
  // in bootstrap: viewerRef.current = viewer; setCesiumReady(true);
  // flyTo deps: [site?.center_lon, site?.center_lat, cesiumReady]
  ```
- **Loading indicator**: while `!cesiumReady && !error`, show an overlay over
  the container div so the user sees progress, not a blank area:
  ```tsx
  {!cesiumReady && !error && (
    <div style={{ position: "absolute", inset: 0, display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 2 }}>
      🌐 Loading globe…
    </div>
  )}
  ```
- **Container height**: if the globe is wrapped in a `<div className="ph-shell">`
  inside a `flex flex-col` layout with a nav bar, the shell div MUST get
  `style={{ flex: 1 }}` and the outer wrapper MUST have a definite height
  (`height: "100dvh"`), NOT `min-h-screen` — flex children with `height: 100%`
  collapse to 0 inside a `min-height` parent.

# Mobile-fullscreen Three.js + swappable center model + Cesium combo page

## When to use
A Next.js App Router page that is a **marketing/showcase hero** where:
- The center of the screen is a Three.js stage showing a 3D model (default procedural, admin-swappable for uploaded GLB)
- Below the fold is a Cesium globe with geotagged data (shops, events)
- The page is mobile-first: full-screen canvas, touch controls, safe-area aware
- Hero content (title, tagline, stats) is admin-editable via a Supabase JSONB table, not hardcoded
- Visitors browse freely without registration; only RSVP/engage requires an account

## Architecture (proven in Trip.Pancing)

```
src/
  app/
    page.tsx          — hero: Three.js (LureScene) + CesiumGlobe below
    admin/page.tsx     — CMS for hero text, stats, center model upload
  components/
    LureScene.tsx      — Three.js stage (OrbitControls, swappable GLB)
  hooks/
    useLandingContent.ts — fetches landing_content JSONB from Supabase
  supabase/migrations/
    005_landing_content.sql — JSONB table for hero/stats/center_model
```

## The Three.js stage (LureScene.tsx)

```tsx
'use client';
import { useEffect, useRef } from 'react';

export default function LureScene({ glbUrl }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    let disposed = false;
    Promise.all([
      import('three'),
      import('three/addons/loaders/GLTFLoader.js'),
      import('three/addons/controls/OrbitControls.js'),
    ]).then(([THREE, { GLTFLoader }, { OrbitControls }]) => {
      if (disposed) return;
      const canvas = canvasRef.current;
      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setSize(window.innerWidth, window.innerHeight);
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(42, innerWidth/innerHeight, 0.1, 100);
      camera.position.set(0, 0.4, 7);
      // lights (ambient + key + rim + fill)
      const controls = new OrbitControls(camera, canvas);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.enablePan = false;
      controls.minDistance = 3; controls.maxDistance = 12;
      controls.autoRotate = true; controls.autoRotateSpeed = 0.8;
      controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
      // wireframe globe background
      // center model (GLB or procedural lure)
      const setCenterModel = (obj) => {
        const box = new THREE.Box3().setFromObject(obj);
        const size = new THREE.Vector3(); const center = new THREE.Vector3();
        box.getSize(size); box.getCenter(center);
        const scale = 3.5 / Math.max(size.x, size.y, size.z);
        obj.scale.setScalar(scale);
        obj.position.sub(center.multiplyScalar(scale));
        scene.add(obj);
      };
      if (glbUrl) new GLTFLoader().load(glbUrl, g => setCenterModel(g.scene));
      else setCenterModel(buildLure());
      // animate loop
    });
    return () => { disposed = true; };
  }, [glbUrl]);
  return <canvas ref={canvasRef} style={{ display:'block', width:'100%', height:'100%' }} />;
}
```

## Mobile rules (these matter)
- **`position: fixed; inset: 0`** for the stage container — full viewport, not 100vh (100vh jumps on mobile browser chrome).
- **`controls.touches`** must be set explicitly — OrbitControls defaults to `ROTATE/PAN` on touch, but `DOLLY_PAN` gives pinch-zoom which feels natural for a center model.
- **`safe-area-inset-*`** on iOS: title bar and bottom wheel use `env(safe-area-inset-top)` and `env(safe-area-inset-bottom)`.
- **`-webkit-tap-highlight-color: transparent`** on body — removes blue flash on tap.
- **`<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">`** — prevents accidental zoom while inspecting the model.
- **`scroll-snap-type: x mandatory`** on the bottom wheel — horizontal swipe feels native on mobile.

## Dynamic import (critical in Next.js)
Three.js touches `window` at import time. In a Next.js page, the viewer component MUST be:
```tsx
const LureScene = dynamic(() => import('@/components/LureScene'), { ssr: false });
```
And inside LureScene itself, Three.js is imported with `import('three')` inside `useEffect`, not at module top — this avoids SSR window errors even with `ssr: false` on the parent.

## Admin-only model swap (security pattern)
- Upload path: admin popup → `supabase.storage.from('bucket').upload(path, file)` → get public URL → save URL to `landing_content` table (section=`center_model`, jsonb `{url, use_default_lure:false}`).
- The upload UI is hidden behind an auth gate: admin page checks `profiles.role === 'admin'`; non-admins never see upload controls.
- Center model URL is passed as prop to LureScene; if null, show procedural lure.
- Deleting/resetting also writes to `landing_content` so all visitors see the change.

## Hero content editing (JSONB pattern)
Create one table for all admin-editable landing content:
```sql
CREATE TABLE landing_content (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  section text NOT NULL UNIQUE,  -- 'hero' | 'stats' | 'center_model' | 'highlights'
  data jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz DEFAULT now()
);
-- RLS: public SELECT, admin-only INSERT/UPDATE
```
This lets an admin CMS page (`/admin`) upsert rows by section, and the hero page fetches all rows on mount. No code change needed to edit text, stats, or the center model.

## Verification
- `npx tsc --noEmit` — clean types.
- `npm run build` — page compiles (Cesium via CDN script tag, not bundled).
- Mobile check: real device test for touch rotate + scroll wheel + safe-area.
- Admin check: non-admin user visits `/admin` → redirected to `/`.

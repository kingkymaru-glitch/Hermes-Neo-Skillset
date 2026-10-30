# Next.js App Router feature recipes (LunaV Studio)

Tested patterns from the 2026-08-25 GAP 2 wedge demo: connect an edge device
(Jetson / "Luna EDGE" YOLO) to a LunaV twin view via a public HTTP endpoint.

## 1. Route + page at the same segment = 500
`app/wedge/route.ts` + `app/wedge/page.tsx` → `Conflicting route and page at /wedge`.
Split: API under `app/api/wedge/route.ts`, UI at `app/wedge/page.tsx`.

## 2. Public session-free endpoint (machine client)
`src/middleware.ts` `isPublic` block — add BOTH:
```ts
path.startsWith("/api/wedge") ||
path.startsWith("/wedge");   // read-only live view page
```
The matcher regex does NOT exclude `/api/*`, so middleware still runs on the API
route — the allow-list is what opens it. Without it: `307 → /login`.

## 3. Shared in-memory store across route files (survives HMR)
`src/lib/wedge-global.d.ts` (single source of truth for the type):
```ts
export {};
declare global {
  globalThis: { __wedgeStore?: { detections: WedgeDetection[] } };
  type WedgeDetection = {
    id: string; camera_id: string; ts: number; class: string;
    confidence: number; bbox: { x: number; y: number; w: number; h: number };
    acknowledged?: boolean; action?: string;
  };
}
```
Route file init (NOT redeclared per file — that widens to `never[]`):
```ts
import type { WedgeDetection } from "@/lib/wedge-global";
const store: { detections: WedgeDetection[] } =
  globalThis.__wedgeStore ?? (globalThis.__wedgeStore = { detections: [] as WedgeDetection[] });
```
POST appends; GET returns `{ detections: [...] }`; ack route flips `acknowledged`.

## 4. Edge device = plain HTTP POST (the real Jetson hook)
The simulator `scripts/luna_edge_sim.py` is literally what the Jetson runs:
```bash
python3 scripts/luna_edge_sim.py --url http://localhost:3000/api/wedge --rate 1.2
```
JSON shape: `{ "camera_id": "CAM-02", "class": "trespasser",
"confidence": 0.91, "bbox": {"x":0.2,"y":0.3,"w":0.15,"h":0.25} }`
For prod: add an edge auth token header on `/api/wedge` and persist to Supabase.

## 5. Verification recipe (no browser — MARU rule: no headless Chrome)
```bash
# start dev (note port — 3000 may be taken -> 3001)
npm run dev
B=http://localhost:3001
curl -s -X POST $B/api/wedge -H 'Content-Type: application/json' \
  -d '{"camera_id":"CAM-02","class":"trespasser","confidence":0.91,"bbox":{"x":0.2,"y":0.3,"w":0.15,"h":0.25}}' \
  -w "HTTP %{http_code}\n"      # -> 200
curl -s $B/api/wedge | python3 -c "import sys,json;print(len(json.load(sys.stdin)['detections']))"
curl -s -o /dev/null -w "PAGE HTTP %{http_code}\n" $B/wedge   # -> 200 (NOT 307)
```
Run the Python sim in parallel to prove multi-detection ingest end-to-end.

## 6. LunaV visual constants (match the twin's look)
- Stage bg `0x232d3a`, grid + rim `0x00e5c3` (turquoise), camera at `(30,20,30)`.
- Panels: solid `rgba(20,28,38,0.72)`, blur 12, 1px `rgba(0,229,195,0.25)` border,
  radius 8, text `#cdd6e0` / muted `#7d8aa0`.
- Threat class palette: trespasser=#ff4d4f, fire=#ff7a45, smoke=#ffb84d,
  flood=#4d9bff, vehicle=#9b6dff, wildlife=#7ed957, ppe_missing=#ffd166.
- Three.js `CSS2DRenderer` for HTML marker labels (same as Viewer3D markers).

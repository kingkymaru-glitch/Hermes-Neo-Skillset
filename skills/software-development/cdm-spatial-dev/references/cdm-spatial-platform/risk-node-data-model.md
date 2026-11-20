# CDM risk-node data model

## `risk_nodes` (the core table)

PK: `uuid` default `gen_random_uuid()`; `project_id` FK → `projects(id) ON DELETE CASCADE`.

| Column | Type | Notes |
|---|---|---|
| `risk_level` | text CHECK IN ('RED','AMBER','GREEN') | **derived** from L×S; drives the RING colour |
| `name` | text | user-editable label |
| `color` | text | **category** colour (hex), NOT criticality |
| `category` | text | `fire`/`water`/`geo`/`congestion`/`structure`/`traffic`/`utility`/`env`/`other` |
| `source` | text CHECK IN ('MANUAL','AI_DETECTED','HUMAN_ADJUSTED') | audit |
| `status` | text CHECK IN ('DETECTED','OPEN','REJECTED','MITIGATED') | audit + gate |
| `center_lon`, `center_lat` | numeric | numeric, NOT PostGIS |
| `height`, `locked_elevation` | numeric | locked elevation = metres above ground, unclamped |
| `radius_m`, `radius_fill`, `radius_width`, `radius_opacity` | numeric/bool | area-of-interest circle |
| `polygon_geom` | jsonb | optional "expanded" traced boundary |
| `likelihood`, `severity` | integer CHECK 1–5 | OSHCIM L×S inputs |
| `accepted_by`, `reviewed_at`, `ai_confidence`, `hazard_class` | text/timestamptz/numeric/text | audit trail |

RLS: permissive-for-POC (`select using (true)`) like the other tables; tighten with real auth
before client data. Only `site_risks` uses PostGIS `geometry(Polygon,4326)` — keep new tables
numeric lon/lat.

## Review state machine

```
                 (YOLO scan)                    (human drops a marker)
                      |                                  |
                      v                                  v
              status=DETECTED                      status=OPEN
              source=AI_DETECTED                   source=MANUAL
              ai_confidence set                    accepted_by set
                      |
        +-------------+-------------+
        |             |             |
      Accept       Adjust        Dismiss
        |             |             |
        v             v             v
  status=OPEN   status=OPEN   status=REJECTED
  source=HUMAN_ADJUSTED (both)   (never reportable)
  accepted_by + reviewed_at
```

**Reportable predicate:** `status === 'OPEN' && !!accepted_by`.

UI: DETECTED candidates get Accept / Dismiss in BOTH the sidebar panel and the floating node
editor, showing `ai_confidence` and `hazard_class` so the reviewer sees why it was proposed.

## RAG thresholds (OSHCIM)

```
scoreRisk(L,S) = L * S
levelForScore(score):  >= 15 RED   |  >= 5 AMBER   |  else GREEN
defaultRiskSelection:  RED [4,5]=20  |  AMBER [3,3]=9  |  GREEN [1,2]=2
```

`lib/risk.ts` is the single source of truth — `scoreRisk`, `levelForScore`, `RISK_LEVEL_STYLE`
(tailwind classes for the editor UI). Never re-derive thresholds inline in a component.

## Two-channel encoding — why it exists

MARU needs more hazard TYPES than red/amber/green can express (water/flood, geotechnical,
congestion/public unrest…) yet still needs the RAG matrix to show criticality for HSE.
Resolution: **node colour = category, ring colour = RAG criticality**, ring always drawn.
Any new visual surface must respect this split — a legend mapping colour→severity is wrong.

Ring handler: `ragLevel = levelForScore(likelihood * severity)`; ring colour is a lookup
(`RED`→`#ef4444`, `AMBER`→`#f59e0b`, `GREEN`→`#10b981`), independent of `node.color`.

## Adding a category

Add to `RISK_CATEGORIES` in `contexts/RiskNodesContext.tsx` (`{key, label, color}`); picking a
category sets BOTH `category` and the node `color`. No migration needed — `category` is free text.

## Schema-change checklist

1. Write the bare SQL to `~/Desktop/apply_cdm_<feature>.sql` (comment-free) AND the annotated copy
   to `supabase/migrations/`.
2. Add the camelCase `normalizeX(row)` mapping in the matching `app/api/<feature>/route.ts`.
3. Extend the context (`contexts/<X>Context.tsx`) with optimistic local update + PATCH on save.
4. Add the Cesium render effect keyed by `<prefix>-<id>`, guarded by `Number.isFinite` and
   try/catch, with a `viewerReady` dep so it paints as soon as the globe is live.
5. `npx tsc --noEmit` → `npx next build` → commit → push → restart dev.

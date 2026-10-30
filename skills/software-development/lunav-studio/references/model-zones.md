# Zones — grouping model placements into site sections

Depth for the "Grouping models" section of SKILL.md. Read that section first: the
invariants live there, this file is the how.

## Decision table — how a repeated GLB is modelled

| Approach | What the DB holds | Consequence |
|---|---|---|
| one row referenced by N zones (m2m) | 1 `models` row + a join table | Markers hang off `model_id`, so BOTH zones show the same findings and analytics double-counts them — it is one asset rendered twice, not two assets. REJECTED. |
| one FILE, many PLACEMENTS | N `models` rows sharing `file_url`, each with its own `zone_id`, transform, scale and markers | Two zones = two honest inspections; zero extra R2 storage (the file is uploaded once). CHOSEN. |

A new placement starts with NO pins — the inspector inspects that asset fresh. Copying the
original pins was offered and declined; do not "helpfully" carry them over.

## Schema (founder runs the bare SQL — see the SQL hand-off rule in SKILL.md)

```sql
create table if not exists public.model_groups (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  unique (project_id, name)
);

alter table public.models add column if not exists zone_id uuid references public.model_groups(id) on delete set null;
create index if not exists models_zone_id_idx on public.models(zone_id);

alter table public.model_groups enable row level security;
drop policy if exists model_groups_owner_all on public.model_groups;
create policy model_groups_owner_all on public.model_groups
  for all using (exists (select 1 from public.projects p
                where p.id = model_groups.project_id and p.owner_id = auth.uid()))
  with check (exists (select 1 from public.projects p
                where p.id = model_groups.project_id and p.owner_id = auth.uid()));

notify pgrst, 'reload schema';
```

- Owner-only RLS mirrors `models_owner_all` (project-scoped). Clients never read the table
directly — they get zones through `get_shared_project`.
- Mirror the same DDL into `supabase/schema.sql`. Order matters there: define
`model_groups` BEFORE `models`, because `models.zone_id` references it in the same script.
- A `unique (project_id, name)` violation must surface as a friendly toast
("Zone already exists"), since the UI also pre-checks case-insensitively.

## Panel-tree recipe (Project Models panel in `ProjectWorkspace.tsx`)

State: `zones`, `collapsedZoneIds`, `zoneRenameId`/`zoneRenameDraft`,
`zoneNewOpen`/`zoneNewDraft`, `zoneMenuModelId` (one open row-menu at a time),
`confirmZoneDeleteId`.

Helpers:
- `sortedZones = useMemo(sort by sort_order then created_at)` — never rely on the server
  query order alone after a local reorder.
- `placementsInZone(zoneId: string | null) = models.filter(m => (m.zone_id ?? null) === zoneId)`
  — `null` IS the Ungrouped bucket; the same helper renders both.
- Extract `renderModelRow(m)` as one local function and use it for zoned AND ungrouped rows,
  or the two list variants drift apart.

Mutations: `createZone` (insert with `sort_order = zones.length`), `renameZone`,
`reorderZone(id, ±1)` (swap locally, then persist the whole new order with
`Promise.all(update ...)`), `deleteZone` (delete row + locally null the placements'
`zone_id`), `moveModelToZone(modelId, zoneId | null)`, `reuseModelInZone(modelId, zoneId)`
(insert the copy, append with `markers: []`, make it the active model).

Rendering rules:
- Empty state = `models.length === 0 && sortedZones.length === 0`, otherwise zones with zero
  placements still render (an empty zone is legitimate and shows a hint).
- Ungrouped block renders LAST and only when it has placements.
- The row menu renders in normal flow under the row (the panel scrolls — see the SKILL.md
  dropdown pitfall).
- Every destructive zone action goes through the in-app confirm modal and the copy must say
  the placements/findings are KEPT.

## Report + analytics changes

- Flatten at the source: `allMarkers` should carry `modelName` AND the model's zone
  (`zoneId`/`zoneName`) so the report and analytics share one derived shape.
- Report: group the table by zone with a section header row carrying per-zone
  FAIL/WARNING/PASS subtotals and a collapse toggle; add a Zone dropdown beside the
  severity pills and AND the two filters (never make them exclusive — "FAIL in Block B" is
  the whole point).
- **Gate the section headers on `zones.length > 0`.** A project that has never used zones
  (and the client portal, until the RPC projection lands) must render the old flat table,
  not a single artificial "Ungrouped" section header.
- Assign the row number (`m.no`) while bucketing into sections, not from the array index —
  numbering has to stay continuous across sections so a finding keeps its report number.
- Keep the two empty states distinct: `allMarkers.length === 0` → "No inspection findings
  recorded yet", versus a zone/severity filter that matched nothing → "No findings match
  this filter". One message for both hides a filter bug behind "no data".
- Analytics: a zone scope selector narrows the severity strip, the time series AND the bar
  blocks together; add per-zone bars above the per-model bars.
- **Re-key the per-model bar Map from `model_name` to `model_id` while you are in there.**
  It is keyed by display name today, so two placements named the same (very likely once a
  file is reused across zones) silently merge into one bar.
- Client portal: add the zone fields to BOTH the `get_shared_project` model projection and a
  top-level `zones` array, or clients see the report with no grouping at all.

## Build order (one chunk per turn; verify each before the next)

1. DB + types + zone CRUD/tree in the panel (move + reuse).
2. Sidebar zone-filter mode.
3. Report zone sections + zone filter.
4. Analytics zone dimension + the `model_id` keying fix.
5. Client portal projection, then version stamp + tag + Release.

Verify per chunk with `npx tsc --noEmit && npm run build` plus a real DB check once the
founder has run the SQL. Before claiming a chunk is live, verify the deploy by commit
(`gh api repos/<owner>/<repo>/deployments` → `/statuses`) — do NOT curl a chunk filename
taken from the local `.next/` build, it always 404s on the deployed site.

## As built (chunks 1–3 delivered; 4–5 open)

- **Chunk 1** — schema + types + panel tree + all six zone mutations. Confirmed live that a
  code-only deploy leaves the feature inert until the founder runs the SQL: the REST probe
  of the new table returned `PGRST205 Could not find the table`. The workspace tolerates that
  (query error → `zones: []`), so ship the code before the SQL when the founder is the one
  running it.
- **Chunk 2** — `zoneFilter` state as a single string (`"all" | "ungrouped" | <zone id>`)
  rather than a nullable id, so Ungrouped is a first-class scope instead of a special case.
  Two effects do the work: snap `activeModelId` into `scopedModels` when the scope excludes
  it, and fall back to `"all"` when the scoped zone no longer exists. The viewer needs no
  change — scoping a single-model viewer is a state snap.
- **Chunk 3** — `ReportMarker` type (`Marker & { modelName; zoneId; zoneName }`) built in the
  `allMarkers` memo; `reportSections` buckets the severity+zone-filtered rows by
  `zoneId ?? "ungrouped"`, orders them by `sortedZones` then Ungrouped, and stamps `no`.
  Sections render via `<Fragment key={...}>` (a keyed `<>` is not legal).
- **Chunk 4** — one `analyticsZoneFilter` drives `analyticsMarkers`, and the strip / series /
  both bar blocks all read from it; `scopedCounts` was split out from the project-wide
  `counts` so the 3D-tab severity donut keeps showing whole-project totals. `modelStats`
  re-keyed to `modelId` (and now carries `zoneName` for the row label); `zoneStats` buckets
  by `zoneId ?? "ungrouped"` and is ordered by `sortedZones` then Ungrouped rather than by
  size, so the roll-up matches the inspector's arrangement. The FAIL/WARN/PASS bar markup
  was extracted into one `SeverityBars` component used by both blocks.
- **Chunk 5 (client portal projection + release stamp/tag) is the only chunk still open** —
  do not describe it as shipped. Until it lands the client portal renders flat, which is
  why every zone affordance is gated on `zones.length > 0`.

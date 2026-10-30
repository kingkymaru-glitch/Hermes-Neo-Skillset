# CHECK-constrained INSERT → bare 400 (no detail)

## Symptom
Client `supabase.from('proxies').insert({ shape: 'dimension' | 'annotation', ... })`
returns `Failed to load resource: status 400 ()` with NO error body. Browser
console shows two identical `400 () (proxies, line 0)`. No `42703`, no "column
does not exist". Looks identical to "migration not applied" but re-running a
column-only SQL does not fix it.

## Root cause
The live table's CHECK constraint still only permits the OLD enum values:
`check (shape in ('box','plane'))`. PostgREST rejects the row at the constraint
BEFORE column logic — so adding columns the row needs is irrelevant. A bare
`400 ()` with no JSON body is the tell-tale of a CHECK rejection (PostgREST
returns detail for missing columns, not for constraint violations of this kind).

## Fix (idempotent — safe to re-run if a half-fix was already applied)
```sql
begin;

alter table public.proxies drop constraint if exists proxies_shape_check;
alter table public.proxies
  add constraint proxies_shape_check
  check (shape in ('box','plane','dimension','annotation'));

-- columns the new shapes carry (idempotent):
alter table public.proxies add column if not exists point_a jsonb;
alter table public.proxies add column if not exists point_b jsonb;
alter table public.proxies add column if not exists dimension_value text;
alter table public.proxies add column if not exists dimension_unit text;
alter table public.proxies add column if not exists dimension_note text;
alter table public.proxies add column if not exists annotation_text text;

-- recorded value is a free-text inspection record, not computed → nullable:
alter table public.proxies alter column dimension_value drop not null;

commit;
```
No `NOTIFY pgrst` needed for CHECK/column add in modern Supabase (PostgREST
auto-reloads), but harmless to include if unsure.

## Why column-only fix failed earlier
First hand-off SQL added `dimension_value/unit/note` + `point_a/b` but never
touched `proxies_shape_check`. User re-ran it, still 400'd — confirming the
constraint, not the columns, was the blocker.

## Code side (so the app sends the right shape)
- `types.ts`: `shape: "box" | "plane" | "dimension" | "annotation";` + add
  `annotation_text?: string | null;` to `ProxyShape`.
- Viewer render: handle `shape === 'annotation'` → arrow (cone + line + base
  sphere) + CSS2D text label; clicking the label fires an edit callback.
- ProjectWorkspace: armed `addAnnotationMode` → click handler → `insert` with
  `shape:'annotation'`, `point_a` set, `annotation_text:''`. Editor modal
  writes `annotation_text`. Delete button calls `removeProxy` (which already
  has a confirm() guard).
- Dimension: same pattern — `shape:'dimension'`, `point_a/point_b`, recorded
  value/unit/note via a label-click editor; NO computed length (model is a
  representation, not survey-accurate).

## Deploy note
Code merged to `main` + Vercel auto-deploys. The SQL must ALSO be run in the
LIVE Supabase SQL Editor (Dashboard > SQL > New query). Until then the app
still 400s in production. Agent cannot run live SQL (no Supabase CLI link /
no creds) — ship the script to ~/Desktop and tell the user to paste it.

## Verification after applying SQL
Attempt the actual client write (click the Dimension/Annotation tool) → should
persist, no 400. If still 400, the SQL did not actually run on the live
project (wrong project / wrong branch) — re-check which Supabase project the
app's keys point at.

# Extending the client-share bundle (documents, proxies, new entity types)

This codebase (`ss-rover-cloud`) shows a 3D digital-twin inspector with a public
read-only client portal keyed by an unguessable UUID share token. Adding a new
first-class entity that must appear in BOTH the owner cockpit and the shared view
follows one exact recipe. Skipping any step = the new data is visible to the owner
but invisible to the client, or breaks the build.

## Why the RPC must be re-emitted, not just added
The share portal does NOT query tables directly (no anon RLS). It calls ONE
`security definer` function `get_shared_project(share_token uuid)` that returns the
whole bundle as `jsonb`. Adding a table + RLS policy is NOT enough — you must
RE-WRITE the function body to `coalesce(jsonb_agg(...))` the new entity inside the
`jsonb_build_object(...)`. Postgres does not auto-include new tables.

## The recipe (idempotent, re-runnable)
1. **Migration SQL** (separate `supabase/phaseN.sql` file — do not edit the original
   `schema.sql` in place for additive work):
   ```sql
   create table if not exists public.documents (
     id uuid primary key default gen_random_uuid(),
     project_id uuid not null references public.projects(id) on delete cascade,
     file_name text not null, file_url text not null,
     file_ext text not null check (file_ext in ('pdf','jpg','jpeg','png','webp','gif')),
     kind text not null default 'doc' check (kind in ('doc','photo')),
     created_at timestamptz not null default now()
   );
   create index if not exists idx_documents_project on public.documents(project_id);
   alter table public.documents enable row level security;
   create policy if not exists "documents_owner_all" on public.documents
     for all using (exists (select 1 from public.projects p
       where p.id = documents.project_id and p.owner_id = auth.uid()))
     with check (exists (select 1 from public.projects p
       where p.id = documents.project_id and p.owner_id = auth.uid()));
   ```
2. **Re-emit the RPC** — `create or replace function public.get_shared_project(...)`
   with the new block added INSIDE the top-level `jsonb_build_object`:
   ```sql
   'documents', coalesce((
     select jsonb_agg(jsonb_build_object(
       'id', d.id, 'file_name', d.file_name, 'file_url', d.file_url,
       'file_ext', d.file_ext, 'kind', d.kind, 'created_at', d.created_at)
       order by d.created_at)
     from public.documents d where d.project_id = p.id
   ), '[]'::jsonb),
   ```
3. **TS types** (`src/lib/types.ts`): add the interface, extend `SharedProjectBundle`:
   ```ts
   export interface ProjectDocument { id:string; project_id:string; file_name:string;
     file_url:string; file_ext:string; kind:"doc"|"photo"; created_at:string; }
   export interface SharedProjectBundle {
     project: ...; documents: ProjectDocument[]; proxies: ProxyShape[]; models: ...; }
   ```
4. **Owner page** (`src/app/project/[id]/page.tsx`): fetch + forward defensively:
   ```ts
   const { data: documents } = await supabase.from("documents").select("*")
     .eq("project_id", id).order("created_at");
   documents: (documents ?? []) as ProjectDocument[],
   ```
5. **Share page** (`src/app/share/[token]/page.tsx`): forward from the RPC bundle:
   ```ts
   documents: bundle.documents ?? [],
   ```
6. **Client component** (`ProjectWorkspace.tsx`): `WorkspaceData` gains optional
   `documents?` / `proxies?`; `useState(initial.documents ?? [])`; tab body renders
   them; R2 upload reuses the existing `uploadToR2(file, projectId, "doc", onProgress)`.
7. **Edge Function** (`r2-presign/index.ts`): extend `ALLOWED_EXT` (add `"pdf"`),
   and map the new `kind` to an R2 prefix (`kind === "doc" ? "docs" : ...`).

## Fail-safe pattern (so the app builds before the SQL is applied)
- Every forward uses `?? []` / `as Type[]` so a missing table (SQL not yet run)
  yields an empty list, not a crash.
- DB writes (`insert`/`update`/`delete`) are wrapped in try/catch that surfaces a
  toast — a schema-migration-not-yet-applied state shows an error toast; the app
  keeps running.
- `npm run build` (TypeScript) is the gate, NOT lint. This repo's `npm run lint`
  reports ~130 "errors" that are pre-existing ESLint-rule nits in the ORIGINAL code
  (e.g. `liveRef.current` assigned during render, `setState` inside `useEffect`)
  and still exits 0. If `next build` passes, the code is shippable.

## Deploy order (after build is green, local-only)
- Schema: paste the migration SQL into the Supabase SQL Editor, or `supabase db push`.
- Edge Function: `supabase functions deploy r2-presign` (so new ext/kind are accepted).
- These are Supabase-side. The `git push` to a Vercel-linked main is the go-live
  event and is held until the user explicitly approves (local-first gate).

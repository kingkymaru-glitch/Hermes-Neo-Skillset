# LUNASCAN Import Seam — Implementation Notes

## Edge Function: r2-list

Location: `supabase/functions/r2-list/index.ts`

### Pattern
Follows same auth + S3 pattern as `r2-presign`:
- Supabase user JWT required (auth.getUser)
- Inspector role check (profiles table)
- Approved check
- Uses `@aws-sdk/client-s3` `ListObjectsV2Command`

### Response shape
```typescript
{
  scans: [{
    prefix: "job-2026-08-05/site/",
    glb: { key, size, lastModified, url } | null,
    manifest: { key, size, lastModified, url } | null,
    otherFiles: [{ key, size, lastModified, url }]
  }]
}
```

### Grouping
Files are grouped by directory prefix (everything before the last `/`). A `site_model.glb` under `job-42/site/` pairs with `job-42/site/manifest.json` as one scan group.

### Secrets
Same R2 secrets as `r2-presign`: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

## DB Migration

Location: `supabase/migrations/20260805_lunascan_import.sql`

```sql
do $$ begin
  alter table public.models
    add column source text not null default 'manual'
    check (source in ('manual', 'lunascan'));
exception
  when duplicate_column then null;
end $$;

create index if not exists idx_models_source
  on public.models(source);
```

Idempotent — safe to re-run. Uses DO block with exception catch for duplicate_column.

## Client-side: r2-list.ts

Location: `src/lib/r2-list.ts`

Calls edge function via `supabase.functions.invoke("r2-list", { body: { projectId } })`. Returns `R2ListResponse`.

## Import modal: ImportScanModal.tsx

Location: `src/components/ImportScanModal.tsx`

- Fetches scans on mount via `listR2Scans(projectId)`
- Shows loading/error/empty states
- Each scan card shows: GLB filename, size, manifest metadata
- "Import" button calls `onImport(scan)` which inserts into `models` table
- Loading skeleton, error toast pattern matches rest of LunaV UI

## Workspace wiring: ProjectWorkspace.tsx

Three insertions:
1. **Import**: `ImportScanModal`, `ScanGroup` type
2. **State**: `const [importOpen, setImportOpen] = useState(false)`
3. **Handler**: `handleImportScan(scan: ScanGroup)` — inserts into Supabase `models` table with `source: "lunascan"`, updates local state, sets active model
4. **Button**: "Import from R2" below "+ Add Model" in sidebar
5. **Modal**: `<ImportScanModal>` before toasts block in return

## Validation

- `npx tsc --noEmit`: 0 errors
- `npm run build`: ✓ compiled, all pages generated
- Pre-existing `/admin` prerender failure: fixed by providing `.env.local` with `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` (auto-gitignored by `.gitignore`)

## Deploy steps

1. Run migration in Supabase SQL Editor: `supabase/migrations/20260805_lunascan_import.sql`
2. Deploy edge function: `supabase functions deploy r2-list` (secrets should already be in vault from `r2-presign`)
3. E2E test: run LUNASCAN with `--r2-upload`, then "Import from R2" in LunaV
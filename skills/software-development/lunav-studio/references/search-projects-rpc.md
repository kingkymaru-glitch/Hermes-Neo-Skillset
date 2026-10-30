# search_projects RPC — full SQL

Run in Supabase SQL Editor for the LunaV project (`okzmblyboudjffaifixa`).

```sql
create or replace function public.search_projects(
  p_search   text default null,
  p_severity text default null,
  p_sort     text default 'updated'
)
returns table(
  id                  uuid,
  project_name        text,
  created_at          timestamptz,
  updated_at          timestamptz,
  client_share_token  uuid,
  model_count         bigint,
  fail_count          bigint,
  warning_count       bigint,
  pass_count          bigint
)
language sql
security definer set search_path = public
stable
as $$
  with project_stats as (
    select
      p.id,
      p.project_name,
      p.created_at,
      greatest(
        p.created_at,
        coalesce(max(m.created_at),  p.created_at),
        coalesce(max(mk.created_at), p.created_at)
      ) as updated_at,
      p.client_share_token,
      count(distinct m.id) as model_count,
      count(distinct mk.id) filter (where mk.status = 'FAIL')    as fail_count,
      count(distinct mk.id) filter (where mk.status = 'WARNING') as warning_count,
      count(distinct mk.id) filter (where mk.status = 'PASS')    as pass_count
    from public.projects p
    left join public.models  m  on m.project_id  = p.id
    left join public.markers mk on mk.model_id   = m.id
    where p.owner_id = auth.uid()
    group by p.id
  )
  select *
  from project_stats ps
  where
    (p_search is null or p_search = ''
     or ps.project_name ilike '%' || p_search || '%'
     or exists (
       select 1 from public.models m
       where m.project_id = ps.id and m.model_name ilike '%' || p_search || '%'
     ))
    and (p_severity is null or p_severity = ''
         or case p_severity
           when 'FAIL'    then ps.fail_count    > 0
           when 'WARNING' then ps.warning_count > 0
           when 'PASS'    then ps.pass_count    > 0
           else true
         end)
  order by
    case when p_sort = 'name'    then ps.project_name end asc,
    case when p_sort != 'name'   then ps.updated_at   end desc
  ;
$$;

grant execute on function public.search_projects(text, text, text) to authenticated;
```

## How it works

1. CTE `project_stats` LEFT JOINs `projects → models → markers`, aggregates per project:
   - `updated_at` = latest of project.created_at, any model.created_at, any marker.created_at
   - `model_count` = distinct models per project
   - `fail_count/warning_count/pass_count` = distinct markers filtered by status
   - `WHERE owner_id = auth.uid()` scopes to current user (RLS equivalent)
2. Outer WHERE applies search (ILIKE) and severity filter (CASE)
3. ORDER BY uses CASE expressions for dynamic sort direction
4. Uses `security definer` so the function runs as the database owner, bypassing RLS — the `auth.uid()` check provides equivalent row-level scoping

## Frontend call pattern

```ts
// Dashboard homepage call (2026-08-05: severity filter REMOVED — always passes null)
const { data } = await supabase.rpc("search_projects", {
  p_search: searchTerm || null,
  p_severity: null,           // no longer used on dashboard — filter is on Audit Report tab
  p_sort: "updated"            // "updated" | "name"
});
// data: ProjectCard[] — typed via src/lib/types.ts
```

The `p_severity` parameter still works in the RPC (FAIL/WARNING/PASS filter on project-level severity counts), but the dashboard homepage consumer always passes `null`. Severity filtering for individual findings was moved to the Audit Report tab (see `references/audit-report-filter-pattern.md`).

## Pitfalls

- **Column-order mismatch (Error 42P13):** The CTE's `SELECT` column order MUST match the `RETURNS TABLE(...)` column order exactly. Postgres matches by position, not by name. If you get `ERROR: 42P13: return type mismatch ... Final statement returns uuid instead of timestamp with time zone at column 4`, swap columns in the CTE to match the return type declaration. This happened with `client_share_token` (uuid) at position 4 where `updated_at` (timestamptz) was expected.
- `bigint` in Postgres maps to `number` in JavaScript for counts — handled automatically by PostgREST
- Empty string vs null: both `null` and `''` bypass the filter in the WHERE clause
- The function is `stable`, not `immutable`, because it calls `auth.uid()`
- Always run with `create or replace` — idempotent, safe to re-run
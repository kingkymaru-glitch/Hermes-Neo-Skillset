# pgvector RAG over Supabase (vector writes + semantic search via supabase-js)

Working, verified path for enabling pgvector retrieval on a Supabase project and
driving it from a Next.js/Node client. PostgREST has no native vector JSON type,
so both the WRITE (seeding) and the QUERY embedding must be handled explicitly.

## Migration (002_vector_schema)
```sql
create extension if not exists vector;

create table if not exists public.document_chunks (
  id          uuid primary key default gen_random_uuid(),
  category    text not null,
  hazard      text not null,
  description text not null,
  mitigation  text not null,
  embedding   vector(1536),            -- dimension MUST match the embedder
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now()
);

create index if not exists document_chunks_embedding_hnsw_idx
  on public.document_chunks using hnsw (embedding vector_cosine_ops);

alter table public.document_chunks enable row level security;
create policy "Enable read access for all users"
  on public.document_chunks for select using (true);
```

## THE trap: pass the query embedding as pgvector-LITERAL TEXT, not an array
A supabase-js `rpc()` argument that is a JS array (`[0.1, 0.2, ...]`) is sent as
JSON; PostgREST then mangles or rejects it when the SQL casts to `vector`. The
reliable form is to serialize to the pgvector literal string and cast in SQL:

```sql
create or replace function public.search_document_chunks(
  query_embedding_text text,          -- pgvector literal, e.g. "[0.1,0.2,...]"
  match_count int default 3
)
returns table (category text, hazard text, description text, mitigation text,
               similarity double precision)
language sql stable security invoker
as $$
  select dc.category, dc.hazard, dc.description, dc.mitigation,
         1 - (dc.embedding <=> query_embedding_text::vector) as similarity
  from public.document_chunks dc
  where dc.embedding is not null
  order by dc.embedding <=> query_embedding_text::vector
  limit match_count;
$$;
grant execute on function public.search_document_chunks(text, int)
  to anon, authenticated, service_role;
```
Serialize on the client: `'[' + embedding.join(',') + ']'`.

## Seeding / writing the vector column
PostgREST cannot `.insert()` a `vector` value from JSON either (same class of
problem as PostGIS `geometry`). Unlike geometry, `vector` DOES accept a
text-literal through a normal insert:
```ts
await supabase.from("document_chunks").insert({
  category, hazard, description, mitigation,
  embedding: toVectorLiteral(embedding),   // "[0.1,0.2,...]"
  metadata: { source: "..." },
});
```
If you prefer an RPC for writes, mirror the WKT→geometry pattern: take a text
param and store via `CAST(p_embedding_text AS vector)`.

## supabase-js `rpc()` type-inference failure (v2.116)
Even with a correct `Database` generic declaring the function under `Functions`,
some supabase-js versions type `supabase.rpc`'s args as `undefined`, so a typed
call fails with `Argument of type {...} is not assignable to parameter of type
'undefined'`. Don't fight the generic — cast narrowly and keep the result typed
by assigning to your own interface:
```ts
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const { data, error } = await (supabase.rpc as any)("search_document_chunks", {
  query_embedding_text: toVectorLiteral(embedding),
  match_count: 3,
});
const results = (data ?? []) as { category: string; hazard: string;
  mitigation: string; similarity: number }[];
```
`data` for a `returns table(...)` function is an ARRAY of row objects.

## One shared embedder drives BOTH seed and search
Put `embedText()` in one module imported by both the seed script and the search
route so the mock/real split can never diverge between write-time and query-time.
- `OPENAI_API_KEY` set → `text-embedding-3-small`, `dimensions: 1536`.
- key absent → deterministic, L2-NORMALIZED mock. NOT zeros: map each word to a
  stable bucket (FNV-1a hash `% dim`, increment), then normalize. All-zeros make
  every cosine distance identical (meaningless ranking); a bag-of-words histogram
  gives keyword-overlap similarity that actually ranks a test corpus correctly.
- Log a warning once when the mock is used ("keyword-overlap, not semantic") so a
  future run knows the scores aren't semantic. Same helper both sides means
  swapping in a real key later needs NO code change — just re-run the seed.

## Idempotent RAG seed
Clear before insert so re-running never duplicates:
```ts
await supabase.from("document_chunks").delete().in("category", categories);
```
Then insert each chunk. Report row + category counts at the end.

## Verify
- `curl -X POST .../api/search -H 'Content-Type: application/json' -d '{"query":"..."}'`
- With the mock, check RANKING not magnitude: similarity values are small
  (~0.1–0.3) but the intended hit should be #1 for a keyword-matched query.

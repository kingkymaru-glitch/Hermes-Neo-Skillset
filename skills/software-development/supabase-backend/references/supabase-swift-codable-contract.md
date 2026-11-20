# Supabase ↔ Swift (supabase-swift) decode contract

When the iOS client uses `supabase-swift` (PostgREST) to decode rows into `Codable`
structs, a WRONG COLUMN TYPE yields a **silent runtime decode failure** — not a compile
error, not a `swiftc -parse` error. The CLI host cannot catch these; only a live fetch
or a `swift` mirror test does. Rules proven on AnglerGO (2026-07-27):

## Column type → Swift mapping
- **`String`-backed `Codable` enum with non-identifier raw values** (emoji `"🎣 Tackle"`,
  spaces, punctuation): store as **`text`**. A Postgres `ENUM` makes PostgREST return
  `{name:"tackleShop"}` instead of the raw string → `Decodable` throws.
  **NEVER use a PG enum for a Swift String-raw enum.**
- **Nested collections** (`[String: [TimeSlot]]`, `[[String:Any]]`): store as **`jsonb`**
  (default `'{}'::jsonb`). `text`/`json` will NOT decode into a Swift Dictionary/Array.
- **UUID foreign keys** (`owner_user_id` → `auth.users(id)`): `uuid`. The Swift model can
  keep it as `String?`; PostgREST returns the uuid as a string and `Codable` maps fine.
- **`timestamptz` dates**: configure `SupabaseClient` `dateDecodingStrategy = .iso8601`.
  Swift's default (seconds-since-1970) throws on ISO strings (see AnglerGO `SupabaseService` init).
- **Binary (images)**: NEVER store in the table. Store `image_url text` (public Storage URL)
  and keep `Data?` local-only, excluded from `CodingKeys` (the 1 MB doc-limit rule).

## RLS + ownership (so the fetch returns rows)
- Owner-scoped tables: every policy `using (auth.uid() = <owner_col>)`.
- Public discovery (marketplace): `for select using (true)`.
- Anon key is safe client-side; RLS enforces ownership. Do NOT ship `service_role`.

## DDL decisions that diverged from a directive (AnglerGO 7D, 2026-07-27)
When a task directive's SQL conflicts with the ACTUAL Swift model, the model wins (rule #2:
read code, not docs). Concrete case: directive said `owner_user_id UUID ... NOT NULL ...
ON DELETE CASCADE` + a single `FOR ALL` policy; the model (`Shop.ownerUserID: String?`)
and the dashboard's empty-string-owner seed path meant `NOT NULL` risked insert failures and
`CASCADE` would delete marketplace rows when an owner closed their account. Corrected to
`owner_user_id uuid ... ON DELETE SET NULL` (nullable) + 3 scoped policies (insert/update/delete).
**Always diff the directive's DDL against the real `Codable` model + call sites before applying.**

## Porting a Firebase Firestore listener to Supabase (no Realtime channel)
Supabase free tier real-time needs Realtime channels; a straight port can substitute a
**one-shot fetch on init + a re-callable `load()`** for marketplace/discovery (no live updates).
Keep the public facade identical (`@Published var items`, `save(item, …) { result in }`) so
call sites compile untouched. Only add Realtime if the UI genuinely needs live push.

## Verification when no DB is on the host
1. `swiftc -parse` the model file (syntax ONLY — does NOT prove decode).
2. Executable mirror test: decode a sample JSON (matching column names + jsonb shape) into
   the REAL struct with `JSONDecoder` on the macOS `swift` CLI. Catches type/key mismatches
   without PostgREST.
3. Static SQL check (`scripts/verify_sql_static.py`): paren/quote balance + assert
   decode-critical columns (`availability jsonb`, `shop_type text`).

## Harness pitfalls (bit this session — ad-hoc verification only)
- **Swift ternary-as-statement fails to parse** in a throwaway mirror test written via a
  single-line `cat >` heredoc: `let x: Int = cond ? a : b` as a *statement* errors
  ("consecutive statements on a line must be separated by ';'" / "cannot convert Bool to Int").
  Use MULTI-LINE form with the ternary inside an expression/return, or wrap in `if/else`.
- **Python f-string cannot contain a regex backslash** (`\s`, `\.`). Inside a heredoc
  `python3 <<'PY' …` this raises `SyntaxError: f-string expression part cannot include a
  backslash`. Capture the match with `bool(re.search(r"…", src))` into a plain variable, then
  `print("label ->", "OK" if ok else "BAD")` — never put the regex inside the f-string.
- Run the ad-hoc check from a `hermes-verify-*` temp file (the gate's expected prefix); it is
  static analysis, NOT a DB execution — label it accordingly.

## Anon key is now the "Publishable key"
Settings → API Keys → `sb_publishable_…`. It is a long JWT; paste it COMPLETE — chat
truncates long secrets (see P8).

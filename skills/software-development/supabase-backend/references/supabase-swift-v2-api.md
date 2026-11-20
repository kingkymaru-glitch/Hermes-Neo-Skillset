# supabase-swift v2 API surface (authoritative, fetched from source)

Pinned in AnglerGO: **supabase-swift 2.53.0** (`Package.resolved`). Tags on
GitHub use a `v` prefix (`v2.53.0`). Fetch real signatures from
`https://raw.githubusercontent.com/supabase/supabase-swift/v2.53.0/Sources/...`
— do NOT guess from memory; the installed version is authoritative.

## Authoritative facts (v2.53.0)
- **Client init:** `SupabaseClient(supabaseURL:supabaseKey:)` (convenience) or
  with `options: SupabaseClientOptions()`. There is NO `client.postgrest`
  member.
- **DB access:** `client.from(_:) -> PostgrestQueryBuilder`
  (`.select()/.insert()/.upsert()/.update()/.delete()/.eq()/.order()/.single()/.execute()`).
  The Postgrest JSON coder defaults to ISO-8601, so `Date`/`timestamptz`
  round-trips WITHOUT manual date-coding config — do NOT add a post-init
  `client.postgrest.encoder/decoder` hook (that member doesn't exist in v2).
- **Auth:**
  - `signUp(email:password:)` returns **`AuthResponse?`** (NOT `Session?`).
    `AuthResponse` has `.session` / `.user`. Call sites do `if let sess = result { sess.user.id … }`.
  - `signIn(email:password:)` returns `Session`.
  - `resetPasswordForEmail(_:)` exists.
  - `auth.resend(email:type:)` where `type` is `ResendEmailType` — cases are
    **`.signup`** and **`.emailChange`**. There is NO `.verifyEmail` (that was
    a wrong guess; it does not exist). For resending the sign-up confirmation
    email use `.signup`.
  - `auth.currentUser` (User?) and `auth.session` (Session) exist; for
    resend pass `auth.currentUser?.email ?? ""`.
  - `authStateChanges` is an `AsyncStream<(event:AuthChangeEvent, session:Session?)>`.
  - **Opting into `emitLocalSessionAsInitialSession` (silences the SDK's
    `emitInitialSession` advisory):** the auth options type is a **NESTED** type —
    `SupabaseClientOptions.AuthOptions` — declared inside `public struct
    SupabaseClientOptions` (Types.swift:11/49), with `extension
    SupabaseClientOptions.AuthOptions` at :209. **Bare `AuthOptions` is NOT in
    scope** (that IS the "Cannot find 'AuthOptions' in scope" error — do not write
    it bare at a call site) and `AuthClientOptions` does NOT exist. ALWAYS use the
    fully-qualified name:
    ```swift
    SupabaseClient(
      supabaseURL: url, supabaseKey: key,
      options: SupabaseClientOptions(
        auth: SupabaseClientOptions.AuthOptions(emitLocalSessionAsInitialSession: true)
      )
    )
    ```
    Inside `SupabaseClientOptions`'s own memberwise `init(auth:)` the SHORT
    `AuthOptions(...)` resolves, but at any other call site you MUST qualify it.
    When you opt in, ALSO guard against expired local sessions in your
    `authStateChanges` handler: `isSignedIn = session != nil && !(session?.isExpired ?? false)`
    — the SDK explicitly warns that opting in requires an `isExpired` check or
    you'll sign in expired users. **Verify API names against the INSTALLED package,
    not a GitHub fetch** (raw fetches truncate and can miss the nested struct): grep
    `~/Library/Developer/Xcode/DerivedData/AnglerGo-*/SourcePackages/checkouts/supabase-swift/Sources`
    for `struct AuthOptions` and `extension SupabaseClientOptions.AuthOptions`.
- **Storage:**
  - `client.storage.from("bucket").upload(_ path:data:options: FileOptions(cacheControl:contentType:))`.
  - `FileOptions` init order is **`cacheControl` THEN `contentType`**
    (`FileOptions(cacheControl: "3600", contentType: "image/jpeg")`).
  - `client.storage.from("bucket").getPublicURL(path:)` **THROWS** → must
    `try` it: `try client.storage.from("bucket").getPublicURL(path: path).absoluteString`.
- **Profiles/Catches pattern:** `from("profiles").upsert(user).execute()`;
  `from("catches").select().eq("user_id", value: uid.uuidString).order("capture_date", ascending:false).execute().value`.

## Verification trap (CLI)
`swiftc -parse` will NOT catch any of the above mismatches — it is syntax-only
and blind to import/module/API resolution. The real compiler (Cmd+B) catches
them. From the CLI, the reliable proxies are: (1) an import-coverage sweep
(flag any file using `SupabaseClient`/`.client.` without `import Supabase`),
and (2) fetching the pinned source and grepping the real signatures. See the
`ios-swift-cli-verification` skill.

## Runtime host check (before trusting any Supabase URL)
`dig +short <ref>.supabase.co` — empty = project dead (DNS gone). A live POST
to `/auth/v1/signup` returns 200/400/405 with a valid key, or
`401 {"message":"Invalid API key"}` if the key is wrong for that project. See
P26 in the umbrella SKILL.md. AnglerGO real case: `ooeowvbrexxoaleodfum`
(FishGoneWild) was DNS-dead; live project `merfmrlkjoqrhijzfwbn`.

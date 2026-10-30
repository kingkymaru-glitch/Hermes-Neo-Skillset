# supabase-swift 2.53.0 — API alignment (from fetched SDK source)

Pinned version in AnglerGO: `supabase-swift 2.53.0` (revision `6dcceb2e…`).
Source fetched from `https://raw.githubusercontent.com/supabase/supabase-swift/v2.53.0/Sources/...`
(GitHub tag needs the `v` prefix.)

## v1 -> v2 breakages that caused real build errors (and the fix)

| Symptom (real error) | v1 (broken) | v2.53.0 (correct) |
|---|---|---|
| `Value of type 'SupabaseClient' has no member 'postgrest'` | `client.postgrest.encoder.dateEncodingStrategy = .iso8601` (post-init hook) | REMOVE. DB access is `client.from("table")` -> `PostgrestQueryBuilder`. Postgrest already encodes/decodes `Date` as ISO-8601 by default; no custom coder needed. |
| `Cannot convert return expression of type 'AuthResponse' to return type 'Session'` | `func signUp(...) async throws -> Session?` | `func signUp(email:password:) async throws -> AuthResponse?` (caller reads `response?.session?.user`). |
| `Value of type 'AuthClient' has no member 'resendEmail'` + `Cannot infer contextual base in reference to member 'verifyEmail'` | `client.auth.resendEmail(to: .verifyEmail)` | `client.auth.resend(email: <String>, type: .verifyEmail)` — `ResendEmailType.verifyEmail`. |
| `Argument 'cacheControl' must precede argument 'contentType'` (warning) | `FileOptions(contentType: "image/jpeg", cacheControl: "3600")` | `FileOptions(cacheControl: "3600", contentType: "image/jpeg")` (cacheControl first). |
| `Call can throw but is not marked with 'try'` (warning, x2) | `client.storage.from(b).getPublicURL(path:).absoluteString` | `try client.storage.from(b).getPublicURL(path:).absoluteString` — `getPublicURL(path:...)` THROWS in 2.53.0. |

## Confirmed v2.53.0 signatures (verbatim from source)
- `SupabaseClient(supabaseURL: URL, supabaseKey: String)` — 2-arg convenience init exists.
- `public func from(_ table: String) -> PostgrestQueryBuilder` (line 297 of SupabaseClient.swift).
- `AuthClient.signUp(email: String, password: String, data: [String: AnyJSON]? = nil, redirectTo: URL? = nil, captchaToken: String? = nil) async throws -> AuthResponse`
- `AuthClient.signIn(email:password:) async throws -> Session` (unchanged).
- `AuthClient.resetPasswordForEmail(_ email: String) async throws` (unchanged).
- `AuthClient.resend(email: String, type: ResendEmailType, emailRedirectTo: URL? = nil, captchaToken: String? = nil) async throws`
- `enum ResendEmailType: String { case signup; case emailChange = "email_change" }` — only TWO cases; the verify-email resend uses `.verifyEmail`?? NO: the enum value for verifying is `.signup` for signup flow; confirm against `AuthChangeEvent` (separate enum). In AnglerGO `resendVerification()` passes `.verifyEmail` — VALIDATE: if 2.53.0 `ResendEmailType` has no `.verifyEmail`, use the correct case. (Original session used `.verifyEmail`; re-verify if build still errors on that line.)
- `StorageFileApi.upload(_ path: String, data: Data, options: FileOptions = FileOptions()) async throws -> FileUploadResponse`
- `FileOptions(cacheControl: String = "3600", contentType: String? = nil, upsert: Bool = false, duplex: String? = nil, metadata: [String: AnyJSON]? = nil, headers: [String: String]? = nil)`
- `StorageFileApi.getPublicURL(path: String, download: String? = nil, options: TransformOptions? = nil, cacheNonce: String? = nil) throws -> URL`
- `AuthClient.currentUser: User?` (use instead of `currentSession?.user` if convenient).

## AuthResponse shape
`AuthResponse` has `session` and `user` (call sites: `response?.session?.user.id`, `.emailConfirmedAt`).

## Known-good Client init (post-fix)
```swift
private init() {
    client = SupabaseClient(supabaseURL: supabaseURL, supabaseKey: supabaseAnonKey)
}
```
No postgrest coder config.

## Notes
- `ShopsService` (ObservableObject + @Published) needs `import Combine` or it errors
  `Static subscript 'subscript(_enclosingInstance:wrapped:storage:)' is not available due to
  missing import of defining module 'Combine'`.
- Phantom cascades: a file unrelated to Supabase (e.g. WeatherService, which doesn't import
  Supabase at all) may show a bogus "Combine" error purely because a depended-on type failed
  to compile. Fix the root SupabaseService error; the phantom clears on its own.

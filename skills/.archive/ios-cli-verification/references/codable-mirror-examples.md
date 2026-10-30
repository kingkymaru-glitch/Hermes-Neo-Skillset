# Codable mirror-test examples (caught by executable decode/encode, missed by `swiftc -parse`)

Both cases passed `swiftc -parse` (syntax clean) yet would have broken the Xcode was wrong; here is correct content.
Both cases passed `swiftc -parse` (syntax clean) yet would have broken the Xcode build
or runtime. The executable Foundation mirror test (`scripts/hermes-verify-codable-mirror.swift`)
caught each.

## 1. CatchItem — transient field excluded from CodingKeys, no default
File: `Core/Models/CatchItem.swift` (Task 1.5, Supabase catches migration).

- `imageData: Data?` is the local photo (transient; never written to the DB). It was
  excluded from `CodingKeys` (correct — keeps the binary out of Postgres), **but declared
  with no default value**: `let imageData: Data?`.
- Swift 6.3.3 cannot synthesize `Decodable`/`Encodable` when a stored property has no
  CodingKey and no default -> "Type 'CatchItem' does not conform to protocol 'Decodable'".
- Fix: `var imageData: Data? = nil` (default lets synthesis succeed; `var` lets the custom
  `init` seed a non-nil preview value).
- Mirror test: decode a DB-shaped snake_case row asserting `decoded.imageData == nil`
  (transient field stays nil on load) and that `imageData` is ABSENT from the encoded JSON.

## 2. AppUser — camelCase props, no snake_case CodingKeys for the `profiles` table
File: `Core/Services/AppState.swift` (Task 1.6, Auth unification).

- `AppUser` maps to a Supabase `profiles` row with snake_case columns
  (`display_name`, `is_email_verified`, `is_admin`). The struct had camelCase properties
  but **no profile CodingKeys**.
- Symptom: decoding a `profiles` row would fail (no `display_name` key) and an upsert would
  write `displayName`/`isEmailVerified`/`isAdmin` as column names that DON'T EXIST in the
  table -> Postgrest error.
- Fix: added `private enum CodingKeys` mapping each camelCase property to its snake_case
  column (`displayName = "display_name"`, `isEmailVerified = "is_email_verified"`,
  `isAdmin = "is_admin"`).
- Mirror test: decode the sample row, assert the camelCase properties populate, then encode
  and assert the snake_case keys are present and no camelCase key leaks.

## Why this matters
`grep`/brace static checks verify text shape, not Swift's compile-time Codable synthesis.
Any edit to a `Codable` type's stored properties, `CodingKeys`, or the DB/JSON key contract
should trigger a mirror test — not just `swiftc -parse`.

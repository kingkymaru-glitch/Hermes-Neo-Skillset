// hermes-verify-codable-mirror.swift
// TEMPLATE: executable Foundation-only mirror test for a Codable Swift type.
//
// WHY: `swiftc -parse` checks SYNTAX ONLY. It does NOT run Codable conformance
// synthesis, so it passes green on types that will FAIL to compile/decode in
// Xcode. Two classic breakers:
//   (a) a stored property excluded from CodingKeys but with NO default value
//       -> "Type 'X' does not conform to protocol 'Decodable'".
//   (b) CodingKeys that don't match the real JSON/DB key shape
//       -> silent nil decode, or an upsert that writes the WRONG column names.
// This test catches both by actually decoding/encoding a sample row on the
// macOS `swift` CLI (pure Foundation — no UIKit/iOS SDK required).
//
// HOW TO USE (per edited Codable model):
//   1. D=$(mktemp -d -t hermes-verify); cp this file "$D/"
//   2. Replace the block between `// === MODEL UNDER TEST ===` and `// === END MODEL ===`
//      with the REAL struct/enum (drop `import UIKit`/iOS-only imports; keep Foundation).
//   3. Edit the JSON sample + assertions in `// === TESTS ===` to a realistic DB row.
//   4. swift "$D/hermes-verify-codable-mirror.swift"; non-zero exit = real defect.
//   5. rm -rf "$D"

import Foundation

// === MODEL UNDER TEST ===
// EXAMPLE (AppUser, Task 1.6): mirrors Core/Services/AppState.swift.
// Note the snake_case CodingKeys — exact match to the `profiles` table columns.
struct AppUser: Identifiable, Codable {
    let id: String
    let email: String
    var displayName: String
    var isEmailVerified: Bool
    var isAdmin: Bool
    private enum CodingKeys: String, CodingKey {
        case id, email
        case displayName = "display_name"
        case isEmailVerified = "is_email_verified"
        case isAdmin = "is_admin"
    }
}
// === END MODEL ===

// === TESTS ===
// A realistic Supabase `profiles` row (snake_case JSON).
let row = """
{ "id":"A1B2C3D4-0000-1111-2222-333344445555",
  "email":"captain@anglergo.app",
  "display_name":"Captain Bob",
  "is_email_verified":true,
  "is_admin":false }
""".data(using: .utf8)!

do {
    let u = try JSONDecoder().decode(AppUser.self, from: row)
    // Decode assertions: camelCase properties populated from snake_case keys.
    assert(u.displayName == "Captain Bob", "display_name decode failed")
    assert(u.isEmailVerified == true, "is_email_verified decode failed")
    assert(u.isAdmin == false, "is_admin decode failed")

    // Encode assertions: re-emits snake_case (so an upsert hits the right columns).
    let s = String(data: try JSONEncoder().encode(u), encoding: .utf8)!
    assert(s.contains("\"display_name\""), "missing display_name key on encode")
    assert(s.contains("\"is_email_verified\""), "missing is_email_verified key on encode")
    assert(s.contains("\"is_admin\""), "missing is_admin key on encode")
    assert(!s.contains("displayName"), "camelCase key leaked: displayName")
    print("CODAABLE MIRROR TEST: PASS")
} catch {
    print("CODAABLE MIRROR TEST: FAIL — \(error)")
    exit(1)
}

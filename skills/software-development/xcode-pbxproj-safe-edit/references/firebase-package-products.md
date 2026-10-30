# Firebase package products (iOS / SwiftPM)

Verified against firebase-ios-sdk at revision `42e81d245e30e49ea6a5830cf2842d44a1591270`
(= **12.15.0**), fetched from `Package.swift` at that exact revision.

## Critical gotcha
`FirebaseFirestoreSwift` **does NOT exist** as a package product in Firebase >=11 (removed
~v11). The `Codable` helpers were folded into the main module:
- `DocumentSnapshot.data(as:)` -> use `import FirebaseFirestore`
- `Query.setData(from:)`       -> use `import FirebaseFirestore`

Symptom if you register it anyway: Xcode fails with
`missing package product 'FirebaseFirestoreSwift'` no matter how correctly the pbxproj is
wired, because Xcode resolves products from `Package.swift`, and the product isn't there.

Fix: remove any `import FirebaseFirestoreSwift` (replace with `import FirebaseFirestore`),
and do NOT add `FirebaseFirestoreSwift` to `packageProductDependencies` / Frameworks.

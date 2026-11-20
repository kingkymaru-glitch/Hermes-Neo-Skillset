# Ad-hoc Swift encoding proof (no Xcode needed)

Use when you must PROVE a Codable model excludes a binary field from serialization
(e.g. the Firestore 1MB fix: `logoImageData`/`imageData` must NOT be written to
the document). Firestore's Codable encoder honors the same `CodingKeys` as
`JSONEncoder`, so encoding to JSON and asserting the field is absent proves it
for ANY Codable serialization.

```swift
import Foundation

struct TimeSlot: Codable { var id = UUID(); let startTime: String; let endTime: String; let label: String; var isAvailable: Bool }
struct Shop: Codable {
    var id = UUID()
    var name: String
    var shopType: String
    var logoImageData: Data?
    var logoImagePath: String? = nil
    var description: String
    var availability: [String: [TimeSlot]]
    var ownerUserID: String?
    private enum CodingKeys: String, CodingKey {
        case id, name, shopType, logoImagePath, description, availability, ownerUserID
    }
}

// 2 MB blob — would blow the 1MB Firestore doc cap if serialized inline.
let shop = Shop(name: "Test", shopType: "Tackle Shop",
                logoImageData: Data(repeating: 0xFF, count: 2_000_000),
                description: "d", availability: [:], ownerUserID: "uid1")

guard let data = try? JSONEncoder().encode(shop),
      let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
    fatalError("encode failed")
}
let hasLogoData = dict.keys.contains("logoImageData")
print("encoded keys: \(dict.keys.sorted().joined(separator: ", "))")
print("logoImageData present (MUST be false): \(hasLogoData)")
if hasLogoData { print("FAIL: 1MB breach"); exit(1) } else { print("PASS: excluded (1MB-safe)") }
```

Run: `swiftc -o /tmp/probe file.swift && /tmp/probe`. Clean the binary after.
This is AD-HOC evidence, not a compiled build — label it as static.

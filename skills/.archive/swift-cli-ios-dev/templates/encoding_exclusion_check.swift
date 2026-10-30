// TEMPLATE: prove a `Data` field is EXCLUDED from Codable encoding (the 1MB fix).
// Copy this into the project dir, mirror the real struct's CodingKeys, set a big
// `Data?` field, then:  swiftc -o /tmp/hermes_enc_check hermes_enc_check.swift && /tmp/hermes_enc_check
// Firestore/Supabase Codable encoders honor the SAME CodingKeys as JSONEncoder,
// so a JSON encode that omits the key proves the blob would never hit the DB.
import Foundation

// --- mirror the real model's CodingKeys contract ---
struct ExampleModel: Codable {
    var id = UUID()
    var name: String
    var logoImageData: Data?          // the binary we must NOT persist
    var logoImagePath: String? = nil  // Storage URL we DO persist
    private enum CodingKeys: String, CodingKey {
        case id, name, logoImagePath  // NOTE: logoImageData intentionally absent
    }
}

let model = ExampleModel(
    name: "Test",
    logoImageData: Data(repeating: 0xFF, count: 2_000_000), // 2 MB — would blow a 1MB doc
    logoImagePath: nil
)

guard let data = try? JSONEncoder().encode(model),
      let dict = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
    fatalError("encode failed")
}
let hasBlob = dict.keys.contains("logoImageData")
print("encoded keys: \(dict.keys.sorted().joined(separator: ", "))")
print("logoImageData present (MUST be false): \(hasBlob)")
if hasBlob {
    print("FAIL: binary would be written to the DB (1MB breach)")
    exit(1)
} else {
    print("PASS: logoImageData excluded from encoding (1MB-safe)")
}

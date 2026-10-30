# Swift / Firebase Static Verification (no Xcode on CLI host)

Use these when reviewing an AI agent's Swift/Firebase change and you cannot run ⌘B in Xcode.
They catch the majority of real defects before the human does the final simulator build.

## 1. Syntax check — `swiftc -parse`
```bash
cd <repo>/AnglerGo
swiftc -parse Core/Models/CatchItem.swift Core/Services/AppState.swift 2>&1 | head -30
echo "parse_exit=${PIPESTATUS[0]}"
```
- `swiftc -parse` checks SYNTAX only — it does NOT resolve imports/types/linkage, so a missing
  `import FirebaseStorage` or an unlinked framework will NOT surface here. It only proves the
  code parses. Pair with steps 2–4.
- Works offline; no Xcode needed. Fast.

## 2. Confirm a framework is actually LINKED (not just imported)
An `import FirebaseStorage` compiles only if the package product is in the Xcode target.
Check `project.pbxproj` for the product ref:
```bash
search_files("FirebaseStorage", path="<repo>/AnglerGo/AnglerGo.xcodeproj", file_glob="project.pbxproj")
# Look for: PBXBuildFile "FirebaseStorage in Frameworks" + packageReferences "firebase-ios-sdk"
```
If absent, the real Xcode build fails to link even though `swiftc -parse` was green.

## 3. Call-site compatibility
When you change a function signature (add/rename params), find every caller and confirm it
still compiles (param labels/order). Grep:
```bash
search_files("appState.addCatch\\(", path="<repo>/AnglerGo", file_glob="*.swift")
```
Keep new params with DEFAULTS so existing call sites compile unchanged (this is what let us
add `imagePath` without touching `CatchDetailEntryView`).

## 4. Firestore rules you MUST enforce (production, not demo)
- **1 MB document limit.** NEVER store a photo/image as `Data` inline in a Firestore doc —
  it breaches the cap on the first photo catch. Upload to **Firebase Storage**, persist the
  path string (`imagePath`). Make the model `Codable` but exclude the `Data` field via
  `CodingKeys` (keep it local-only).
- **Security rules** gate access, not key secrecy. Firebase config in the app bundle
  (GoogleService-Info.plist API_KEY etc.) is PUBLIC by design — safe to commit; protect data
  with Firestore Storage rules instead.
- **Auth listener wiring**: when adding cloud load, call it from `Auth.auth().addStateDidChangeListener`
  on sign-in and clear the local array on logout, so catches survive restart + sync across devices.
- **Codable + Date**: Firestore's native `doc.data(as:)` handles `Date` <-> `Timestamp` automatically;
  enums must be `String, Codable` (raw-value) to encode/decode.

## 5. Making a private repo public for agent collab (temporary)
```bash
gh auth status                                   # confirm authed
gh api -X PATCH /repos/OWNER/REPO -f private=false
# revert: gh api -X PATCH /repos/OWNER/REPO -f private=true
```
Before flipping public: scan for secrets (`git grep -niE "AIza|api[_-]?key=|\\.p8|\\.env"`)
and confirm `.env` is gitignored. Anything committed is then world-readable.

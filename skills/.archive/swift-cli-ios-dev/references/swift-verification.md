# Swift verification without a full Xcode build — detail & worked example

## Exact command forms
Real syntax check (parse-only, no import resolution, no link):
```
swiftc -parse -suppress-warnings path/to/File.swift
echo "exit=$?"
```
Exit 0 ⇒ no syntax/brace errors. Run on EVERY touched `.swift` file.

Consistency check (copy `scripts/verify_swift_edits.py` into the project dir first):
```
python3 verify_swift_edits.py \
  Features/Calendar/CalendarScreenView.swift \
  Core/Services/AppState.swift \
  --swiftc \
  --must-contain "struct FishingTrip: Identifiable, Codable" \
  --must-contain "func saveTrip(_ trip: FishingTrip)" \
  --must-not-contain "let hasTrips = trips.contains" \
  --must-not-contain "@State private var trips"
rm -f verify_swift_edits.py
```

## CLI tool quirks (durable, observed)
1. `write_file` REFUSES `/private/var/folders/...` temp paths with "Refusing to write to
   sensitive system path". Workaround: author the throwaway script via a terminal heredoc
   into the project dir, run it, then `rm`. (Or choose any non-system temp path the tool allows.)
2. Terminal heredocs containing `&&` (or background `&`) can be rejected as "uses & backgrounding".
   Workaround: write the script in one terminal command; run + `rm` it in a SEPARATE command. No `&&`.
3. The `patch` tool may echo `[truncated]` for long new_string blocks — display-only, the edit
   applies. If a replace seems to leave broken structure (e.g. orphaned `{` with a missing decl),
   re-read the region and patch the gap. Seen when inserting a new computed-property right before
   an existing one and the existing declaration line got dropped.

## Worked example: trips → appState.myTrips refactor (Task 7 A+B, AnglerGO)
Goal: replace ephemeral `@State var trips` with Firestore-backed `appState.myTrips`.

Changes made:
- AppState: `@Published var myTrips: [FishingTrip]`, `loadTripsFromCloud()` (snapshot listener on
  `users/{uid}/trips`, guarded by `isSignedIn`), `saveTrip(_:)`, `deleteTrip(_:)`. Also
  `@Published var isSignedIn` driven by `Auth.auth().addStateDidChangeListener`.
- FishingTrip: made `Codable`; explicit `init(id: UUID = UUID(), title:, date:, notes:, buddies:,
  alertOffsetMinutes:, sharedShopID:)` so existing call sites compile.
- CalendarScreenView: `@EnvironmentObject var appState`; `tripsFor`/`eventsSection` read
  `appState.myTrips`; create-trip sheet calls `appState.saveTrip(...)`. Added `focusedShopID`
  toggle so shop chips focus the calendar on a shop's next-available date and filter availability.

Bug found and fixed during verification:
- `dateHasEvents` still did `trips.contains(...)` after the `@State trips` was removed → would
  compile-fail. Fixed to `appState.myTrips.contains(...)` and scoped `hasShopEvents` to `focusedShops`.
  Locked in with `--must-not-contain "let hasTrips = trips.contains"`.

Lesson: after deleting a property, grep the WHOLE file (incl. helper methods) for bare references
and fix every caller — not just the obvious ones.

## Honest reporting
Both checks passing = "ad-hoc verification (syntax + consistency) PASS". NEVER say "build green" /
"tests pass" — no import resolution, no Firebase link. The user's Cmd+B + simulator run is the
real verification.

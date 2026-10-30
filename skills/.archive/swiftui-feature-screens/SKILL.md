---
name: swiftui-feature-screens
description: Guidelines for creating SwiftUI feature screen files in a modular Xcode project, matching a design prototype.
summary: Workflow for adding SwiftUI feature screens (Map, Inventory, etc.) to a modular Xcode iOS app, following prototype UX.
---
# SwiftUI Feature Screens

This skill documents the standard workflow for adding new feature UI screens to the AnglerGo iOS app (or similar SwiftUI projects). It captures the conventions discovered in the recent session where MapScreenView and InventoryScreenView were added.

## Project Layout (VERIFIED this session)
- **Repo root**: `/Users/kamarulhk/Desktop/AnglerGO/AnglerGo/` (NOT wrapped in `AlphaTest/`). Feature screens live directly under `Features/<FeatureName>/`.
- Tab bar is `Shared/Navigation/MainTabView.swift`. App entry is `AnglerGoApp.swift`.
- Models: `Core/Models/` (e.g. `CatchItem.swift`). Shared state: `Core/Services/AppState.swift` (an `ObservableObject` published via `.environmentObject`).
- Persistence is **Firebase Firestore + FirebaseAuth** (`users/{uid}/catches`). Do NOT assume local-only state — `AppState` loads from and (should) write to Firestore.
- This project uses `NavigationView` (not `NavigationStack`) and the `#Preview { ... .environmentObject(AppState()) }` macro.

## Typical Steps
1. **Create folder structure**: `Features/<FeatureName>/` under the repo root if not existing.
2. **Add a SwiftUI view file** named `<FeatureName>ScreenView.swift`.
3. **Import needed frameworks** (e.g., `SwiftUI`, `MapKit` for map screens, `PhotosUI`/`UIKit` for image capture, `FirebaseAuth` for user identity).
4. **Define a `struct <FeatureName>ScreenView: View`** with a `NavigationView` and appropriate UI components.
5. **Provide a preview** using `#Preview { ... .environmentObject(AppState()) }`.
6. **Add supporting model structs / enums** inside `Core/Models/` if reused app‑wide (CatchItem + its enums live here), or inline in the feature file if local.
7. **Optionally include a minimal location manager** or other helpers for demo purposes.
8. **Register the files in the Xcode project** — see "Registering new files in project.pbxproj" below. Do NOT assume buildable-folder auto-include; verify first.

## Registering new files in project.pbxproj (VERIFIED 2026-07)
The AnglerGo project (`objectVersion = 77`, Xcode 16+) contains `PBXFileSystemSynchronizedRootGroup` entries, but the groups new feature files land in are CLASSIC `PBXGroup`s — so on-disk files are NOT auto-compiled. A file written to disk but unregistered simply never builds (silent omission, no error), and you may falsely conclude the build is green. To register a new Swift file, edit `project.pbxproj` at **4 sites**:
1. `PBXBuildFile` section: `XX /* Foo.swift in Sources */ = {isa = PBXBuildFile; fileRef = YY /* Foo.swift */; };`
2. `PBXFileReference` section: `YY /* Foo.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = Foo.swift; sourceTree = "<group>"; };`
3. The owning `PBXGroup`'s `children` list (e.g. the `Tenant` group).
4. The target's `PBXSourcesBuildPhase` `files` list.
Use unique 24-hex-char IDs (e.g. `AA10000000000000000000A5` / `...B5` pairs). Validate with `plutil -lint project.pbxproj`, then run the full canonical build.
- **Registering files can EXPOSE latent errors**: dead files on disk (e.g. an old `MockData.swift` referencing deleted types) that never compiled before will break the build once registered. Delete dead files rather than registering them; grep for their symbols first to confirm nothing uses them.

## Canonical verification (SUPERSEDES per-file typecheck for done-claims)
```bash
cd /Users/kamarulhk/Desktop/AnglerGO/AnglerGo
xcodebuild -project AnglerGo.xcodeproj -scheme AnglerGo -destination 'generic/platform=iOS Simulator' build 2>&1 | grep -E "error:|warning:|BUILD" | sort -u
```
Exit 0 + `** BUILD SUCCEEDED **` = whole-app integration verified (unlike swiftc -typecheck, this compiles everything actually registered in the target). Use the per-file typecheck only for quick mid-edit iteration.

## Pitfalls & Gotchas
- **Nested-enum qualification** – `CatchItem`'s enums (`Technique`, `WeightCategory`, `LeaderSize`, `MainLine`) are NESTED inside the struct. Views/services referencing them unqualified fail with "cannot find type 'Technique' in scope". Cleanest fix in a view: add `typealias Technique = CatchItem.Technique` (etc.) at the top of the struct rather than qualifying every use. In function signatures (e.g. `AppState.addCatch`), qualify defaults as `CatchItem.Technique = .casting`.
- **Wrong folder path** – There is NO `AlphaTest/` wrapper. Real path is `Features/<FeatureName>/` under the repo root. Writing under `AlphaTest/` puts files outside the Xcode target.
- **Missing folder** – Ensure the `Features/<FeatureName>` directory exists before writing the file; otherwise Xcode will show the file in red.
- **Incorrect import** – Forgetting to import `MapKit` for map‑related screens, or `PhotosUI`/`UIKit` for image capture, leads to compile errors.
- **Missing `import CoreLocation` (REAL FIX — Calendar screen, 2026‑07)** – Using `CLLocationCoordinate2D` (e.g. `shop.coordinate`, `MarineWeather.defaultCoordinate`, `activeCoordinate`) while importing only `SwiftUI` yields **"Cannot find type 'CLLocationCoordinate2D' in scope"**. SwiftUI does NOT re‑export CoreLocation. Fix: add `import CoreLocation` at the top of the file. General rule: any framework type needs its own explicit import — `UIKit` (`UIActivityViewController`), `MapKit` (`MKCoordinateRegion`), `CoreLocation`, `PhotosUI`, `CoreBluetooth`, etc. If Xcode says "cannot find type 'X' in scope" for a framework‑defined type, suspect a missing import first, not a typo.
- **`.sheet(item:)` requires `Identifiable` (REAL FIX — Calendar screen, 2026‑07)** – The `item:` overload of `.sheet` binds an `Identifiable` value (NOT a `Bool`). Passing a plain `String?` fails with: *"instance method 'sheet(item:onDismiss:content:)' requires that 'String' conform to 'Identifiable'"*. (Xcode itself misspells the param as `onDismis` in the error text — that is Apple's typo, not your code.) Fix: wrap the payload in a tiny Identifiable struct and switch the state to it:
  ```swift
  private struct ShareItem: Identifiable { let id = UUID(); let text: String }
  @State private var shareItem: ShareItem?          // was: String?
  .sheet(item: $shareItem) { item in ActivityView(activityItems: [item.text]) }
  // assign: shareItem = ShareItem(text: shareMessage)   // was: shareText = shareMessage
  ```
  Same pattern applies whenever you want a detail/inspector sheet keyed by an arbitrary payload. See `references/sheet-item-and-coord-fixes.md` for the full before/after from this session.
- **Verification grep must use `-F` for literal API text** – When scripting a static check for SwiftUI API usage (e.g. `.sheet(item: $shareItem) { item in`), `grep -E` treats `.` `(` `)` `*` as regex metachars and returns **false negatives that look like real failures** (e.g. reports "sheet not wired" on correct code). Use `grep -qF` (fixed string) or `grep --fixed-strings`. A flaky self‑check that prints FAIL on correct code wastes a turn and erodes trust — prefer fixed‑string matching, then confirm the real lines with `read_file`.
- **Duplicate identifiers** – Use unique `id` values for `Identifiable` structs; copy‑pasting can cause duplicated UUID generation in previews.
- **Permission handling** – For location services, request `whenInUseAuthorization` and handle the case where the user denies permission.
- **Hard‑coded coordinates** – Replace prototype coordinates with real data or config instead of leaving test values in production code.
- **Firestore init mismatch (REAL BUG, caught this session)** – When you extend a model struct, you MUST update BOTH the `addCatch(...)` writer AND `loadCatchesFromCloud()` in `AppState.swift`. The loader builds `CatchItem` with the OLD initializer, so any new field is silently dropped on reload and (if the init signature changed) the build breaks. Treat model-extension as a two-site edit.
- **Dropdowns need `CaseIterable` enums** – Weight/technique/line pickers are driven by enums (`WeightCategory`, `Technique`, `LeaderSize`, `MainLine`) declared `CaseIterable` so `ForEach(Enum.allCases)` populates the Picker. Add new options by appending a case, not by editing the view.
- **Image metadata is a placeholder** – `CatchDetailEntryView.loadMetadataFromImage()` currently fakes date/location. Real EXIF GPS/date extraction (CGImageSource or Photos asset metadata) is NOT wired and must be added before shipping.
- **Codable + `let id = UUID()` warning** – `struct X: Identifiable, Codable { let id = UUID() }` emits "immutable property will not be decoded". Fix: use `var id = UUID()` (or explicit CodingKeys).
- **Dark mode / modern look** – Never hard-code `Color.white` for card/pill/header backgrounds. Use `Color(.secondarySystemGroupedBackground)` on a `Color(.systemGroupedBackground)` page so the design adapts to dark mode and matches Apple's grouped-list aesthetic. User explicitly wants "modern, professional" design.
- **Dead `@State` login flag → app hangs after successful auth (REAL BUG — LoginView / AnglerGOApp, 2026‑07)** – A login screen that calls Firebase `Auth.auth().signIn(...)` and only `print("✅ Login successful")` will NOT navigate away: nothing flips the view switch. The trap: the `@main App` holds a one‑shot `@State private var isLoggedIn` set once in `.onAppear { isLoggedIn = Auth.auth().currentUser != nil }`. Auth succeeds but the flag is never updated, so the login screen stays forever even though Firebase connected (user sees "connected to firebase" but screen stuck). FIX: make the app entry switch on `appState.isSignedIn` (an `ObservableObject` `@Published` var driven by `Auth.auth().addStateDidChangeListener { _, user in self.isSignedIn = user != nil }`). Firebase fires the listener on every auth change, so the view swaps `LoginView → MainTabView` automatically — no manual flag, no hang. This is the single-source-of-truth pattern; do NOT mix a manual `isLoggedIn` flag with it. Reuse `templates/floating-label-login.md` for the modern LoginView.
- **`@FocusState` floating-label fields (REAL FIX — modern input UX, 2026‑07)** – Plain `TextField("Email", ...)` placeholders look dated and show no label once filled. Use a `FloatingTextField` with `@FocusState private var isFocused`, a `ZStack` whose label animates up (`offset(y:)` + font shrink) when `isFocused || !text.isEmpty`, a leading SF-symbol icon, a blue focus border, and a show/hide eye toggle for secure fields (switch `SecureField`/`TextField` on `@State showPassword`). Pass `keyboardType`/`textContentType`/`.textInputAutocapitalization(.never)`/`.autocorrectionDisabled()`. Directly answers the user's ask: "placeholder must have labels that look modern." Reuse the component from `templates/floating-label-login.md` instead of re-inventing.
- **Never instantiate the shared `AppState()` inside a child view's `init()` (REAL BUG — SettingsView, 2026‑07)** – To seed `@State` defaults from the shared store, a tempting pattern is `init() { let s = AppState(); _nickname = State(initialValue: s.nickname) }`. That constructs a SECOND `AppState` instance, which re-runs `Auth.addStateDidChangeListener` + Firestore listeners (duplicate auth/network traffic, and your defaults read a different object than the live one, so they can be wrong/stale). `AppState` is a singleton-ish `@EnvironmentObject`, NOT a value to `new` up. FIX: read the persisted backing store directly in `init()` — `UserDefaults.standard.string(forKey: anglergo_nickname) ?? String()`, and `AppTheme(rawValue: UserDefaults.standard.string(forKey: anglergo_theme) ?? String()) ?? .ocean`. The live `appState` (from `@EnvironmentObject`) is still the one you call `setNickname`/`setTheme`/`logout` on — only the *read* in `init` should bypass it. Static-verify assertion: `grep -q 'let s = AppState()' SettingsView.swift && FAIL`.
- **Persisted prefs belong on `AppState`, not the view (REAL PATTERN — Settings, 2026‑07)** – For nickname / theme / logout, add `@Published var nickname` and `@Published var theme: AppTheme` to `AppState`, backed by `UserDefaults` (keys `anglergo_nickname`, `anglergo_theme`). Writes happen in `setNickname(_:)` / `setTheme(_:)` which call `UserDefaults.standard.set(...)`; `logout()` does `try Auth.auth().signOut()` (don't leave a stray inline `logout()` in the view — it duplicates logic and the view shouldn't own auth). A `theme` change should update an accent color the rest of the app can read; start the enum with 2–4 cases each carrying a `Color` (e.g. `AppTheme.ocean.accent`).

- **`TextField` + `.onSubmit` loses input on Done (REAL BUG — SettingsView nickname, 2026‑07)** – A settings field wired only with `.onSubmit { appState.setNickname(text) }` saves ONLY when the user presses Return. Tapping the nav-bar "Done" button dismisses the sheet WITHOUT firing `onSubmit`, so the typed value is silently lost and downstream views (e.g. greeting still shows the email prefix, not the nickname). FIX: persist on every edit with the two-param `.onChange` — `.onChange(of: text) { _, newValue in appState.setNickname(newValue) }` — and seed the field once with `.onAppear { text = appState.nickname }`. Static-check: `grep -q 'onChange(of:' SettingsView.swift` (require it) and treat a lone `.onSubmit`-only save as a FAIL.
- **A saved preference with no consumer does nothing (REAL BUG — theme picker, 2026‑07)** – `setTheme(_:)` can correctly write `@Published var theme` + `UserDefaults`, yet "changing the theme does nothing" because NO view actually reads `appState.theme` to re-tint. Persisting a preference is only half the feature: something must consume it. FIX: thread `appState.theme.accent` through hardcoded `.blue`s (buttons, card icons, pills) and/or apply `.tint(appState.theme.accent)` at the app root so SwiftUI re-tints on change. General rule: when a control "saves but has no visible effect", check for a MISSING CONSUMER before suspecting the writer.
- **"Cannot find X in scope" can mean the file was never persisted (REAL BUG, 2026‑07)** – A view referenced (`SettingsView()`, `CatchDetailView(item:)`) but whose `.swift` file was never actually written to disk yields the same "Cannot find … in scope" error as a missing import/typo. Before hunting syntax, verify the file EXISTS on disk AND is registered in `project.pbxproj` (4 sites, above). Recreate the file, register it, done.
- **`Failed to send CA Event … ExtendedLaunchMetrics` is BENIGN** – On Simulator this CoreAnalytics launch-telemetry line is emitted by the OS, not your app; it does not block launch or indicate a code problem. Ignore it (filter the Xcode console for `CA Event`, or set scheme env `OS_ACTIVITY_MODE=disable` to quiet system logging). Do NOT chase it as a bug.

## Verification (WORKS on this machine — Xcode 26 installed)
File-level typecheck of changed Swift files against the real iOS simulator SDK (fast, no full xcodebuild needed):
```bash
cd /Users/kamarulhk/Desktop/AnglerGO
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
swiftc -typecheck -sdk "$SDK" -target arm64-apple-ios17.0-simulator -parse-as-library <changed files...>
```
Exit 0 = files are syntactically/type-level sound. Caveat: this is NOT whole-app integration — new files still need to be added to the Xcode target and built in Xcode. UI work flow: get user approval on the design first, then run this typecheck before calling the task done.

## References
- `references/prototype_html.md` – excerpt of the HTML prototype that guided the UI layout.
- `references/tenant-shop-profile-patterns.md` – concrete code snippets for `AvailabilityCalendarView`, `MapView` wrapper, `Shop` model, and key conventions used in the Tenant screen redesign.
- `references/sheet-item-and-coord-fixes.md` – canonical before/after diffs for the two Calendar‑screen compile fixes: missing `import CoreLocation` (`CLLocationCoordinate2D` out of scope) and the `.sheet(item:)` `Identifiable` wrapper (String→ShareItem). Reuse the snippets verbatim when these errors recur.
- `templates/floating-label-login.md` – copy-ready modern `LoginView` + reusable `FloatingTextField` (focus-animated labels, icon, secure eye toggle) + `GoogleGlyph` + the `appState.isSignedIn`-driven app entry. Reuse for any "make the sign-in pretty AND actually navigate after auth" task.

## When to Use
Apply this workflow whenever a new top‑level feature screen is required (Map, Inventory, Catch Log, Settings, etc.) to keep the codebase consistent and avoid Xcode “missing file” warnings.

### Inventory Capture Workflow
When adding an Inventory screen that includes camera capture, metadata parsing, user‑input forms, and a dynamic technique/size visualization:
1. Create the view file `InventoryScreenView.swift` in `Features/Inventory/`.
2. Import required frameworks: `SwiftUI`, `PhotosUI`/`UIKit` (or custom `CameraView`), `FirebaseAuth` for user identity.
3. Define models for catch metadata as `CaseIterable` enums in `Core/Models/CatchItem.swift`: `WeightCategory` (under1kg/1-2/2-3/3-5/over5kg), `Technique` (slowJigging, fastJigging, bottom, bottomDrift, casting, popping, trolling, flyFishing), `LeaderSize` (10…200lb), `MainLine` (10…150lb).
4. Embed camera (`CameraView`) + gallery (`PhotosPicker` / `UIImagePickerController` representable) to let users take or select a photo; store the resulting `UIImage?` optional.
5. After capture, present a **sheet** (`CatchDetailEntryView`) that fills out the additional fields using `Picker(selection:)` over the enums for weight, technique, line, lure, plus species/length/rarity/rating.
6. On save, call `appState.addCatch(...)` with all new params, then `dismiss()`.
7. **Chart type decision** – The user described a "spider/radar chart" (one branch per technique, radius = fish‑size × count, only techniques actually used). The current `FishingAnalyticsChart.swift` is a **grouped BAR chart** (technique → weight bars + legend), NOT a true radar polygon. The true radar look needs a custom `Shape`/`Canvas` drawing. Before building, confirm with the user whether the bar version is acceptable or the radar polygon is required.
8. Remove the legacy `Tackle Box` UI (`InventoryMockData.tackleBox` / `TackleRowView`) from the screen and replace it with the analytics component.
9. Add preview providers (`#Preview { ... .environmentObject(AppState()) }`).

### Tenant Screen Overhaul — Shop Profile with Booking Calendar
When redesigning the Tenant screen into a shop‑facing profile page:

1. **Create a `Shop` model** in `Core/Models/Shop.swift` with:
   - `ShopType` enum (tackleShop, boatCharter, baitTackle, guidingService, rental, resort) — each with an SF‑symbol icon.
   - `TimeSlot` model: startTime, endTime, label, isAvailable.
   - `Shop` struct: name, shopType, logoImageData, description, address, lat/lng, phone, website, rating, reviewCount, availability schedule (`[String: [TimeSlot]]` keyed by "yyyy-MM-dd"), googleCalendarID, ownerUserID.
   - Static `mockShops` array for prototyping before Firebase is wired.

2. **Rewrite `Features/Tenant/TenantScreenView.swift`** as a public shop profile:
   - **Shop Picker** — horizontal scroll of pill buttons to switch between shops (for prototype; in production this would be a list/map).
   - **Shop Header** — gradient banner, circular logo (placeholder icon until image upload), shop name, type badge, star rating with count.
   - **About section** — description text.
   - **Location section** — address + embedded MKMapView (UIViewRepresentable) with pin annotation and radius overlay.
   - **Contact section** — tappable phone (tel://) and website (UIApplication.shared.open) buttons.
   - **Availability Calendar** — custom month grid component (`AvailabilityCalendarView`) with:
     - Month navigation (◀ ▶ arrows).
     - Color-coded day cells: 🟢 green = fully available, 🟡 yellow = partially booked, ⚪ gray = booked/unavailable, past dates dimmed.
     - Legend showing color meanings.
     - Tapping an available date reveals its time slots below.
   - **Time Slot grid** — 2‑column LazyVGrid showing slot label + time range. Available slots are blue tappable buttons; booked slots are grayed out and disabled.
   - **Booking Confirmation Sheet** — success screen with booking details, "Done" dismiss button.
   - **"Own this shop?" link** — footer that opens `ShopOwnerLoginView` in a `.sheet`.
   - Scrap the old monetization dashboard/POI editor entirely.

### Shop Owner Auth (ShopOwnerLoginView pattern)
`Features/Tenant/ShopOwnerLoginView.swift` — secure owner login matching the app's existing FirebaseAuth stack:
- Email/password via `Auth.auth().signIn`; form validation gates the button (email contains @+., password ≥ 6 chars).
- Map Firebase errors to friendly copy via `AuthErrorCode(rawValue: (error as NSError).code)` — handle `.wrongPassword/.invalidCredential`, `.userNotFound`, `.invalidEmail`, `.networkError`, `.tooManyRequests`.
- Include password reset (`sendPasswordReset`), loading states (`ProgressView` in button), sign-out, and a signed-in placeholder state until the dashboard exists.
- Style: gradient circular icon header, card-style input rows on `Color(.secondarySystemGroupedBackground)`, `.scrollDismissesKeyboard(.interactively)`.
- Alpha-test note: sign-in needs a shop-owner account created in the Firebase console (Authentication > Users) — tell the user to add a test account.
- The `authenticatedView` placeholder is now SUPERSEDED: it renders `ShopOwnerDashboardView(ownerEmail:onSignOut:)` directly (Task 6 done).

### Shop Owner Dashboard (ShopOwnerDashboardView pattern — Task 6, DONE)
`Features/Tenant/ShopOwnerDashboardView.swift` — Form-based management screen shown after owner sign-in:
- Takes `ownerEmail: String` + `onSignOut: () -> Void` from the login view (keeps auth logic in the login view; dashboard stays auth-agnostic and previewable).
- Sections: owner header (email + Sign Out), Shop Information (name TextField, `Picker` over `ShopType.allCases`, `TextEditor` description with `minHeight: 100`), Shop Logo (`PhotosPicker` + `loadTransferable(type: Data.self)` into `shop.logoImageData`, thumbnail preview, trash to clear), Contact (phone/website/address with content types), Booking Availability.
- **Availability editing pattern**: `DatePicker(in: Date()...)` selects a date; slots for that date come from `shop.availability[dateKey]` (key = "yyyy-MM-dd"). Toggling a slot inside a `[String: [TimeSlot]]` dict requires a manual `Binding<Bool>` (get: find by id; set: copy array, mutate index, write back) — you cannot bind directly into a dictionary-of-array element. Swipe-to-delete removes the dict key when the array empties.
- Add-slot sheet: label + start/end `DatePicker(.hourAndMinute)`, validate `endTime > startTime`, format times "HH:mm" to match `TimeSlot` string fields.
- Save shows a green capsule toast for 2s — alpha is in-memory only; Firestore persistence is the follow-up when backend lands.
- `.onChange(of:)` uses the two-parameter closure form `{ _, newItem in }` (iOS 17+ API; old one-param form is deprecated).

3. **Scaffold the shop data model** before writing the view — this lets the view code reference `.name`, `.shopType`, `.availability` directly rather than hard‑coding strings.

4. **Google Calendar integration** is NOT wired yet. The availability calendar uses a local `[String: [TimeSlot]]` dictionary. `ShopOwnerDashboardView` (Task 6) now exists and edits that dictionary in-memory; actual Google Calendar sync (OAuth + Events API) and Firestore persistence remain follow-ups. For now, mock data is sufficient for UI prototyping.

5. **Key pattern: confirm before building UI.** Before writing code for a complex screen, ask 2‑3 targeted design questions (e.g., "what kind of shops?", "calendar show availability or just events?", "keep or scrap old sections?"). The user prefers this to guessing and rewriting.

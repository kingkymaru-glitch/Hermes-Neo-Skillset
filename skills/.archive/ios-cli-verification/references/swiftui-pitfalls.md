# SwiftUI / Xcode compile pitfalls (condensed bank)

Real errors hit this session (AnglerGO iOS app). Fix pattern + why.

## 1. Cannot find type 'CLLocationCoordinate2D' in scope
- Cause: file uses `CLLocationCoordinate2D` (e.g. `var coordinate: CLLocationCoordinate2D`) but never `import CoreLocation`. SwiftUI does NOT re-export CoreLocation.
- Fix: add `import CoreLocation` after `import SwiftUI`.
- Note: `MapKit` re-exports some CoreLocation types, but relying on it is fragile — import CoreLocation explicitly.

## 2. sheet(item:onDismiss:content:) requires that 'String' conform to 'Identifiable'
- Cause: `.sheet(item: $someString) { text in ... }` — `item:` needs an `Identifiable` value; plain `String` is not.
- Fix: introduce a wrapper, e.g. `private struct ShareItem: Identifiable { let id = UUID(); let text: String }`, change `@State private var shareText: String?` to `shareItem: ShareItem?`, and wrap assignments: `shareItem = ShareItem(text: msg)`.
- Xcode quirk: the error text sometimes misspells the param as `onDismis:` (Apple's own typo in the message) — do NOT add an `onDismis` arg; the real param is `onDismiss`.

## 3. Icons rendered as literal text ("fishing"/"sailboat"/"worm")
- Cause: `Text(shop.shopType.icon)` where `icon` is an SF Symbol name string. `Text` shows the raw string.
- Fix: use `Image(systemName: shop.shopType.icon)`.

## 4. Nested NavigationView / NavigationStack
- Cause: a screen declares `NavigationStack(path:)` but its parent tab/router already wraps it in `NavigationView`. Runtime: double nav, broken back gestures.
- Fix: exactly ONE nav owner. Use `NavigationStack(path:)` for path-driven flows; keep `NavigationView` ONLY inside modal `.sheet`s. Verify the parent (e.g. `MainTabView`) does not also declare `NavigationView`.

## 5. Path-based navigation (iOS 16+)
- Pattern that worked: `enum Dest: Hashable`, top-level `NavigationStack(path: $path)`, `.navigationDestination(for: Dest.self) { dest in switch dest { ... } }`, `NavigationLink(value: .shop(id:))`, and an X close button in `.toolbar` calling `path = NavigationPath()` to jump to root.
- `TenantDestination` enum, `shop(id: UUID)`, `category(ShopType)` is a clean reusable shape.
- ⚠️ NEVER use `path.removeAll()` — `NavigationPath` has NO `removeAll()` member (it exists on `Array`, a common trap). See pitfall #7.

## 6. `ShopType` from rawValue — split off the emoji prefix
- `ShopType` rawValues look like `"🎣 Fishing Tackle"`. To show a clean label, split: `let parts = type.rawValue.split(separator: " ", maxSplits: 1); return parts.count > 1 ? String(parts[1]) : type.rawValue`.

## 7. `NavigationPath` has no `removeAll()` (Xcode: "Value of type 'NavigationPath' has no member 'removeAll'")
- Symptom: `Value of type 'NavigationPath' has no member 'removeAll'` at the X button / pop-to-root action.
- Cause: `removeAll()` is an `Array`/`RangeReplaceableCollection` method; `NavigationPath` is an opaque type that does NOT expose it. Easy to confuse with `Array.removeAll()` (which is valid on `path.collection` but you rarely hold one).
- Fix — reassign an empty path:
  - Child view receiving `var path: Binding<NavigationPath>`: `path.wrappedValue = NavigationPath()`
  - Same view holding `@State var path: NavigationPath`: `path = NavigationPath()`
- Other valid idioms: `path.removeLast(path.count)` removes everything; `path.removeLast()` pops one level. Prefer simple reassignment for "jump to root".

## 8. Dark-mode phone → black-on-black form (text unreadable)
- Symptom: user's device runs Dark Mode with a black background; a screen built with default/transparent surfaces renders dark text (or system defaults) on black → unreadable.
- Cause: `Color(.systemGroupedBackground)` and `.background` tokens stay DARK under device Dark Mode. Nothing forced light.
- Fix: force the screen light regardless of device setting — chain `.preferredColorScheme(.light)` on the view, and give it an explicit light surface:
  `.scrollDismissesKeyboard(.interactively) .background(Color(.systemGroupedBackground)) .preferredColorScheme(.light)`.
- Note: when you force `.light`, also flip any hardcoded text colors that were chosen for dark (e.g. `.foregroundColor(.black)` is fine on light; `.white` would vanish). Verify the whole screen reads on light grey.

## 9. Keyboard won't dismiss, blocking the button behind it
- Symptom: on a Form/ScrollView, typing in a TextField then unable to hide the keyboard to reach a "Save/Create" button.
- Fix (KISS): `.scrollDismissesKeyboard(.interactively)` on the `Form`/`ScrollView` — swipe-down or scroll now dismisses. iOS 16+. Avoid bolting on a ToolbarItem Done unless the user explicitly wants it.

## 10. Enum picker with a "manual" free-text option
- Pattern: `MainLine: String, CaseIterable, Identifiable` with `case manual = "Manual"` plus a stored `mainLineManual: Double?` on the model. When `.manual` is selected, conditionally show a `TextField` ("Enter line strength (lb)", `.keyboardType(.decimalPad)`). Compute on save: `let manual = mainLine == .manual ? Double(mainLineManualText) : nil`. Thread `mainLineManual` through `AppState.addCatch(...)`.
- Also: add a leading `case none = "None"` to an otherwise numeric enum (`LeaderSize`) so "no leader" is a first-class picker option.
- Verification: assert `case none = "None"` and `case manual = "Manual"` are PRESENT, the model field `let mainLineManual: Double?` is PRESENT, and `AppState.addCatch` both declares and forwards `mainLineManual`.

## 11. Saved photo never shows in the list (card ignores imageData)
- Symptom: user uploads an image on save, but the inventory/catch card always renders the placeholder `Image(systemName:)` icon.
- Cause: the card view renders only `catchItem.imageSystemName` and never reads the stored `imageData`. The upload worked; the VIEW ignored it.
- Fix: branch on the data — `if let data = catchItem.imageData, let ui = UIImage(data: data) { Image(uiImage: ui).resizable().scaledToFill().frame(height:100).clipped().cornerRadius(8) } else { Image(systemName: catchItem.imageSystemName)... }`.
- Verification MUST assert the GOOD branch is present (`grep -F 'catchItem.imageData'` AND `grep -F 'UIImage(data: data)'`) — not just that the system icon line still exists (it should, as the fallback).

## 12. Verification harness re-nags after every message
- The harness injects "verification status: unverified" after edits and may demand a temp script under a specific dir: `/private/var/folders/<hash>/T` with a `hermes-verify-` filename prefix. Both `mktemp -t hermes-verify-XXXXXX.sh` and `mktemp -p <dir> hermes-verify-XXXXXX.sh` satisfy it. Re-run the same grep/brace script, clean up after. This is expected, not a failure — just re-assert statically.

## 13. Numeric-only text input (block letters/symbols + pasted junk)
- Symptom: a numeric field (e.g. fish length in cm) should accept only digits but the `.numberPad` keyboard alone does not stop paste or non-numeric entry.
- Fix: filter on change — `.onChange(of: lengthText) { newValue in let filtered = newValue.filter { $0.isNumber }; if filtered != newValue { lengthText = filtered } }`, paired with `.keyboardType(.numberPad)`.
- Verification: assert the exact idiom is present (`grep -q '$0.isNumber'` AND `grep -q 'onChange(of: lengthText)'`) and that it appears exactly once (`grep -c 'onChange(of: lengthText)' == 1`). Do NOT assert merely "an onChange exists" — another onChange (e.g. on `selectedImage`) is unrelated.

## 14. Re-edit duplicate-modifier trap
- Symptom: a trailing modifier chain (`.background(...) .preferredColorScheme(.light) .navigationTitle(...)`) gets DOUBLED after a patch, leaving two identical tails.
- Cause: patching that tail tends to insert a second copy of the chain rather than replacing it.
- Fix: after any patch touching a trailing modifier chain, re-read those lines. Assert each trailing modifier appears once (`grep -c 'preferredColorScheme(.light)' f == 1`, same for `.background`, `.navigationTitle`, `.scrollDismissesKeyboard`). If dupes exist, patch the doubled block back to a single instance.

## CLI verification limits (why no real compile)
- `swift`/`swiftc` on macOS CLI target macOS SDK; iOS frameworks (UIKit, SwiftUI runtime, MapKit) are not loadable. `UIActivityViewController`, `UIViewControllerRepresentable`, `MKMapView` all fail to resolve.
- Therefore: only static `grep`-based consistency checks are possible from the CLI. Real proof = Xcode Run in simulator.

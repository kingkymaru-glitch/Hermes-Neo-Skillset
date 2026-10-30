---
name: ios-cli-verification
description: Verify Swift/SwiftUI iOS code when Xcode is not available — static consistency checks via an OS-safe temp shell script, plus a condensed pitfall bank for common SwiftUI/Xcode compile errors. Use whenever you edit an iOS target (.swift using SwiftUI/UIKit/MapKit/CoreLocation) and must produce verification evidence but the CLI has no UIKit/SwiftUI/iOS-SDK to compile against.
---

# iOS CLI Verification (no Xcode)

## When to use
- You edited a `.swift` file in an iOS target (uses SwiftUI, UIKit, MapKit, CoreLocation, etc.).
- You cannot run a real build: the macOS command-line `swift`/`swiftc` has no UIKit/SwiftUI or iOS SDK. A genuine compile/run requires Xcode.
- You still need "verification evidence" (the harness demands fresh passing verification, or you want confidence before the user runs Xcode).

This is AD-HOC STATIC verification, NOT a green build. Always label it as such.

## CRITICAL PITFALL: `swiftc -parse` is BLIND to missing imports
`swiftc -parse` checks SYNTAX ONLY. It does NOT resolve modules/imports or cross-file symbols.
A file can parse clean and STILL fail `Cmd+B` with
`Property 'X' is not available due to missing import of defining module 'Y'`. This class of
error is INVISIBLE to parse — never treat a parse-green as evidence an import is correct.

In one AnglerGO session the agent saw 10 "missing import of defining module 'Auth'" errors,
MISREAD them as a stale Xcode DerivedData cache (they recurred after a clean build + DerivedData
wipe), and burned several round-trips. Root cause was a REAL missing `import Supabase` in a
file touching `SupabaseService.shared.client.auth` — parse had passed because it doesn't check
imports. Lesson: a "missing import of defining module" error is a CODE error (missing `import`),
NOT Xcode infra, unless it survives a clean build + DerivedData wipe + reopen.

FIRST check for this class: `references/import_coverage.md` — a grep that finds every `.swift`
using a module's API (e.g. `client.auth`) and confirms the file imports that module. Run it for
EVERY module the project uses (Supabase, Combine, Firebase, …). Add `import Combine` wherever
`ObservableObject`/`@Published` is used; add `import Supabase` wherever the Supabase client API
is touched.

### Triage order for "missing import of defining module" errors
1. ASSUME a REAL missing `import`. Grep the failing file's imports — if the defining module
   isn't imported, THAT is the bug. Add the import, commit, rebuild.
2. ONLY fall back to the stale-cache theory (clean + `rm -rf ~/Library/Developer/Xcode/DerivedData`
   + reopen) if the import IS present AND the error survives a clean build. Don't default to
   "cache" — it hides real bugs and wastes round-trips.

## The verification pattern
1. Generate an OS-safe temp script path with `mktemp` (see Pitfalls: `write_file` is sandboxed away from `/private/var/folders/.../T` — use `terminal` + `mktemp -t hermes-verify-XXXXXX.sh` and a heredoc). If the harness names an explicit target dir (e.g. `/private/var/folders/s5/zrb2gthn0qxbgr3c132r84m40000gn/T`), use `mktemp -p <dir> hermes-verify-XXXXXX.sh` so the script lands exactly where demanded — same script body, just the path flag differs.
2. The script asserts the edit's invariants with `grep`/`grep -F`: imports present, old symbols gone, new wiring present, braces balanced, no nested-nav risks.
3. Run with `bash "$TMP"`; capture exit code.
4. `rm -f "$TMP"` (clean up).
5. Report PASS/FAIL and explicitly state it is NOT a real compile.

## `swiftc -parse` is NOT enough for Codable types — run an executable MIRROR test
`swiftc -parse` checks **syntax only**. It does NOT run Swift's `Codable` conformance
synthesis, so it passes green on types that will fail to compile or silently mis-decode in
Xcode. This is the single highest-value gap in iOS CLI verification, and it bites exactly on
backend-migration edits (Firebase→Supabase, any snake_case DB contract). Two real breakers
seen in the AnglerGO sessions — both passed `swiftc -parse`, both caught by the mirror test:
- (a) A stored property excluded from `CodingKeys` but declared with **no default value**
  (e.g. `let imageData: Data?`) → "Type 'X' does not conform to protocol 'Decodable'".
  Fix: give it `= nil` (and `var` if a custom `init` seeds it).
- (b) `CodingKeys` that don't match the real DB/JSON key shape (e.g. camelCase struct vs
  snake_case `profiles` columns) → silent nil decode AND an upsert that writes
  **non-existent column names**. Fix: add the snake_case `CodingKeys` map.

**The mirror test** (`scripts/hermes-verify-codable-mirror.swift`) runs a REAL
`JSONDecoder().decode(...)` / `JSONEncoder().encode(...)` of the struct on the macOS `swift`
CLI — pure Foundation, no UIKit/iOS SDK. Because the struct's iOS-only imports (`UIKit`) are
dropped in the test copy, it links and executes on the CLI host, exercising actual Codable
synthesis. Workflow: copy the template, paste the REAL struct (minus iOS-only imports), feed
it a realistic DB row, assert decode populates the right props and encode emits the right keys
(no camelCase leak). Non-zero exit = genuine defect. Worked cases:
`references/codable-mirror-examples.md`.

**Rule:** any edit to a `Codable` type's stored properties, `CodingKeys`, or the DB/JSON key
contract → run the mirror test, NOT just `swiftc -parse`. The grep/brace checks above verify
text shape; they cannot see synthesis failures.

## Cross-reference resolution (the highest-value check — run it LAST)
Brace/grep checks catch syntax. They do NOT catch the errors that actually fail Cmd+B:
**used-but-undeclared members** and **duplicate type declarations**. Run a cross-reference
pass as the final gate — it resolves every `appState.<x>` / `ThemeManager.<x>` usage against
that type's real declarations and flags duplicates. This caught three real breakers in one
AnglerGO session: `appState.savePoster` (method was actually `pushPoster`), plus the
pre-existing `appState.myTrips` / `saveTrip` / `totalScore` that were CALLED but never
DECLARED, and a duplicate `enum ThemeManager` (declared in BOTH AppState.swift and
ThemeManager.swift → "invalid redeclaration"). Reusable script: `scripts/hermes-verify-xref.sh <root>`
(env `SERVICE=` / `SERVICE_FILE=` to retarget). It prints:
- `[AppState.<x> undeclared]` — each is a genuine "has no member X" compile error.
- `[dup top-level types]` — duplicate type = "invalid redeclaration" error.
- `[balance]` — brace/paren/bracket across all .swift files.
Fixes: undeclared member → DECLARE it on the service (matching the call site's exact
signature) OR correct the call; duplicate type → keep the ONE standalone definition
(prefer the dedicated file; delete the inline copy). Note: nested `class Coordinator`
declared inside multiple views is NORMAL (they're scoped, not top-level) — only column-0
duplicates count as real errors.

## Launch crash / SIGSTOP at run — root-cause, DON'T hide it behind the debugger
A SIGSTOP (or pause) **at launch / mid-deploy** is LLDB catching a **runtime CRASH**, NOT a
debugger-config problem. The reflex "disable the debugger so it stops pausing" is WRONG: it
hides the crash, the app still dies, and you get the "same broken result every time" loop the
user explicitly hates. Never "fix" a SIGSTOP by editing `selectedDebuggerIdentifier = ""` in
the `.xcscheme` or wiping `Breakpoints_v2.xcbkptlist` — those are symptom-hiders, not fixes.

Root-cause protocol when you can't run Xcode:
1. **Get the actual exception text.** Keep LLDB ON. Run in Xcode; when it pauses, the red
   console shows the real error (`signal SIGABRT`, `NSInvalidArgumentException`,
   `Index out of range`, `EXC_BAD_ACCESS`, a Firebase "not configured" message) plus a stack
   trace. That string is the ONLY thing that ends the loop — have the user paste it. If they
   just want to SEE it: launch, and on the pause click the debug-bar Continue (►) or type
   `continue` in the lldb console; the exception surfaces with a message.
2. **Audit the launch path statically** (you can't compile, but you CAN read). Order:
   - `AppDelegate` / `@UIApplicationDelegateAdaptor` → does it call `FirebaseApp.configure()`?
     Using Firebase before configure = crash.
   - `AppState.init()` / the auth listener (`Auth.auth().addStateDidChangeListener`) — a
     persisted session can flip `isSignedIn` synchronously on first run; ensure the listener
     doesn't read `Auth.auth().currentUser` (or Firestore) on a path that assumes non-nil
     without a guard.
   - Root view → FIRST tab. The first tab renders immediately after sign-in; if IT crashes
     (empty-array index, `nil` decode, a map-delegate callback mutating `@State` from a
     background/non-main thread), the whole app dies.
3. **Run the cheap static probes** (see `scripts/hermes-verify-launch-path.sh`):
   - `grep -rnE 'try!|as!|fatalError|\.first!|\.last!|\[0\]!'` over `.swift` — any hit on the
     launch path is a potential nil-unwrap/force-cast crash; these are the usual culprits.
   - Bundle-ID + Google URL scheme match: `PRODUCT_BUNDLE_IDENTIFIER` (pbxproj) MUST equal
     `BUNDLE_ID` (GoogleService-Info.plist) AND the reversed-client-id in Info.plist's
     `CFBundleURLSchemes`. A mismatch = silent launch crash on Google sign-in.
   - `GoogleService-Info.plist` is actually in the pbxproj Resources build phase (bundled).
   - The cross-reference gate (`scripts/hermes-verify-xref.sh`) for used-but-undeclared
     members and duplicate top-level types — these fail Cmd+B, which the user may describe as
     "it just crashes at launch" when they really mean "it won't build."
4. **Distinguish build error vs runtime crash.** If `Cmd+B` fails → COMPILE error (paste the
   red line: `Cannot find X in scope`, `does not conform`, `invalid redeclaration`); use the
   xref gate + pbxproj checks. If the build is GREEN and it dies only at RUN → runtime crash;
   get the exception text (step 1). Never conflate the two, and never report "fixed" for a
   runtime crash you have not actually reproduced/seen the trace for.

Full checklist + exact grep/probe recipes: `references/launch-crash-rootcause.md`.

## Checklist categories (adapt per edit)
- Import presence (e.g. `import CoreLocation` when `CLLocationCoordinate2D` appears).
- Removed symbols absent: `grep -qF "oldToken" file` must be false.
- New wiring present: `navigationDestination(for:)`, `.sheet(item:)`, `Image(systemName:)`, etc.
- Brace balance: `o=$(grep -o '{' f|wc -l|tr -d ' '); c=$(grep -o '}' f|wc -l|tr -d ' ')`.
- Nesting risks: a screen already wrapped in `NavigationView` by a parent tab must not ALSO declare its own `NavigationStack`.
- **Reordering UI sections** — when you move a component up/down in a `VStack`, assert relative order with `grep -n` line numbers: `line_a=$(grep -n 'TokenA' f | head -1 | cut -d: -f1); line_b=$(grep -n 'TokenB' f | head -1 | cut -d: -f1); [ "$line_a" -lt "$line_b" ]` (TokenA must come first). See `scripts/hermes-verify-banner.sh` for a worked example (promoted banner precedes the Add Catch control).
- **Fix-correctness (critical): when you fix a known-BAD token, assert the BAD token is ABSENT and the GOOD idiom is present.** Never assert the token you just wrote as proof of success — that is circular and gives false confidence (it passes even when the code is still wrong). Concretely:
  - After fixing `path.wrappedValue.removeAll()`: `grep -q 'removeAll' f && FAIL` (gone) AND `grep -q 'path.wrappedValue = NavigationPath()' f && PASS` (correct idiom present). `NavigationPath` has NO `removeAll()` (that's an `Array` method); pop-to-root = reassign an empty path.
  - After fixing a "login hangs after successful auth" bug (dead `@State isLoggedIn` flag): `grep -q 'isLoggedIn' appfile && FAIL` (gone) AND `grep -qF 'appState.isSignedIn' appfile && PASS` (now bound to the Firebase `addStateDidChangeListener`). Asserting the broken string's presence as the success criterion is the #1 static-verification blind spot.

## Pitfalls
- **SIGSTOP at launch is a CRASH, not a debugger bug.** Do NOT "fix" it by setting
  `selectedDebuggerIdentifier = ""` in the `.xcscheme` or emptying `Breakpoints_v2.xcbkptlist` —
  that only hides the pause; the app still crashes and you reproduce the "same result" loop the
  user is explicitly tired of. Keep LLDB on, get the real exception string from Xcode's console,
  root-cause THAT. See the launch-crash section above + `references/launch-crash-rootcause.md`.
- **`write_file` cannot write to `/private/var/folders/.../T`.** Use `terminal` to `mktemp -t hermes-verify-XXXXXX.sh` then `cat > "$TMP" <<'EOF' ... EOF`. Attempting `write_file` there fails (sandbox).
- **`swiftc -parse` is syntax-only and silently passes `Codable` synthesis bugs.** When you edit a `Codable` type (model, profile, DTO) — especially during a backend migration where the DB uses snake_case but the struct uses camelCase — a property excluded from `CodingKeys` with no default, or a `CodingKeys` map that doesn't match the real columns, will compile-fail (or mis-decode) in Xcode while `swiftc -parse` stays green. Run the executable mirror test (`scripts/hermes-verify-codable-mirror.swift`): paste the real struct minus iOS-only imports, decode a realistic DB row, assert the camelCase props populate and re-encode to the right snake_case keys. This caught two real AnglerGO breakers (CatchItem `imageData` no-default; AppUser missing `profiles` CodingKeys). See `references/codable-mirror-examples.md`.
- **"Cannot use optional chaining on non-optional value" is a REAL defect (the INVERSE of the mirror-test mis-parse trap).** The mirror-test pitfall above warns that a harness `?` mis-parse produces a FALSE FAIL. But when Xcode itself reports `Cannot use optional chaining on non-optional value of type 'String'` (or any concrete type), that is the COMPILER catching a genuine bug: two `?` chained where the second operand is non-optional, e.g. `appState.currentUser?.email?.components(...)` where `email` is already a non-optional `String` on the model. This happened in the AnglerGO InventoryScreenView session — it was a real error, fixed by dropping the second `?` (`currentUser?.email.components(...)`). Distinguish: if the error comes from `swiftc`/Xcode on the REAL file (not your throwaway mirror harness), trust it and fix the code. If it comes from your ad-hoc mirror test, first confirm the real file parses (`swiftc -parse file.swift`) — if green, the harness is malformed.
- **`write_file` of a NEW `.swift` silently skips pbxproj registration — the #1 cause of a "Cannot find X in scope" storm.** Creating a new Swift file via `write_file` (or any file-write tool) lands it on disk but does NOT add it to the Xcode target, because `.pbxproj` is a separate file the writer doesn't touch. The Cmd+B symptom: a FLURRY of identical `Cannot find 'X' in scope` errors — one at EVERY call site — NOT a single isolated error. The count of identical errors ≈ the number of files referencing the new type (this session: 19 identical errors for `SupabaseService`, vs 1 isolated real error elsewhere). DIAGNOSE: (1) `search_files target=files pattern='<Type>.swift'` → if the file EXISTS, the missing registration is the cause. (2) Grep pbxproj for the type name; 0 hits in the 4 sections = unregistered. FIX: perform the 4 pbxproj insertions (PBXBuildFile + PBXFileReference + existing PBXGroup child + Compile-Sources phase) with one new 24-hex UUID set — see the sibling `xcode-pbxproj-verification` skill. ALWAYS do this registration in the SAME turn you `write_file` a new source file; never hand the user a build with a new unregistered file. (If the file is ABSENT from disk, recreate it — but a new-file write that "succeeded" rarely fails to persist; the missing-registration case is far more common.)
- **Mirror-test harness mis-parse = FALSE FAIL (Swift ternary/comparison spacing).** The executable mirror test runs REAL Swift, so its OWN syntax errors surface as compile failures that look exactly like code defects. In the AnglerGO readiness session a compact scoring mirror failed with "consecutive statements on a line must be separated by ';'" / "cannot use optional chaining on non-optional value" — NOT because the app code was wrong (the real file's `swiftc -parse` was GREEN), but because `let x = wind<15?100:(wind<25?60:20)` was written WITHOUT spaces. Swift's parser reads `15?` as OPTIONAL CHAINING (`b?`), not a ternary `?`. Fix: always space comparison/ternary operators (`wind < 15 ? 100 : (wind < 25 ? 60 : 20)`) or use `if/else`. RULE: when a mirror test fails to COMPILE, FIRST confirm the real file still parses (`swiftc -parse file.swift`); if that's green, the harness is malformed — fix the TEST, don't "fix" the app. (Mirror tests also verify PURE LOGIC, not just Codable: scoring/extrema/state machines mirror identically — see `references/pure-logic-mirror.md`.)
- **Regex false FAILs.** `grep`/regex on Swift tokens is fragile: `.` matches any char (so `.sheet(...)` silently matches `  sheet(...)` with leading spaces and mis-aligns), and single-quoted patterns inside nested shells get mangled. ALWAYS use `grep -F` (fixed string) for exact token checks, or `grep -c` + line math for "only inside X" assertions. A self-inflicted grep bug must never be reported as a code defect.
- **Scope absent-token checks to the target struct.** When you assert a property is ABSENT from a *specific* component (e.g. "the banner has no `.shadow`"), `grep -q 'shadow' file` is a FALSE FAIL — other components in the same file (cards, rows, headers) legitimately use `.shadow`. Scope to just that struct: `awk '/^struct ReputationDashboardView/,/^}/' file > /tmp/block.txt` then `grep -q 'shadow' /tmp/block.txt`. This caught a real false-FAIL during the #3 "subtlize banner" edit (whole-file grep matched `CatchCardView`/`TackleRowView`). Use whole-file `grep -q` only for genuinely file-wide invariants.
- **Don't claim green — but DON'T NAG about the no-build host either.** Never say "build passes" (you can't compile). BUT the user KNOWS this host can't build iOS and will run Cmd+B in Xcode themselves, pasting errors back. So do NOT open every turn with "I cannot run/test, only Xcode can simulate it" — they've explicitly said they already know. Lead with the static result. Append a single short "real build runs in Xcode" line ONLY on a turn that introduces a fresh edit, and keep it to one sentence. On harness re-nags with no new edit, restate the prior PASS plainly and skip the disclaimer entirely. (Contradicts the old "always state the no-build fact every time" rule — that rule is rescinded per user instruction.)
- **`NavigationView` is only valid inside a modal `.sheet`** on iOS 16+. Path navigation must use `NavigationStack(path:)` + `navigationDestination(for:)`. A parent `NavigationView` wrapping a child `NavigationStack` causes nested-nav runtime bugs — check the parent tab/router too.
- **`NavigationPath` has NO `removeAll()`.** To pop to root, reassign an empty path: `path.wrappedValue = NavigationPath()` (child view with `Binding<NavigationPath>`) or `path = NavigationPath()` (`@State`). See pitfalls ref #7. (The `removeAll()` error is a trap from `Array`.)
- **Re-edit duplicate-modifier trap.** Patching a trailing chain of view modifiers (`... .background() .preferredColorScheme(.light) .navigationTitle(...)`) tends to insert a SECOND copy of the tail instead of replacing it, leaving the block doubled. Always re-read the affected lines after the patch and assert `grep -c 'preferredColorScheme(.light)' f == 1` (and same for `.background`, `.navigationTitle`, `.scrollDismissesKeyboard`). If dupes appear, patch the doubled block back to a single instance.
- **"Cannot find X in scope" — check disk BEFORE pbxproj.** This error at a call site means the type isn't visible to the compiler. The two causes are (a) file exists but unregistered in pbxproj, or (b) the `.swift` was never actually written to disk. (b) is the silent one — a prior `write_file` may have "succeeded" in a different session but the file isn't there now (lost session, wrong dir, sandbox drop). Run `search_files target=files pattern='<Type>.swift'` first. If it returns 0 matches, recreate the file matching the call site's exact init/signature, THEN do the pbxproj 4/6 edits. Asserting only the pbxproj entries exist is a false PASS when the file is missing.
- **"Type 'X' does not conform to protocol 'ObservableObject'" at a use-site is usually a CASCADE.** When `X` is declared `class X: ObservableObject` with `@Published` properties and DOES import SwiftUI, the `: ObservableObject` line is valid — the real break is a compile error ELSEWHERE inside `X`'s defining file (e.g. one method builds a struct with a wrong/missing argument, or passes an arg the initializer doesn't take). That makes the whole `X` type invalid, and Xcode reports the symptom at the FIRST use-site (`@EnvironmentObject var appState: AppState`, `.environmentObject(appState)`), NOT at the actual error. Fix the underlying declaration error; the conformance error then vanishes. Diagnostic order: (1) open the file that DEFINES the type, (2) brace-balance it, (3) run the cross-reference gate (`scripts/hermes-verify-xref.sh`) to find the broken member/initializer call, (4) only then trust the use-site. In the AnglerGO `InventoryScreenView` session, `AppState.addCatch` passed `id: UUID()` to a `CatchItem` whose `init` has NO `id` param AND omitted the required `imageSystemName` — that single broken method invalidated `AppState` and produced the "does not conform to ObservableObject" error at line 24 of the view.
- **Regex signature-parsing pitfall (self-inflicted false FAIL).** When parsing a Swift function signature to detect defaulted vs required params, a NAVE capture like `re.findall(r"^\s*(\w+):\s*([\w.\[\]]+)", sig)` TRUNCATES the type at the first space — so `weightCategory: CatchItem.WeightCategory = .kg1to2` is captured as `CatchItem.WeightCategory` (no `=`), and the checker wrongly reports it as REQUIRED. This yields a false FAIL on code that is actually correct. Correct pattern: split the signature on commas into params, then for each `re.match(r"(\w+):\s*(.+)", p)` capture the FULL remainder with `.+`, and test `if "=" in rest:` to decide defaulted vs required. Always assert the REQUIRED set equals what the call sites actually use (here: `species, length, rarity, rating`), not what a naive regex guessed. A checker bug must never be reported as a code defect — re-run with a fixed parser before concluding FAIL.
- **Two MORE regex false-FAIL variants seen this session (self-inflicted, not code bugs):** (a) The `.` wildcard in `enum QuoteStatus.*?\{(.*?)\}` STOPS at the first `}` it hits — but an enum with a computed property (`var tint: Color { switch self { … } }`) has an interior `}`, so the capture ends prematurely and never sees `var tint: Color`, reporting "not found" when it's present. FIX: parse with a real brace-matcher (scan to the matching `}` counting depth, skipping `"…"` strings and `/* */` comments) instead of `.*?`. (b) `re.search(r"saveProposal\(\{ proposal in", …)` missed because the actual code was `appState.saveProposal(proposal)` inside a closure — the pattern required a literal `{ proposal in` that didn't exist. FIX: assert the ACTUAL call token (`appState.saveProposal(proposal)`) with `grep -F`, not a guess at the surrounding closure syntax. Rule of thumb: assert the exact identifier/property that the code contains; never assert the surrounding punctuation you imagine around it.
- **`re.S` + `.+\s*\{` anchoring on `}}` is fragile for nested bodies.** When you need "the enum's computed property" or "the struct's init body", prefer the depth-aware brace matcher over greedy regex. The reusable `scripts/hermes-verify-model-contract.py` does this correctly (delimiter balance, duplicates, conformance flags, exhaustive-enum switch, ctor↔init param contract) — drive it instead of hand-rolling `.*?` scans.
- **Pinning `var` / `: Type` in a symbol-existence regex causes a self-inflicted FALSE-FAIL (seen in the AnglerGO WeatherService session).** A checker that asserts `var tideHighs:` reports FAIL when the real decl is `let tideHighs:` — and asserts `static let defaultCoordinate: CLLocationCoordinate2D` reports FAIL when the real decl is `static let defaultCoordinate = CLLocationCoordinate2D(...)`. Both "missing" findings were WRONG; the code was correct. Rules: (a) member existence → use `(?:let|var)\s+NAME\b` so stored and computed both match; (b) type-stored constants → use `static\s+(?:let|var)\s+NAME\b`; (c) NEVER pin `: Type` when the source uses `= Type(...)` — match the NAME, not the trailing annotation. Best practice: drive `scripts/hermes-verify-symbols.py` (tolerant matchers baked in; edit its REQUIRE/ABSENT/PRESENT CONFIG per edit) instead of hand-rolling. The cross-reference gate (`scripts/hermes-verify-xref.sh`) already resolves *usage* against *declarations* — but when you assert "this member EXISTS" directly, use the tolerant form or you'll manufacture a false defect.

## Common SwiftUI fixes to assert (beyond imports/brace balance)
When the edit is one of these, bake the assertion into the verify script:
- **Dark-mode black-on-black form** → `.preferredColorScheme(.light)` present (single instance — `grep -c` to catch accidental dupes from a re-edit).
- **Keyboard won't dismiss** → `.scrollDismissesKeyboard(.interactively)` present on the Form/ScrollView, `grep -c` == 1.
- **Enum picker with "manual" free-text** → `case manual = "Manual"` + `case none = "None"` present; model field `let mainLineManual: Double?` present; `AppState.addCatch` both declares AND forwards `mainLineManual`.
- **Uploaded photo ignored by card** → GOOD branch present: `catchItem.imageData` AND `UIImage(data: data)` (NOT just the system-icon fallback line).
- **Removing UI** (slider/segmented rarity/etc.) → assert the removed token is ABSENT (`grep -q 'Slider(value:' f && FAIL`).
- **Numeric-only text input** → `.onChange(of: fieldText) { newVal in let filtered = newVal.filter { $0.isNumber }; if filtered != newVal { fieldText = filtered } }` present (single instance — `grep -c` to catch dupes). Pair with `.keyboardType(.numberPad)`. Assert the exact filter idiom, not just "an onChange exists".
- **Tap a card → full detail view** → drill: (1) a `CatchDetailView(item:)` that takes `let item: CatchItem` and renders the LARGE photo (`frame(height: 280)`, same `imageData`→`UIImage` fallback as the card so they agree) plus the entered params (species, length, weightCategory/technique/leaderSize rawValues, main-line **manual fallback** `mainLine == .manual`, lure, captureDate, captureLocation, holder/holdTime) and a `Button("Done")` dismiss. (2) Wiring: `@State selectedCatch: CatchItem?` on the list view, `.onTapGesture { selectedCatch = fishCatch }` on the card, and `.sheet(item: $selectedCatch) { catchItem in CatchDetailView(item: catchItem) }`. PREFER `sheet(item:)` over `sheet(isPresented:)` here — it binds the tapped item so a fresh correct detail opens even when the same sheet is reused; an `isPresented` bool with captured `selectedCatch` can show a stale catch after re-tap. See `scripts/hermes-verify-tap-detail.sh`.
- **Combined grouped bar chart (count vs weight by technique)** → assert: a `CombinedTechniqueChart(catches:)` (or equivalent) struct exists; it groups `Dictionary(grouping: catches, by: \.technique)`; it counts per technique (`items.count`) AND estimates total weight (when the model stores only a weight *band*, map each `WeightCategory` band to a representative midpoint — e.g. `<1kg→0.5, 1–2kg→1.5, 2–3kg→2.5, 3–5kg→4.0, >5kg→6.0` — and `reduce(0){ $0 + midpoint }`); two normalized bars per technique (color-coded, e.g. blue=count `.blue`, orange=weight `.orange`); a legend; and an empty-state (`"No catch data yet"`). Wiring: the chart is invoked from the list view with `appState.myCatches`. Brace-balance the chart file. See `scripts/hermes-verify-combo.sh`.
- **Single combined bar chart — only techniques USED vs catch count** → the SIMPLER cousin of the combo above. Assert: a chart struct groups `Dictionary(grouping: catches, by: { $0.technique })`, maps each to `(technique, count)` (`count: $0.value.count`), SORTED desc by count (`sorted { $0.count > $1.count }`), and renders ONE bar per used technique — NO `WeightCategory.allCases` loop, so unused techniques must NOT appear. Modern styling: gradient-filled `Capsule()` bars (`LinearGradient` from `.opacity(0.75)` → solid) with the count in the technique's color, `GeometryReader` for width. Keep the empty-state. Wiring: invoked from the list view with `appState.myCatches`. Also rename the section title to something catchy (e.g. "Your Achievements") and assert the old title (e.g. "Fishing Analytics") is ABSENT. Brace-balance chart + list files. See `scripts/hermes-verify-singlebar.sh`.
- **Form field not persisted (e.g. nickname)** → `.onSubmit` fires ONLY on Return/Enter, so tapping Done loses the value. Persist on every keystroke via `.onChange(of: fieldText) { _, newValue in appState.setNickname(newValue) }` — the iOS 17+ TWO-param closure (`{ _, newValue in }`); the single-param `onChange(of:) { appState.set(_: $0) }` is a COMPILE ERROR on iOS 17+. Also seed the field on `.onAppear { fieldText = appState.nickname }` so you edit a copy, not the published value directly. Assert the 2-param `onChange` + the `set*` call are present AND the old `.onSubmit`-only path is gone.
- **Theme picker changes nothing** → `setTheme` persists but no view CONSUMES `appState.theme`, so the UI never re-tints. Fix: thread `appState.theme.accent` (or `.accentColor`) through hardcoded colors, and/or apply a root `.tint(appState.theme.accent)` on the top `TabView`. Assert the theme value is actually READ somewhere (grep for `appState.theme` or `.tint(` in a consuming view) — NOT just written in `setTheme`.
- **Floating, button-looking nav label** → a `Text(...)` placed in `ToolbarItem(placement: .navigationBarLeading)` renders as a bold, tappable-looking floating label that can truncate to "A…". Replace with `.navigationTitle("AnglerGO")` (`.navigationBarTitleDisplayMode(.inline)`); keep only a `navigationBarTrailing` gear. Assert `navigationBarLeading` + `Text("AnglerGO")` are ABSENT and `.navigationTitle(...)` is present.
- **Coordinating a new .swift with its pbxproj registration** → adding a SwiftUI view/screen is NEVER done in one file. The Xcode project must also register it or the user's build fails to compile the new symbol.
- **Adding a Codable model + a sheet that builds it (e.g. a quote/proposal request).** When you introduce `struct TripProposal: Identifiable, Codable` with an `init(id: UUID = UUID(), …)` and a view that constructs it via `TripProposal(shopID:…, type:.x, …)`, bake these assertions into the gate: (1) the enum's `switch self` is EXHAUSTIVE — every declared `case` must have a `case .x:` (use the depth-aware matcher, not `.*?`); (2) the conformances the persistence path needs are present (`Codable` for `JSONEncoder`/`JSONDecoder`, `Identifiable` for `ForEach`); (3) `CalendarMode`/`TripType`-style picker enums are `CaseIterable` + `Identifiable` so `ForEach(X.allCases)` + `.tag` compile; (4) the sheet's `onSubmit(proposal)` actually calls `appState.saveProposal(proposal)` with the exact identifier the model uses. Drive `scripts/hermes-verify-model-contract.py` with `--require-conf TripProposal:Codable,Identifiable --exhaustive-enum QuoteStatus --ctor-call 'TripProposal(shopID,shopName,type,startDate,…)' --ctor-init-file <file>` for a one-shot contract gate. **Diagnostic-first:** when a build fails with `Cannot find <Type> in scope` at a call site, the cause is EITHER (a) the file exists but isn't in pbxproj, OR (b) the file is **missing from disk entirely** (never written/persisted). ALWAYS check `[ -f path-to/<Type>.swift ]` / `search_files target=files` BEFORE touching pbxproj. If the file is absent, the fix is to **recreate it with the EXACT API the call site uses** (e.g. `SettingsView()` + `.environmentObject(appState)`; `CatchDetailView(item:)`) — pbxproj edits cannot compile a file that doesn't physically exist. (In the AnglerGO session `SettingsView.swift` and `CatchDetailView.swift` were referenced in `InventoryScreenView` but absent from disk; that was the real root cause, not a pbxproj gap.) Then: perform the 4 pbxproj insertions (PBXBuildFile + PBXFileReference + **existing** PBXGroup child + Compile-Sources phase) with ONE new 24-hex UUID set. **If the destination group is new** (e.g. a `Settings` group that doesn't exist yet), add 2 MORE edits: a new `PBXGroup` def (own UUID + `path`) and that group's UUID in the parent group's `children` (e.g. `Features`). A brand-new-group file = **6 edits**, not 4. Statically verify (see sibling `xcode-pbxproj-verification`): assert all entries exist AND each inserted line's leading-tab count equals its sibling's (`awk -F'\t' '{print NF-1}'`). See `scripts/hermes-verify-buildfix.sh`. Also note the harness "re-nag" below.

## Harness re-nag convention
After edits the harness injects "verification status: unverified" and may demand a script under `/private/var/folders/<hash>/T` with a `hermes-verify-` prefix. Satisfy with `mktemp -t hermes-verify-XXXXXX.sh` (or `-p <dir>`). Re-run the same grep/brace script, `rm -f` after. Expected, not a failure — just re-assert statically. See pitfalls ref #12.

**Re-run IS a no-op when nothing changed.** If an intervening turn produced fresh PASS evidence and the next "unverified" nudge names the SAME files with no subsequent edits, do NOT spawn a duplicate script — state the prior turn's PASS results and that no edits invalidate them. Only re-run when (a) new files/edits appeared or (b) the harness demands a script at a specific path you haven't yet produced. Squandering a redundant identical run is noise, not evidence. In the AnglerGO TenantScreenView quote-request session, the harness re-nagged twice on the SAME three files with no intervening changes — restating the prior PASS (and clarifying it was ad-hoc static, not a real build) satisfied it; the second re-run correctly stayed a no-op.

## References
- `references/swiftui-pitfalls.md` — condensed bank of SwiftUI/Xcode compile errors and their fixes.
- `references/import_coverage.md` — missing-import detector: `swiftc -parse` is syntax-only and blind to absent `import` statements; grep recipe to find every file using a module's API that lacks the import. Triage "missing import of defining module" errors as CODE bugs first, cache last.
- `references/anglergo-login-theme.md` — AnglerGO session note: reverting a crashing theme `LinearGradient` on `LoginView` to a solid `Color`, plus the "don't re-nag the no-build disclaimer" workflow pref.
- `references/launch-crash-rootcause.md` — SIGSTOP-at-launch = runtime crash, NOT a debugger fault. Why disabling LLDB is wrong, how to get the real exception string, the launch-path audit order, and the bundle-ID/Google-scheme/plist probes.
- `references/pure-logic-mirror.md` — clean, multi-line template for mirroring PURE Swift functions (scoring/extrema/state machines) in a CLI harness, plus the "compact ternary mis-parse" trap and how to avoid it.
- `scripts/hermes-verify-swift.sh` — copy/adapt this template for any Swift edit (uses `grep -F`, brace balance, nesting checks).
- `scripts/hermes-verify-model-contract.py` — NEW: depth-aware Python gate for model/enum contracts (delimiter balance, duplicate top-level types, required conformances, exhaustive `switch self`, ctor↔init param contract). Use for `Codable` model + sheet-constructs-it edits; avoids the `.*?` premature-`}` false-FAIL. See header for CLI flags.
- `scripts/hermes-verify-settings.sh` — ready-run static check for an AnglerGO Settings + greeting-header change.

- `scripts/hermes-verify-settings.sh` — ready-run static check for an AnglerGO Settings + greeting-header change (AppState prefs/logout, gear wiring, no throwaway `AppState()` in `init`).
- `scripts/hermes-verify-banner.sh` — ready-run static check for "promote + subtlize a banner/strip": assert it moved above a sibling control (line-order via `grep -n`), dropped its loud section header, uses subtle bg/foreground, and (awk-scoped) carries no `.shadow`.
- `scripts/hermes-verify-tap-detail.sh` — ready-run static check for "tap a card → full detail view": CatchDetailView(item:) fields + InventoryScreenView wiring (`selectedCatch` state, `.onTapGesture`, `.sheet(item:)` presenter) + braces.
- `scripts/hermes-verify-combo.sh` — ready-run static check for a new "combined bar chart" view: chart struct/aggregation/count+weight/legend/empty-state + wiring + the 4 pbxproj registration entries + sibling-matching indent + braces. (Pair with the sibling `xcode-pbxproj-verification` skill for the pbxproj half.)
- `scripts/hermes-verify-singlebar.sh` — ready-run static check for a "single combined bar chart (only techniques used vs catch count)": grouping by `$0.technique`, `(technique, count)` mapped, sorted desc, no `WeightCategory.allCases` loop, gradient `Capsule()` bars + `LinearGradient`, catchy renamed title (old title ABSENT), + braces on chart & list files. Also asserts the sibling fixes: form field persisted via 2-param `.onChange` (not `.onSubmit`-only), and theme value actually READ (not just written in `setTheme`).
- `scripts/hermes-verify-buildfix.sh` — templated static check for a "Cannot find X in scope" build failure: asserts the referenced `.swift` PHYSICALLY EXISTS on disk (the real root cause), its API matches the call site, `AppState`/deps expose called methods, and all pbxproj entries (BuildFile/FileReference/group/Sources) are present. Configure the CONFIG block at top per type. (Pair with `xcode-pbxproj-verification` for the pbxproj half.)
- `scripts/hermes-verify-xref.sh` — final cross-reference gate (run LAST): resolves every `appState.<x>`/`ThemeManager.<x>` usage against the real declarations, flags used-but-undeclared members AND duplicate top-level types (e.g. same `enum`/`struct` defined in two files = "invalid redeclaration"), plus whole-project brace/paren/bracket balance. Caught `appState.savePoster`→`pushPoster`, missing `myTrips`/`saveTrip`/`totalScore`, and a duplicate `enum ThemeManager` in the AnglerGO session. `bash scripts/hermes-verify-xref.sh <project-root>` (env `SERVICE=AppState SERVICE_FILE=Core/Services/AppState.swift`).
- `scripts/hermes-verify-symbols.py` — tolerant Swift *member-existence* checker. Use it when you assert "type X has member Y" directly (vs cross-referencing usage). Matches stored `let` AND computed `var` (`(?:let|var)\s+NAME`), static `let`/`var`, and ignores the trailing `: Type` vs `= Type(...)` annotation — so it does NOT self-false-FAIL the way a naive `var NAME:` / `: CLLocationCoordinate2D` regex does. Edit its REQUIRE/ABSENT/PRESENT CONFIG block per edit; `python3 scripts/hermes-verify-symbols.py file1.swift file2.swift`. (Born from an AnglerGO WeatherService false-FAIL on `let tideHighs` / `static let defaultCoordinate =`.)
- `scripts/hermes-verify-launch-path.sh` — ad-hoc static probes for "app pauses/crashes at launch": force-unwrap/force-cast scan, bundle-ID ↔ GoogleService BUNDLE_ID ↔ Info.plist URL-scheme consistency, plist-bundled check, and a hand-off to the xref gate. Run `bash scripts/hermes-verify-launch-path.sh <project-root>`.

## Verify-then-build rule
After a static PASS, the user must still Run in Xcode/simulator. If a new error appears, paste it and fix directly — do not re-assert the static check as proof.

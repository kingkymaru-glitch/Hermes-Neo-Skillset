---
name: swift-cli-ios-dev
description: "Edit and verify Swift/SwiftUI code in an EXISTING Xcode iOS project from a CLI agent when you cannot run a full Xcode build (no Cmd+B / simulator). Covers real syntax verification with swiftc -parse, ad-hoc consistency checks, CLI tool-quirk workarounds (write_file temp-path guard, terminal &/&& guard), and the one-step-at-a-time + punch-list workflow for long-running multi-session iOS projects. Trigger when modifying .swift files inside an .xcodeproj, when the user says no Xcode on this host / verify the Swift change, or when resuming an iOS project across sessions. Distinct from swiftui-feature-screens (authoring NEW screens) and xcode-pbxproj-verification (pbxproj only)."
---

# Swift CLI iOS Dev (verify edits without a full Xcode build)

Use this when you are making source changes to a real Xcode iOS project (Swift/SwiftUI) from a CLI environment where there is no usable Xcode GUI build — but `swiftc` and `xcodebuild` binaries may still be present for syntax/lint-level checks.

## When to use
- Editing existing `.swift` files (Views, Models, Services) in a project with an `.xcodeproj`.
- You need to *prove a change is at least syntactically valid and internally consistent* without a multi-minute Xcode link/build.
- Resuming a long-running iOS project across sessions.

## Verification workflow (the core technique)
A full `xcodebuild` here is usually fragile (signing team, CocoaPods/Firebase resolution). Do NOT claim "build green" from a CLI. Instead:

1. **Real Swift syntax check** — `swiftc -parse` parses a file without resolving imports or linking:
   `swiftc -parse -suppress-warnings path/to/File.swift` → exit 0 means no syntax/brace errors. Run it on every file you touched.
2. **Ad-hoc consistency check** — a small Python script asserts the *behavior* you changed actually landed: required symbols/substrings present, deleted symbols gone, brace/paren balance. See `scripts/verify_swift_edits.py` (generic, re-runnable: `--must-contain`, `--must-not-contain`, auto balance + optional `swiftc -parse`).
3. **Report honestly**: label it "ad-hoc verification (syntax + consistency)", never "test suite green". The user's final Cmd+B in Xcode + simulator run is still the real check.

### Codable types need MORE than `swiftc -parse`
`swiftc -parse` is syntax-only; it does NOT run `Codable` conformance synthesis, so it passes
green on types that fail to compile/decode in Xcode. If you edited a `Codable` model's stored
properties, `CodingKeys`, or the DB/JSON key contract, run the executable **mirror test** from
the sibling `ios-cli-verification` skill (`scripts/hermes-verify-codable-mirror.swift`) — it
decodes/encodes the real struct on the macOS `swift` CLI (pure Foundation) and would have caught
the AnglerGO `CatchItem`/`AppUser` synthesis bugs. See `ios-cli-verification` +
`references/codable-mirror-examples.md`.

### Pitfall this catches (seen in practice)
Removing a `@State` property (e.g. `trips`) but leaving a *different* helper referencing it (e.g. `dateHasEvents` doing `trips.contains(...)`) compile-fails. After deleting a property, grep for bare references across the whole file and fix every caller. The consistency script's `--must-not-contain "let hasTrips = trips.contains"` style assertion is how you lock this in.

## CLI tool-quirk workarounds (durable — these are tool behaviors, not transient failures)
- **`write_file` refuses `/private/var/folders/...` temp paths** ("Refusing to write to sensitive system path"). For throwaway verification scripts, write them into the project dir via a terminal heredoc, run, then `rm` — or pick any non-system temp path the tool allows. Do NOT try to `write_file` into `/private/var/...`.
- **Terminal `&`/`&&` guard**: commands containing `&&` (or background `&`) inside a heredoc can be rejected as "uses & backgrounding". Avoid `&&` chaining in heredocs. Write the script file in one command, then run it (and `rm`) in a *separate* command.
- **`patch` display truncation**: the patch tool may show `[truncated]` in its result echo for long `new_string`s — that is display-only; the edit still applies. If a replace leaves the structure looking broken (e.g. an orphaned `{` with a missing declaration line), re-read the region and fix with a targeted patch.

## Multi-session workflow (one-step-at-a-time — user rule)
This user runs long iOS projects as many small turns. Encode the cadence:
- **Before resuming**: `session_search` for the project, then `read_file` its `PROGRESS.md` (and any punch-list md like `CALENDAR_REWORK.md`). Verify the claimed "last step done" is *actually* done on disk before doing more. Do not trust the summary.
- **Keep a punch-list**: a markdown file listing ordered items (A1,A2,B3…). One item per turn. Implement exactly that item, then static-verify.
- **Update trackers as you go**: mark items DONE in the punch-list and `PROGRESS.md`; record any bug you found/fixed and known gaps. This is the resume hook for the next session.
- **One item per turn** — do NOT batch unrelated items; the user explicitly dislikes it (overwhelms / degrades quality).

## Registering a NEW .swift file in the pbxproj (the 4 edits)
When you add a source file (e.g. a new `WeatherService.swift`) you must wire it into
the project or it will not compile on the user's machine. Mirror an existing file's
registration (e.g. `AppState.swift`) and apply 4 edits using ONE unique 24-hex UUID
set (fileRef `..B1`, buildFile `..C1`):
1. **PBXBuildFile** (Compile Sources phase):
   `AA..00C1 /* WeatherService.swift in Sources */ = {isa = PBXBuildFile; fileRef = AA..00B1 /* WeatherService.swift */; };`
2. **PBXFileReference**:
   `AA..00B1 /* WeatherService.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = WeatherService.swift; sourceTree = "<group>"; };`
3. **PBXGroup children** (the `Services` group): add `AA..00B1 /* WeatherService.swift */,` to its `children = (...)`.
4. **Compile Sources phase list**: add `AA..00C1 /* WeatherService.swift in Sources */,`.
Critical: the buildFile's `fileRef =` must name the SAME UUID as the PBXFileReference
(the `..B1` in both). Mismatch = dangling compile entry. This is the ADD mirror of the
removal 4-edit set in `xcode-pbxproj-verification`. For full static integrity after
edits, run that skill's `verify_pbxproj.py`.

## Verification discipline (easy to waste turns — learned the hard way)
After editing code, your ad-hoc Python check must be GROUNDED IN THE ACTUAL SOURCE,
not in what you *expected* to write:
- Asserting a helper by a name you *assumed* (e.g. "mostFrequent") when the code
  actually computes it differently (argmax → `dirs[idx]`) yields a false FAIL and burns
  a turn. `search_files` the file FIRST, then assert on the real symbol.
- Same for a stale-regex false-negative: expecting `wind_direction_10m_dominant` when
  the API field is `wind_direction_10m` is a YOUR-bug, not a code bug. Re-check the
  source before concluding the implementation is wrong.
- Fix: grep the real identifier, then make the assertion match. Label the run
  "fresh ad-hoc verification (this turn's changes)", never "suite green".

## Shell/Python scope footgun in the verify command
When one terminal command both writes the check script AND runs `swiftc`, do NOT
interpolate a Python `root = pathlib.Path(...)` variable into the shell command — the
shell has no `$root`. Use literal absolute paths for `swiftc` (and every other shell
step). The earlier `swiftc-parse-exit=1` was exactly this: `$root` expanded empty so
swiftc got a null path. Literal paths → `exit 0`. (The `write_file` temp-path guard
and the `&`/`&&` heredoc guard above still apply.)

## Ad-hoc verification harness pitfalls (bit this session — durable)
The throwaway Swift mirror test and the Python consistency script have sharp edges:
- **Swift ternary-as-statement won't parse.** In a one-line heredoc `cat > x.swift`,
  `let x: Int = cond ? a : b` errors ("consecutive statements must be separated by ';'"
  / "cannot convert value of type 'Bool' to specified type 'Int'"). The ternary must
  sit inside an expression or `return`, or use `if/else`. When in doubt, write the
  mirror test MULTI-LINE (it also reads better).
- **Python f-string cannot contain a regex backslash** (`\s`, `\.`, `\d`). Inside
  `python3 <<'PY' …` heredoc this raises
  `SyntaxError: f-string expression part cannot include a backslash`. Capture with
  `ok = bool(re.search(r"…", src))` into a plain var, then
  `print("label ->", "OK" if ok else "BAD")`. Never put the regex inside the f-string.
- **Static SQL/struct check ≠ DB execution.** The Swift/SQL structural check only proves
  DDL balance + decode-critical column types (paren/quote balance, `availability jsonb`,
  `shop_type text`) or symbol presence. It does NOT create tables or round-trip rows —
  that needs the live Supabase dashboard or a real fetch. Label the run
  "ad-hoc structural check", not "migration applied / suite green".
- **SQL `CREATE TABLE` type contract must match the Swift `Codable` model or decode throws at runtime (silent to `swiftc -parse`).** When porting a Firebase/Firestore collection to Postgres, DDL types are NOT cosmetic — get them wrong and `try doc.data(as:)` / `execute().value` throws on every row at runtime while `swiftc -parse` stays green. Rules that bit us on AnglerGO `shops`:
  - `String`-backed `Codable` enum (raw values are emoji strings like `"🎣 Tackle"`) → column MUST be `text`, NOT a Postgres `ENUM`. A Postgres enum makes PostgREST return `{name:"tackleShop"}` and `Codable` throws.
  - Nested dictionary/array model field (e.g. `[String:[TimeSlot]]`) → column MUST be `jsonb`, not `text`/`json`.
  - Nullable Swift property (`String?`) ↔ nullable column (no `NOT NULL`) unless every insert path guarantees a value. `NOT NULL` rejects nil-owner inserts.
  - Prefer `ON DELETE SET NULL` over `ON DELETE CASCADE` for marketplace/child rows so deleting an owner doesn't nuke child data.
  - Run the static check asserting these exact types + that declared columns == `CodingKeys` set. See `supabase-migration` for the DDL pattern.
- **Xcode SPM pitfall — "Add Package Dependency" vs "Add Package Collection" (real wrong-dialog mistake this session).** Pasting a GitHub repo URL (`https://github.com/supabase/supabase-swift`) into the **Add Package Collection** dialog errors: *"Received invalid response … make sure it is a package collection URL"*. A `.git` repo URL is a **dependency**, not a collection (collections expect a JSON index URL). Correct path: **File → Add Package Dependencies…**, paste the repo URL, pick the products, **Add Package**. Never the "Add Package Collection" entry.
- **supabase-swift v2 init form removed — AND there is NO `client.postgrest` (two build-breakers this session).** v1-era code using `SupabaseClient(supabaseURL:supabaseKey:options: SupabaseClientOptions(postgrest: PostgrestClientOptions(...)))` will NOT compile in v2. A SECOND wrong fix (once written here, and pushed by a peer "Chairman" agent) was to configure the coder AFTER init via `client.postgrest.encoder/decoder.dateEncodingStrategy = .iso8601` — that ALSO fails in 2.53.0 because `SupabaseClient` has NO `postgrest` member (error: `has no member 'postgrest'`). CORRECT: just `client = SupabaseClient(supabaseURL:, supabaseKey:)` and call `client.from("table")...`; the Postgrest builder already uses an ISO-8601 JSON coder by default, so `Date` columns round-trip with NO manual coder config. Verified 2.53.0 signatures (fetched from GitHub raw source): `signUp` returns `AuthResponse` (`.session`/`.user`); `signIn` returns `Session`; `resendVerification` does NOT exist → use `client.auth.resend(email:type:)` with `ResendEmailType.signup` (NO `.verifyEmail` case); `resetPassword` → `resetPasswordForEmail(_:)`; Storage `upload(_:data:options:)` with `FileOptions(cacheControl:contentType:)` (cacheControl FIRST) and `getPublicURL(path:)` THROWS (wrap in `try`). See `references/supabase-swift-v2.md` for the full call table, the "fetch the real pinned SDK via curl" trick, the "file emptied → `git checkout HEAD -- <file>`" path, and the Xcode STALE-BUFFER trap (Discard Changes reverts to last COMMITTED version — commit before discarding or the same errors reappear).
- **Never apply another agent's full-file "corrected" paste blindly (cross-agent trap).** This session a peer agent ("Chairman") pasted a "v2-compatible" `SupabaseService.swift` that (a) DELETED 8 methods that 26 live call sites depended on, and (b) hardcoded the WRONG Supabase project URL (`merfmrlkjoqrhijzfwbn` vs the real `ooeowvbrexxoaleodfum`). Had it been applied it would have caused a 26-error regression + pointed the app at the wrong DB. Rule: when an agent says "replace the whole file," diff it against the real call sites and the real project config FIRST; keep every required method; never swap the project URL. Prefer a minimal surgical fix (e.g. only the v2 init block) over a full replacement. See `ai-coding-collaboration` for the reviewer discipline.
- Write the temp script to a `hermes-verify-*` path (the verification gate's expected
  prefix) and `rm` it after; do not `write_file` into `/private/var/folders/...`.

## Xcode phantom / stale build-error diagnosis (CLI agent CANNOT run the build)
When `swiftc -parse` is clean, every call site is verified present, and `git` shows the
file is correct on disk — but Xcode STILL reports an error, the CLI agent is flying blind.
This session burned many turns on exactly this. Use this diagnosis tree (in order):

1. **Confirm disk really is correct.** `git cat-file -p HEAD:<file> | cmp - <file>` →
   IDENTICAL means your committed version is what Xcode *should* compile. If DIFFERS,
   your edit didn't stick (the "file emptied in Xcode" case) → `git checkout HEAD -- <file>`
   and re-apply the minimal fix, then commit.
2. **Stale editor buffer (most common).** Xcode's open tab can hold an old buffer that
   predates your write. In Xcode: right-click the file → Source Control → **Discard
   Changes** (reverts the tab to the committed-correct version), or close + reopen the tab.
   Then Cmd+Shift+K → Cmd+B.
3. **`#Preview` mis-attribution (easy to miss).** A "Missing argument for parameter 'X' in
   call" attributed to `SomeView` is often NOT in the body — it's in the file's `#Preview`
   block, which instantiates the view with the OLD initializer signature. This session the
   error "Missing argument for ownerUID" pointed at `ShopOwnerDashboardView` and the cache
   mis-blamed the `saveShop` call site, but the REAL broken call was the `#Preview`:
   `ShopOwnerDashboardView(ownerEmail:"…", onSignOut:{})` ← missing `ownerUID:`. Grep the
   file for every initializer call (body AND `#Preview`) before concluding the caller is wrong.
4. **Multiple stale DerivedData caches (nuclear option).** After enough quit/reopen/index
   churn, Xcode can accumulate SEVERAL `DerivedData/AnglerGo-*` folders; the index resolves
   symbols from an old cache and the error never clears via steps 1–3. Cure:
   ```bash
   osascript -e 'quit app "Xcode"'      # must quit first — Xcode LOCKS the active folder
   sleep 2; pkill -f Xcode
   rm -rf ~/Library/Developer/Xcode/DerivedData/AnglerGo-*   # clears ALL of them
   ```
   Then reopen the project, let indexing FINISH (spinner gone), Cmd+Shift+K → Cmd+B. This
   was the actual fix for the persistent ownerUID error after steps 1–3 had failed.
5. **Only ⌘B is truth.** All of the above are heuristics; the CLI agent cannot link SPM
   packages. After the tree, the user's clean build is the final arbiter.

Trigger: the user pastes a build failure screenshot and you've already verified the code is
correct on disk. Do NOT keep re-editing correct files — diagnose the cache/preview first.

## Patterns that worked here (reuse)
- **Mirror existing Firestore code** for new collections: copy the project's `loadCatchesFromCloud()` snapshot-listener shape and `addCatch()` write shape rather than inventing new sync. Add `@Published var myX: [Model]`, `loadXFromCloud()` (guard writes with `isSignedIn`/uid), `saveX(_:)`, `deleteX(_:)`.
- **Make model `Codable`** when moving it to Firestore; if other code relied on the default memberwise initializer, add an explicit `init(...)` so call sites still compile.
- **`@EnvironmentObject` reuse**: a child view can read `@EnvironmentObject var appState` if an ancestor already injects it via `.environmentObject(...)` — no new plumbing needed.
- **Scope UI to a focused entity** with a toggle state (e.g. `focusedShopID`): filtering helpers (`focusedShops`, `slotsFor`, `dateHasAvailability`, `dateHasEvents`) all respect it; tapping the active chip again clears focus.
- **Xcode phantom errors — diagnose, don't re-edit correct code.** When `swiftc -parse` + on-disk git prove the code is right but Xcode still errors, the cause is almost always cache/preview, not your edit. Walk the 5-step "Xcode phantom / stale build-error diagnosis" tree above: confirm disk via `git cat-file -p HEAD:<f> | cmp - <f>`, discard/reopen the stale tab, grep the file's `#Preview` block for the missing-arg call (the ownerUID error this session was actually in `#Preview`, mis-blamed on `saveShop`), and if all else fails `rm -rf ~/Library/Developer/Xcode/DerivedData/AnglerGo-*` after quitting Xcode. See that tree for the exact commands.

## Support files
- `scripts/verify_swift_edits.py` — generic, re-runnable Swift-edit consistency + `swiftc -parse` checker. Copy into the project dir, run, `rm`.
- `scripts/fetch_supabase_sdk.sh` — fetches the ACTUAL pinned supabase-swift source from GitHub and greps the signatures you need (SupabaseClient members, AuthClient funcs, `ResendEmailType` cases, Storage upload/getPublicURL). Use this BEFORE editing any Supabase call so you verify against real signatures, not a peer's paste. `bash scripts/fetch_supabase_sdk.sh` auto-reads `Package.resolved` for the pin.
- `references/swift-verification.md` — exact command forms, the tool-quirk details, and a worked example of the trips to appState.myTrips refactor verification.
- `references/supabase-swift-v2.md` — supabase-swift v2 API changes (removed init form, AuthResponse return types, resend/reset renames, Storage upload signature, the `#Preview` mis-attribution, multi-DerivedData nuke) + recovery path when a file is emptied in Xcode.

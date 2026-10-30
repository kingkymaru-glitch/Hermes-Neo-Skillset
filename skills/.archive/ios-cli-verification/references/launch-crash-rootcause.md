# Launch crash / SIGSTOP root-cause checklist (iOS, no Xcode)

When the user reports "the app pauses at launch / mid-deploy" or "it crashes every time I
run it," treat it as a RUNTIME CRASH caught by LLDB — NOT a debugger fault. Do not disable
the debugger. Root-cause instead.

## 1. Get the real exception string (the only thing that ends the loop)
- Keep LLDB ON (Xcode ▸ Product ▸ Scheme ▸ Edit Scheme ▸ Run ▸ Info ▸ Debugger → LLDB).
- Run. When Xcode pauses, the console shows a red error + stack trace. Common shapes:
  - `Thread 1: signal SIGABRT` + `*** Terminating app due to uncaught exception`
    `NSInvalidArgumentException` / `unrecognized selector` — a bad API call / nil where an
    object was required.
  - `Fatal error: Index out of range` — an array subscript (`[0]`, `.first!`) on empty.
  - `Thread 1: EXC_BAD_ACCESS` — use-after-free / unretained delegate / mutating SwiftUI
    state from a non-main thread.
  - Firebase: `GoogleService-Info.plist ... could not be found` or
    `The default Firebase app has not been configured yet` — configure() not called first,
    or plist not bundled.
- If they only see a pause with no message: click Continue (►) in the debug bar (or type
  `continue` in lldb) a few times — the exception will surface.

## 2. Audit the launch path (read-only, you can't compile)
Order of execution at cold start:
  AppDelegate.didFinishLaunching → FirebaseApp.configure()
  → AppState.init() (auth listener) → Root view
  → if signed-in, MainTabView → FIRST TAB renders immediately.
Watch for:
- Firebase used before `FirebaseApp.configure()`.
- A persisted Firebase session flipping `isSignedIn` synchronously; any view that reads
  `Auth.auth().currentUser?.email` / `.uid` / Firestore on the FIRST render without a
  non-nil guard.
- The first tab (often a Map/MapKit view) doing an empty-array index, a `nil` decode, or a
  map-delegate callback that mutates `@State` from a background thread.

## 3. Cheap static probes (run before asking the user for the trace)
(a) Force-unwrap / force-cast scan — the usual launch-crash culprits:
    grep -rnE 'try!|as!|\bfatalError|\.first!|\.last!|\[0\]!' <root>
    Any hit on the launch path is suspect; make it safe (guard / if-let / optional chain).
(b) Bundle-ID + Google URL scheme consistency (silent Google-sign-in crash):
    - pbxproj PRODUCT_BUNDLE_IDENTIFIER  ==  GoogleService-Info.plist BUNDLE_ID
    - Info.plist CFBundleURLSchemes reversed-client-id == GoogleService-Info reversed id
(c) GoogleService-Info.plist is actually bundled — referenced in the pbxproj Resources /
    Copy Bundle Resources build phase.
(d) Cross-reference gate (scripts/hermes-verify-xref.sh) for used-but-undeclared members and
    duplicate top-level types. These produce a GREEN-build-blocker the user may describe as
    "it crashes at launch" when they mean "it won't compile."

## 4. Build error vs runtime crash — don't conflate
- Cmd+B FAILS → compile error. Paste the red error; usually `Cannot find X in scope`,
  `does not conform to protocol`, `invalid redeclaration`. Use xref gate + pbxproj checks.
- Cmd+B GREEN, dies at RUN → runtime crash. Get the exception text (step 1).
- Never report "fixed" for a runtime crash you have not actually reproduced/seen the trace for.

Reusable static probe script: scripts/hermes-verify-launch-path.sh <project-root>

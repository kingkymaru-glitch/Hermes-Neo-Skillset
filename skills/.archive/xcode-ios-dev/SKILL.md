---
name: xcode-ios-dev
description: iOS/SwiftUI dev collaboration model for users who build in Xcode themselves. Covers the tight edit → static-verify → user-feedback loop, the rule NOT to over-disclaim "I can't run Xcode", ad-hoc static verification patterns, and fixes for common launch/deploy crashes (SIGSTOP debugger pauses, corrupted SwiftUI modifiers, gradient background crashes). Load whenever editing .swift / .xcscheme / .xcbkptlist / .pbxproj in an Xcode project the user builds themselves.
---

# Xcode iOS / SwiftUI dev workflow

## When to use
The user owns the Xcode build (Cmd+B / Run) and pastes compiler/runtime errors back.
You edit source, scheme, or project files and the user re-simulates. This is the normal
loop — do NOT try to "finish" by compiling yourself (you can't here).

## Critical behavior rule
The user has explicitly said: do NOT repeatedly state "I can't run/test this, only Xcode can
simulate it." They know. State the Xcode-only caveat ONCE per session at most, then let your
static verification results speak. Never claim a green build.

## Collaboration loop (per turn)
1. Read the file(s) you must change. Always re-read the whole file before overwriting it —
   partial pagination views can hide corruption elsewhere.
2. Make the targeted fix (patch tool, not sed/echo).
3. Run ad-hoc static verification (see scripts/verify_swift.py and the pattern below).
4. Report: what broke, what you changed, and the one-line verification summary. No lecture.

## Ad-hoc static verification (no compiler available)
- **Brace/quote balance**: string-aware scan; a NEGATIVE depth dip means a syntax
  corruption (e.g. a SwiftUI modifier lost its opening `(`). See scripts/verify_swift.py.
- **Known corruption greps**: `.aler"` or `.aler ` instead of `.alert(`, stray chars inside
  a modifier call. These are how edits silently break a view.
- **plutil -lint** on .pbxproj / .xcscheme: OK = parseable. Ignore its
  "Encountered unknown tag Scheme/Bucket on line 2" quirk — that's expected for Xcode plists.
- Use an OS-safe tempfile with a `hermes-verify-` prefix for throwaway scripts, and clean it
  up after the run.

## Common crash fixes (this class)
### 1. SIGSTOP / app pauses mid-deploy
Cause: LLDB debugger attaches on launch and a breakpoint or signal halts the process.
Fix:
- In the .xcscheme, set `selectedDebuggerIdentifier = ""` in BOTH `<TestAction>` and
  `<LaunchAction>` (disables debugger attach = "Run Without Debugging").
- Reset `xcuserdata/<user>.xcuserdatad/xcdebugger/Breakpoints_v2.xcbkptlist` to an empty
  `<Bucket>` (no `<Breakpoint>` children).
- `launchStyle = "0"` should stay (auto-launch, not "wait for executable").
Reference recipe: references/sigstop-fix.md

### 2. Corrupted SwiftUI modifier (e.g. `.aler"` instead of `.alert(`)
Symptom: build pauses/crashes, or a view won't render. The brace-depth scan goes NEGATIVE
because the lost `(` leaves a `{` that closes an unopened block. Grep for `\.aler` and repair
to the full modifier. Verify depth returns to 0.

### 3. Gradient background crash on a themed view
If a theme-gradient `LinearGradient` introduced a crash, revert to a solid `Color(...)`
background that ignores safe area. Keep the view KISS — the theme color can live in cards/
accents instead of the full-bleed background.

## Xcode stale-buffer + Discard-Changes trap (cost many turns on AnglerGO)
When a fix "doesn't take" and the same errors reappear after quit/reopen/reindex, it's
almost always a STALE EDITOR BUFFER, not a code defect:
- "Source Control → Discard Changes" reverts the file to the LAST COMMITTED version. If
  your fix wasn't committed, the discard throws it away and Xcode rebuilds the broken
  committed version. Symptom: screenshot shows the OLD code even though you "fixed" it.
- Fix: COMMIT the correct edit first (so discard can't revert to broken); THEN tell the
  user to discard/reopen the tab so Xcode loads the committed-correct buffer.
- A "Missing argument for parameter 'X' in call" with a caller that clearly passes X
  usually means a STALE buffer of the CALLEE, not a real signature mismatch. Have the user
  discard/reopen the callee file, then Cmd+Shift+K → Cmd+B.
- When a file is emptied by "Select All + Delete" in Xcode, `git checkout HEAD -- <file>`
  recovers the last committed good version (the committed copy is intact even if the
  working file is 0 bytes).

## Never apply another agent's full-file "corrected" paste blindly
A peer ("Chairman") agent once pasted a "v2-compatible" `SupabaseService.swift` that
(a) DELETED 8 methods 26 live call sites depended on, and (b) hardcoded the WRONG
Supabase project URL. Applied, it would have caused a 26-error regression + pointed the
app at the wrong DB. Rule: when any agent says "replace the whole file," diff it against
the real call sites and real project config FIRST; keep every required method; never swap
the project URL. Prefer a minimal surgical fix. (Full supabase-swift v2 API facts +
the "fetch the real pinned SDK from GitHub" trick live in `swift-cli-ios-dev` →
`references/supabase-swift-v2.md`.)

## KISS/DRY before commit
Hold off linters/tests on creative UI work until the user likes the result or is about to
commit. Match surrounding code style. Keep it concise and elegant.

## Support files
- scripts/verify_swift.py — string-aware brace/quote balance + corruption grep for a .swift file.
- references/sigstop-fix.md — exact recipe to stop Xcode SIGSTOP pauses during deploy.

## Related skills
- xcode-pbxproj-safe-edit — for editing the project.pbxproj (wiring new files). Use it, do
  NOT hand-edit pbxproj with sed/Python string inserts.

# Stop Xcode SIGSTOP pauses during app deploy

## Symptom
App build/run keeps pausing at launch (mid-deploy). Xcode halts on a SIGSTOP as if a
breakpoint fired, but no visible breakpoint exists.

## Root cause
LLDB debugger attaches on launch. A saved breakpoint, an exception/signal breakpoint, or
"wait for executable" launch style sends SIGSTOP and halts the process.

## Fix
1. Edit the scheme (`.xcodeproj/xcshareddata/xcschemes/<Name>.xcscheme`):
   - Set `selectedDebuggerIdentifier = ""` in BOTH `<TestAction>` and `<LaunchAction>`.
     This detaches LLDB = same as Xcode's "Run Without Debugging". App still launches.
   - Keep `launchStyle = "0"` (auto-launch; do NOT set "1" = wait for executable).
2. Reset the per-user breakpoints list to an empty bucket:
   `.xcodeproj/xcuserdata/<user>.xcuserdatad/xcdebugger/Breakpoints_v2.xcbkptlist`
   should contain only `<Bucket ...></Bucket>` with no `<Breakpoint>` children.

## Re-enable later
Product ▸ Scheme ▸ Edit Scheme ▸ Run ▸ Info ▸ Debugger: LLDB.

## Verify (ad-hoc, no Xcode)
Grep the scheme for `selectedDebuggerIdentifier = ""` (expect ≥2). Confirm no
`<Breakpoint` element in the bkpt list. `launchStyle = "0"` present.

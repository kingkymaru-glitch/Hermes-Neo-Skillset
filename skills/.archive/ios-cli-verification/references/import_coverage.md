# Import-coverage check (missing-import detector)

`swiftc -parse` is SYNTAX-ONLY. It cannot detect a missing `import`. A file can parse
clean and still fail `Cmd+B` with:
`Property 'X' is not available due to missing import of defining module 'Y'`

This check catches that class of error from the CLI. Run it whenever you touch an
external module's API (Supabase, Combine, Firebase, etc.) in an iOS target.

## Shell one-liner (per module)
```bash
# Supabase: files that use the client API but don't import Supabase
grep -rL "^import Supabase" --include="*.swift" . \
  | xargs grep -l "client\.auth\|SupabaseClient\|SupabaseService\.shared\.client" 2>/dev/null
# empty output = covered; any listed path = MISSING IMPORT (real bug, not cache)

# Combine: ObservableObject / @Published without import Combine
grep -rL "^import Combine" --include="*.swift" . \
  | xargs grep -l "ObservableObject\|@Published" 2>/dev/null
```

## Rule of thumb
A "missing import of defining module" error is a CODE bug (missing `import`) by default.
Only fall back to the stale-Xcode-cache theory AFTER:
  1. confirming the import is actually present, AND
  2. the error survives a clean build (`rm -rf ~/Library/Developer/Xcode/DerivedData`,
     reopen, Cmd+Shift+K -> Cmd+B).
Defaulting to "cache" without checking imports hides real bugs and wastes round-trips.

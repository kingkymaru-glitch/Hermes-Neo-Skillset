# macOS Malloc Stack Logging — LUNASCAN Performance Killer

## Symptoms

- COLMAP subprocesses run EXTREMELY slowly (10-100x slower than normal)
- Console filled with malloc/free stack traces
- `MallocStackLogging` environment variable visible in process environment
- Memory-heavy operations (SfM, masking, video decode) become unusable

## Root cause

macOS has a debugging feature called Malloc Stack Logging. When enabled (via Xcode scheme, Instruments, or `launchctl setenv`), it logs every `malloc`/`free` call with a stack trace. This is catastrophic for memory-intensive C++ programs like COLMAP and Python image processing — the logging I/O dominates execution time.

The environment variables are:
- `MallocStackLogging=1` — basic logging
- `MallocStackLoggingNoCompact=1` — uncompacted logging (even worse)

These can be set system-wide via `launchctl setenv` and survive across reboots.

## How it gets enabled in the DMG app

The PyInstaller `--windowed` app bundle inherits environment from launchd. If `MallocStackLogging` was ever set via `launchctl setenv`, every child process (COLMAP, Python subprocesses) gets it — even if the user's current terminal doesn't show it.

## Fix applied to LUNASCAN

In `app/run.py` (the app's entry point), before any imports or GUI setup:

```python
import os

for _var in ("MallocStackLogging", "MallocStackLoggingNoCompact"):
    os.environ.pop(_var, None)
```

This strips the vars from the Python process's environment. Since `subprocess.run()` inherits the parent environment, all COLMAP subprocesses launched from the app will also be clean.

## How to clear it globally

```bash
# Check if set
launchctl getenv MallocStackLogging
launchctl getenv MallocStackLoggingNoCompact

# Clear (affects new processes from launchd; restart affected apps)
launchctl unsetenv MallocStackLogging
launchctl unsetenv MallocStackLoggingNoCompact
```

## How to verify the fix

```python
import os, subprocess

# Should be None/not set after run.py strips them
print(os.environ.get("MallocStackLogging"))  # None

# COLMAP should run at normal speed
result = subprocess.run(["colmap", "feature_extractor", "--help"], 
                       capture_output=True, text=True)
assert result.returncode == 0  # or 1 (help exit) — not killed/timed out
```

## Other macOS performance pitfalls

- **Font cache rebuilding:** Matplotlib rebuilds font cache on first import inside DMG — normal, one-time cost
- **Apple Silicon native vs Rosetta:** COLMAP installed via Homebrew is ARM-native. If COLMAP was built for x86_64, it runs under Rosetta 2 with ~30-50% performance penalty. Verify: `file /opt/homebrew/bin/colmap` should show `arm64`
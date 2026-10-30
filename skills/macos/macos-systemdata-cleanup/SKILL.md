---
name: macos-systemdata-cleanup
description: User says cleanup, free macOS System Data disk space.
---

# macOS System Data / Disk Cleanup

Trigger: user says "cleanup" or asks to free up System Data / disk space on their Mac.

## What "System Data" is
A catch-all bucket in About This Mac → Storage. It is NOT the OS — it's caches, app container data, Xcode sims/DerivedData, Docker VM, and temp. All reclaimable.

## STEP 1 — AUDIT (report numbers, do not delete yet)
Run these and show the user the breakdown:
```
df -h /System/Volumes/Data | grep -v Filesystem
du -sh ~/Library/Caches /Library/Caches ~/Library/Developer/Xcode/DerivedData ~/Library/Developer/CoreSimulator ~/Library/Containers /Library/Updates /private/var/folders 2>/dev/null
du -sh ~/Library/Containers/* 2>/dev/null | sort -rh | head -25
diskutil apfs list 2>/dev/null | grep -iE 'Capacity In Use By Volumes'
```
NOTE: `df /` reports the sealed SYSTEM volume (always ~11 GB) — use `/System/Volumes/Data` for the real data volume. Measure BEFORE and AFTER to report honest reclaimed GB.

## STEP 2 — SAFE CLEARS (always do these, no risk)
```
rm -rf ~/Library/Developer/Xcode/DerivedData            # regenerates
rm -rf ~/Library/Caches/*                              # apps rebuild; SIP-protected subdirs error "Operation not permitted" — ignore
sudo rm -rf /Library/Caches/*                          # system caches
xcrun simctl delete all                                # iOS simulators (only if user doesn't test in sim)
```
Some `~/Library/Caches/*` subdirs are SIP-protected (CloudKit, Safari, HomeKit, findmy.*, FamilyCircle, containermanagerd) — `rm` errors on them are expected, leave them.

## STEP 3 — BIG LEVERS (ask before deleting; user picks)
From the Containers audit, the usual outliers:
- `com.liuliu.draw-things` = Draw Things AI models (often 30+ GB). Quit app (`pkill -f 'Draw Things'`), then `rm -rf ~/Library/Containers/com.liuliu.draw-things`. A 36 KB `.com.apple.containermanagerd.metadata.plist` stub will refuse deletion (SIP) — normal, space is reclaimed.
- `com.docker.docker` = Docker VM disk (often 29 GB). If daemon is OFF: `rm -rf ~/Library/Containers/com.docker.docker` directly (Docker rebuilds empty on next launch). If daemon is UP: `docker system prune -a --volumes -f`. Always confirm with user before removing either container.

## DO NOT TOUCH (explain why)
- `/Library/Updates` — SIP-locked CLI Tools installers; even `sudo rm` refused ("Operation not permitted"). `softwareupdate --cleanup` deprecated/unavailable. Leave it. Normal (~1.8 GB).
- `/Library/Developer` simulators + `~/Library/Containers/com.apple.mediaanalysisd` (Photos face cache) — leave unless user insists.
- Never mass-`rm` all of `~/Library/Containers` — holds Mail, Messages, Notes. Only remove the specific large app container the user names.

## Pitfalls
- `rm -rf ~/Library/Caches/*` hitting SIP dirs prints "Operation not permitted" — NOT a failure, continue.
- Deletes of tens of GB exceed 60s default — run with timeout 180–300 or background. If exit 124 mid-run, re-run remaining `rm` lines (idempotent).
- Always re-measure `df -h /System/Volumes/Data` AFTER to report real reclaimed GB.

## Report format
State: data-volume in-use before → after (GB reclaimed), what cleared, what left (and why), remaining lever if any.

---
name: macos-disk-cleanup
description: Triage and free macOS "System Data" disk bloat safely.
---

# macOS System Data / Disk Cleanup

## Trigger
User reports: "System Data is X GB", "my disk is full", "why is my Mac using so much space", "free up space", "clear my caches/temp". Also a natural follow-up after killing a stuck app. Class-level — covers any macOS disk-triage session, not one specific machine.

## What "System Data" actually is
macOS Storage lumps everything that isn't Apps / Documents / Photos / Messages / Mail / Music / Trash into the grey "System Data" bucket. On a dev/creator machine it is overwhelmingly **reclaimable junk**:
- app + user caches
- iOS Simulator runtimes
- Xcode DerivedData
- Docker VM disk
- app Container data (incl. local AI model weights, e.g. Draw Things)

It is NOT the operating system. Almost all of it can be cleared without losing user files.

## HOW TO MEASURE (the part everyone gets wrong)
`df /` reports the **sealed system volume** — it always shows ~11 GB used and barely moves. To see the real number measure the data volume:
```
df -h /System/Volumes/Data
diskutil apfs list        # read the "Capacity In Use By Volumes" line
```
Enumerate culprits (sorted), then drill into Containers per-app:
```
du -sh ~/Library/Containers ~/Library/Caches /Library/Caches \
     /private/var/folders ~/Library/Developer/CoreSimulator \
     ~/Library/Developer/Xcode/DerivedData /Library/Updates 2>/dev/null
du -sh ~/Library/Containers/* 2>/dev/null | sort -rh | head -25
```
GUI cross-check:  → About This Mac → Storage (hover the grey bar).

## SAFE TO CLEAR (regenerates automatically, no user-data loss)
```
rm -rf ~/Library/Developer/Xcode/DerivedData     # ~6 GB
rm -rf ~/Library/Caches/*                         # ~19 GB; SIP-locked subdirs skip themselves
xcrun simctl delete all                           # iOS simulators, ~20 GB
sudo rm -rf /Library/Caches/*                     # ~4 GB
```
- **Docker** (daemon running): `docker system prune -a --volumes`. If Docker is OFF, the ~29 GB VM disk is at `~/Library/Containers/com.docker.docker` — `rm -rf` that dir; Docker rebuilds an empty one on next launch (no reinstall needed).
- **Draw Things** (local AI image gen): 32 GB of model weights live in `~/Library/Containers/com.liuliu.draw-things` — remove only when the app is not running (`pkill -f 'Draw Things'` first).

## SIP-PROTECTED — DO NOT FORCE
These refuse even `sudo rm` with "Operation not permitted" (System Integrity Protection). `softwareupdate --cleanup` is deprecated and won't help. Leave them; macOS reclaims the stubs over time. Do NOT suggest disabling SIP for these — not worth ~1.8 GB:
- `/Library/Updates` — leftover Command Line Tools installers (~1.8 GB). Normal, harmless.
- `~/Library/Caches/CloudKit`, `com.apple.Safari`, `com.apple.HomeKit`, `com.apple.findmy.*`, `FamilyCircle`
- `*.containermanagerd.metadata.plist` stubs (~36 KB) left after removing a Container — harmless leftover.

## PITFALLS
- Never report `df /` as the reclaimed number — that's the sealed system volume. Use `/System/Volumes/Data`.
- Bulk `rm -rf ~/Library/Containers` is dangerous (can wipe Mail/Photos app data and app settings). Target SPECIFIC large containers only, with explicit user consent. List them first, let the user pick.
- Recursive `rm` of tens of GB can exceed a 60 s tool timeout — raise `timeout=` (foreground max 600) or run `background=true`.
- After big clears, re-measure `/System/Volumes/Data` to report an honest before/after, not the estimate.

## REFERENCES
- references/system-data-breakdown.md — measured real-world profile + ready command recipes.

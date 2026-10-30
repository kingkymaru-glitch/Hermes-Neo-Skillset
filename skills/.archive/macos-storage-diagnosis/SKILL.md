---
name: macos-storage-diagnosis
description: Diagnose huge macOS System Data, safely reclaim disk space.
---

# macOS storage / "System Data" diagnosis

## Trigger
User says any of: "System Data is X GB", "why is my disk full", "how do I check storage usage", "what's eating my Mac", or asks to free up space. Also fires when About This Mac → Storage shows a large grey "System Data" bar.

## What "System Data" actually is
In  → About This Mac → Storage, "System Data" (older macOS called it "Other") is a CATCH-ALL bucket: everything that is NOT Apps, Documents, Photos, Messages, Mail, Music, or Trash. It is overwhelmingly caches, app container data, Docker/VM images, and iOS simulators — and nearly all of it is reclaimable. It is NOT the operating system, despite the ominous name.

The GUI Storage bar is slow and often inaccurate. Trust `du` for ground truth.

## Diagnostic recipe (fastest, one terminal block)
```
du -sh ~/Library/Containers ~/Library/Caches /Library/Caches /private/var/folders \
      ~/Library/Developer/CoreSimulator /Library/Developer \
      ~/Library/Developer/Xcode/DerivedData 2>/dev/null
```
Then capacity context:
```
df -h /
diskutil apfs list        # shows Capacity In Use / purgeable
tmutil listlocalsnapshots /   # local TM snapshots hide in System Data
```
For interactive, navigable exploration install ncdu: `brew install ncdu && sudo ncdu /`.

A full worked example with real measured numbers is in `references/diagnostic-recipe.md`.

## Typical culprits, largest first (on a dev Mac)
- `~/Library/Containers` — app data (Mail, Messages, misc app support). Usually the BIGGEST line. NEVER blanket-rm (holds real user data); only clear a specific subfolder when you know it is safe.
- Docker ( `~/Library/Containers/com.docker.docker` + image store ) — commonly 20–40 GB.
- iOS Simulator runtimes ( `~/Library/Developer/CoreSimulator` ) — 15–25 GB. Safe if you don't test in the simulator: `xcrun simctl delete all`.
- `~/Library/Caches` — safe, apps rebuild: `rm -rf ~/Library/Caches/*`.
- `/Library/Developer` — simulator/SDK installs. Safe if no simulator need.
- `/private/var/folders` — temp/session files. Safe, macOS rebuilds.
- Xcode DerivedData ( `~/Library/Developer/Xcode/DerivedData` ) — safe, regenerates: `rm -rf ~/Library/Developer/Xcode/DerivedData`.
- `/Library/Updates` — leftover software-update payloads. Safe to clear.
- swap + Logs — minor.

## Safe immediate wins (regenerate, will not break anything)
```
rm -rf ~/Library/Developer/Xcode/DerivedData
rm -rf ~/Library/Caches/*
xcrun simctl delete all
# Docker — ONLY if the user is not using it:
docker system prune -a --volumes
```
On a typical dev Mac this returns ~80 GB before you touch Containers or Docker images.

## Pitfalls
- Do NOT `rm -rf ~/Library/Containers` — that wipes Mail/Photos/iCloud app data. Clear specific subfolders only, with confirmation.
- `docker system prune -a --volumes` DESTROYS all images and volumes. Confirm Docker is unused first; offer to quit Docker and remove just its container dir instead.
- Local Time Machine snapshots count as System Data and auto-purged as space is needed; `tmutil listlocalsnapshots /` tells you if they are present.
- Always confirm destructive clears (Docker, Containers) with the user before running. Caches/DerivedData/Simulator are safe to clear without asking.

## Verify after cleanup
`df -h /` should show more Avail. Re-open  → About This Mac → Storage to confirm the System Data bar shrank (may take a minute to recompute).

# Photogrammetry intake — RealityScan-style scan → MARU GLB

User asks to "install RealityScan" to feed scanned 3D models into the digital twin.
RealityScan (Epic / Capturing Reality) desktop is **Windows + NVIDIA-CUDA only**; it
cannot run on this Apple-Silicon Mac. Before failing an install, diagnose and offer a
route that actually works. The scan's output is a `.glb`/`.usdz` — which then flows
into MARU via the GLB-intake recipes in this skill.

## Environment reality-check first (cheap, always do it)
- `sw_vers` / `uname -m` → confirm macOS arm64 (no NVIDIA).
- `brew search --casks realityscan` → empty (not on Homebrew).
- `ls ~/Downloads` → user may already hold scan assets. In this project we found
  `riscan_pro_2` / `riscan_pro_2-2` = **RiSCAN PRO by RIEGL** (terrestrial laser
  scanner software), a DIFFERENT product from RealityScan, also Windows `.exe`
  (`SetupRiSCAN_PRO.exe`, per its ReadMe.txt). Do not conflate them; neither runs on macOS.
- `xcrun --show-sdk-path` + `find <SDK> -iname "ObjectCapture.framework"` → Apple's
  native RealityKit Object Capture is NOT in the base SDK on this box (ships as a
  separate App Store / Reality Composer Pro component requiring Apple-ID sign-in).
  `realitytool` exists under Xcode usr/bin but is for reality file conversion, not capture.

## Decision tree (present to user; don't silently pick)
1. **RealityScan on the S22 Ultra (recommended when fidelity-to-request matters).**
   Mobile app; S22 is the project's target device. Capture on phone → export model →
   we wire import into MARU. Agent can't push apps to the phone; prepare MARU's
   ingestion side and give tap-by-tap steps.
2. **Native macOS alternative — Apple Object Capture / Polycam.**
   Runs on this Mac, exports GLB, no Windows. Needs the App Store component + user
   sign-in (don't log into Apple account unattended). Once present, script
   photo-folder → GLB → MARU.
3. **Windows VM (Parallels/UTM).** Real RealityScan desktop, but GPU is virtualized →
   slow on large scans. Only if user already has a Windows ISO + VM tool.
4. **Fetch/hold installer for inspection** (won't run here).

## Hard rule
Never claim "RealityScan installed" on macOS. If the user wants the desktop app, the
answer is a non-macOS route. Capture the scan on a capable device, bring the GLB home,
then use the desktop-intake / pin-iframe-3d-viewer recipes to land it in MARU.

## MARU ingestion pointer
Once you have a `.glb`: strip spaces from filename → `public/assets/` → reference
`/assets/<name>` → verify it serves → prefer pin + sandboxed-iframe flyout
(`references/pin-iframe-3d-viewer.md`), NOT in-globe (heavy GLB crashes the renderer).

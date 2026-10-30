---
name: xcode-prototype-packaging
title: Xcode Prototype Packaging
description: |
  Turn an HTML/CSS/JS prototype into a functional iOS app using Xcode. Includes folder scaffolding, WebView integration, asset handling, Firebase configuration, bundle identifier updates, and build‑ready project generation.
version: 1.0
---

## Overview
This skill outlines the end‑to‑end workflow for converting a static web prototype (HTML file) located in a `PROTOTYPE` directory into a complete Xcode project that can be launched as an Alpha test.

### Prerequisites
- macOS with Xcode installed.
- Access to the `AnglerGO` codebase (framework files, Swift source, Firebase config).
- The HTML prototype file (e.g., `anglergo_ui_ux_interactive_prototype-8.html`).
- A valid Apple developer team (for signing) and Firebase project (optional).

## Step‑by‑Step Procedure
1. **Create a new Xcode project folder**
   ```bash
   mkdir -p "$HOME/Desktop/PROTOTYPE/AlphaTest"
   cd "$HOME/Desktop/PROTOTYPE/AlphaTest"
   # Use the Xcode GUI or the `xcodeproj` command to generate a SwiftUI iOS app skeleton
   ```
   The skill prefers the manual `xcodeproj` creation via the GUI because it ensures proper signing files; the script can be used for automation.

2. **Copy framework source**
   ```bash
   cp -R "$HOME/Desktop/AnglerGO" ./AnglerGoFramework
   ```
   Keep the folder structure (`App/`, `Core/`, etc.) intact.

3. **Add a WebView wrapper**
   - Create `Shared/Views/PrototypeWebView.swift` containing a `WKWebView` that loads the local HTML file at runtime.
   - Register the view in `MainTabView.swift` (or a dedicated tab) so the prototype is reachable from the app.

4. **Integrate the HTML prototype**
   - Copy the HTML file and any assets (CSS, images, JS) into the Xcode project’s `Resources` folder.
   - Mark them as *Copy Bundle Resources* in the target’s Build Phases.

5. **Update bundle identifier**
   - Open the generated `.pbxproj` and replace the default identifier with the professional format `com.kamarulhk.anglergo` (or any user‑specified value).
   - Use the `patch` tool for a reliable replace‑all operation.

6. **Configure Firebase / Google Sign‑In**
   - Place `GoogleService‑Info.plist` in the project root.
   - Ensure URL schemes from `Info.plist` match the Firebase client ID.
   - Add required keys (`CFBundleURLTypes`, usage descriptions) if missing.

7. **Add necessary permissions**
   - Camera, Location, and any other usage strings should already be present in `Info.plist`; verify them.

8. **Finalize project settings**
   - Set *Deployment Target* (e.g., iOS 16).
   - Choose *Swift Language Version* (currently Swift 6).
   - Enable *Automatic Signing* or select a provisioning profile.

9. **Build & Run**
   ```bash
   open "AlphaTest/AnglerGo.xcodeproj"
   # In Xcode: Product → Build (⌘B) then Run on a simulator/device.
   ```
   Verify the prototype tab loads the HTML correctly.

## Pitfalls & Workarounds
- **Missing assets** – Xcode will silently ignore files not added to *Copy Bundle Resources*. After copying assets, always check the Build Phases.
- **Bundle identifier mismatch** – The identifier is stored both in the `.pbxproj` and may appear in `Info.plist` if manually edited. Always run the `patch` replace‑all on the `.pbxproj` and double‑check the Xcode UI.
- **WebView security** – Local file loading requires `allowFileAccessFromFileURLs` on the `WKWebView` configuration.
- **Firebase config** – Using a placeholder `GoogleService‑Info.plist` will cause runtime crashes when the app attempts to initialise Firebase. Ensure the correct file from the Firebase console is present before building.

## References
- `references/xcode_prototype_packaging.md` – detailed command log and folder tree produced during the last session.
- `templates/PrototypeWebView.swift` – starter implementation of the WebView wrapper.
- `scripts/create_xcode_project.sh` – reproducible script that scaffolds the project from scratch.

---
*Maintained for user Kamarul HK – reflects the preferred concise style and the class‑level workflow for turning HTML prototypes into launchable Xcode apps.*
---
name: ios-xcode-prototype-packaging
title: Packaging UI/UX Prototype into Xcode for Alpha Testing
description: |
  Guidance for turning a web‑based UI prototype (HTML/CSS/JS) into a lean, professional Xcode project ready for alpha testing on iOS. Covers folder layout, Xcode project creation, asset integration, Firebase setup, and common pitfalls.
tags: [iOS, Xcode, prototype, packaging, alpha-test, SwiftUI, Firebase]
---

## Overview
This skill provides a repeatable workflow to convert a static HTML prototype (e.g., `anglergo_ui_ux_interactive_prototype-8.html`) into a full‑stack iOS app scaffold using Xcode. It is useful when the backend already exists (see the **AnglerGO** codebase) and you need a quick, maintainable entry point for UI/UX testers.

## When to Use
- You have an HTML prototype that demonstrates the desired UI flow.
- A Swift/SwiftUI codebase (AnglerGO) already contains data models, services, and Firebase integration.
- You want a minimal Xcode project that imports the existing Swift modules and serves the prototype as a WebView or native views.

## Prerequisites
1. macOS with Xcode 15+ installed.
2. The **AnglerGO** repository cloned on the same machine (e.g., `~/Desktop/AnglerGO`).
3. A valid `GoogleService-Info.plist` for the target Firebase project.
4. Basic familiarity with Swift Package Manager (SPM) and Xcode project settings.

## Step‑by‑Step Procedure

### 1. Create a Dedicated Alpha‑Test Directory
```bash
mkdir -p ~/Desktop/PROTOTYPE/AlphaTest
cd ~/Desktop/PROTOTYPE/AlphaTest
```
> **Why:** Keeps the prototype isolated from the main repo while allowing easy removal after the test.

### 2. Initialise a New Xcode Project
1. Open Xcode → *File → New → Project*.
2. Choose **App** (SwiftUI) → *Next*.
3. Set **Product Name**: `AnglerGoPrototype`.
4. Set **Interface**: *SwiftUI*, **Language**: *Swift*.
5. Uncheck *Use Core Data* and *Include Tests* for a lean package.
6. Choose the folder created above as the location and **Create Git repository** if you want versioning.

### 3. Add Existing Source Files
```bash
# Assuming you are still in AlphaTest directory
cp -R ~/Desktop/AnglerGO/AnglerGo/Shared ./Shared
cp -R ~/Desktop/AnglerGO/AnglerGo/Core ./Core
cp -R ~/Desktop/AnglerGO/AnglerGo/Features ./Features
cp ~/Desktop/AnglerGO/AnglerGo/App/AnglerGoApp.swift ./
```
> **Pitfall:** Preserve the folder hierarchy; Xcode relies on relative import paths.

### 4. Integrate the HTML Prototype
1. Create a new SwiftUI view `PrototypeWebView.swift`:
```swift
import SwiftUI
import WebKit

struct PrototypeWebView: UIViewRepresentable {
    let url: URL
    func makeUIView(context: Context) -> WKWebView { WKWebView() }
    func updateUIView(_ uiView: WKWebView, context: Context) {
        uiView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
    }
}
```
2. Place the prototype file in the project:
```bash
cp ~/Desktop/PROTOTYPE/anglergo_ui_ux_interactive_prototype-8.html ./Resources/
```
3. Add `Resources` folder to Xcode (drag‑and‑drop → *Create folder references*).
4. Update `AnglerGoApp.swift` to launch the web view for alpha builds:
```swift
#if DEBUG
    ContentView()
#else
    MainTabView()
#endif
```
5. In `ContentView.swift` replace the body with:
```swift
PrototypeWebView(url: Bundle.main.url(forResource: "anglergo_ui_ux_interactive_prototype-8", withExtension: "html")!)
```
> **Pitfall:** Ensure the file is part of the *Copy Bundle Resources* build phase.

### 5. Configure Firebase (if the backend uses it)
- Drag `GoogleService-Info.plist` from the AnglerGO repo into the Xcode project (replace any existing one).
- In **Build Settings**, set `OTHER_SWIFT_FLAGS` to `-DPRODUCTION` for release and leave it empty for debug.
- Verify the `FirebaseApp.configure()` call exists in `AppDelegate` or `AnglerGoApp`.

### 6. Adjust Build Settings for a Lean Binary
| Setting | Recommended Value |
|---|---|
| **Enable Bitcode** | **No** |
| **Strip Linked Product** | **Yes** |
| **Dead Code Stripping** | **Yes** |
| **Swift Optimization Level** | **-Osize** (Release) |
| **Enable Testability** | **No** (Release) |

### 7. Run & Validate
```bash
xcodebuild -scheme AnglerGoPrototype -configuration Debug clean build
```
or simply press **⌘R** in Xcode.
- Verify the prototype loads in the simulator.
- Check that backend calls (e.g., inventory API) succeed; adjust `AppState` base URL if needed.

### 8. Package for Alpha Testers
1. In Xcode, select **Product → Archive**.
2. Open **Organizer**, choose the archive, and click **Distribute App → Ad Hoc** to generate an `.ipa`.
3. Share the `.ipa` via TestFlight, Firebase App Distribution, or a direct link.

## Common Pitfalls & Work‑arounds
- **Missing asset permissions** – Add `NSAppTransportSecurity` entry in `Info.plist` if loading remote resources.
- **WebView sandbox restrictions** – Use `allowFileAccessFromFileURLs = true` on the `WKWebView` configuration when the prototype loads local resources.
- **Firebase duplicate initialization** – Ensure only one `FirebaseApp.configure()` call exists (guard with `if FirebaseApp.app() == nil`).
- **Swift package conflicts** – If the main AnglerGO project uses SPM, add the same `Package.swift` to the prototype project or import the `.xcodeproj` as a sub‑project.

## References
- `references/xcode_project_setup.md` – detailed Xcode UI steps.
- `references/firebase_integration.md` – quick checklist for Firebase.
- `templates/PrototypeWebView.swift` – starter SwiftUI WebView implementation.
- `scripts/validate_build.sh` – script that runs `xcodebuild` and exits non‑zero on warnings.

---
*Maintained by the UI/UX & Full‑Stack Dev team. Update this skill when new Xcode versions change project templates or when the backend API contract evolves.*
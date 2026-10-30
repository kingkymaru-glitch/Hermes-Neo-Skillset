# Flutter toolchain on macOS (Sequoia/Tahoe, Apple Silicon)

Verified while building SkyPin on MARU's Mac. The environment had Android SDK + Xcode
but NO Flutter, NO JDK, and a CORRUPT NDK.

## 1. Flutter SDK
```bash
cd ~ && mkdir -p development && cd development
# download stable macos arm64 zip from storage.googleapis.com/flutter_infra_release/...
unzip -q flutter.zip -d flutter
# NOTE: the zip nests flutter/flutter/ — the binary is at:
#   ~/development/flutter/flutter/bin/flutter
~/development/flutter/flutter/bin/flutter --version
```

## 2. JDK 17 (Gradle 8.x REQUIRES Java 17 — "Unable to locate a Java Runtime" without it)
```bash
brew install openjdk@17
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
```

## 3. NDK — fix the corrupt/missing source.properties case
Symptom: `NDK at ~/Library/Android/sdk/ndk/26.3.11579264 did not have a source.properties file`.
```bash
rm -rf ~/Library/Android/sdk/ndk/26.3.11579264
~/Library/Android/sdk/cmdline-tools/latest/bin/sdkmanager "ndk;26.3.11579264"
# verify:
ls ~/Library/Android/sdk/ndk/26.3.11579264/source.properties && echo NDK_OK
```
The download is large — run it in the background (terminal background=true, notify_on_complete)
so it isn't killed by the foreground command timeout.

## 4. Generate native wrappers (do this AFTER writing lib/)
```bash
cd <project>/app
~/development/flutter/flutter/bin/flutter create --platforms=android,ios .
# keeps your lib/ + pubspec; regenerates android/ ios/ with gradle + MainActivity
```
Then re-apply permissions:
- AndroidManifest.xml: INTERNET, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION, CAMERA.
- ios/Runner/Info.plist: NSCameraUsageDescription, NSLocationWhenInUseUsageDescription,
  NSLocationAlwaysAndWhenInUseUsageDescription.

## 5. Build
```bash
# with JAVA_HOME exported
flutter pub get
flutter analyze            # must be 0 errors
flutter build apk --release   # emits installable .apk (side-load for testing)
flutter build ios             # needs Apple Dev $99/yr + real device
flutter build web              # browser view-only viewer (serve, link /room/<token>)
```

## Gotchas
- `flutter analyze` clean does NOT mean the APK builds — the build needs JDK17 + valid NDK.
- First `flutter build apk` downloads the Gradle wrapper + compiles; can exceed 7 min.
  Run in background with notify_on_complete, not foreground (420s timeout kills it).
- Screen files in `lib/screens/` must import siblings with `../` prefix.

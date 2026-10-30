# ar_flutter_plugin 0.7.3 — modern toolchain patches (Flutter 3.29.x / AGP8 / NDK27)

These are the exact edits that make the cached plugin compile. Paths are inside
`~/.pub-cache/hosted/pub.dev/ar_flutter_plugin-0.7.3/`.

## 1. Plugin Android build (android/build.gradle)
- Add `namespace "com.example.ar_flutter_plugin"` at top of `android { }`.
- `com.android.tools.build:gradle` -> `8.1.0` (AGP8).
- Kotlin -> `1.9.22`.
- Repositories: remove `jcenter()` (dead), keep/use `mavenCentral()`.
- `compileSdkVersion` -> `34`, `minSdkVersion` -> `21` (no `targetSdk` needed).

## 2. Plugin manifest (android/src/main/AndroidManifest.xml)
- Delete the `package="com.example.ar_flutter_plugin"` attribute (merger
  conflict with the namespace; build fails otherwise).

## 3. permission_handler_android (v11.x cached)
In `android/src/main/java/com/BasePermissionMessenger.java` (and any
`PluginRegistry.Registrar` usage):
- Remove the v1 `registerWith(Registrar registrar)` method — under Flutter 3.29
  the `PluginRegistry`/`Registrar` types no longer exist and the file fails to
  compile.
- Remove the now-unused `private PluginRegistry.Registrar pluginRegistrar;`
  field and any assignment to it.
- Keep only the v2 `onAttachedToEngine` / `onDetachedFromEngine` path.

## 4. App-level pubspec.yaml
Real dependency (not just override):
```
  permission_handler: ^11.0.0
dependency_overrides:
  permission_handler_android: ^11.0.0   # plugin hard-pins ^10 which won't compile
```

## 5. App android/app/build.gradle
```
android {
  namespace "<yourapp.pkg>"
  compileSdk 34
  defaultConfig { minSdk 24 }   // ARCore requires 24
  ndkVersion "27.0.12077973"
  buildTypes {
    release {
      minifyEnabled false
      shrinkResources false   // R8 drops com.google.ar.sceneform.* -> build dies
    }
  }
}
```

## 6. Environment (bash before build)
```
export PATH="$HOME/development/flutter/flutter/bin:$PATH"
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export ANDROID_NDK_HOME="$HOME/Library/Android/sdk/ndk/27.0.12077973"
```

## Verify
`flutter analyze` -> 0 errors ; `flutter build apk --release` -> APK produced.

# Swapping ar_flutter_plugin → ar_flutter_plugin_plus (fixes ARCore crash on Android 16)

Verified working fix for the SkyPin V0.17 crash on a Samsung S22 / Android 16. This is the
durable fix for the "Sceneform / destroyed VertexBuffer / ARCore FatalException" family of
crashes that no Dart-side patch can fix.

## Why the old plugin crashes
`ar_flutter_plugin` 0.7.3 is unmaintained and bundles **deprecated Sceneform**. On Android 16
and modern Samsung devices the native frame loop throws:
```
com.google.ar.core.exceptions.FatalException
    at Session.update → ArSceneView.onBeginFrame → doFrame
```
This is a NATIVE crash: a Dart try/catch cannot catch it, and the process dies on the first
bad frame. Dart-side lifecycle/rebuild patches help but never fix it — the engine itself is
incompatible.

## The fix: swap to ar_flutter_plugin_plus
`ar_flutter_plugin_plus` is the maintained fork and uses **Filament instead of Sceneform** —
the exact crash source is gone. API is near-identical (ARView, ARSessionManager/ARObjectManager/
ARAnchorManager/ARLocationManager, ARNode, addNode/removeNode).

### 1. pubspec.yaml
- `ar_flutter_plugin_plus: ^1.1.3`
- remove `ar_flutter_plugin` and any old pins for it.
- dependency_override needed:
  ```yaml
  dependency_overrides:
    vector_math: 2.2.0
  ```
  (The plugin declares `vector_math: ^2.2.0`, which on an older Flutter SDK resolves to a
  Dart 3.10+ build → pin 2.2.0 so it compiles on Flutter 3.29/Dart 3.7.)

### 2. android/settings.gradle.kts — bump Kotlin to 2.2.0
ARCore 1.52 native is compiled with Kotlin 2.x. With the old Kotlin 1.8.22 you get:
```
Error property type is Error Type for 'value' of 'kotlinx.coroutines.CoroutineScope'
incompatible types: TrackingState ...
```
i.e. a "Internal compiler error" / "Error type" / incompatible-enum failure. Bump:
```kotlin
id("org.jetbrains.kotlin.android") version "2.2.0" apply false
```
Matching the transitive Kotlin stdlib the plugin pulls. (2.0.21 still mismatches → 2.2.0.)

### 3. Dart — required API change
The plus fork requires the object manager to be initialized. `_onArCreated` must be async and
await it:
```dart
Future<void> _onArCreated(ARSessionManager s, ARObjectManager o,
    ARAnchorManager a, ARLocationManager l) async {
  ...
  await o.onInitialize();
  ...
}
```

### 4. Build env
- geolocator ^14, permission_handler ^12 (the fork uses these; drop the old ^11 shim override).
- Everything else (stable-key ArView, 10s re-place throttle) stays the same.

## Other AR crash causes that compounded it (all fixed in SkyPin)
- **Black screen** in the AR view → disable Impeller (Vulkan conflicts with AR's GL engine).
  AndroidManifest.xml:
  ```xml
  <application ... android:name="io.flutter.app.FlutterApplication">
    <meta-data android:name="io.flutter.embedding.android.EnableImpeller"
               android:value="false"/>
  </application>
  ```
- **Lifecycle crash (self-inflicted):** disposing the AR session on `inactive`/`paused` is
  WRONG — those fire constantly (share sheet, dialog, notification) → ARCore FatalException on
  the next frame. Only release the session on `detached` (true process kill).
- **Flicker / "destroyed VertexBuffer":** re-placing nodes on every GPS tick — heading jitter
  makes a `turned > 5°` check always true, so it re-places every frame. Fix: a HARD 10s minimum
  between placements (deploy once, then only every 10s), and keep the ArView permanently
  mounted with a stable key (`Offstage` to hide it) so the native AR session is never recreated
  across widget rebuilds.

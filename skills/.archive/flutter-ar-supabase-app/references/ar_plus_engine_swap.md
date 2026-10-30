# ar_flutter_plugin_plus engine swap (Sceneform → Filament)

Why: stock `ar_flutter_plugin 0.7.3` bundles Google's deprecated Sceneform. On
Android 16 / Samsung S22 it throws a NATIVE crash in the frame loop:

```
com.google.ar.core.exceptions.FatalException
  at com.google.ar.core.Session.update
  at ...ArSceneView.onBeginFrame
  at Choreographer.doFrame
```

This is not catchable in Dart (native throw kills the process). Dart-side
mitigations — stable `Key` + `Offstage` keep-alive, placement throttle
(move >3m / turn >5° / ≥1.5s), not disposing on `inactive` — each reduce it but
do NOT eliminate it. Diagnosis: don't keep patching Dart; swap the engine.

## The swap
1. `pubspec.yaml`:
   - `ar_flutter_plugin: ^0.7.3` → `ar_flutter_plugin_plus: ^1.1.3`
   - `geolocator: ^14.0.2` (was ^9), `permission_handler: ^12.0.1` (was ^11)
   - add `dependency_overrides: vector_math: 2.2.0`  (EXACT, not ^2.2.0 —
     `^2.2.0` resolves to 2.4.2 which needs Dart 3.10 > your Flutter 3.7:
     "The language version 3.10 specified for the package 'vector_math' is too
     high. The highest supported language version is 3.7.")
2. `android/settings.gradle.kts`: `org.jetbrains.kotlin.android` 1.8.22 → **2.2.0**.
   A 1.8.x/2.0.x compiler fails against ARCore 1.52 enum metadata:
   - `internal compiler error ... FirIncompatibleClassExpressionChecker ... source must not be null`
   - `Module was compiled with an incompatible version of Kotlin. binary version ... 2.2.0, expected ... 2.0.0`
   (the transitive kotlin-stdlib resolves to 2.2.0, so the compiler must match).
3. Imports: `package:ar_flutter_plugin/...` → `package:ar_flutter_plugin_plus/...`.
   `hittest_result_types.dart` import is GONE in the plus fork.
4. `ARObjectManager.onInitialize()` is REQUIRED before any `addNode` — without it
   `addNode` silently fails and the beam never renders. Call it in the
   `onARViewCreated` callback; make that callback `async`.
5. Old AGP8 shim hacks (permission_handler hard-pin overrides, patched plugin
   build.gradle, jcenter→mavenCentral) are no longer needed — the fork uses
   modern deps. You can drop the `dependency_overrides: permission_handler*`.

Verified working build env for the plus fork (2026): Flutter 3.29.3, JDK 17,
NDK 27.0.12077973, Kotlin 2.2.0, AGP 8.7.0, Gradle 8.10.2.

## Version facts (ar_flutter_plugin_plus)
- 6 versions, newest 1.1.3 published 2026-01-28, active repo (Feb 2026 commits).
- Uses ARCore 1.52.0 + Filament 1.68.4 + gltfio (no Sceneform/SceneView).
- Requires geolocator ^14, permission_handler ^12, vector_math ^2.2.0.
- Near-identical Dart API to stock (same ARSessionManager/ARObjectManager/
  ARAnchorManager/ARLocationManager/ARNode), so the swap is localized to
  `ar_view.dart` + pubspec + gradle.

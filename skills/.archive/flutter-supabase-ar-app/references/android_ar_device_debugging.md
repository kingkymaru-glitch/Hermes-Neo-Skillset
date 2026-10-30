# Android device-level debugging for ar_flutter_plugin + location AR

Born from SkyPin V0.06–V0.11 on a Galaxy S22 (SM-S908E, Android 16). These are the
real-device diagnostics that found root causes a desktop build could not.

## The professional loop (use this instead of guessing)
1. Instrument the app: `debugPrint('[SKYPIN] ...')` at every decision point (permission
   status, location-service state, GPS stream event, every error).
2. Install on a USB-connected device with USB debugging on.
3. Read real logcat — do NOT ask the user what they see.
4. Split the question: does the DEVICE have a fix, or is the APP not receiving one?

## Build + install for diagnostics
- `debugPrint` is stripped in `flutter build apk --release`. To see it in logcat you MUST
  build a debug APK (`flutter build apk --debug`) OR use `print()`. An empty logcat from a
  release build proves nothing.
- Install/replace cleanly; a same-version `adb install -r` can silently not take. If
  `adb shell pm path <pkg>` returns empty despite "Success", do `adb uninstall` then
  `adb install` fresh.

## Read the right logs (filter the noise)
Samsung/Android logcat is dominated by system chatter (GOS, Finsky, WeChat, minksocket,
lmkd). Filter to the app process:
```
adb shell pidof com.example.skypin            # -> PID
adb logcat -d --pid=<PID>                      # app-process logs only
adb logcat -c                                  # clear before a run
```
To see whether the PHONE itself has a fix (independent of the app):
```
adb shell dumpsys location | grep -iE "last location|provider"
adb shell settings get secure location_mode   # 3=high accuracy, 1=sensors, 0=off
```
A `last location=network ... hAcc=16m` in dumpsys while the app still shows no GPS = the
device is locatable and the BUG IS IN THE APP (usually: app only waits on the throttled
stream and never reads the cached fix).

## Signature log lines and what they mean
- `Unable to open libpenguin.so` → BENIGN Samsung noise, not ar_flutter_plugin (which ships
  `libarsceneview_jni.so` / `libarcore_sdk_jni.so` / `libfilament-jni.so`).
- `Using the Impeller rendering backend (Vulkan)` then
  `Gralloc4: isSupported(...) failed with 5` / `qdgralloc: gralloc failed to allocate` /
  `AHardwareBuffer: GraphicBuffer(...) failed` → **Impeller/Vulkan conflicts with the
  plugin's OpenGL ES/Sceneform engine → black camera screen**. Fix: disable Impeller in
  AndroidManifest.xml:
  ```xml
  <application ...>
    <meta-data android:name="io.flutter.embedding.android.EnableImpeller" android:value="false"/>
  </application>
  ```
  Verify it took by grepping logcat for `AdrenoGLES` (OpenGL) instead of `Impeller`.
- `(REDACTED) stationary throttling engaged` / `location delivery to X blocked - too close`
  → Samsung FusedLocation is power-throttling high-frequency GPS. Location AR apps must not
  rely on a continuous streaming fix.
- `Choreographer: Skipped N frames` → UI jank from removeNode+addNode churn every GPS tick,
  not a hard ANR (app stays topResumedActivity and responsive).

## geolocator pitfalls that bite
- `getPositionStream(locationSettings: LocationSettings(timeLimit: ...))` THROWS an
  unhandled `TimeoutException` that KILLS the whole stream when the first fix is slow
  (`FlutterGeolocator: Geolocator position updates stopped`). Remove `timeLimit` from the
  stream so it survives delays.
- `Geolocator.getLastKnownPosition()` returns the cached network/GPS fix instantly and works
  indoors / when the stream is throttled. Call it alongside `getCurrentPosition()` — this is
  how Google Maps feels instant. This is the single highest-value fix for "no GPS" on a
  device that dumpsys says is locatable.
- `getCurrentPosition(desiredAccuracy: low, timeLimit: ~6-12s)` with a `getLastKnownPosition`
  fallback in the catch is the reliable "go to my location" pattern.

## Flutter-state trap that looks like a device bug
A StatelessWidget reading provider state (`room.gpsWaiting` / `room.gpsError`) in `build()`
but WITHOUT `context.watch<RoomProvider>()` renders once and never rebuilds — a permanently
frozen spinner even when the provider logic is correct. Always watch the provider at the top
of `build()`.

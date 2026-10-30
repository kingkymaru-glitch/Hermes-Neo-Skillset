# Geolocator stream `timeLimit` kills the stream + Samsung GPS throttling (SkyPin V0.07–0.08)

Durable lessons from the "GPS never fixes on a physical S22" debugging stretch,
after the Impeller black-screen and frozen-widget bugs were already solved.

## geolocator stream `timeLimit` = the stream dies
Putting a `timeLimit` on `Geolocator.getPositionStream(...)` does NOT make it
fail gracefully — it THROWS a `TimeoutException` that terminates the entire
stream. When Android delays the first fix (throttling), the app logs:
```
[SKYPIN] GPS stream ERROR: TimeoutException ... Time limit reached while waiting for position update.
Unhandled Exception: TimeoutException ... Time limit reached while waiting for position update.
FlutterGeolocator: Geolocator position updates stopped   # stream is DEAD
```
`Geolocator.getCurrentPosition(...)` (the one-shot) accepts `timeLimit` safely
because you `await` it inside a try/catch. The STREAM does not — `timeLimit` is
the parameter that kills it.

FIX: do NOT pass `timeLimit` to `getPositionStream`. Keep the stream running
indefinitely (`distanceFilter: 1` avoids flooding). Let the one-shot
`getCurrentPosition` provide the initial coarse fix, and use a SEPARATE
wall-clock `Timer` (e.g. 20s) to surface "Retry GPS" guidance rather than
relying on the stream to time out.

## Android/Samsung FusedLocation throttles continuous location
On Samsung (S22, Android 16, battery optimization on), logcat shows:
```
I/FusedLocation: stationary throttling engaged
I/FusedLocation: location delivery to ... blocked - too close
```
The OS suppresses an app's high-frequency location updates when it decides the
device is stationary. Google Maps still "works" because it falls back to coarse
WiFi/cell and runs as foreground navigation. A plain app that requests
continuous GPS is starved -> the fix is slow/absent indoors even though the
`last location` (via `adb shell dumpsys location`) is fresh for the system.

This is the core reason continuous live-GPS AR is fragile on Samsung. Robust
fix: anchor the pin to a FIXED coordinate the user explicitly chooses (the
anchor-pin model — see SKILL.md) so the device only needs ONE coarse fix to
compute distance/direction, not a continuous high-frequency stream. The heavier
alternative is a foreground service (treated as navigation so it isn't
throttled).

## Debugging posture that ended the guessing loop
1. Connect the physical device and read real logcat instead of inferring from
   source + "what do you see": `adb devices`, `adb install -r`,
   `adb logcat -c`, capture to file via `adb logcat -v time > /tmp/logs.txt`
   (background=true), grep for your tag / `FusedLocation` / `FlutterGeolocator` /
   `TimeoutException`.
2. Confirm which build is installed: `aapt dump badging <apk>` ->
   `versionName`/`versionCode`. Release APKs strip `debugPrint` (use `print()`).
3. On Android 16, `adb install -r` can report "Success" yet the package is NOT
   registered (`adb shell pm path <pkg>` is empty, monkey says "No activities
   found"). Do `adb uninstall <pkg>` (ignore DELETE_FAILED_INTERNAL_ERROR) then
   `adb install` to force a clean register, and confirm with `pm path`.

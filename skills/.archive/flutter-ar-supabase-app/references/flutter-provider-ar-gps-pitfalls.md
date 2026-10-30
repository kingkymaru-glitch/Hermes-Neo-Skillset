# Flutter provider + AR/GPS pitfalls (SkyPin, 2026-08-31)

Durable lessons from debugging a Flutter+Supabase AR app (SkyPin, world-anchored
AR pin over live GPS). Three lessons: the frozen-widget provider bug, AR pin
heading rotation, and coarse-first GPS.

## Frozen-widget provider bug (the "GPS spins forever" trap)
Symptom: a screen shows a state-dependent overlay (spinner / error) that NEVER
updates — e.g. "Waiting for GPS…" spins non-stop even though the provider's GPS
logic resolved (coarse fix arrived, or the 20s safety timer set an error). The
state IS changing; the UI just isn't re-rendering.

Root cause: the widget is a `StatelessWidget` that receives the provider
(e.g. `RoomProvider`) via constructor and reads `room.gpsWaiting` /
`room.gpsError` in `build()`, but never subscribes to it. When the provider
calls `notifyListeners()`, nothing triggers a rebuild — the overlay is frozen on
the first frame forever.

Fix: read the provider from the tree inside `build()` so a rebuild is wired to
`notifyListeners()`:
```dart
final room = context.watch<RoomProvider>(); // NOT just the constructor-injected widget.room
```
Add `import 'package:provider/provider.dart';`. This same root cause also freezes
live roster / distance / arrival updates — any screen built from a mutable
provider must `context.watch` it, not only use the constructor handle.

Diagnostic that proved it: the source + installed APK were verified correct
(version bumped, safety-net timer present), yet the UI never changed — a pure
render-path bug, not a data bug. When "the fix didn't work" persists after you
confirm the state logic + build are right, suspect the widget isn't rebuilding.

## AR pin heading rotation
Placing an AR node at raw ENU `Vector3(east, 0, -north)` assumes the AR world's
+x is east / -z is north. That is only true if the phone starts facing north —
the AR session's axes align to the device's INITIAL orientation. Without
rotating by the live compass heading the beam points the wrong way on a real
2-device test. Feed the device heading (`FlutterCompass.events`) into the
provider, then rotate the ENU vector before placing the node:
```dart
final h = room.myHeading;
if (h != null) {
  final rad = h * pi / 180;
  enu = (enu.$1 * cos(rad) - enu.$2 * sin(rad),
         enu.$1 * sin(rad) + enu.$2 * cos(rad));
}
```

## Coarse-first GPS (don't hold the UI hostage on a precise fix)
Requesting `LocationAccuracy.high` and blocking the whole screen until it
resolves makes the app "feel" broken indoors vs Google Maps, which shows a
coarse (WiFi/cell) position instantly and refines. Use `LocationAccuracy.low`
for the initial stream + one-shot so a rough position appears in ~1-2s, and let
the stream refine. Add a hard timeout (e.g. 20s) that surfaces guidance +
Retry instead of an infinite spinner.

Also: check `isLocationServiceEnabled()` AND each permission explicitly, and
return a per-reason code (`location_off` / `location` / `camera`) so the UI can
offer an "Open Settings" button (`openAppSettings()` from permission_handler)
instead of a silent black screen. A denied CAMERA silently falls into
battery-saver black (`if (!ok) batterySaver = true`) — a confusing "black
screen" that looks like GPS failed when it's really a camera permission. Surface
it.

Note: in this permission_handler version, `Permission.locationWhenInUse` is a
`PermissionWithService`; use the top-level `openAppSettings()` (not
`Permission.locationWhenInUse.openAppSettings()`, which doesn't exist).

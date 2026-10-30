# Map picker, last-known position, and the Sceneform crash (SkyPin V0.09–0.12)

## Map picker replaces coordinate entry (user-driven, V0.09–0.10)
The summoner flow initially used a lat/lng text field. MARU's feedback was a
HARD UX correction: "it's impossible for people to remember coordinates, can
we pick it from a map?" — always offer a map tap-to-place, never require
typed coordinates.

Recipe (`flutter_map` + `latlong2`, both free, OpenStreetMap tiles, NO API key):
- Add to pubspec: `flutter_map: ^7.0.2`, `latlong2: ^0.9.0`.
- `FlutterMap(mapController: _mc, options: MapOptions(initialCenter: _center,
  initialZoom: 14, onTap: (_, ll) => _setPin(ll)))`.
- Marker = a red pin at `_pin`; show live lat/lng text at the bottom; a
  "Place SkyPin here" confirm + "Enter manually" fallback.
- **"Go to my location" button (crosshair, top-right)** — one-shot fix that
  centers the map (`_mc.move(loc, 16)`) AND drops the pin. This button is the
  key to the whole flow (see last-known below).
- Wrap the map in a `Stack` so you can overlay the locate button and loading
  spinner on top of `FlutterMap`.

## last-known-position = the indoor fix (V0.11)
See gps-stream-timeout-and-throttling.md for the stream/timeout background.
The concrete fix that finally worked: ALSO call
`Geolocator.getLastKnownPosition()` at start AND in the locate button, using
the result immediately. The OS's `dumpsys location` proves a fresh network fix
(hAcc≈16m) exists even when the continuous stream is throttled/starved; the
app just wasn't reading it. This unblocked instant centering and the beam.

## "Camera is dark / flickering, no beam" — root cause + fix (V0.10–0.12)
Symptom: after placing the pin and confirming, the AR screen shows a dark
flickering camera with no beam.

TWO distinct causes, don't conflate them:
1. NO POSITION = no beam (expected). The beam is positioned RELATIVE to the
   device, so a summoner without ANY fix sees only the camera. Fix with
   last-known (above). This is why the my-location button "helps a lot."
2. Native crash = hard app close (V0.12). Once you DO have a fix, the AR
   screen can still crash. Capture logcat and look for `FATAL EXCEPTION`:
```
java.lang.IllegalStateException: Calling method on destroyed VertexBuffer
  at com.google.android.filament.VertexBuffer.getNativeObject
  at com.google.ar.sceneform.rendering.CameraStream.recalculateCameraUvs
  at com.google.ar.sceneform.ArSceneView.onBeginFrame
```
ROOT CAUSE: `RoomScreen` uses `context.watch<RoomProvider>()` (added to fix
the frozen GPS spinner), so it rebuilds on EVERY provider notify (every GPS
tick / timer). The `ArView` sat directly in the build tree with no stable
identity, so Flutter kept tearing it down and recreating the native Sceneform
AR session mid-frame → destroyed VertexBuffer.

FIX: keep the ArView permanently mounted with a stable key and hide it rather
than unmount it:
```dart
Positioned.fill(
  child: Offstage(
    offstage: room.batterySaver,            // hide, don't unmount
    child: ArView(key: const ValueKey('arview'), room: room),
  ),
),
```
Never conditionally include/exclude the AR widget across rebuilds. This is
the general rule: an AR (Sceneform/ARCore) view must never be recreated by a
parent rebuild.

## Debug posture recap
- `adb shell dumpsys location` to see what fix the SYSTEM has (distinguish
  "app can't get a fix" from "app not reading an available fix").
- `adb logcat -v time > /tmp/x.log` (background) then grep for
  `FATAL EXCEPTION` / the process name to catch native crashes.

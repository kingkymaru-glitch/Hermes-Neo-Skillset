# ar_flutter_plugin 0.7.3 — verified API (read from plugin source, not docs)

## Imports (the barrel does NOT re-export managers)
```dart
import 'package:ar_flutter_plugin/ar_flutter_plugin.dart';          // only ARView
import 'package:ar_flutter_plugin/managers/ar_session_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_object_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_anchor_manager.dart';
import 'package:ar_flutter_plugin/managers/ar_location_manager.dart';
import 'package:ar_flutter_plugin/datatypes/node_types.dart';        // NodeType
import 'package:ar_flutter_plugin/datatypes/config_planedetection.dart'; // PlaneDetectionConfig
import 'package:ar_flutter_plugin/models/ar_node.dart';
import 'package:vector_math/vector_math_64.dart';                    // Vector3
```

## ARView callback shape
```dart
ARView(
  onARViewCreated: (ARSessionManager session,
                    ARObjectManager object,
                    ARAnchorManager anchor,
                    ARLocationManager location) {
    session.onInitialize(showFeaturePoints: false, showPlanes: false,
                         customPlaneTexturePath: null, showWorldOrigin: false);
    location.startLocationUpdates();   // ONLY updates device GPS
  },
  planeDetectionConfig: PlaneDetectionConfig.none,
)
```

## CRITICAL: ARLocationManager does NOT anchor nodes at lat/lng
`startLocationUpdates()` just keeps the device's GPS current. To draw a pin at a
friend's real location you compute the ENU (east/north) offset from YOUR gps to
THEIR gps and place an ARNode there, then re-place on every GPS tick:

```dart
// geo.dart
static (double east, double north) enuOffset(lat1, lng1, lat2, lng2) {
  const r = 6371000.0;
  final dLat = (lat2-lat1) * pi/180, dLng = (lng2-lng1) * pi/180;
  final east  = r * dLng * cos((lat1+lat2)/2 * pi/180);
  final north = r * dLat;
  return (east, north);
}

// place node (Z negative = forward/north in AR space)
final enu = Geo.enuOffset(me.lat, me.lng, p.lat, p.lng);
final node = ARNode(
  type: NodeType.localGLTF2,
  uri: 'https://.../arrow.glb',
  position: Vector3(enu.$1, 0, -enu.$2),
  scale: Vector3.all(8.0),
);
await object.addNode(node);
```

## Node management
- `await object.addNode(ARNode(...))` — can throw on the first frames; wrap in try/catch
  and retry on the next GPS tick.
- `await object.removeNode(node)` before re-adding to reposition.
- Keep a `Map<String, ARNode>` keyed by participant id so you update/remove per person.

## Skin/asset notes
- `NodeType.localGLTF2` loads a `.glb` from a URL or local asset path.
- GPS altitude is unreliable → fake vertical height with `scale` on the GLB (cosmetic
  "tower" so the pin is visible over crowds). SkyPin uses ~45m-equivalent scale.

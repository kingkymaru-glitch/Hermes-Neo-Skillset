# Procedural skin generation (Flutter AR + ar_flutter_plugin)

When an AR app needs a few built-in 3D pin/arrow meshes, DO NOT depend on Supabase
Storage uploads for them — generate simple glTF meshes and bundle them as Flutter
assets so the APK works offline.

## Why
- `ARNode(type: NodeType.localGLTF2)` loads a **bundled `.gltf` + `.bin`** from the
  Flutter asset folder (no network). `NodeType.webGLB` loads a `.glb` from a URL
  (network, needs Storage + anon-readable bucket). Built-ins should be offline.
- The anon key cannot INSERT to Storage (RLS requires `auth.uid()`), so anon uploads
  fail with HTTP 400 — another reason to keep built-ins local.

## Generator: scripts/gen_skins.py (no deps)
Writes 4 skins to `app/assets/skins/`:
- `arrow.glb` (red cone tip, #FF3B30), `thunder.glb` (yellow obelisk, #FFCC00),
  `cyclone.glb` (blue sphere+shaft, #5AC8FA), `beam.glb` (green cylinder+cone, #34C759).
- Then splits each `.glb` into `<name>.gltf` + `<name>.bin` (the form `localGLTF2` needs).

## glTF binary (.glb) chunk format (for hand-parsing)
```
[12-byte header] magic=0x46546C67 "glTF", version, length
[chunk 0] JSON: 4-byte uint32 length (LE), 4-byte "JSON", <length bytes JSON>, padded to 4 with spaces
[chunk 1] BIN : 4-byte uint32 length (LE), 4-byte "BIN\0", <length bytes>, padded to 4 with 0x00
```
PARSING PITFALL: the BIN chunk starts at `off += 8 + clen`, but `clen` is the JSON
length and the chunk is padded to a 4-byte boundary. If you don't realign,
`glb[off+4:off+8]` reads `b'BIN\x00'` shifted by 1 and the assertion fails:
```python
off += 8 + clen
off = (off + 3) & ~3          # <<< realign to 4-byte boundary
blen, = struct.unpack("<I", glb[off:off+4])
assert glb[off+4:off+8] == b"BIN\x00"
bin_blob = glb[off+8:off+8+blen]
```
Also strip trailing nulls before `json.loads(json_blob)`.

## pubspec.yaml assets
```yaml
flutter:
  assets:
    - assets/skins/      # recursive: pulls in .gltf + .bin + .glb
```

## App code branch (ar_view.dart)
```dart
final isBundled = !skinKey.startsWith('custom:');
final node = ARNode(
  type: isBundled ? NodeType.localGLTF2 : NodeType.webGLB,
  uri: isBundled ? 'assets/skins/$skinKey.gltf' : <storageUrl>,
  ...
);
```

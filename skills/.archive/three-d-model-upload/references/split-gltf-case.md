# Split glTF case — reproduction + proof of fix

## Symptom (user report)
User uploads `Cyclization_Catalyst_Vessel_A6000.gltf` from FreeCAD. Blue toast:
"`Cyclization_Catalyst_Vessel_A6000.gltf uploaded to R2`" (storage OK). Then red error:
`THREE.GLTFLoader: Failed to load buffer "Cyclization_Catalyst_Vessel_A6000.bin".` Model
never renders.

## Root cause
On disk the export is a PAIR:
- `Cyclization_Catalyst_Vessel_A6000.gltf` (JSON, references the .bin)
- `Cyclization_Catalyst_Vessel_A6000.bin` (5,787,788 bytes — geometry)
- (`...obj` also present — self-contained alternative)

The single-file upload pushed only the `.gltf`. GLTFLoader resolves the buffer's relative
`uri` against the model URL on R2, where the `.bin` does not exist → "Failed to load
buffer".

## Fix
Pack `.gltf` + `.bin` into one `.glb` client-side (`gltfToGlb`), upload the `.glb`. Viewer
loads `.glb` natively; no companion file to fetch.

## Node validation (run before trusting the browser code)
Re-implemented the packer with Node `Buffer`/`TextEncoder`/`btoa` against the real files:

```
external buffers: ['Cyclization_Catalyst_Vessel_A6000.bin']
external images : []
bin exists on disk: True  size: 5787788
GLB magic ok: True  version: 2  length==total: True  total: 7752052
buffers still external after pack: []   (should be [])
buffers inlined count: 1
GLB bytes written (simulated): 7752052
```

All assertions pass → the .glb is valid and contains zero external references. The viewer
will load it with no missing-buffer error.

## UX that prevents the error recurring
- `<input type="file" multiple>` and a hint: "For a split .GLTF, select the .gltf AND its
  .bin together — they are auto-packed into one .glb."
- If only `.gltf` is selected (no `.bin` sibling in the FileList), throw
  `Missing companion file "....bin" — select the .gltf AND its .bin` instead of the cryptic
  THREE error.

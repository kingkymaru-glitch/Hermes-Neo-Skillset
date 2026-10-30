# ODM Command Reference

## Minimal correct `docker run` (Python builder pattern)

```python
def build_docker_command(project_dir: Path, fast: bool = True) -> list[str]:
    fq, pcq, octree = ("medium", "medium", "9")  # feature/pc quality, mesh depth
    flags = [
        "--project-path", "/datasets",
        "code",                       # dataset name; images in /datasets/code/images
        "--feature-quality", fq,
        "--pc-quality", pcq,
        "--ignore-gsd",              # trust our GPS EXIF, don't re-derive GSD
        "--gltf",                    # emit .glb
        "--mesh-octree-depth", octree,
        "--orthophoto-resolution", "20",   # coarse: avoids meshing DEM tile overflow
        "--matcher-neighbors", "0",        # full matching (set >0 for huge sets)
        "--end-with", "mvs_texturing",     # stop after textured model
    ]
    return ["docker", "run", "--rm",
            "-v", f"{project_dir.resolve()}:/datasets",
            "opendronemap/odm:latest"] + flags
```

Stage images to `project_dir/code/images`, mount `project_dir -> /datasets`, run `odm code`.
ODM writes the glb to `code/odm_texturing/odm_textured_model_geo.glb`; copy it to
`output/site_model.glb`.

## Geotag keyframes with piexif (GPS from telemetry aligned by frame index)

```python
import piexif

def geotag_image(path, lat, lon, alt):
    lat_r = _deg_to_rat(abs(lat)); lon_r = _deg_to_rat(abs(lon))
    gps = {
        piexif.GPSIFD.GPSLatitudeRef: b"N" if lat >= 0 else b"S",
        piexif.GPSIFD.GPSLatitude: lat_r,
        piexif.GPSIFD.GPSLongitudeRef: b"E" if lon >= 0 else b"W",
        piexif.GPSIFD.GPSLongitude: lon_r,
        piexif.GPSIFD.GPSAltitudeRef: b"\x00",
        piexif.GPSIFD.GPSAltitude: _ratio(round(abs(alt) * 100), 100),
    }
    exif = piexif.load(path) if os.path.getsize(path) > 0 else {"GPS": {}}
    exif["GPS"] = gps
    piexif.insert(piexif.dump(exif), path)

def _deg_to_rat(deg):
    d = int(deg); m = int((deg - d) * 60); s = int(((deg - d) * 60 - m) * 60)
    return [(d, 1), (m, 1), (s, 1)]
```

Why piexif (not raw PIL GPS IFD): PIL's `exif[ExifTags.IFD.GPS] = {...}` writes malformed
rationals that corrupt the JPEG on save ("tag 6 had too many entries"). piexif handles the
GPS dict + `insert` correctly.

## DEM tile-limit math (why `--orthophoto-resolution 20`)

ODM's meshing `renderdem` uses `--max-tiles 165`. Tiles scale ~ 1 / resolution².
- res 2 cm/px on a large site → ~23856 tiles → OVERFLOW (701 flight, 4502 frames).
- res 20 cm/px → ~239 tiles → safe.
Textured-mesh quality is governed by `--mesh-octree-depth`, NOT orthophoto resolution,
so coarsening is free.

## OpenMVS fusion RAM bound

At Docker's default 7.75 GB limit (16 GB Mac):
- 209 keyframes (703) → fusion fit, exit 0.
- 250 keyframes (701) → `OpenMVS ran out of memory, turning on tiling` → SIGKILL.
- 329 keyframes (701) → same OOM.
Fix: cap keyframes to ~150–200 (`--max-frames`). Raising Docker Desktop → Settings →
Resources → Memory is the alternative if you need more frames.

## Tolerating ODM non-zero exit

```python
glb = find_glb(project_dir)   # checks odm_texturing/odm_textured_model.glb,
                              # odm_georeferencing/odm_textured_model_geo.glb, rglob("*.glb")
if proc.returncode != 0:
    if not glb:
        return fail(...)      # real failure
    log.warning("odm exited %d but produced a .glb — degraded success", proc.returncode)
if not glb:
    return fail(...)
shutil.copy2(glb, output / "site_model.glb")   # accept the artifact
```

ODM writes the textured model to disk *before* the process may be killed (exit 137/SIGKILL
or tiling-fallback exit 1). If `odm_textured_model_geo.glb` exists, it is complete — copy it.

## Validate the produced .glb

```bash
head -c 4 site_model.glb | xxd   # expect "676c 5446" = "glTF"
ls -lh site_model.glb            # non-zero size
```

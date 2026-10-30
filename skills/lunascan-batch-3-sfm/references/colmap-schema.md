# COLMAP Database Schema (v4.1)

Written by LUNASCAN `extractor.py` and queried by `pipeline.py`.

## Tables

### cameras
| Column | Type | Description |
|--------|------|-------------|
| camera_id | INTEGER PK | Always 1 (single camera for LUNASCAN) |
| model | INTEGER | Camera model ID. 0=SIMPLE_PINHOLE, 1=PINHOLE, **2=SIMPLE_RADIAL**, 3=RADIAL, 4=OPENCV, 5=OPENCV_FISHEYE, 6=FULL_OPENCV, 7=FOV, 8=SIMPLE_RADIAL_FISHEYE, 9=RADIAL_FISHEYE, 10=THIN_PRISM_FISHEYE |
| width | INTEGER | Image width in pixels |
| height | INTEGER | Image height in pixels |
| params | BLOB | float64 array. SIMPLE_RADIAL: [f, cx, cy, k1] |
| prior_focal_length | INTEGER | 0=free, 1=fixed |

### images
| Column | Type | Description |
|--------|------|-------------|
| image_id | INTEGER PK | 1-indexed, matches keypoint/descriptor rows |
| name | TEXT | Filename (e.g. `frame_000.png`) |
| camera_id | INTEGER | FK → cameras.camera_id |
| prior_qw/qx/qy/qz | REAL | Orientation prior (quaternion, wxyz). Identity = (1,0,0,0) |
| prior_tx/ty/tz | REAL | Position prior (world coords, meters). ENU from GPS |

### keypoints
| Column | Type | Description |
|--------|------|-------------|
| image_id | INTEGER | FK → images.image_id |
| rows | INTEGER | Number of keypoints |
| cols | INTEGER | 4 for SIFT (x, y, scale, orientation). 6 for affine shape. |
| data | BLOB | (rows × cols) float32 values, row-major |

### descriptors
| Column | Type | Description |
|--------|------|-------------|
| image_id | INTEGER | FK → images.image_id |
| rows | INTEGER | Number of descriptors |
| cols | INTEGER | 128 for SIFT |
| data | BLOB | (rows × cols) uint8 values, row-major |

### matches
Populated by COLMAP matcher. LUNASCAN only creates the empty table.

### two_view_geometries
Populated by COLMAP matcher. LUNASCAN only creates the empty table.

## Keypoint binary format (SIFT)

```
keypoints data blob: [x0, y0, scale0, orient0, x1, y1, scale1, orient1, ...]
  - All float32 (4 bytes per value)
  - 16 bytes per keypoint
  - x, y are in pixel coordinates (origin top-left)
  - scale is the SIFT detection scale (float)
  - orientation is in degrees (-180 to 180)
```

## Descriptor binary format (SIFT)

```
descriptors data blob: [d00, d01, ..., d0127, d10, d11, ..., d1127, ...]
  - All uint8 (1 byte per value)
  - 128 bytes per descriptor
  - Values in [0, 255]
```

## COLMAP camera model parameter vectors

| Model ID | Model Name | Params |
|----------|------------|--------|
| 0 | SIMPLE_PINHOLE | f, cx, cy |
| 1 | PINHOLE | fx, fy, cx, cy |
| 2 | SIMPLE_RADIAL | f, cx, cy, k1 |
| 3 | RADIAL | f, cx, cy, k1, k2 |
| 4 | OPENCV | fx, fy, cx, cy, k1, k2, p1, p2 |
| 7 | FOV | fx, fy, cx, cy, omega |

LUNASCAN default: SIMPLE_RADIAL (model 2). Initial guess: f = focal_length × max(w,h), cx = w/2, cy = h/2, k1 = 0.

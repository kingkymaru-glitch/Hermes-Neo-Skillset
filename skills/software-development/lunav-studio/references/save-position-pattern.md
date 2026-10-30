# savePosition pattern — LunaV marker relocation

Located in `ProjectWorkspace.tsx`. Handles position updates for all marker kinds
with a single axis at a time (called from slider onChange).

```
function savePosition(axis: "x" | "y" | "z", value: number) {
  if (!activeMarker || readOnly) return;
  const oldVal = activeMarker[`position_${axis}`] as number;
  if (oldVal === value) return;
  const delta = value - oldVal;

  if (activeMarker.kind === "along" && activeMarker.geometry_json?.points) {
    // Shift all path vertices by the same delta so the tube moves as a whole
    const points = activeMarker.geometry_json.points.map((p) => ({
      ...p,
      [axis]: (p[axis] ?? 0) + delta,
    }));
    saveMarker({
      [`position_${axis}`]: value,
      geometry_json: { ...activeMarker.geometry_json, points },
    });
  } else {
    saveMarker({ [`position_${axis}`]: value });
  }
}
```

## Why delta-shift for along markers

Along markers use `geometry_json.points[]` (absolute world-space coordinates)
to build the TubeGeometry path in Viewer3D. The `position_x/y/z` is the
centroid — it's NOT used for rendering. Changing only `position_x/y/z`
would update the DB field but produce no visible change in the 3D view.

Delta-shifting all path vertices by the same amount moves the entire tube.
The computed centroid in `position_x/y/z` is also updated to stay consistent.

For point and box markers, `position_x/y/z` IS the rendered position, so
a simple `saveMarker({ position_x: newVal })` suffices.

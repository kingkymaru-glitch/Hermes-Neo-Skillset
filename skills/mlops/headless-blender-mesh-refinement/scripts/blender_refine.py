"""
blender_refine.py — headless Blender mesh refinement.

Turns a raw reconstruction into a clean, web-ready asset. Blender does NOT
reconstruct anything here; it cleans and normalises geometry a photogrammetry or
3DGS engine already produced.

  blender --background --python-exit-code 1 --python blender_refine.py -- \
      --in mesh.ply --out object.glb --target-tris 60000 \
      [--voxel 0.0] [--smooth-iters 0] [--scale-longest-mm 0.0] [--no-uv]

--python-exit-code 1 is MANDATORY: Blender exits 0 even when its Python raises,
so without it a failed run looks successful and the caller then reads a file that
was never written.
"""
import argparse
import math
import os
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="src", required=True)
    p.add_argument("--out", dest="dst", required=True)
    p.add_argument("--target-tris", type=int, default=60000)
    p.add_argument("--voxel", type=float, default=0.0,
                   help="voxel size for a uniform remesh; 0 disables")
    p.add_argument("--smooth-iters", type=int, default=0)
    p.add_argument("--scale-longest-mm", type=float, default=0.0,
                   help="real length of the model's LONGEST axis in mm; "
                        "0 leaves the reconstruction unitless (not measurable)")
    p.add_argument("--no-uv", action="store_true")
    return p.parse_args(argv)


def log(msg):
    print(f"[refine] {msg}", flush=True)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_mesh(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        raise RuntimeError(f"unsupported input extension: {ext}")
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("import produced no mesh objects")
    log(f"imported {len(meshes)} mesh object(s)")


def join_meshes():
    """Collapse to a single object so downstream maths is unambiguous."""
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(meshes) == 1:
        return meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def capture_colour_attr(obj):
    """Capture the vertex-colour attribute name BEFORE modifiers can drop it."""
    attrs = getattr(obj.data, "color_attributes", None)
    if attrs and len(attrs):
        name = attrs[0].name
        log(f"vertex colour attribute: {name}")
        return name
    log("no vertex colour attribute found")
    return None


def clean(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-5)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.dissolve_degenerate()
    bpy.ops.object.mode_set(mode="OBJECT")
    log(f"cleaned — {len(obj.data.polygons):,} faces")


def voxel_remesh(obj, size):
    if size <= 0:
        return
    m = obj.modifiers.new("remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = size
    m.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier=m.name)
    log(f"voxel remesh @ {size} — {len(obj.data.polygons):,} faces")


def smooth(obj, iters):
    if iters <= 0:
        return
    m = obj.modifiers.new("smooth", "SMOOTH")
    m.iterations = iters
    bpy.ops.object.modifier_apply(modifier=m.name)
    log(f"smoothed x{iters}")


def decimate(obj, target_tris):
    """Collapse-decimate toward a triangle budget. Ratio must be in (0, 1]."""
    tris_now = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris_now <= target_tris or tris_now == 0:
        log(f"decimate skipped — {tris_now:,} tris already within budget")
        return
    ratio = max(0.01, min(1.0, target_tris / float(tris_now)))
    m = obj.modifiers.new("decimate", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=m.name)
    log(f"decimated {tris_now:,} -> {len(obj.data.polygons):,} faces (ratio {ratio:.3f})")


def shade(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    m = obj.modifiers.new("wn", "WEIGHTED_NORMAL")
    m.keep_sharp = True
    try:
        bpy.ops.object.modifier_apply(modifier=m.name)
    except RuntimeError:
        log("weighted normals skipped")


def unwrap(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
        log("smart UV unwrap done")
    except RuntimeError as exc:
        log(f"UV unwrap failed (non-fatal): {exc}")
    bpy.ops.object.mode_set(mode="OBJECT")


def build_material(obj, colour_attr):
    """glTF only exports COLOR_0 when a material references the attribute."""
    mat = bpy.data.materials.new("ObjectBaked")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out.location = (400, 0)
    bsdf.location = (100, 0)
    bsdf.inputs["Roughness"].default_value = 0.85
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = 0.0
    if colour_attr:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = colour_attr
        attr.location = (-200, 0)
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1.0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def normalise(obj, scale_longest_mm):
    """Centre on origin, drop to Z=0, optionally set real-world scale."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    dim = mx - mn
    obj.location = -(mn + mx) / 2.0
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    longest = max(dim.x, dim.y, dim.z)
    if longest <= 0:
        raise RuntimeError("degenerate bounding box — the mesh has no extent")
    if scale_longest_mm > 0:
        target_m = scale_longest_mm / 1000.0
        f = target_m / longest
        obj.scale = (f, f, f)
        bpy.ops.object.transform_apply(scale=True)
        log(f"scaled x{f:.6f} — longest axis now {target_m:.4f} m")
    else:
        log(f"left unitless — longest axis {longest:.4f} units (no --scale-longest-mm)")


def export(obj, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    kwargs = dict(filepath=dst, export_format="GLB", use_selection=False, export_apply=True)
    try:
        bpy.ops.export_scene.gltf(**kwargs, export_vertex_color="MATERIAL")
    except TypeError:
        bpy.ops.export_scene.gltf(**kwargs)
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise RuntimeError(f"glTF export produced no file at {dst}")
    log(f"exported {dst} ({os.path.getsize(dst):,} bytes)")


def main():
    a = parse_args()
    if not os.path.exists(a.src):
        raise RuntimeError(f"input mesh not found: {a.src}")
    clear_scene()
    import_mesh(a.src)
    obj = join_meshes()
    colour_attr = capture_colour_attr(obj)
    clean(obj)
    voxel_remesh(obj, a.voxel)
    smooth(obj, a.smooth_iters)
    decimate(obj, a.target_tris)
    shade(obj)
    if not a.no_uv:
        unwrap(obj)
    build_material(obj, colour_attr)
    normalise(obj, a.scale_longest_mm)
    export(obj, a.dst)
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    print(f"REFINE_OK tris={tris} verts={len(obj.data.vertices)}", flush=True)


if __name__ == "__main__":
    main()

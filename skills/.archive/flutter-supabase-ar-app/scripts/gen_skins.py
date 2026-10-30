#!/usr/bin/env python3
"""Generate SkyPin's procedural .glb pin skins + bundle them as .gltf/.bin.

No external deps. Each skin is a simple colored vertical mesh standing from y=0
up; the app applies scale (pin height ~45 m) and material tint at runtime.
Author's note: this exact approach was used in the SkyPin build and produces
valid glTF that ar_flutter_plugin loads via NodeType.localGLTF2 offline.

Usage:  python3 gen_skins.py
Output: arrow.glb/thunder.glb/cyclone.glb/beam.glb  (+ .gltf/.bin splits)
"""
import struct, json, math, os

# name -> (hex color, builder function returning list of triangle-vertex tuples
#          as (x,y,z) in metres, centered around x=z=0, base at y=0).
def _cone(radius, height, segs=8):
    verts = []
    tip = (0.0, height, 0.0)
    for i in range(segs):
        a0 = 2*math.pi*i/segs; a1 = 2*math.pi*(i+1)/segs
        p0 = (radius*math.cos(a0), 0, radius*math.sin(a0))
        p1 = (radius*math.cos(a1), 0, radius*math.sin(a1))
        verts += [tip, p0, p1]          # cone side (single color, no base)
    return verts

def _cylinder(r, h, segs=10):
    verts = []
    for i in range(segs):
        a0 = 2*math.pi*i/segs; a1 = 2*math.pi*(i+1)/segs
        b0=(r*math.cos(a0),0,r*math.sin(a0)); t0=(r*math.cos(a0),h,r*math.sin(a0))
        b1=(r*math.cos(a1),0,r*math.sin(a1)); t1=(r*math.cos(a1),h,r*math.sin(a1))
        verts += [b0,t0,b1, b1,t0,t1]
    return verts

def _box(w,h,d):
    x=w/2; z=d/2
    corners=[(-x,0,-z),(x,0,-z),(x,0,z),(-x,0,z)]
    top=[(c[0],h,c[2]) for c in corners]
    faces=[(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),
           (1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
    verts=[]
    for f in faces:
        for idx in f: verts.append(corners[idx] if idx<4 else top[idx-4])
    return verts

def _sphere(r, segs=8):
    verts=[]
    for i in range(segs):
        lat0=-math.pi/2 + math.pi*i/segs; lat1=-math.pi/2 + math.pi*(i+1)/segs
        for j in range(segs):
            lo0=2*math.pi*j/segs; lo1=2*math.pi*(j+1)/segs
            p=lambda lat,lo:(r*math.cos(lat)*math.cos(lo), r*math.sin(lat)+r, r*math.cos(lat)*math.sin(lo))
            verts += [p(lat0,lo0),p(lat0,lo1),p(lat1,lo0), p(lat1,lo0),p(lat0,lo1),p(lat1,lo1)]
    return verts

SKINS = {
    "arrow":   ("#FF3B30", lambda: _cone(0.5, 3.0)),
    "thunder": ("#FFCC00", lambda: _box(0.7, 3.0, 0.7)),
    "cyclone": ("#5AC8FA", lambda: _sphere(1.0) + _cylinder(0.15, 2.0)),
    "beam":    ("#34C759", lambda: _cylinder(0.4, 2.4) + _cone(0.7, 0.8)),
}

def build_glb(positions, color_hex):
    r = int(color_hex[1:3],16)/255.0; g=int(color_hex[3:5],16)/255.0; b=int(color_hex[5:7],16)/255.0
    float32 = struct.pack("<" + "f"*len(positions)*3, *[c for p in positions for c in p])
    nrm = struct.pack("<" + "f"*len(positions)*3, *[0.0]*len(positions)*3)
    color = struct.pack("<" + "f"*len(positions)*3, *[v for _ in positions for v in (r,g,b)])
    bin_blob = bytearray()
    bin_blob += struct.pack("<II", 0, 0)               # POSITION accessor min/max placeholder
    bin_blob += float32
    bin_blob += nrm
    bin_blob += color
    pos_acc = {"bufferView":0,"componentType":5126,"count":len(positions),"type":"VEC3","max":[0,3,0],"min":[0,0,0]}
    nrm_acc = {"bufferView":1,"componentType":5126,"count":len(positions),"type":"VEC3"}
    col_acc = {"bufferView":2,"componentType":5126,"count":len(positions),"type":"VEC3"}
    gltf = {
        "asset":{"version":"2.0"},
        "scenes":[{"nodes":[0]}], "scene":0,
        "nodes":[{"mesh":0}],
        "meshes":[{"primitives":[{"attributes":{"POSITION":0,"NORMAL":1,"COLOR_0":2},"mode":4}]}],
        "buffers":[{"byteLength":len(bin_blob)}],
        "bufferViews":[
            {"buffer":0,"byteOffset":8,"byteLength":len(float32)},
            {"buffer":0,"byteOffset":8+len(float32),"byteLength":len(nrm)},
            {"buffer":0,"byteOffset":8+len(float32)+len(nrm),"byteLength":len(color)},
        ],
        "accessors":[pos_acc, nrm_acc, col_acc],
        "materials":[{"name":"skin","pbrMetallicRoughness":{"baseColorFactor":[r,g,b,1],"metallicFactor":0.1,"roughnessFactor":0.8}}],
    }
    json_blob = json.dumps(gltf, separators=(",",":")).encode("utf-8")
    pad = (4 - len(json_blob)%4)%4; json_blob += b" "*pad
    glb = b"glTF\x02\x00\x00\x00"
    total = 12 + 8 + len(json_blob) + 8 + len(bin_blob)
    glb += struct.pack("<I", total)
    glb += struct.pack("<I", len(json_blob)) + b"JSON" + json_blob
    glb += struct.pack("<I", len(bin_blob)) + b"BIN\x00" + bytes(bin_blob)
    return glb

def split_gltf(glb_path):
    glb = open(glb_path,"rb").read()
    clen = struct.unpack("<I", glb[12:16])[0]
    json_blob = glb[20:20+clen]
    off = 20 + clen
    off = (off + 3) & ~3
    blen = struct.unpack("<I", glb[off:off+4])[0]
    bin_blob = glb[off+8:off+8+blen]
    base = glb_path[:-4]
    gltf = json.loads(json_blob.decode("utf-8"))
    gltf["buffers"][0] = {"uri": base.split("/")[-1] + ".bin", "byteLength": blen}
    with open(base + ".gltf","w") as f: f.write(json.dumps(gltf, indent=2))
    with open(base + ".bin","wb") as f: f.write(bin_blob)

os.makedirs("app/assets/skins", exist_ok=True)
for name,(color,builder) in SKINS.items():
    out = f"app/assets/skins/{name}.glb"
    open(out,"wb").write(build_glb(builder(), color))
    split_gltf(out)
    print("wrote", out)
print("done")

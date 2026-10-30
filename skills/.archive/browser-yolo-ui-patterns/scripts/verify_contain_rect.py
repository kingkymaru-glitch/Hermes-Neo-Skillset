#!/usr/bin/env python3
"""verify_contain_rect.py — deterministic probe of canvas-px -> normalized-frame mapping.

Run in the project venv:  python3 verify_contain_rect.py
Asserts the contain-rect math from references/canvas_contain_rect.md:
  - a frame-normalized box maps onto the contained rect (no full-canvas stretch)
  - a canvas-px box inverts back to the correct normalized coords (label correctness)
Delete after use (throwaway verification, not a committed test).
"""
import math

def contain_rect(fw, fh, cw, ch):
    scale = min(cw / fw, ch / fh)
    dw, dh = fw * scale, fh * scale
    return {"x": (cw - dw) / 2, "y": (ch - dh) / 2, "w": dw, "h": dh}

def frame_to_canvas(box, cr):
    cx, cy, w, h = box
    return [cr["x"] + cx * cr["w"], cr["y"] + cy * cr["h"],
            w * cr["w"], h * cr["h"]]

def canvas_to_frame(x0, y0, x1, y1, cr):
    cx_n = ((x0 + x1) / 2 - cr["x"]) / cr["w"]
    cy_n = ((y0 + y1) / 2 - cr["y"]) / cr["h"]
    w_n  = abs(x1 - x0) / cr["w"]
    h_n  = abs(y1 - y0) / cr["h"]
    return [min(1, max(0, cx_n)), min(1, max(0, cy_n)),
            min(1, max(0, w_n)),  min(1, max(0, h_n))]

def approx(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))

ok = True
# Frame 1920x1080, canvas 600x800  (16:9 video in tall canvas -> letterbox top/bottom)
cr = contain_rect(1920, 1080, 600, 800)
assert cr["w"] == 600.0 and abs(cr["h"] - 337.5) < 1e-6 and cr["x"] == 0.0, cr
assert abs(cr["y"] - 231.25) < 1e-6, cr

# A normalized box maps onto the contained rect, not full canvas
box = [0.5, 0.5, 0.3, 0.4]
bx, by, bw, bh = frame_to_canvas(box, cr)
assert approx([bx, by, bw, bh], [300.0, 400.0, 180.0, 135.0]), (bx, by, bw, bh)

# Inverse: drag a canvas-px box at that location -> back to original normalized (clamped)
x0, y0 = bx - bw / 2, by - bh / 2
x1, y1 = bx + bw / 2, by + bh / 2
inv = canvas_to_frame(x0, y0, x1, y1, cr)
assert approx(inv, box), inv

# Off-canvas drag (partially outside letterbox) clamps into [0,1]
inv2 = canvas_to_frame(-50, -50, 100, 100, cr)
assert all(0.0 <= v <= 1.0 for v in inv2), inv2

print("contain-rect mapping: PASS" if ok else "FAIL")

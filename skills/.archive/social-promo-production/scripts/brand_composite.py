#!/usr/bin/env python3
"""Reusable branding compositor: build a wordmark + bake punchlines onto keyframes.

Usage:
  python3 brand_composite.py --frames f1.png f2.png f3.png f4.png \
      --outdir /Users/kamarulhk/Desktop \
      --hook "YOUR TYRES ARE|LYING TO YOU" --hero "GRIP YOU CAN TRUST"

Design notes:
  - Wordmark = BLACK + accent-colored second word + small flame icon (PIL, transparent bg).
  - Fonts available on macOS: Arial Black (Supplemental), SF Compact Bold (Library).
  - ALWAYS measure textlength vs frame width and shrink until it fits with margin;
    center-aligned text spills both edges if over-width (silent clip).
"""
import argparse, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
FONT_BOLD  = "/Library/Fonts/SF-Compact-Display-Bold.otf"
RED = (225, 6, 0); BLK = (20, 20, 20); WHITE = (255, 255, 255)

def make_logo(scale=1.0, word1="BLACK", word2="FIRE", sub="STORE"):
    pad = 40
    fb = ImageFont.truetype(FONT_BLACK, int(150*scale))
    fs = ImageFont.truetype(FONT_BOLD, int(64*scale))
    d = ImageDraw.Draw(Image.new("RGBA", (10,10)))
    wb, wf = d.textlength(word1, font=fb), d.textlength(word2, font=fb)
    gap = int(18*scale); top_w = int(wb+gap+wf)
    ws = d.textlength(" ".join(sub), font=fs)
    store_w = max(ws, top_w)
    W = int(store_w + pad*2); H = int(150*scale + 64*scale + int(30*scale) + pad*2)
    img = Image.new("RGBA", (W,H), (0,0,0,0)); dr = ImageDraw.Draw(img)
    x0 = (W-top_w)/2; y0 = pad
    dr.text((x0, y0), word1, font=fb, fill=BLK)
    dr.text((x0+wb+gap, y0), word2, font=fb, fill=RED)
    fy = y0 + int(150*scale) + int(20*scale)
    draw_flame(dr, (W-store_w)/2, fy, int(46*scale))
    dr.text(((W-store_w)/2 + int(54*scale), fy - int(6*scale)), " ".join(sub), font=fs, fill=BLK)
    return img

def draw_flame(dr, cx, base_y, h):
    tip = base_y - h; half = h*0.42
    dr.polygon([(cx,tip),(cx+half,base_y-h*0.25),(cx+half*0.35,base_y-h*0.05),
                (cx,base_y+h*0.04),(cx-half*0.35,base_y-h*0.05),(cx-half,base_y-h*0.25)], fill=RED)
    dr.polygon([(cx,tip+h*0.30),(cx+half*0.5,base_y-h*0.18),(cx,base_y-h*0.02),
                (cx-half*0.5,base_y-h*0.18)], fill=(255,140,0))

def paste(img, ov, box, rot=0, shadow=True):
    ov = ov.convert("RGBA").resize((box[2], box[3]), Image.LANCZOS)
    if rot: ov = ov.rotate(rot, expand=True, resample=Image.BICUBIC)
    if shadow:
        sh = Image.new("RGBA", ov.size, (0,0,0,0)); ImageDraw.Draw(sh).rectangle([0,0,*ov.size], fill=(0,0,0,90))
        sh = sh.filter(ImageFilter.GaussianBlur(6)); img.alpha_composite(sh, (box[0]+6, box[1]+8))
    img.alpha_composite(ov, (box[0], box[1])); return img

def bake_text(img, lines, box, size, color=WHITE, stroke=BLK):
    f = ImageFont.truetype(FONT_BLACK, size); d = ImageDraw.Draw(img)
    W = img.size[0]; lh = int(size*1.12); total = len(lines)*lh
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f)
        assert w < W*0.92, f"text '{ln}' too wide ({round(w)}>{round(W*0.92)}); shrink size"
    y = box[1] + (box[3]-total)/2
    for ln in lines:
        w = d.textlength(ln, font=f); x = box[0]+(box[2]-w)/2
        d.text((x,y), ln, font=f, fill=color, stroke_width=max(2,int(size*0.06)), stroke_fill=stroke); y += lh
    return img

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--frames", nargs="+", required=True)
    ap.add_argument("--outdir", default="."); ap.add_argument("--hook", default="")
    ap.add_argument("--hero", default=""); ap.add_argument("--logo-word1", default="BLACK")
    ap.add_argument("--logo-word2", default="FIRE"); ap.add_argument("--logo-sub", default="STORE")
    a = ap.parse_args()
    logo = make_logo(2.2, a.logo_word1, a.logo_word2, list(a.logo_sub))
    for i, fp in enumerate(a.frames):
        im = Image.open(fp).convert("RGBA"); W,H = im.size
        if a.hook and i == 0:
            im = bake_text(im, a.hook.split("|"), (int(W*0.05),int(H*0.08),int(W*0.90),int(H*0.26)), int(H*0.050), color=WHITE, stroke=RED)
        if a.hero and i == len(a.frames)-1:
            im = bake_text(im, [a.hero], (int(W*0.04),int(H*0.76),int(W*0.92),int(H*0.13)), int(H*0.040), color=WHITE, stroke=BLK)
            lw, lh = int(W*0.32), int(W*0.32*logo.size[1]/logo.size[0])
            im = paste(im, logo, (int(W*0.64), int(H*0.87)-lh, lw, lh))
        out = os.path.join(a.outdir, os.path.splitext(os.path.basename(fp))[0] + "_tagged.png")
        im.save(out); print("wrote", out)
    lp = os.path.join(a.outdir, "blackfirestore_logo.png"); logo.save(lp); print("wrote", lp)

if __name__ == "__main__": main()

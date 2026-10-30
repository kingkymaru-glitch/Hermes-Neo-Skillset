# Aspect-ratio canvas + floating collapsible sidebar (Luna-EDGE)

## Why
Stretching the video frame to the canvas (`drawImage(bmp,0,0,canvas.w,canvas.h)`)
squashes a 16:9 movie in a tall panel. Worse: in learning mode the drawn box maps
to the warped canvas, so training labels are corrupted. Fix = preserve native aspect
ratio (letterbox) and draw overlays against the contained rect.

## paint() — contain math
```js
const fw = latestBitmap.width, fh = latestBitmap.height;
const cw = canvas.width, ch = canvas.height;
const scale = Math.min(cw/fw, ch/fh);          // object-fit: contain
const dw = fw*scale, dh = fh*scale;
const dx = (cw-dw)/2, dy = (ch-dh)/2;          // letterbox offset
containRect = {x:dx, y:dy, w:dw, h:dh};
ctx.fillStyle='#000'; ctx.fillRect(0,0,cw,ch);
ctx.drawImage(latestBitmap, dx, dy, dw, dh);
// boxes: scale against contained rect, offset by dx/dy
const sx = dw/fw, sy = dh/fh;
ctx.strokeRect(dx + b.x*sx, dy + b.y*sy, b.w*sx, b.h*sy);
```

## Learning-mode box-draw -> normalized label
Mouse is in canvas px. Convert through containRect, then clamp 0..1:
```js
const nx0 = (x0 - cr.x)/cr.w, ny0 = (y0 - cr.y)/cr.h;
const nx1 = (x1 - cr.x)/cr.w, ny1 = (y1 - cr.y)/cr.h;
const cx = (nx0+nx1)/2, cy = (ny0+ny1)/2;
const bw = Math.abs(nx1-nx0), bh = Math.abs(ny1-ny0);
// clamp 0..1, send [cx,cy,bw,bh]
```
Do NOT divide by canvas.width/height — that bakes the distortion into the label.

## Floating collapsible sidebar (full-aspect video)
- `.row` is `position:relative`; `#sidebar` is `position:absolute; top:16px; left:16px;
  width:280px; z-index:15` (glass). `#feedWrap` is `width:100%; height:calc(100vh-78px)`.
- Collapse: add `.collapsed { transform:translateX(-110%) }`; a ☰ button removes it,
  clicking the header title adds it. Transition 0.25s.
- Keep `body { padding-bottom:46px }` if a bottom railing exists so it never covers content.

## Pitfall
If you relabel on a STRETCHED frame the saved `.txt` boxes are wrong → the model
trains on distorted geometry. Always label against the contained (letterboxed) rect.

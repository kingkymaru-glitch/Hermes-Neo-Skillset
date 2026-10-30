# Canvas contain-rect math + box mapping

## The bug
`ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height)` stretches the frame to the
canvas. If the video is 16:9 and the canvas is tall, the subject is squashed. Any
detection box (or user-drawn label box) computed against full-canvas w/h is then
placed on the *warped* image — invisible on screen, and if used as a training
label, it trains the model on distorted coordinates.

## The fix: contain (letterbox)
Every paint, compute the largest rect with the frame's aspect ratio that fits the
canvas, center it.

```
scale = min(canvas.w / frame.w, canvas.h / frame.h)
dw = frame.w * scale;  dh = frame.h * scale
dx = (canvas.w - dw) / 2;  dy = (canvas.h - dh) / 2
containRect = {x:dx, y:dy, w:dw, h:dh}
ctx.drawImage(bmp, dx, dy, dw, dh)   // NOT full canvas
```

## Drawing detection boxes (server pushes normalized bbox)
Server sends `bbox = [cx, cy, w, h]` in 0..1 of the *frame*. Map to canvas via the
contained rect:
```
bx = containRect.x + cx * containRect.w
by = containRect.y + cy * containRect.h
bw = w  * containRect.w
bh = h  * containRect.h
```

## User-drawn box -> normalized frame coords (for labeling / learning mode)
User drags on the canvas; you have canvas-px `(x0,y0,x1,y1)`. Invert:
```
cx_n = ((x0 + x1)/2 - containRect.x) / containRect.w
cy_n = ((y0 + y1)/2 - containRect.y) / containRect.h
w_n  = |x1 - x0| / containRect.w
h_n  = |y1 - y0| / containRect.h
# clamp each to [0,1]
```
Write `class_id cx_n cy_n w_n h_n` to the `.txt`. This is the ONLY correct mapping;
skip `containRect` and you label the warped canvas, not the video.

## Worked example
Frame 1920x1080 (16:9). Canvas 600x800.
scale = min(600/1920, 800/1080) = min(0.3125, 0.7407) = 0.3125
dw = 600, dh = 337.5 -> dy = (800-337.5)/2 = 231.25, dx = 0.
A frame-normalized box [0.5,0.5,0.3,0.4] draws at:
bx=0+0.5*600=300, by=231.25+0.5*337.5=400, bw=0.3*600=180, bh=0.4*337.5=135.

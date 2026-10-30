# In-app "teach the model" loop (1 frame -> ~16 training samples)

## Why upload, not pick
The YOLO engine runs server-side (cv2 reads real files on the Mac). A browser
`<input type=file>` only yields a `File` object the server cannot read by path.
So labeling must UPLOAD the captured frame to the server (loopback, instant, no
internet), which saves + augments + (later) trains.

## Endpoint shape (Flask)
POST /api/learn/capture  json: { image: "data:image/jpeg;base64,...", box:[cx,cy,w,h],
                                  class_name:"monkey", dataset:"custom" }
- Decode base64 -> numpy frame.
- Assign class_id (monotonic per dataset; or look up if class_name already seen).
- Save `learn/capture/<dataset>/<ts>.jpg` + `.txt` (YOLO format).
- Run augment() -> ~16 files, each with transformed .txt.

GET /api/learn/classes  -> { ok, classes: model.names }  (so UI shows what exists)
POST /api/learn/train  json: { dataset, mode:"custom"|"coco_ext", epochs }
  -> build_dataset() writes learn/datasets/<ds>/{train,val}/images+labels + data.yaml
  -> model.train(data=yaml, epochs, device="mps")  (Apple Silicon)
  -> copy runs/<ds>/weights/best.pt -> skills/<ds>.pt

## Augmentation recipe (pure numpy + cv2, NO albumentations dependency)
Each op returns (img, label_transform_fn). Apply to the SAME base label so boxes
stay correct. Base label = [cx, cy, w, h] in 0..1.

- flipH : cv2.flip(img,1)            ; label cx -> 1-cx
- flipV : cv2.flip(img,0)            ; label cy -> 1-cy
- rot90 : cv2.rotate(img, ROTATE_90) ; swap + invert: cx->cy, cy->1-cx, w<->h
- rot15 : rotate(img,+15)   ; rotate label box corners by +15deg about center, re-enclose
- rot-15: rotate(img,-15)   ; same, -15deg
- bright+ : img*1.25 + 30 (clip)     ; label unchanged
- bright- : img*0.75 - 30            ; label unchanged
- scale08: resize 0.8, pad to canvas ; label unchanged (coords are normalized)
- scale12: resize 1.2, crop center   ; label unchanged
- blur   : cv2.GaussianBlur(7)       ; label unchanged
- noise  : + randn*8 (clip)          ; label unchanged

TOTAL produced per capture: 1 base + 15 augs = 16. Keep ops that fail (e.g. tiny
box after crop) out, so count is ">=10" not exactly 16.

## Label-transform correctness (the easy-to-miss bug)
For flips/rot90 the box coordinates MUST be recomputed, not copied. A horizontal
flip with unchanged cx trains the box on the wrong side of the animal. Verify each
transform by rendering the new box on the new image and eyeballing one sample.

## Train modes
- custom: data.yaml `nc = N` (only the new classes). Use when you only want the
  asset items detected (e.g. hardhat, crack) and not person/car/etc.
- coco_ext: start from yolov8n.pt, data.yaml `nc = 80 + N`; the 80 COCO ids keep
  their meaning, new classes append. YOLO output layer is fixed-width, so you
  CANNOT append a class to an existing .pt — you must retrain with nc+1.

## device
On Mac use device="mps" (Metal). Small datasets (few hundred imgs, few classes)
train in minutes. For bigger jobs Colab free GPU is faster but data leaves machine.

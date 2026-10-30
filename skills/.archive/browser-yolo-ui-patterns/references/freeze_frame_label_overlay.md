# Freeze-frame label overlay (teach tab)

Reproduce-with-modifications reference for the "pause a video → snapshot the frame →
draw a label box on it" UI used in the Luna-EDGE `/learn` tab. Battle-tested fix for
two bugs seen in the wild (split-screen layout, box drift).

## Markup
```html
<div class="media-wrap">
  <video id="srcVideo" playsinline muted loop></video>
  <img id="freezeImg" alt="frozen frame" />
  <canvas id="drawCanvas" class="hidden"></canvas>
  <div class="freeze-badge" id="freezeBadge">⏸ Frozen — drag a box on the object</div>
</div>
```

## CSS (the layering fix)
```css
.media-wrap { position: relative; width: 100%; background:#0f1216; overflow:hidden; }
video { width: 100%; display: block; }                 /* in-flow height anchor */
#freezeImg { position:absolute; inset:0; width:100%; height:100%;
             object-fit:contain; background:#0f1216; display:none; }
#drawCanvas { position:absolute; inset:0; width:100%; height:100%; display:none; }
.freeze-badge { position:absolute; top:10px; left:10px; z-index:5;
                display:none; align-items:center; gap:6px; font-size:12px;
                color:#ffb340; background:rgba(20,23,28,0.82);
                border:1px solid rgba(255,179,64,0.5); border-radius:999px; padding:5px 12px; }
```

## JS
```js
const cv = document.getElementById('drawCanvas');
let box=null, frozen=false, drawing=false;

function freeze(){
  const v = document.getElementById('srcVideo');
  v.pause();
  const c = document.createElement('canvas'); c.width=v.videoWidth; c.height=v.videoHeight;
  c.getContext('2d').drawImage(v,0,0);
  const img = document.getElementById('freezeImg'); img.src = c.toDataURL();
  img.style.display = 'block';                  // overlay the video, don't replace it
  cv.width = c.width; cv.height = c.height;     // canvas internal px = video px
  cv.classList.remove('hidden'); cv.style.display='block';
  cv.style.aspectRatio = c.width+'/'+c.height;
  document.getElementById('freezeBadge').style.display = 'inline-flex';
  box=null; frozen=true; drawBox();
}
function unfreeze(){
  document.getElementById('freezeImg').style.display='none';
  cv.classList.add('hidden'); cv.style.display='none';
  document.getElementById('freezeBadge').style.display='none';
  document.getElementById('srcVideo').play().catch(()=>{}); frozen=false;
}

// COORD FIX: mouse is in CSS px, canvas is in video px → scale.
function toCanvas(e){
  const r = cv.getBoundingClientRect();
  const sx = cv.width/r.width, sy = cv.height/r.height;
  return { x:(e.clientX-r.left)*sx, y:(e.clientY-r.top)*sy };
}
cv.addEventListener('mousedown', e=>{ if(!frozen) return; drawing=true;
  const p=toCanvas(e); box={x1:p.x,y1:p.y,x2:p.x,y2:p.y}; });
cv.addEventListener('mousemove', e=>{ if(!drawing) return;
  const p=toCanvas(e); box.x2=p.x; box.y2=p.y; drawBox(); });
window.addEventListener('mouseup', ()=>drawing=false);

function drawBox(){
  if(!frozen) return;
  const ctx=cv.getContext('2d'); ctx.clearRect(0,0,cv.width,cv.height);
  if(box){ const x=Math.min(box.x1,box.x2), y=Math.min(box.y1,box.y2),
    w=Math.abs(box.x2-box.x1), h=Math.abs(box.y2-box.y1);
    ctx.strokeStyle='#ffb340'; ctx.lineWidth=3; ctx.strokeRect(x,y,w,h);
    ctx.fillStyle='rgba(255,179,64,0.12)'; ctx.fillRect(x,y,w,h); }
}

// Save → POST normalized coords (0..1) to the server
async function saveFrame(){
  if(!frozen || !box) return;
  const x=Math.min(box.x1,box.x2), y=Math.min(box.y1,box.y2),
        w=Math.abs(box.x2-box.x1), h=Math.abs(box.y2-box.y1);
  const nx=(x+w/2)/cv.width, ny=(y+h/2)/cv.height, nw=w/cv.width, nh=h/cv.height;
  await fetch('/api/learn/capture', {method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({image:document.getElementById('freezeImg').src,
      box:[nx,ny,nw,nh], class_name:name, dataset:DATASET})});
}
```

## Why this ordering
- Video stays `display:block` in flow; only the frozen `<img>` + `<canvas>` are
  `position:absolute; inset:0`. This keeps the stage height correct and the canvas
  exactly on top of the frame — no second block below.
- `object-fit:contain` on the frozen image matches the video's letterbox so the box,
  drawn on the canvas at the same `inset:0`, lines up with the object regardless of
  clip aspect ratio.
- `toCanvas` is the single source of truth for pointer→canvas mapping; both mouse and
  touch call it so boxes never drift on retina / resized windows.

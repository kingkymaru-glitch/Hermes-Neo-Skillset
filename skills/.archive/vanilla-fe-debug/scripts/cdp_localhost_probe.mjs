#!/usr/bin/env node
// cdp_localhost_probe.mjs — decisive "dead button" diagnostic for LOCAL dev servers.
//
// WHY: `browser_exec` is blocked from localhost/private addresses, and `curl`/`node --check`
// only prove the ENTRY script loaded — not that the ES module graph resolved or handlers bound.
// A single 404 on a transitive import aborts the WHOLE module; the page looks fine but clicks
// do nothing. This drives a real local Chrome via the DevTools CDP protocol and reports which.
//
// USAGE:
//   node scripts/cdp_localhost_probe.mjs [URL] [ELEMENT_ID] [BOOT_FLAG] [PORT]
//   node scripts/cdp_localhost_probe.mjs http://localhost:8753/web/index.html p-run __bootRan 9333
//
// READ THE OUTPUT IN THIS ORDER:
//   1. NON-200 ON .js/.css  -> module-graph 404 (this is usually THE bug)
//   2. onclick type         -> "object"(=null, unbound) vs "function"(bound)
//   3. __bootRan            -> "undef" means the binding IIFE body never ran
//   4. console/exceptions   -> module import failures live here, not always in a page error overlay

import { spawn } from 'node:child_process';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const URL = process.argv[2] || 'http://localhost:8753/web/index.html';
const EL = process.argv[3] || 'p-run';
const BOOT = process.argv[4] || '__bootRan';
const PORT = parseInt(process.argv[5] || '9333', 10);

const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const chrome = spawn(CHROME, [
    '--headless=new', '--no-sandbox', '--disable-gpu',
    `--remote-debugging-port=${PORT}`, 'about:blank'
  ], { stdio: 'ignore', detached: true });

  let targets;
  for (let i = 0; i < 6; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/list`); targets = await r.json(); break; }
    catch { await sleep(1000); }
  }
  if (!targets) { console.log('CHROME START FAIL'); process.exit(1); }

  const tab = targets.find(t => t.type === 'page');
  if (!tab) { console.log('NO PAGE TARGET'); process.exit(1); }
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  let id = 0; const pending = {};
  const send = (method, params) => new Promise(res => {
    const mid = ++id; pending[mid] = res;
    ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
  });
  const logs = [], net = [];
  ws.addEventListener('message', m => {
    const j = JSON.parse(m.data);
    if (j.id && pending[j.id]) return;
    if (j.id && pending[j.id]) { pending[j.id](j.result || j.error); delete pending[j.id]; return; }
    if (j.method === 'Runtime.consoleAPICalled' || j.method === 'Runtime.exceptionThrown') logs.push(j);
    if (j.method === 'Network.responseReceived') {
      const u = j.params?.response?.url || '';
      const s = j.params?.response?.status;
      if (/\.(js|mjs|css)(\?|$)/.test(u)) net.push({ s, u });
    }
  });
  await new Promise(r => ws.addEventListener('open', r));
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable', {});

  await send('Page.navigate', { url: URL });
  await sleep(4000);

  const probe = await send('Runtime.evaluate', {
    expression: `(() => {
      const el = document.getElementById(${JSON.stringify(EL)});
      const log = document.getElementById('p-log');
      const err = document.getElementById('err');
      return new Promise(resolve => resolve({
        bootRan: (typeof window[${JSON.stringify(BOOT)}] !== 'undefined') ? window[${JSON.stringify(BOOT)}] : 'undef',
        onclickType: el ? (typeof el.onclick) : 'no-el',
        errOverlay: err ? err.textContent.slice(0, 400) : 'NO ERR OVERLAY',
        pLog: log ? log.textContent.slice(0, 200) : 'NO p-log'
      }));
    })()`,
    returnByValue: true
  });

  console.log('=== PROBE (' + EL + ') ===');
  console.log(JSON.stringify(probe.result, null, 2));
  console.log('=== NETWORK .js/.css (non-200 = module-graph break) ===');
  const bad = net.filter(n => n.s >= 400);
  (bad.length ? bad : net).forEach(n => console.log(n.s, n.u));
  console.log('=== CONSOLE / EXCEPTIONS (' + logs.length + ') ===');
  logs.slice(0, 12).forEach(l => {
    const p = l.params;
    if (l.method === 'Runtime.exceptionThrown')
      console.log('EXCEPTION:', p.exceptionDetails?.exception?.description || p.exceptionDetails?.text);
    else
      console.log('CONSOLE[' + p.type + ']:', p.args?.map(a => a.value ?? a.description).join(' '));
  });
  process.exit(0);
})().catch(e => { console.error('FATAL', e); process.exit(1); });

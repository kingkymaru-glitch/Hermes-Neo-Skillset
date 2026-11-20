// live_audit.mjs — RUN ON THE USER'S MAC, not the agent terminal.
// The agent execution sandbox egress-blocks every *.supabase.co host, so a live
// check there returns ENOTFOUND and tells you NOTHING about the user's config.
// Usage:  cd /Users/kamarulhk/my-digital-twin && node live_audit.mjs
import { createClient } from '@supabase/supabase-js';
import fs from 'fs';

const env = fs.readFileSync('.env', 'utf8');
const get = (k) => { const m = env.match(new RegExp('^' + k + '=(.*)$', 'm')); return m ? m[1].trim() : ''; };
const URL = get('VITE_SUPABASE_URL');
const ANON = get('VITE_SUPABASE_ANON_KEY');
const SRV = get('SUPABASE_SERVICE_ROLE_KEY');

const ok = (c) => (c ? 'present' : 'MISSING');
console.log('vars: URL=' + ok(URL) + ' ANON=' + ok(ANON) + ' SERVICE=' + ok(SRV));
if (!URL || !ANON || !SRV) { console.log('FAIL: missing one of the three keys in .env'); process.exit(1); }

const anon = createClient(URL, ANON);
const admin = createClient(URL, SRV, { auth: { autoRefreshToken: false, persistSession: false } });

const results = [];
const check = (name, pass, detail) => { results.push({ name, pass }); console.log((pass ? 'PASS ' : 'FAIL ') + name + (detail ? ' — ' + detail : '')); };
const transport = (e) => e && /fetch failed|ENOTFOUND|getaddrinfo|ECONNREFUSED|ETIMEDOUT/i.test(e.message || String(e));

// 1. anon reaches project (https + key valid)
try {
  const t0 = Date.now();
  const { error } = await anon.from('profiles').select('count').limit(1);
  const ms = Date.now() - t0;
  check('ANON reach project (https + key valid)', !transport(error), error ? `roundtrip ${ms}ms err=${error.message}` : `roundtrip ${ms}ms, table reachable`);
} catch (e) { check('ANON reach project', false, String(e).slice(0, 120)); }

// 2. profiles table exists
{ const { error } = await anon.from('profiles').select('id').limit(1);
  check('profiles table exists', !(error && /relation .* does not exist/.test(error.message)), error ? error.message : 'ok'); }

// 3. RLS: anon cannot read superadmin row
{ const { data, error } = await anon.from('profiles').select('email,role,status').eq('email', 'AdminMARU@maru.app');
  check('RLS: anon CANNOT read superadmin row', !error && (!data || data.length === 0), data && data.length ? 'LEAK: ' + JSON.stringify(data) : 'hidden (good)'); }

// 4. RLS: anon insert blocked
{ const { error } = await anon.from('profiles').insert({ role: 'superadmin', status: 'approved' });
  check('RLS: anon INSERT blocked', !!(error && (/policy/.test(error.message) || error.code === '42501')), error ? error.message.slice(0, 80) : 'no error (unexpected)'); }

// 5. service role: superadmin seeded
{ const { data, error } = await admin.from('profiles').select('email,role,status').eq('email', 'AdminMARU@maru.app').single();
  if (error) check('superadmin seeded', false, error.message);
  else check('superadmin seeded (role+status)', data.role === 'superadmin' && data.status === 'approved', `email=${data.email} role=${data.role} status=${data.status}`); }

// 6. service role: auth user created
{ const { data, error } = await admin.auth.admin.listUsers();
  if (error) check('auth user exists', false, error.message);
  else { const u = data.users.find((x) => x.email === 'AdminMARU@maru.app'); check('auth user AdminMARU created', !!u, u ? 'confirmed_email=' + (u.email_confirmed_at ? 'yes' : 'no') : 'not found'); } }

const failed = results.filter((r) => !r.pass).length;
console.log(`\n=== SUMMARY: ${results.length - failed}/${results.length} checks passed ===`);
if (failed) console.log('(If the ANON roundtrip shows ENOTFOUND/transport fail, you likely ran this in the agent sandbox — run on the user Mac instead.)');
process.exit(failed ? 1 : 0);

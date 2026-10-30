#!/usr/bin/env node
// Reusable Supabase key-validity + data probe (anon key).
// Run: ANON=<publishable_key> URL=https://<ref>.supabase.co node probe_supabase_key.cjs [table]
// If [table] given, it also does a count(*) select to prove the key works for reads.
//
// DIAGNOSES:
//   1. Is the JWT well-formed + what project/role does it claim? (decode payload)
//   2. Does a live `from(table).select('count')` succeed or return "Invalid API key"?
// If "Invalid API key" but the decoded ref matches the URL ref => the key was
// ROTATED in the dashboard; copy the current Publishable key. The OLD key is
// rejected for reads AND writes, so any "node vanished" symptom is a stale
// credential, NOT a broken insert path (a row proving the earlier insert exists).
const { createClient } = require('@supabase/supabase-js');

const anon = process.env.ANON;
const url = process.env.URL;
const table = process.argv[2];

if (!anon || !url) {
  console.error('Usage: ANON=<key> URL=https://<ref>.supabase.co node probe_supabase_key.cjs [table]');
  process.exit(2);
}

// 1) Decode JWT payload (base64url of 2nd segment).
try {
  const seg = anon.split('.')[1];
  const pad = seg + '==='.slice((seg.length + 3) % 4);
  const payload = JSON.parse(Buffer.from(pad, 'base64').toString('utf8'));
  console.log('JWT payload:', JSON.stringify({
    iss: payload.iss, ref: payload.ref, role: payload.role, exp: payload.exp,
  }));
  const refInUrl = url.replace('https://', '').split('.')[0];
  console.log('URL ref:', refInUrl, '| JWT ref:', payload.ref, '| match:', refInUrl === payload.ref);
} catch (e) {
  console.log('JWT decode failed:', e.message);
}

// 2) Live read test.
(async () => {
  const sb = createClient(url, anon, { auth: { persistSession: false } });
  const target = table || 'projects';
  const { data, error } = await sb.from(target).select('count');
  if (error) {
    console.log(`READ ${target}: ERROR -> ${error.message}`);
    if (/Invalid API key/i.test(error.message)) {
      console.log('DIAGNOSIS: key rejected. If JWT ref matches URL ref, the key was rotated — get the current Publishable key from dashboard Settings > API.');
    }
  } else {
    console.log(`READ ${target}: OK -> ${JSON.stringify(data)}`);
  }
})();

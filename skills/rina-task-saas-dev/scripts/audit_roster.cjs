// Safe READ-ONLY roster audit for a RINA org. Never mutates.
// Usage: RINA_EMAIL=... RINA_PW=... node audit_roster.cjs <orgId>
const fs = require('fs');
const { createClient } = require('/Users/kamarulhk/riina/node_modules/@supabase/supabase-js');
function env(k){const t=fs.readFileSync('/Users/kamarulhk/riina/.env.local','utf8');return t.match(new RegExp(k+'=(.+)'))[1].replace(/[^ -~]/g,'').trim();}
const sb = createClient(env('VITE_SUPABASE_URL'), env('VITE_SUPABASE_ANON_KEY'), { auth:{persistSession:false} });
const ORG = process.argv[2];
(async()=>{
  if(!ORG){ console.log('usage: node audit_roster.cjs <orgId>'); process.exit(1); }
  const email = process.env.RINA_EMAIL || 'neo.superadmin@rina-test.dev';
  const pw = process.env.RINA_PW || 'RinaTest!2026';
  const { error } = await sb.auth.signInWithPassword({ email, password: pw });
  if(error){ console.log('AUTH_FAIL', error.message); process.exit(1); }
  const { data, error: e2 } = await sb.from('user_profiles')
    .select('id,name,email,role,level,reports_to_ids,active')
    .eq('organization_id', ORG).order('level');
  if(e2){ console.log('READ_FAIL', e2.message); process.exit(1); }
  console.log('TOTAL', data.length);
  console.log(JSON.stringify(data.map(u=>({
    n: u.name || '(empty)', r: u.role, l: u.level,
    rep: (u.reports_to_ids||[]).length, active: u.active
  })), null, 0));
})().catch(e=>console.log('FATAL', e.message));

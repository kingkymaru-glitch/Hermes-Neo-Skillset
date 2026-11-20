// Reusable live-flow probe for a Supabase Auth + signup-trigger project.
// Run: ANON=<publishable_key> node verify_signup.mjs
// Proves: key valid, trigger creates org+profile, confirmation state.
// Place in a dir with node_modules/@supabase/supabase-js installed.

import { createClient } from '@supabase/supabase-js';

const url = process.env.SUPABASE_URL || 'https://<ref>.supabase.co';
const anon = process.env.ANON;
if (!anon) { console.error('set ANON (publishable key)'); process.exit(2); }
const supabase = createClient(url, anon);

const ts = Date.now();
const email = `diag+signup${ts}@gmail.com`; // plus-address = your inbox, valid domain

const r = await supabase.auth.signUp({
  email,
  password: 'TestPass123!',
  options: { data: { company_name: 'DiagCo', name: 'Diag', position: 'GM', department: 'Exec' } },
});
console.log('signup: session?', !!r.data?.session, '| user?', !!r.data?.user,
  '| error:', r.error ? JSON.stringify(r.error) : 'none');
// session?false + over_email_send_rate_limit  => confirmation ON
// session?true                                => confirmation OFF
// 401 Invalid API key                          => key truncated/wrong project

const uid = r.data?.user?.id;
if (uid) {
  // NOTE: a CHAINED select right here can return null even though the AFTER-INSERT
  // trigger DID create the profile (trigger not yet visible in same script process).
  // Treat this script's profile report as a weak signal only. To CONFIRM the trigger
  // fired, run a SEPARATE `supabase db query --linked` (owner role) afterwards:
  //   select count(*) from public.user_profiles where id = '<uid>';
  const { data: prof } = await supabase
    .from('user_profiles').select('id, organization_id, role, active').eq('id', uid).single();
  console.log('profile (chained, may under-report):', !!prof, JSON.stringify(prof));
  // Cleanup: do NOT use supabase.auth.admin.deleteUser here (needs service_role Bearer
  // token -> fails "This endpoint requires a valid Bearer token"). Clean via owner role:
  //   supabase db query --linked --file cleanup.sql   (delete from auth.users +
  //   public.user_profiles + public.organizations where email like '%diag+signup%')
  console.log('CLEANUP: run supabase db query --linked to delete auth.users + profile + org for', email);
}

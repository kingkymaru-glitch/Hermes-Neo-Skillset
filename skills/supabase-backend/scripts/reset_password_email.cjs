// Triggers a Supabase password-reset email for a user. Loads .env.local
// itself so secrets are never echoed to chat. Reports only success/failure.
// Usage: node reset_password_email.cjs <email> [origin]
const fs = require("fs");
const path = require("path");

const envPath = path.join(__dirname, ".env.local");
const env = {};
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
}
process.env.NEXT_PUBLIC_SUPABASE_URL = env.NEXT_PUBLIC_SUPABASE_URL;
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const { createClient } = require("@supabase/supabase-js");

const email = process.argv[2];
const origin = process.argv[3] || (process.env.NEXT_PUBLIC_SITE_URL || "https://lunavsolution.vercel.app");
if (!email) {
  console.error("usage: node reset_password_email.cjs <email> [origin]");
  process.exit(2);
}

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

(async () => {
  const { error } = await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${origin}/update-password`,
  });
  if (error) {
    console.error("RESET_FAIL: " + error.message);
    process.exit(1);
  }
  console.log("RESET_OK: recovery email dispatched to " + email);
  console.log("REDIRECT: " + origin + "/update-password");
})();

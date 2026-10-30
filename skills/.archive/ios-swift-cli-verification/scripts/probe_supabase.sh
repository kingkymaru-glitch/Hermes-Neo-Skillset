#!/usr/bin/env bash
# probe_supabase.sh <URL> <ANON_KEY> [probe_email]
# Live-reachability + key-validity probe for a Supabase auth endpoint.
# Reports:
#   DNS resolves?  (dead project => "hostname could not be found" at runtime, NOT a code bug)
#   GET /auth/v1/signup with key:
#       405 = key accepted + host alive (method rejected; expected for GET)
#       401 "Invalid API key" = WRONG key for this project (keys are project-scoped)
#   POST /auth/v1/signup with a probe email:
#       200/400/422 = auth API reachable (400/422 = our fake email; real one would 200)
#       429 = email rate limit exceeded (throttle, NOT a bad email)
#       "Could not resolve host" = dead project / typo in URL
set -u
URL="${1:?usage: probe_supabase.sh <URL> <ANON_KEY> [email]}"
KEY="${2:?missing anon key}"
EMAIL="${3:-probe_verify+$(date +%s)@example.com}"
HOST=$(echo "$URL" | sed -E 's#https?://##; s#/.*##')

echo "=== DNS resolution of $HOST ==="
if dscacheutil -q host -a name "$HOST" >/dev/null 2>&1; then echo "RESOLVES"; else echo "DOES NOT RESOLVE (dead project / typo)"; fi

echo "=== GET /auth/v1/signup with key (405=key OK+host alive; 401=invalid key) ==="
curl -sS --max-time 12 -o /dev/null -w "GET HTTP %{http_code}\n" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" "$URL/auth/v1/signup" 2>&1

echo "=== POST /auth/v1/signup (probe) — 200/400/422=reachable; 429=rate limit; host-not-found=dead ==="
curl -sS --max-time 15 -w "\nPOST HTTP %{http_code}\n" -X POST \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"TempPassw0rd!23\"}" "$URL/auth/v1/signup" 2>&1 | tail -4

#!/usr/bin/env bash
# R2 credential + public-access smoke test.
# Usage: ./r2-smoke-test.sh ACCOUNT_ID ACCESS_KEY_ID SECRET BUCKET PUB_BASE
# Proves: (1) S3 keys can write, (2) r2.dev public read works, (3) cleans up.
set -euo pipefail
ACCT="$1"; KEY="$2"; SECRET="$3"; BUCKET="$4"; PUB="$5"
EP="https://${ACCT}.r2.cloudflarestorage.com/${BUCKET}"
TMP=$(mktemp); echo "r2-smoke-$(date +%s)" > "$TMP"

echo "-- signed PUT --"
curl -s --aws-sigv4 "aws:amz:auto:s3" --user "${KEY}:${SECRET}" \
  -X PUT --data-binary @"$TMP" "${EP}/smoke-test.txt" -w "PUT: %{http_code}\n"

echo "-- public GET --"
curl -s "${PUB}/smoke-test.txt" -w " | GET: %{http_code}\n"

echo "-- cleanup --"
curl -s --aws-sigv4 "aws:amz:auto:s3" --user "${KEY}:${SECRET}" \
  -X DELETE "${EP}/smoke-test.txt" -w "DELETE: %{http_code}\n"
rm -f "$TMP"
# Interpretation: PUT 403 with correct-looking keys => wrong credential TYPE
# (cfat_ account token instead of 32-hex S3 Access Key ID).
# PUT 200 but browser still 403 => missing bucket CORS policy (preflight).

#!/bin/bash
# R2 credential smoke test: signed PUT -> public GET -> DELETE.
# Usage: ./r2-smoke-test.sh ACCOUNT_ID ACCESS_KEY_ID SECRET_KEY BUCKET PUBLIC_BASE
# Expect: PUT 200, read 200 (echoes content), cleanup 204.
# PUT 403 => wrong credential type (cfat_ token instead of 32-hex S3 Access Key ID).
set -euo pipefail
ACC=$1; KEY=$2; SECRET=$3; BUCKET=$4; PUB=$5
EP="https://${ACC}.r2.cloudflarestorage.com/${BUCKET}/smoke-test.txt"
echo "r2-smoke-$(date +%s)" > /tmp/r2test.txt
curl -s --aws-sigv4 "aws:amz:auto:s3" --user "${KEY}:${SECRET}" \
  -X PUT --data-binary @/tmp/r2test.txt "$EP" -w "PUT: %{http_code}\n"
curl -s "${PUB}/smoke-test.txt" -w " | public read: %{http_code}\n"
curl -s --aws-sigv4 "aws:amz:auto:s3" --user "${KEY}:${SECRET}" \
  -X DELETE "$EP" -w "cleanup: %{http_code}\n"

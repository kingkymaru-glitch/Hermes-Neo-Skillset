# OpenRouter free-model reference (verified 2026-07-16)

Verify live before each build — free tiers change:
  curl -s https://openrouter.ai/api/v1/models | python3 -c "import sys,json;d=json.load(sys.stdin);[print(m['id'],m.get('pricing',{}).get('prompt','?')) for m in d.get('data',[]) if 'hy3' in m['id'].lower()]"

## Verified values (snapshot)
- tencent/hy3:free  -> prompt pricing 0  (FREE)  <-- what we route Cursor onto
- tencent/hy3       -> 0.0000002 (paid)
- tencent/hy3-preview -> 0.000000063
- tencent/hunyuan-a13b-instruct -> 0.00000014

## Caveats
- FREE tier is rate-limited and occasionally shows "model unavailable". Proxy
  retries 3x with backoff, then returns a clean error so the client doesn't hang.
- OpenRouter is OpenAI-compatible: base URL https://openrouter.ai/api/v1, key from
  https://openrouter.ai/keys (free account). Cursor's "Override OpenAI Base URL"
  points at the LOCAL proxy, not directly at OpenRouter (model rewrite needed).

## Nous fallback (does NOT work for this)
- api.nousresearch.com / inference.nousresearch.com /v1/models -> empty (no public
  free inference endpoint). portal.nousresearch.com is a web app only.
- When user "prefers Nous but free", use OpenRouter instead — it's reachable+free.

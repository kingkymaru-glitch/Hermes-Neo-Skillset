# Hermes API server + custom wiring

> Preserved from the original hermes-voice-conversation skill (2026-11 restructure).

## Enabling the Hermes API server (required by jarvis)

1. Generate a key: `python3 -c "import secrets; print(secrets.token_hex(24))"`.
2. Append `API_SERVER_KEY=<key>` to `~/.hermes/.env`.
3. Add under `gateway:` in `~/.hermes/config.yaml` (edit the file directly; config tools may refuse it):
   ```
   api_server:
     key: <key>
     port: 8642
   ```
4. Restart the gateway from a *separate* terminal: `hermes gateway restart`. It cannot be restarted from inside the gateway process — the child gets SIGTERM.
5. Verify: `curl -s -m 5 -H "Authorization: Bearer <key>" http://127.0.0.1:8642/health`.


## Wiring to Hermes (when building custom)

1. Capture mic → STT (Whisper local).
2. Send text to Hermes (CLI or API on :8642).
3. TTS reply to speakers + show text.
4. Keep everything local except LLM + TTS cloud calls.

Pitfall: Bluetooth mic adds ~200ms latency — acceptable. Use Whisper "base" on Apple Silicon (~1-2s/sentence).

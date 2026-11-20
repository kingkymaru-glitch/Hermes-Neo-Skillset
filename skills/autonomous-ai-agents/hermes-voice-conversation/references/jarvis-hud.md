# J.A.R.V.I.S HUD (optional, cloud TTS)

> Preserved from the original hermes-voice-conversation skill (2026-11 restructure).

## Preferred path: use the existing J.A.R.V.I.S repo

Repo: `cooperativelyincorporated/jarvis` (self-hosted, Iron-Man-style HUD).
- STT: faster-whisper (local, free). TTS: ElevenLabs (cloud, ~0.5 credits/char Flash).
- Browser HUD with push-to-talk, live transcription, streaming reply speech, typed chat sharing one session.
- Embeds Hermes kanban board + session browser as pop-up panels.
- Requires: Hermes Agent configured, Python 3.11+, ElevenLabs API key, modern browser on LAN.

Safety audit before install (always):
- Clone into a scratch dir first, not the live location.
- Grep for eval/exec/os.system/subprocess shell=True/base64 decode/hardcoded URLs/backdoors; confirm all network calls are to documented endpoints (local Hermes API, ElevenLabs, health checks).
- Only copy to the real location after the audit passes.

Install:
1. Clone the repo.
2. macOS only: `brew install portaudio` (needed by PyAudio/RealtimeSTT).
3. Create venv and install deps: `python3 -m venv .venv && .venv/bin/pip install requests uvicorn pyyaml numpy anthropic fastapi RealtimeSTT` (large; may take minutes).
4. Run `scripts/make-certs.sh` (browser mic needs HTTPS).
5. Run `scripts/make-boot-audio.sh YourName`.
6. Set `JARVIS_HUD_TOKEN` and ElevenLabs key in `~/.hermes/.env`.
7. `.venv/bin/python server.py` → expect startup lines for ws :8765, https :443/:8766 HUD, and :9443 dashboard proxy. Open `https://HOST/hud/` → accept cert → enter token → talk.
8. For auto-start on boot, use `launchd/` (macOS) — read its notes on TCC + FD limits.

Pitfalls:
- Port 8765 is already used by the Hermes team dashboard (if running). jarvis also binds 8765 for its WebSocket; stop the dashboard first or expect a bind conflict.
- PyAudio (RealtimeSTT dependency) needs PortAudio on macOS: `brew install portaudio` before `pip install RealtimeSTT`, or the wheel build fails with "portaudio.h not found".
- RealtimeSTT pulls torch/faster-whisper and is a large install (minutes). Install with `background=true` and poll.
- Self-signed cert: the browser shows a privacy error on first open; the user must click Advanced → Proceed manually. Cannot be automated.
- ElevenLabs API key permissions: a key with only "Text to Speech" works for TTS but not for listing voices (`voices_read`). If you need a voice id, use the default Rachel id `21m00Tcm4TlvDq8ikWAM` or create the key with voices_read permission.
- Do not port-forward to the internet — LAN-only by design. Hermes API key must never reach the browser; the HUD proxies through the voice server allowlist.
- Do not attempt to swap ElevenLabs for macOS `say` in the jarvis server: it streams raw PCM over WebSocket and `say` outputs files — a big rewrite. Use the ElevenLabs free tier (10k chars/month) or the standalone browser Web Speech page instead.
- Standalone Web Speech page must be served over HTTP (not file://) or Chrome blocks the mic. Run `python3 -m http.server 8080` in the file's folder.
- ElevenLabs is paid but has a free tier; confirm the user wants cloud TTS before committing.


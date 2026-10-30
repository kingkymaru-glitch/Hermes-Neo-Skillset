---
name: hermes-voice-conversation
description: Add two-way voice conversation to Hermes Agent.
version: 1.0.0
author: neo
license: MIT
metadata:
  hermes:
    tags: [voice, tts, stt, jarvis, hermes]
    related_skills: [elegant-web-design-language]
---

# Voice Conversation with Hermes

## When to Use

Use when the user wants to talk to Hermes by voice (mic in, speaker out), build a voice pipeline, or set up the J.A.R.V.I.S HUD. Trigger phrases: "voice conversation", "talk to Hermes", "Jarvis", "mic", "speech to text".

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

## Free no-API path (browser Web Speech + local bridge)

When the user wants zero API keys and zero heavy installs, use the browser's built-in Web Speech API for STT/TTS and a tiny local HTTP bridge that shells out to `hermes -z "<text>"`.

Files (place in `~/hermes-voice/`):
- `bridge.py`: ThreadingHTTPServer on `127.0.0.1:8790`. `GET /` serves `index.html`; `POST /ask` runs `subprocess.run(["hermes","-z", text], ...)` and returns `{"reply": ...}`.
- `index.html`: `SpeechRecognition` → POST /ask → `speechSynthesis.speak(reply)`.

Run: `cd ~/hermes-voice && python3 bridge.py`, then open `http://127.0.0.1:8790` in Chrome/Safari and allow mic.

Pitfalls:
- Port 8790 avoids the team dashboard on 8765; do not reuse 8765.
- Page must be served over HTTP (`http://127.0.0.1`), not `file://`, or Chrome blocks the mic.
- `hermes -z` depends on a working default model. If the configured model is unavailable (e.g. free tier retired), fix with `hermes model` before testing voice — otherwise the bridge returns an error reply.
- `hermes -z` can take 10-30s on free models; set subprocess timeout >= 120s.
- Override a broken default model at runtime with `-m <model>` (e.g. `-m reflection/beam-1.0-501b-a23b:free`) in the bridge subprocess call; editing `~/.hermes/config.yaml` may be blocked by security-sensitive config guards.
- To run alongside the team dashboard, embed the bridge as an iframe at `http://127.0.0.1:8790/` in a dashboard tab; keep the bridge on 8790 and the dashboard on 8765.
- The bridge subprocess can hang and return an empty reply; restart the bridge with logging (`python3 bridge.py > /tmp/bridge.log 2>&1`) and check the log before debugging the frontend.
- Bluetooth mic adds ~200ms latency — acceptable.
- Free-tier model context windows may be reduced (e.g. reflection/beam-1.0-501b-a23b:free is capped at 262,144 tokens on the free tier vs 1M on direct hosting). Rarely matters for voice, but avoid sending huge pasted text.
- Do not auto-send on speech end. Dictate into an editable textarea and let the user press Enter; users need to review/correct dictated text and paste images/URLs before sending.

## Free no-API path: UI/UX and optional neural TTS

User preference (durable): no paid API keys; any voice is acceptable; keep a written transcript log so the user can read/catch up while building hands-free; dark HUD theme with cat avatars per agent; large push-to-talk button.

Optional neural TTS upgrade (still free-ish, no API key): generate audio with `edge-tts` (local CLI) inside the bridge and return an `audio` URL; the frontend plays it and falls back to `speechSynthesis` if missing. Voice example: `en-US-AriaNeural` (more natural than `en-US-AvaMultilingualNeural`).

HUD layout (recommended): top status line + model/profile; left column with animated orb (pulses on speech), info panel, controls (Clear/Replay/Stop); right column scrollable transcript (user/agent bubbles, timestamps, replay button); bottom mic button + volume slider. Cat avatar (🐱) next to agent messages.

Terminal-style variant (preferred by this user): monospace scrollback log with prompt prefixes (❯ user, ↳ agent, · system); an editable <textarea> input (not auto-send) that accepts typing, copy/paste, URLs, and image paste; voice dictation (interim results) fills the textarea so the user can review/edit before pressing Enter to send. Image paste: intercept paste, save the image to a temp file via a bridge /upload endpoint, insert a `[image:/path]` token into the textarea at the cursor and show a thumbnail. Slash commands handled by the bridge: `/model <name>` switches the session model, `/clear` clears the log, others are passed to Hermes as text. Enter (no Shift) sends; Shift+Enter inserts a newline.

## Quick-test path (no install)

Use a standalone HTML page with the browser Web Speech API (`SpeechRecognition` + `speechSynthesis`).
- Serve over HTTP (not `file://`) or Chrome blocks the mic.
- Reply is a placeholder until wired to Hermes.

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

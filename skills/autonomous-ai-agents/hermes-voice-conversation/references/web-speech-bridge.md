# Zero-key Web Speech bridge + HUD UX

> Preserved from the original hermes-voice-conversation skill (2026-11 restructure).

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


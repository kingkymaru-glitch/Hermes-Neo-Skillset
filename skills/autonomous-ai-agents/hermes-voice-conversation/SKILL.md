---
name: hermes-voice-conversation
description: "Use when talking to Hermes by voice or building a voice HUD."
version: 2.0.0
author: neo + nini
license: MIT
metadata:
  hermes:
    tags: [voice, tts, stt, jarvis, hermes, wake-word, dictation]
    related_skills: [conversational-build, hermes-agent]
---

# Voice Conversation with Hermes

Two-way voice (mic in, speaker out) and hands-free building. NATIVE voice
mode first — it ships with Hermes and needs no external repo. Custom HUDs
are optional upgrades, not the default path.

Trigger phrases: "voice conversation", "talk to Hermes", "Jarvis", "mic",
"speech to text", "dictate", "hey hermes".

## Path 1 — native voice mode (default, zero extra repos)

Docs: /docs/user-guide/features/voice-mode, /docs/user-guide/features/wake-word,
/docs/guides/use-voice-mode-with-hermes (fetch via hermes-agent skill routing).

- CLI/TUI: Ctrl+B records; silence auto-detected; agent replies in voice.
- Slash commands: `/voice on` (voice-to-voice), `/voice tts` (always speak
  replies), `/voice off`.
- Wake word: "Hey Hermes" opens a fresh voice session hands-free (CLI, TUI,
  desktop) — see the wake-word docs page for setup.
- Messaging: Telegram/Discord auto voice replies; Discord bot can join a
  voice channel and converse live.

Setup:

```bash
brew install portaudio ffmpeg opus     # macOS system deps
hermes tools                           # configure STT/TTS providers
```

- STT: local faster-whisper needs NO API key (base model ~150 MB downloads
  on first use). Cloud alternatives: Groq Whisper (free tier, GROQ_API_KEY),
  OpenAI Whisper (VOICE_TOOLS_OPENAI_KEY), Mistral Voxtral.
- TTS: edge-tts works with no key; ElevenLabs/OpenAI premium need keys.
  A paid Nous Portal subscription covers OpenAI TTS via the Tool Gateway.
- Keys live in ~/.hermes/.env; settings via `hermes config set` (stt.enabled,
  stt.provider, tts.provider) — never hand-edit config.yaml.
- Restart Hermes after dependency/environment changes.

Pitfalls:
- Local faster-whisper is excluded on Intel macOS and Windows ARM64 — use a
  cloud STT provider there.
- First whisper download comes from huggingface.co; on blocked networks set
  HF_ENDPOINT to a mirror (+ HF_HUB_DISABLE_XET=1) in the shell that starts
  Hermes.
- "No audio device found" → portaudio missing or mic permission denied for
  the terminal host; check System Settings > Privacy & Security > Microphone.
- Bluetooth mic adds ~200 ms latency — acceptable. Whisper base on Apple
  Silicon runs ~1-2 s/sentence.

## Dictation while building (durable user preference)

- Do NOT auto-send on speech end. Dictation fills an editable input; the
  user reviews/corrects, pastes URLs/images, then presses Enter.
- Keep a written transcript log so the user can read/catch up while
  building hands-free.
- Voice turns follow the conversational-build skill: one idea per reply,
  echo back misheard names/numbers/paths before acting, verbal gate on
  deploy/send/delete.

## Path 2 — zero-key custom HUD (Web Speech bridge)

Browser SpeechRecognition + speechSynthesis + a tiny local HTTP bridge that
shells out to `hermes -z`. No API keys, no heavy installs. Terminal-style
transcript UI preferred by this user (monospace scrollback, editable
textarea, image paste, edge-tts neural voice upgrade).
Read `references/web-speech-bridge.md` — includes the port rules (8790, not
8765), HTTP-not-file:// mic rule, and the full HUD layout spec.

## Path 3 — J.A.R.V.I.S HUD (optional, cloud TTS)

Self-hosted Iron-Man HUD (cooperativelyincorporated/jarvis): faster-whisper
STT + ElevenLabs TTS, push-to-talk, kanban/session panels. Requires an
ElevenLabs key and a safety audit before install.
Read `references/jarvis-hud.md` — audit checklist, install steps, cert and
port pitfalls. Confirm the user wants cloud TTS before committing.

## Custom wiring (any path)

Capture mic → STT → Hermes (CLI or API server :8642) → TTS + text.
API server enablement and restart rules: `references/api-server-and-wiring.md`.

## Verification

After setup: record one spoken sentence, confirm the transcript text is
correct, confirm the reply plays AND appears as text. A voice path that
only half-works (hears but silent, or speaks but no transcript) is not done.

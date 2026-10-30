---
name: lunav-intel-m-dev
description: Use when running LUNAV Intel-M predictive maintenance.
version: 1.0.0
author: Neo (Hermes Agent)
license: MIT
tags: [lunav, predictive-maintenance, fastapi, nextjs, tmux, anomaly-detection, rul]
metadata:
  hermes:
    tags: [lunav, predictive-maintenance, fastapi, nextjs, tmux, anomaly-detection, rul]
    related_skills: [lunav-sado-dev, lunav-studio, luna-edge-dev]
---

# LUNAV Intel-M — predictive maintenance stack

Predictive-maintenance monitoring dashboard. Backend streams sensor readings over a
WebSocket and scores each with a fused IsolationForest + LSTM autoencoder trained on
**normal** rows only; the frontend visualises scores and a RandomForest RUL estimate.

- Repo: `~/LUNAV-Intel-M` (git) · frontend `frontend/` (Next.js) · backend `backend/` (FastAPI + `.venv`)
- The backend ships its own venv; use `backend/.venv/bin/python`, never a global interpreter.

## When to Use

- "Start / restart / bring up the Intel-M dashboard or process."
- The dashboard is blank, the stream is dead, or "is Intel-M running?"
- Changing anything in `backend/` or `frontend/` — read the wiring rules below first.

## Stack — 3 processes, all local, all in tmux

| Process | Port | tmux session | Command |
|---|---|---|---|
| Backend (FastAPI) | `127.0.0.1:8001` | `intel-backend` | `.venv/bin/python -m uvicorn app.main:app --port 8001 --host 127.0.0.1` |
| Frontend (Next.js) | `localhost:3000` | `intel-frontend` | `npm run dev` |
| Mac sensor agent | — | `intel-mac-agent` | `.venv/bin/python app/mac_agent.py` |

Start in that order: the agent POSTs to the backend and the frontend proxies to it, so a
backend that is not up yet looks like "the agent is broken" and "the dashboard is blank"
from two different symptoms.

```bash
cd ~/LUNAV-Intel-M/backend
tmux new-session -d -s intel-backend  -c ~/LUNAV-Intel-M/backend  ".venv/bin/python -m uvicorn app.main:app --port 8001 --host 127.0.0.1 2>&1 | tee -a ~/.hermes/logs/intel-backend.log"
cd ~/LUNAV-Intel-M/frontend
tmux new-session -d -s intel-frontend -c ~/LUNAV-Intel-M/frontend "npm run dev 2>&1 | tee -a ~/.hermes/logs/intel-frontend.log"
tmux new-session -d -s intel-mac-agent -c ~/LUNAV-Intel-M/backend ".venv/bin/python app/mac_agent.py 2>&1 | tee -a ~/.hermes/logs/intel-mac-agent.log"
```

Logs: `~/.hermes/logs/intel-{backend,frontend,mac-agent}.log`. `tmux ls` is the source of
truth for "is it running"; a process that died leaves no port listening.

## Verify before reporting "it's up"

`scripts/check_stack.sh` runs all of this in one shot. Minimum manual version:

```bash
curl -s localhost:8001/api/health      # {"status":"ok",...}
curl -s localhost:8001/api/status      # models_loaded, active_model, datasets, sessions
curl -s localhost:3000/api/health      # same body THROUGH the Next.js /api rewrite
wc -l  backend/data/mac_sensors_live.csv   # growing => the agent is really posting
```

Three separate green lights are required: backend health, the frontend returning 200, and
the Mac CSV row count advancing. A dashboard that loads with empty panels is a proxy or
buffer problem, not a bug in the page.

## Port and wiring rules

- **The stack is wired for 8001.** The backend README's quick start says `--port 8000`; ignore
  it. `8001` is what `backend/app/config.py` CORS, `frontend/next.config.js` rewrites, and
  `frontend/.env.local` (`NEXT_PUBLIC_WS_URL`) all point at. Changing the port means changing
  all three in the same edit, or the dashboard silently talks to nothing.
- **Next.js rewrites do NOT proxy a WebSocket upgrade.** REST goes through the `/api` rewrite;
  the live stream reads `NEXT_PUBLIC_WS_URL` directly. If the WS panel is dead while REST
  works, suspect the env var, not the rewrite.
- `8000` is reserved for Luna-EDGE — never bind Intel-M there.

## Pitfalls

- **`temp_c` is structurally 0 on macOS.** `psutil.sensors_temperatures()` returns nothing on
  macOS (no SMC access without a helper), so the agent falls through to its `except` branch and
  emits `0`. Do not debug this as a broken sensor; the Mac panel is CPU / RAM / disk / battery /
  processes / network / uptime.
- **The RUL model starts untrained.** `/api/status` and the health panel report
  `"degraded … No trained RUL model. POST /api/train-rul first."` That is the default state, not
  a fault — anomaly detection works without it. Train RUL before promising a health %.
- **The Mac agent fails silently.** Backend-down POSTs are logged at DEBUG and the loop keeps
  running, so a quiet log looks identical to a healthy agent. Confirm liveness from the
  backend side (`/api/mac-stream` buffer size, CSV row count), never from the agent log.
- **`data/mac_sensors_live.csv` is append-only and grows without bound.** Check its row count
  before training on Mac data, or a long-idle session re-ingests weeks of stale rows.
- **Nothing survives a reboot.** The agent is a plain tmux process, not a launchd service —
  there is no plist for it. After a restart, bring up all three sessions again.
- Backend startup logs `No persisted detector found` until a first successful `/api/train`;
  `models/detector.pt` is written after each train and auto-loaded on the next boot.

## References

- `backend/README.md` — API/WS surface, feature expansion (5 raw → 14 model inputs), the
  detector ensemble and the runnable verification scripts under `backend/tests/`.
- `scripts/check_stack.sh` — one-shot health/buffer/port probe.

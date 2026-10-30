---
name: predictive-maintenance
description: "AI predictive maintenance pipeline design."
version: 1.0.0
author: Neo
platforms: [linux, macos, windows]
---

# Predictive Maintenance

AI-driven predictive maintenance for industrial infrastructure (transformers, switchgear, motors, pumps). Unsupervised anomaly detection + supervised prediction layer.

## MARU's Context

- **Target**: TNB substations (Malaysia's national utility)
- **Stack**: Supabase + Cesium globe + LunaV Studio + PC2 GPU worker
- **Constraint**: software-first — no hardware builds
- **Data sources**: SCADA, vibration, temperature, acoustic, oil DGA sensors
- **Business model**: per-asset-per-year custody fee + verified maintenance history report

## Pipeline (6 Stages)

### 1. Data Collection

Sensors at the substation feed an edge gateway, which buffers and syncs to cloud.

| Sensor | Detects | Placement |
|--------|---------|-----------|
| Vibration (accelerometer) | Bearing wear, imbalance, misalignment | Transformers, motors, pumps |
| Temperature | Overheating, insulation degradation | Windings, oil, ambient |
| Current/Voltage | Load imbalance, harmonics, arcing | Busbars, feeders |
| Acoustic | Corona discharge, partial discharge | Switchgear, transformers |
| Oil quality (DGA) | Internal faults, insulation breakdown | Transformer oil tanks |

**Reality check**: Does the client already collect this via SCADA? If not → hardware installation required (cost + time). Substations may lack internet → edge gateway with local buffering.

### 2. Data Ingestion

```
Sensors → Edge Gateway (industrial PC / Raspberry Pi) → Cloud (Supabase)
                                  ↓
                            SCADA (if existing) → API → Cloud
```

Edge gateway role: local buffering when offline, protocol conversion (Modbus/OPC-UA → MQTT/HTTP), pre-processing (filtering, downsampling), store-and-forward.

### 3. Feature Extraction

Raw sensor data is noise. AI needs patterns.

| Raw Signal | Feature Extraction | Reveals |
|------------|-------------------|--------|
| Vibration | FFT → frequency spectrum | Bearing faults, imbalance, misalignment |
| Temperature | Rate-of-change, deviation from baseline | Overheating, insulation breakdown |
| Current | Harmonic distortion, load profile | Arcing, load imbalance |
| Sound | Spectral signatures | Corona discharge (specific frequency bands) |
| Oil DGA | Gas ratios (CH4, C2H2, CO, H2) | Internal faults, thermal decomposition |

### 4. Anomaly Detection (Unsupervised)

Learns "normal" from 3-6 months of continuous data. Flags deviations — **no failure labels needed**.

**Algorithms**:
- Isolation Forest — fast, works well on sensor data
- Autoencoder — neural network; high reconstruction error = anomaly
- LSTM Autoencoder — time-series, captures temporal patterns
- One-Class SVM — small datasets, clear boundaries

**Output**: anomaly score (0-1) per asset per time window. Flag when score > threshold (e.g., 0.85).

### 5. Prediction Layer (Supervised)

Anomaly ≠ prediction. To predict failure, need historical failure examples.

- Anomaly + labeled failures → supervised classifier
- Output: failure probability (0-100%) + predicted time-to-failure (days/weeks)
- Minimum: 20-50 labeled failure examples per asset type

**Algorithms**: Random Forest (interpretable), XGBoost (best accuracy), LSTM (remaining useful life prediction).

### 6. Alerting & Workflow

```
Anomaly detected → Alert → Create inspection task (LunaV Studio)
  → Assign inspector → Inspector confirms/rejects
  → Confirmed failures feed back to retrain model
```

Dashboard: Cesium globe with substations colored green/yellow/red. Health score per asset (0-100). Anomaly timeline + trend.

## Integration with Existing Stack

| Component | Tool | Role |
|-----------|------|------|
| Dashboard | Cesium globe (CDM/R-Tessera) | Substation health map |
| Inspection workflow | LunaV Studio | Task creation + assignment |
| Data storage | Supabase | Sensor data + model outputs |
| AI training | PC2 GPU worker | Model training + inference |
| Edge AI | Luna-EDGE | Real-time anomaly detection |

## Honest Gaps

| Gap | Impact | Mitigation |
|-----|--------|------------|
| Client data access | No data = no model | Start with simulation, prove value |
| Failure history | No prediction layer | Start with anomaly detection, build history over time |
| Connectivity | Substations offline | Edge gateway with local buffering |
| Scale | Thousands of substations | Start with 5-10 pilot substations |
| Sensor cost | Hardware investment | Use existing SCADA where possible |

## LUNAV Intel-M — Built Prototype (V0.1.0)

A working webapp at `~/LUNAV-Intel-M/` — FastAPI backend + Next.js frontend, dark glass LunaV family theme.

**Architecture:**
- Backend: FastAPI + scikit-learn (Isolation Forest) + PyTorch (LSTM Autoencoder), WebSocket streaming
- Frontend: Next.js 14 + TypeScript + recharts, 4 pages (Monitor, Models, Data, History)
- Data: AI4I predictive maintenance dataset (10K rows, 14 features: 5 raw + 9 derived)
- ML: Isolation Forest (n_estimators=100, contamination=0.05) + LSTM Autoencoder (hidden=64, 20 epochs)
- Verified: AUC 0.97 on test data, WebSocket streaming at 2 readings/sec, anomaly detection live

**Key design decisions:**
- Train on normal data only (Target=0), flag deviations — no failure labels needed
- Feature expansion: 5 raw sensors → 14 features (thermal delta, mechanical power, wear-normalized torque/speed) — **only applied when AI4I schema detected**; other datasets pass through as-is
- Streaming: WebSocket with adjustable rate (0.1-10 sec), anomaly zones highlighted in red on chart
- No CUDA required — Mac M1 Pro 16GB handles training in minutes
- Per-sensor anomaly attribution: backend computes `sensor_status` (value vs training min/max per sensor) and `exceeding_sensors` list — frontend shows which sensor breached and by how much

## RUL Prediction Layer (Added V0.2)

The app now has BOTH layers:

| Layer | What it does | Model | Data |
|-------|-------------|-------|------|
| Anomaly Detection | "Something is abnormal NOW" | Isolation Forest | AI4I machine sensors |
| RUL Prediction | "X cycles remaining, Y% failure risk" | Random Forest | NASA CMAPSS (100 engines run-to-failure) |

**RUL Model details:**
- Feature engineering: rolling mean/std (window=10), trend slope per sensor, op settings, engine age
- Health index: `100 * (1 - exp(-3 * rul / max_rul))` — 100%=healthy, 0%=failed
- Failure probability: `1 - exp(-H / rul)` for horizon H cycles
- Endpoints: `POST /api/train-rul`, `GET /api/rul-predict`, `GET /api/health`
- Frontend: HealthGauge (SVG semicircle), FailureProbability bars (30d/90d), trend indicator

**Datasets loaded:**

| Dataset | Type | Source | Status |
|---------|------|--------|--------|
| machine_sensors.csv | AI4I 2020 (10K rows, 339 failures) | UCI ML Repo | In app |
| transformer_etth1/2.csv | ETDataset (17K rows, 2yr monitoring) | GitHub (zhouhaoyi/ETDataset) | In app |
| transformer_ettm1/2.csv | ETDataset 15-min intervals | GitHub | In app |
| nasa_cmapss_fd001*.txt | 100 engines run-to-failure | NASA data portal | Downloaded |
| transformer_overview_mog_a.csv | 20K rows, 7 sensors + MOG_A label | Kaggle (user-downloaded) | In app |

**Mac Sensor Agent (live Mac health monitoring):**
See `references/mac-sensor-agent.md` for architecture, metrics, sleep/wake handling, and how to run the agent via tmux. Frontend polls `/api/mac-stream` every 2s when source=mac_sensors.

**Run (persistent, survives process kills):**
```bash
# Use tmux — plain background processes get killed (exit -9) on this machine
tmux new-session -d -s intel-backend 'cd ~/LUNAV-Intel-M/backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001'
tmux new-session -d -s intel-frontend 'cd ~/LUNAV-Intel-M/frontend && npx next start -p 3000'
# Verify:
curl -s http://localhost:8001/api/status
curl -s http://localhost:3000 | grep '<title>'
```

**Mac Sensor Agent (live Mac health monitoring):**
```bash
# Agent runs in tmux, samples every 2s, ~33MB RAM
tmux new-session -d -s mac-agent 'cd ~/LUNAV-Intel-M/backend && .venv/bin/python app/mac_agent.py'
# Verify:
curl -s http://localhost:8001/api/mac-stream | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Buffer: {d[\"count\"]} readings')"
```

Agent samples 13 metrics via psutil: cpu_percent, cpu_freq_mhz, mem_percent, mem_used_gb, mem_available_gb, disk_percent, disk_free_gb, battery_percent, battery_plugged, battery_secs_left, process_count, temp_c, net_sent_mb, net_recv_mb, uptime_hours.

**Sleep-aware design:** Agent detects gaps >30s = sleep, sends `{"event":"wake"}` on resume. Backend clears anomaly state on wake — no false alarms after lid-open.

**Frontend integration:** When source=`mac_sensors`, frontend polls `GET /api/mac-stream` every 2s (not WebSocket — the agent POSTs to backend, frontend polls the buffer). Chart renders raw sensor values; anomaly detection activates after training on collected data.

**Validation on transformer MOG_A data:** AUC 0.0171 (anti-correlated — MOG_A is a maintenance flag, not a sensor-visible fault). Decision: run pure anomaly detection (unsupervised), do NOT validate against MOG_A. The detector flags unusual sensor patterns without claiming to predict MOG_A alarms.

**NOTE:** Port 8000 is reserved for Luna-EDGE. LUNAV Intel-M backend uses **8001**.

## Build Path

1. ~~**Simulate**~~ — DONE
2. ~~**Prototype**~~ — DONE — LUNAV Intel-M webapp built and verified
3. ~~**Mac Sensor Agent**~~ — DONE — live Mac health monitoring via psutil
4. **Demo** — present to TNB with real sensor data streaming
5. **Pilot** — deploy on 5-10 real substations

## Open Issues (from code review)

1. RUL panel hardcoded to CMAPSS — shows jet-engine numbers for non-CMAPSS datasets. Needs gating.
2. Autoencoder not trained — "ensemble" is just Isolation Forest.
3. Failure probability formula assumes constant failure rate (no wear-out). Weibull would be better.
4. No ground truth for transformer anomalies — MOG_A doesn't correlate with sensor anomalies.

## Pitfalls

- **Anomaly detection is NOT prediction.** Unsupervised models flag "something is different" but cannot predict "it will fail in 14 days" without labeled failure data. Don't oversell anomaly detection as prediction to clients.
- **Feature extraction is where the value lives.** Raw sensor streams are useless without FFT, spectral analysis, or rate-of-change computation. Budget 60% of engineering time here.
- **Start with simulation, not hardware.** A working software demo on synthetic data is more persuasive than a half-built hardware prototype. MARU's rule: prove in software first.
- **Failure history is the bottleneck.** Without labeled failures, you only get anomaly alerts, not predictions. Collect failure records from day one — even paper-based ones.
- **Subagent parallel builds need a shared API contract.** When spawning frontend + backend subagents simultaneously, the frontend agent will GUESS the API shape and it will NOT match the backend. Always write a shared API contract file (endpoints, request/response shapes) BEFORE dispatching parallel builds. Verify by reading both agents' output and diffing the contracts before integrating.
- **WebSocket in Next.js needs an explicit backend URL.** Next.js rewrites do NOT proxy WebSocket upgrades. A same-origin `/ws/stream` will fail silently or with a 403. Fix: set `NEXT_PUBLIC_WS_URL=http://localhost:8000` in `.env.local` so the WebSocket hook connects directly to the backend.
- **Build green ≠ app working.** When a Next.js build passes but the app doesn't work in the browser, check the API contract first — the frontend is likely calling wrong endpoints or parsing wrong response shapes. Use `curl` to test every backend endpoint, then verify the frontend's API layer matches.
- **Multi-schema datasets break hardcoded preprocessors.** When a predictive maintenance app must accept different sensor datasets (AI4I machine sensors vs transformer ETDataset vs NASA CMAPSS), the preprocessor and detector MUST auto-detect numeric columns instead of hardcoding a specific schema. Pattern: drop known metadata columns (date, UDI, Target, etc.), keep all numeric columns, and only apply feature expansion when the exact AI4I 5-column schema is detected. Otherwise the app crashes with "missing required feature columns" on valid data.
- **Plain background processes get killed (exit -9) on this machine.** When starting long-running servers (uvicorn, next start), use `tmux new-session -d` instead of `background=true` or `nohup`. Plain background processes are killed when new background processes start. tmux sessions survive and can be checked with `tmux ls`.
- **Port 8000 is reserved for Luna-EDGE.** LUNAV Intel-M backend uses port 8001. Always check `lsof -ti:8000` before starting a new server on that port.
- **Domain-specific models must not cross-contaminate.** A RUL/health model trained on jet engines (NASA CMAPSS) must NOT display results when the user selects a transformer dataset. The frontend must check the dataset's domain and show "RUL not available for this dataset" rather than presenting jet-engine numbers behind a transformer label. This is a trust issue — users will take the numbers at face value.
- **backdrop-blur traps position:fixed modals.** CSS `backdrop-filter` creates a containing block for `position: fixed` descendants — modals inside a glass card render within the card bounds instead of covering the viewport. Fix: render modals via a React Portal to `document.body` (see `src/components/Portal.tsx` in LUNAV Intel-M). Always test modal centering, not just existence.
- **Non-numeric columns must be skipped, not coerced.** When auto-detecting numeric columns, use `pd.to_numeric(errors='coerce')` then check `.notna().any()` — timestamp columns coerce to NaN and drop ALL rows if not filtered first, producing an empty DataFrame and a confusing "Cannot fit on an empty dataset" error.
- **Kaggle datasets require authentication.** Direct download URLs return JSON error messages, not files. GitHub mirrors of Kaggle datasets are often 404. When a dataset is Kaggle-only, ask the user to download it manually and drop it in the data folder — don't waste time trying bypasses.
- **AUC < 0.5 means anti-correlation.** When validating an anomaly detector against labels, AUC below 0.5 means the model is WORSE than random — it scores normal readings higher than failures. Report this honestly. Do not oversell the detector or try to "fix" it by flipping scores. The label may simply not correlate with sensor patterns (e.g., maintenance flags vs sensor anomalies).
- **User language preference: English only.** MARU requires all responses in English. This is a standing preference, not a per-session choice.
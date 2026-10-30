---
name: ml-pipeline-webapp
description: "Build real-time ML monitoring dashboards."
version: 1.0.0
tags: [ml, anomaly-detection, rul, predictive-maintenance, fastapi, nextjs, websocket, scikit-learn, pytorch]
license: MIT
---

# ML Pipeline Webapp — Real-Time Monitoring Dashboard

Build web apps that stream sensor data, detect anomalies, and predict remaining useful life (RUL). Stack: FastAPI + scikit-learn + PyTorch backend, Next.js + recharts frontend, WebSocket streaming.

## Architecture

```
CSV Upload / Sample Dataset → Preprocess → Feature Extraction → Train Model → Stream → Detect → Alert → Record
                                                                            ↓
                                                              RUL Prediction + Health Index
```

### Backend (FastAPI)
- `app/ml/preprocessor.py` — load CSV, auto-detect numeric columns, StandardScaler
- `app/ml/detector.py` — AnomalyDetector (IsolationForest + LSTM Autoencoder)
- `app/ml/streamer.py` — SensorStreamer (rate-limited, looping, per-sensor status)
- `app/ml/rul_model.py` — RULModel (RandomForestRegressor, rolling features, health index)
- `app/routers/monitor.py` — WebSocket `/ws/stream`, POST `/api/train`, GET `/api/health`
- `app/ml/registry.py` — singleton for trained models

### Frontend (Next.js)
- `src/lib/ws.ts` — WebSocket hook with auto-reconnect, rolling window buffer
- `src/lib/api.ts` — REST helpers matching backend contract
- `src/components/LiveChart.tsx` — recharts with anomaly ReferenceArea bands
- `src/components/AnomalyLog.tsx` — per-sensor breach detail (value vs threshold)
- `src/components/RULPanel.tsx` — health gauge + failure probability bars
- `src/components/HealthGauge.tsx` — SVG semicircle gauge

## Critical Rules

### 1. Auto-detect columns — never hardcode feature names

The preprocessor, streamer, and detector must work with ANY sensor dataset. Drop known metadata columns (date, UDI, Target, etc.) and keep everything else numeric.

```python
# DO: auto-detect
drop_cols = {"UDI", "Product ID", "Type", "Target", "Failure Type", "date", "time"}
df = df.drop(columns=[c for c in df.columns if c in drop_cols])
numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

# DON'T: hardcode
missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
if missing:
    raise ValueError(f"Missing feature columns: {missing}")
```

### 2. Next.js WebSocket needs explicit backend URL

Next.js rewrites do NOT proxy WebSocket upgrades. Set `NEXT_PUBLIC_WS_URL` in `.env.local`:

```
NEXT_PUBLIC_WS_URL=http://localhost:8001
```

### 3. Frontend-backend API contract must match exactly

When building frontend and backend in parallel (e.g., via subagents), the API shapes MUST be reconciled before integration. A frontend written against a different contract will fail silently.

**Rule:** After parallel builds, diff the frontend `api.ts` against the backend routers. Fix mismatches before testing.

### 4. Verify before claiming success

When the user reports "still not working":
1. Check if servers are actually alive (`curl /api/status`)
2. Test the WebSocket directly (Python script)
3. Check browser console for exact error
4. Only claim success after live verification

### 5. Use TMUX for persistent dev servers

Background processes get killed when new ones start. Use tmux sessions:

```bash
tmux new-session -d -s backend 'cd ~/project/backend && .venv/bin/uvicorn app.main:app --port 8001'
tmux new-session -d -s frontend 'cd ~/project/frontend && npx next start -p 3000'
```

### 6. Fresh port to break stale code cycles

If patches don't take effect (backend running old code), kill and restart on a FRESH port. The old process may be holding the port with cached bytecode.

```bash
lsof -ti:8001 | xargs kill -9; sleep 2
# Start on 8010 to verify, then move back
```

### 7. Port reservations

- Port 8000 = LunaV EDGE (reserved)
- Port 8001 = LUNAV Intel-M backend
- Port 3000 = Next.js frontend

### 8. LSTM Autoencoder input size must match actual features

When training on non-AI4I data (different column count), the LSTM `input_size` must be `scaled.shape[1]`, not a hardcoded constant.

```python
# DO
self.autoencoder = LSTMAutoencoder(input_size=scaled.shape[1], ...)

# DON'T
self.autoencoder = LSTMAutoencoder(input_size=INPUT_SIZE, ...)
```

### 9. Auto-retrain on schema mismatch

When the selected dataset has a different number of features than the trained detector, auto-retrain with IsolationForest only (skip LSTM — it's slow and schema-specific):

```python
if detector is not None:
    expected = len(detector.preprocessor.feature_columns)
    actual = data.shape[1]
    if expected != actual:
        detector = AnomalyDetector(model_type="isolation_forest", ...)
        detector.fit(labeled, fit_autoencoder=False)
```

### 10. Handle missing fields in frontend gracefully

When the backend response may omit optional fields (e.g., `trend` before RUL is trained), use optional chaining:

```tsx
{health.trend ? health.trend.charAt(0).toUpperCase() + health.trend.slice(1) : '—'}
```

## RUL Prediction Layer

Anomaly detection = "something is abnormal NOW"
RUL prediction = "X cycles remaining, Y% failure probability in 30 days"

### Feature engineering for RUL
- Rolling mean (window=10) per sensor
- Rolling std (window=10) per sensor
- Trend slope (linear regression over window=10) per sensor
- Operating settings (raw values)
- Engine age (current cycle / max cycle)

### Health index formula
```
health = 100 * (1 - exp(-3 * rul / max_rul))
```

### Failure probability
```
P(fail within H cycles) = 1 - exp(-H / rul) if rul > 0 else 1.0
```

## Testing Checklist

1. Backend: `curl /api/status` returns `{"status": "ok"}`
2. WebSocket: Python test script connects and receives readings
3. Frontend: `curl /api/status` (proxied) returns same response
4. Transformer data: stream works with non-AI4I columns
5. RUL: train via `/api/train-rul`, then `/api/health` returns health index
6. Anomaly log: per-sensor breach detail renders correctly
7. No console errors in browser (F12)

## References

- `references/datasets.md` — public datasets for predictive maintenance (AI4I, NASA CMAPSS, ETDataset)
- `references/api-contract.md` — frontend-backend API shape reference

# Frontend-Backend API Contract

## REST Endpoints

### GET /api/status
Returns current model state.
```json
{
  "status": "ok" | "degraded",
  "models_loaded": {"isolation_forest": true, "autoencoder": false, "ensemble": false},
  "active_model": "isolation_forest",
  "datasets": ["machine_sensors.csv", "transformer_etth1.csv"],
  "sessions": 0,
  "features": ["Air temperature [K]", "..."],
  "version": "0.1.0",
  "detail": null
}
```

### POST /api/train
Trains anomaly detector on a dataset.
- Form fields: `dataset` (filename), `model_type` (isolation_forest|autoencoder|ensemble)
- Returns: `{ok, message, data: {model_type, dataset, rows_trained_on, n_features, ...}}`

### POST /api/train-rul
Trains RUL model on NASA CMAPSS data.
- Form fields: `dataset` (filename)
- Returns: `{ok, message, data: {model_type, dataset, rows_trained_on, ...}}`

### GET /api/health
Returns RUL + health index.
```json
{
  "status": "ok" | "degraded",
  "health_percent": 75.3,
  "rul_cycles": 120,
  "failure_probability": 0.15,
  "horizon": 30,
  "max_rul": 200,
  "unit_id": null,
  "detail": null
}
```

### GET /api/datasets
Returns list of available CSV files.
```json
[{"name": "machine_sensors.csv", "size_bytes": 522048, "rows": 10000, "modified": "..."}]
```

### GET /api/preview?name=X&rows=5
Returns first N rows of a dataset.
```json
{"name": "machine_sensors.csv", "rows": 10000, "columns": [...], "features": [...], "preview": [{...}]}
```

### GET /api/history
Returns past monitoring sessions.
```json
{"count": 2, "sessions": [{"session_id": "...", "source": "...", "model_type": "...", "total_readings": 240, "anomaly_count": 5}]}
```

## WebSocket Protocol

### Connect
```
ws://localhost:8001/ws/stream
```

### Client → Server (initial config)
```json
{"source": "machine_sensors.csv", "rate": 2.0, "model_type": "isolation_forest", "threshold": 0.6}
```

### Server → Client (ready)
```json
{"type": "ready", "config": {...}, "stats": {...}, "model": {...}}
```

### Server → Client (reading)
```json
{
  "type": "reading",
  "timestamp": "2026-10-14T08:00:00Z",
  "readings": {"Air temperature [K]": 298.1, "...": ...},
  "anomaly_score": 0.307,
  "is_anomaly": false,
  "index": 42,
  "sequence": 42,
  "sensor_status": {"Air temperature [K]": {"value": 298.1, "min": 295.3, "max": 304.5, "exceeding": false}},
  "exceeding_sensors": []
}
```

### Client → Server (stop)
```json
{"action": "stop"}
```

## Frontend API Helper Pattern

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { const body = await res.json(); detail = body?.detail ?? detail; } catch {}
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}
```

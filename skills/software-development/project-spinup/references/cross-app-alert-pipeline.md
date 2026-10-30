# Cross-App Alert Pipeline Pattern

Use when a new project spans multiple existing live apps and needs a server-side
AI/analytics layer to glue them together with alerts.

## Control-surface template

| Layer | Owner | Role |
|-------|-------|------|
| **App A: detail workspace** | Field engineer / inspector | Create/edit asset records, defects, documents, IoT readings, AI analytics tab |
| **App B: command dashboard** | Operations command | Fleet/aggregate status, critical alarms, click-through to App A |
| **Edge / field devices** | Autonomous | Sensor ingest, local buffering, telemetry to backend |
| **Server-side AI layer** | Server-side | Polls time-series → RAG + logical rules → writes alerts/recommendations back |
| **Client admin** | Client | Thresholds, alert review, report export, integrations |

## Data-flow pattern

```
Edge / field → backend time-series
        ↓
AI layer (polls time-series)
        ↓
RAG corpus + logical algorithms
        ↓
Writes alerts/recommendations → backend alerts table
        ↓
    ┌───────────────────────────────┐
    ▼                               ▼
App A analytics tab           App B command dashboard
- trends + forecasts          - aggregate status
- alert history               - critical panel
- prescriptive actions        - click-through to App A
```

## AI-layer placement

Run it server-side on dedicated hardware, NOT in the browser.

Rationale:
- Deterministic scheduling/polling
- Keeps large model weights off client devices
- No cloud-GPU dependency if local inference is used
- Can write alerts back to the shared backend without client auth complexity

## Fine-tune vs RAG

Use both for production.

- **Fine-tune** for domain language fluency and output-format consistency
- **RAG** for live factual grounding in current docs/standards/regs

Together: model speaks the client's domain language AND grounds answers in live
authoritative documents.

## Schema seam

Keep AI-generated data in the same backend project as the apps, but in a
dedicated schema/tables so it does not couple App A or App B data models.

Recommended tables:
- `alerts` — id, asset_id, severity, title, body, source, created_at, resolved_at
- `recommendations` — id, asset_id, recommendation_text, confidence, created_at
- `rag_documents` — id, source_uri, chunk_text, embedding, last_indexed_at

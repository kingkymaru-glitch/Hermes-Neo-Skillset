# Agentic ERP / Business-OS Pattern (reusable)

Captured from the ERP-PILOT greenfield build. Reuse this skeleton for any agentic
business / multi-module system, not just ERP.

## Core architecture — 3 strict layers
1. **Deterministic engine (NO LLM).** Every number, transaction, scrape, send is a
   pure tool/function writing to a structured store. The LLM never computes or acts
   irreversibly. This kills hallucination-in-money, cost, latency, eval risk at the source.
2. **Agent harness (LLM, bounded).** The agent runs INSIDE the Hermes harness, which
   drives tool-use, planning, and memory. Responsibilities are ONLY:
   - Reporting (format aggregates per fixed template)
   - Drafting outbound copy
   - Proposing actions (with evidence) into a proposals queue
   - Tool-use loop: inspect state -> call deterministic tools -> observe results; never holds a computed number.
3. **Human approval gate.** Nothing irreversible executes until `proposals.status = approved`.
   Per-action mode: `Manual` (always ask) or `Automated` (pre-whitelisted safe classes only,
   e.g. greeting new signups).

## LLM provider — Nous Portal, model-selectable
MARU's explicit call: pick the model from Nous Portal so the reasoning logic can improve
over time as models evolve, with ZERO code rewiring. Architect the harness provider-agnostic.
Dev on Nous; production swap (Claude/OpenAI) is a config change, not a rewrite.

## Shared data layer (the keystone)
One structured store (Supabase) with COMMON KEYS so modules share real data, not free text:
`customer_id`, `product_id`, `order_id`, `ledger_id`. Plus cross-cutting tables:
- `audit_log` (actor tool|agent|user, timestamp, payload, result) -> also episodic memory source
- `proposals` (module, type, payload, evidence, status, decided_by)
- `tuning` (learned policy adjustments, evidence, approved_by) -> observable learning
- `tax_config` (versioned rate tables, e.g. SST) -> auditable, update without code

## Observable learning (agentic, never silent)
The agent improves over time but every evolution is transparent + gated:
1. **Episodic memory** -> agent queries its own `audit_log` history (e.g. "which greetings
   converted last quarter") from structured rows, NOT LLM recall.
2. **Learned policy** -> proposal rules start as MARU's strategy. Harness tracks approved/
   rejected proposals + outcomes, then proposes a `tuning` adjustment (row + evidence +
   who approved). Tuning change only takes effect after human sign-off.
LLM reasons; data proves; human approves.

## CRM-as-process (not spreadsheet)
Every module = a STATE MACHINE, not a table. Transitions are events firing tool actions.
Example CRM: LEAD -> QUALIFIED -> PROPOSAL -> NEGOTIATION -> WON/LOST. Each transition
writes `audit_log`. This is what makes it a working process, not a contact dump.

## Coordinator (synthesis, not planner)
Runs a synthesis job (daily/on-demand): reads cross-module aggregates, applies YOUR business
rules (e.g. "pipeline < 3mo burn AND stock cover > 60d -> flag promo + pause procurement"),
emits a Coordinator Report (LLM-formatted) + optional proposals. A rule engine + reporter,
not a free-thinking planner -> trustworthy and debuggable. Needs >=2 real modules to cross-read.

## Build sequence (founder preference: SEQUENTIAL, no parallel)
Module-by-module. Founder: "module by module, i dont trust parallel works."
CRM (first vertical, lowest-risk, exercises every layer) -> Accounting/SST (deterministic calc
pattern) -> Finance -> SCM -> Procurement -> Marketing -> Change-Mgmt.
Coordinator layer after >=2 modules exist. Phase 0 (shared schema) precedes all.

## Dev-protocol template (inject into README for co-dev / public repos)
```
## Dev Protocol
- Discussion-first. No code without MARU + the module's domain owner sign-off.
- Any agent coding a module MUST: (1) present its understanding of the module spec,
  (2) explicitly ask MARU + the domain owner to confirm before implementation.
- Keep the deterministic/agent/layer split. LLM never computes numbers or acts without approval.
- All learning observable via audit_log + tuning tables; no silent model changes.
```

## Visibility flip gotcha (public co-dev repos)
`gh repo edit <repo> --visibility public` REQUIRES `--accept-visibility-change-consequences`
or it errors out. Include the flag when flipping programmatically.

## MIT vs Apache-2.0 for co-dev
MIT = simple permissive. Apache-2.0 = adds explicit patent grant (safer for contributors).
Default to MIT unless contributor patent protection matters.

---
name: proposal-response
description: Draft RFI/RFP responses for SS Rover opportunities.
tags:
  - proposal
  - rfi
  - rfp
  - tender
  - pitch
---

# Proposal Response

Use when the user asks to prepare, rewrite, or review an RFI/RFP response or formal tender submission, especially when it must map requirements to existing platforms and products.

## Core workflow

1. Confirm submission constraints first: deadline, format, required sections, page limits, and whether attachments/artifacts are allowed.
2. Identify the single legal entity that will submit and keep every platform/product framed as owned by that entity. Avoid “entity A / entity B” framing.
3. Extract every requirement from the source document and place them into a 3-column table: Requirement | Delivery | Tools/Platforms Used.
4. Write a short narrative section before the table that states the architectural approach, reuse of proven platforms, and scalability claim.
5. Provide a pipeline/architecture section with one descriptive paragraph plus a layer table; include an explicit image-generation prompt block if no approved infographic is ready. Optionally wrap the prompt in a yellow highlight div for visibility.
6. Include a known-challenges/mitigations section for site-specific operational hazards. Frame hazards in bold, then provide mitigations as a matching bullet list.
7. Separate “delivered now” from “upgrade path / additional capabilities.” The pilot scope must match exactly what was requested; everything else goes into an upgrade section.
8. Equipment datasheets should be a single table with columns: Item | Purpose | Key Specifications | Integration. Distinguish between survey hardware and field-agent hardware; include power, communications, vision, lighting, environmental, and motion modules. Include Drone Lidar when structural baseline capture is relevant.
9. Field agent units must include a data policy sub-block: local logging cadence, end-of-day summary, rolling buffer retention period, anomaly-triggered alert and backfill behavior, and overwrite rules.
10. Case studies must be framed as prior work by the submitting entity for the target client, with lessons directly mapped to the proposed solution.
11. Pricing, CAPEX/OPEX, and timeline tables must be clearly labeled as indicative/draft until finalized. Split into POC and Full Scale Deployment when both paths are proposed.

## Naming discipline

- Primary system name: ARRAS-style branding for this specific opportunity.
- Internal platforms keep their canonical names: WAVE, LunaV, ROVER-KIT.
- In the response, surface capabilities as `ARRAS: <Module>` and map them back to the internal platform in the “Tools/Platforms Used” column.
- Never use standalone WAVE/LunaV/ROVER-KIT as the company name in customer-facing documents.

## Upgrade packaging

- Always include an upgrade or scale-up section at the end.
- Use explicit module names so future phases feel like expansion, not new proposals.
- State the commercial model for scale-up separately from the pilot fixed-price turnkey model.

## Pitfalls

- Do not mix pilot scope with scale-up scope in the same deliverable table.
- Do not leave placeholder tables unlabeled; every [tbd] must be marked clearly.
- Do not invent customer standards; if referencing standards like NDWQS, keep them as stated in the RFI.
- Do not promise permanent 24/7 live transmission if the design uses end-of-day sync with anomaly-triggered alerts.

## Outputs

- Markdown response document
- Folder structure on Desktop named after the opportunity, containing the response and any supporting artifacts
- Naming convention reference document if multiple legacy platform names must be unified

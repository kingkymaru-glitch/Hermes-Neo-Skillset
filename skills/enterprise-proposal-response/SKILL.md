---
name: enterprise-proposal-response
description: Use when responding to RFIs, RFPs, or RFQs for enterprise/government technology projects. Governs document structure, entity naming, requirement mapping, cost presentation, and narrative discipline for technical and commercial proposals.
---

# Enterprise Proposal Response

Use when responding to RFIs, RFPs, or RFQs for enterprise/government technology projects. Governs document structure, entity naming, requirement mapping, cost presentation, and narrative discipline for technical and commercial proposals.

## Trigger

User asks to draft, write, review, or structure a proposal response for a tender, RFI, RFP, or similar procurement exercise. Applies to both pilot/POC scopes and full-scale deployment sections.

## Core Principles

1. Single-entity discipline. The responding company is ONE legal entity. Its platforms, products, and frameworks are sub-brands or modules, not co-equal entities. Never write "Company A / Product B" as if they are partners. Correct: "Company A's Product B" or "Product B, by Company A".

2. Primary system branding. Establish one overarching system name for the solution. All functional modules are branded under that system: `ARRAS: Command Centre`, `ARRAS: Predictive Analytics`, etc. Existing internal platform names may be referenced only as the foundation beneath the primary system.

3. Deliver-exact-first. The proposal must map every stated requirement from the procurement document to a specific delivery. Do not bury required items inside upgrade narratives. Additional capabilities belong in a clearly separated "Upgrade Path" or "Additional Capabilities" section after all required sections are complete.

4. De-risk with proven experience. If the team has prior operational experience in the same domain or with the same client, lead with it. Use specific metrics: dates, locations, outcomes, lessons learned. Frame the new proposal as the scalable evolution of proven work, not a fresh start.

5. Challenge → mitigation structure. For harsh operating environments, explicitly list known challenges (GPS-denied, no power, no coverage, confined access, lightning, etc.) and pair each with a concrete mitigation. Show the site constraints are understood, not underestimated.

## Document Structure

Use this section order unless the procurement document explicitly mandates another:

1. Executive Summary — scope, hardware, software, differentiator, timeline
2. Company Profile — legal entity, team, core platforms as sub-brands
3. Technical Proposal
   - Narrative paragraph: what the RFI requests and how the company's existing platforms make this a blueprint integration rather than greenfield development; emphasize scalability
   - Pipeline description: 200-word data-flow narrative covering field → comms → platform → application → AI, with explicit AI/ML/LLM components if applicable
   - Infographic prompt block (yellow-highlighted) + table with layers, functions, and key components
   - Requirement mapping table: `RFI Requirement | ARRAS Delivery | Tools / Platforms Used`
   - GPS-denied / known challenges section: challenge description + mitigation mapping
4. System Architecture — placeholder for diagram + legend table
5. Equipment Datasheets — table format: `Item | Purpose | Key Specifications | Integration`
6. Preliminary Cost Estimation
   - Split into POC and Full Scale Deployment
   - Each with CAPEX table and OPEX table
   - Include development hardware (Mac Mini, MacBook Air) in software line or as dedicated hardware line
   - Training as lump sum unless otherwise specified
7. Project Timeline — phased by month, aligned to POC or full-scale
8. Case Study — prior work with metrics table, lessons applied, strategic value
9. Commercial Information — model, payment terms, pricing reference, vendor registration status, after-sales support
10. Deliverables — checklist table
11. Upgrade Path & Additional Capabilities — separate section for non-required features, future modules, and scale-up narrative
12. Appendix

## Formatting Rules

- Requirement mapping: 3-column markdown table. Columns: `RFI Requirement | ARRAS Delivery | Tools / Platforms Used`
- Pipeline description: one narrative paragraph, then a yellow-highlighted infographic prompt block, then a table with columns `Layer | Function | Key Components`
- Equipment list: 4-column markdown table. Columns: `Item | Purpose | Key Specifications | Integration`
- Cost tables: 4-column markdown table. Columns: `Item | Quantity | Unit Cost (RM) | Total (RM)`
- Case study results: metrics table with parameter columns
- Lessons applied: 2-column table. Columns: `POC Limitation | ARRAS Solution`
- Infographic prompt: wrap in `<div style="background-color: #fff3cd; padding: 1em; border-left: 4px solid #ffc107; margin: 1em 0;">` for yellow highlight

## Naming Convention Pattern

When integrating multiple internal platforms under one primary system name:

| Internal Platform | ARRAS Module Name | Function |
|-------------------|-------------------|----------|
| WAVE Command Centre | ARRAS: Command Centre | Centralised dashboard |
| WAVE Predictive Analytics | ARRAS: Predictive Analytics | Forecasting, trends |
| WAVE Anomaly Detection | ARRAS: Anomaly Detection | Alerts, outliers |
| LunaV Digital Twin | ARRAS: Digital Twin | 3D visualisation |
| LunaV Spatial Inspection | ARRAS: Spatial Inspection | Proxy records, dimensions |
| ROVER-KIT Edge Comms | ARRAS: Edge Communications | GSM/LoRa, message broker |
| ROVER-KIT Sensor Framework | ARRAS: Sensor Framework | Edge firmware, device mgmt |

Usage: first mention uses full mapped name in parentheses; subsequent mentions use short `ARRAS: Module` form. Internal platform names stay internal.

## Field Agent Data Policy Pattern

For edge/IoT nodes with intermittent connectivity and no permanent power:

- Log all basic sensor readings locally
- Transmit daily summary to central platform at end of day
- Retain raw logs for 7 days locally
- On anomaly detection (gyro movement, YOLO defect, temperature spike, etc.): immediately alert central platform and transmit previous 5 days of raw data
- If no anomaly within 7 days: overwrite buffer after sending 7-day average summary

## Cost Estimation Pattern

- POC: smaller quantities, include all development hardware (Mac Mini, MacBook Air), lump-sum training
- Full-scale: bulk quantities (1,600+ nodes), 2x ROV fleet, 2x drones, 4x Mac Mini (2 backup + 2 continuous updates), bulk comms/power/solar
- Full-scale CAPEX must EXCLUDE POC established costs to avoid double charging. Add an explicit note above the full-scale section: "Full-scale deployment excludes POC established costs to avoid double charging or double counting. Items already deployed during the POC phase are not repeated below."
- Split CAPEX and OPEX
- Software development line item should explicitly mention: local storage, client data ingestion + standards integration, AI/ML + LLM training, webapp development, dev machines, tools and licences
- Integration/commissioning: per-site line item
- Training: lump sum for POC, lump sum or per-session for full-scale
- Calibration: per-site per-call line item, excluding claimable costs
- OPEX fixed total should exclude per-site calibration calls

## Post-Submission Meeting / Verbal Pitch

After the written proposal is submitted, the next milestone is usually a client call or presentation. Treat this as a separate deliverable, not an afterthought.

### Pitch structure for a technical proposal call
1. Restate the client's pain in their language — not your platform's features.
2. Present ONE overarching system name, then walk the layered pipeline from field to AI.
3. Lead with proven experience: a specific prior deployment with metrics.
4. Map 2–3 RFI requirements to deliverables live — show you read their brief.
5. Introduce the phased path: pilot → scale-up, with clear go/no-go.
6. Separate "what we deliver now" from "upgrade path" explicitly.

### Demo discipline
- Do not demo the internal platform name; demo the primary-system branded module.
- Keep the demo to the layers the client asked about.
- If you show a live platform, ensure the browser tab URL/branding matches the primary system name, not an internal tool.

## Design-First Gate Before Implementation

When a written proposal includes a future software/dashboard commitment and the client meeting confirms direction, do not start building immediately. Hold a control-surface discussion first.

### Required discussion before any code
- Who acts where? Define read-only vs create/edit roles per surface.
- What is the primary navigation hierarchy? New tab vs new app vs existing route.
- Which data belongs to which surface? Aggregate vs detail vs raw.
- What is the data flow direction? Edge → central → dashboard → detail view.
- What integrations are real vs roadmap? Be honest about what exists now vs what will be built.

### Output of this discussion
A short architecture brief: surfaces, roles, data ownership, and flow. Only after this is agreed does implementation start.

## Pitfalls

- Do not write the company and its products as separate entities. "SS Rover Sdn Bhd / LunaV Solutions" is wrong. Use "SS Rover Sdn Bhd (LunaV)" or "SS Rover Sdn Bhd's LunaV platform".
- Do not place required deliverables in the upgrade section. The upgrade section is strictly for non-requested value-adds.
- Do not use standalone legacy platform names in client-facing documents. Always map to `ARRAS: Module` form.
- Do not promise features in the main body that are only in the upgrade path. Keep the two tiers distinct.
- Do not forget to include development hardware (Mac Mini, MacBook Air) in cost tables when specified by user.
- Do not mix POC and full-scale quantities in one cost table. Split into two sections.
- Do not skip the verbal pitch prep after submission. A strong document paired with a weak call loses the bid.
- Do not start coding the promised dashboard before the control-surface discussion. Agree on who-acts-where first.

## Support Files

- `references/naming-convention.md` — unified brand mapping template
- `references/proposal-structure.md` — detailed section-by-section template
- `references/pipeline-infographic-prompt.md` — ready-to-use image generation prompt
- `references/post-submission-meeting-prep.md` — call agenda, pitch flow, and demo checklist for client meetings after RFI submission
- `templates/rfi-response-template.md` — full markdown skeleton for rapid authoring

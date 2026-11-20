# Engineering (Hermes adaptation)

Matt Pocock-style engineering skills, adapted for Hermes. In Hermes every
skill is model-invoked via the skills index — the Claude Code/Codex
invocation split below is upstream context only (see
`references/upstream-docs/matt-invocation.md`).

2026-11 lean restructure: several skills here were merged into canonical
skills elsewhere in this repo. Their full content is preserved in the
winner's `references/merged/` folder.

## Skills in this folder

- **[triage](./triage/SKILL.md)**: Move issues through a state machine of triage roles.
- **[improve-codebase-architecture](./improve-codebase-architecture/SKILL.md)**: Scan a codebase for deepening opportunities, present a visual HTML report, then grill through the picked one.
- **[setup-matt-pocock-skills](./setup-matt-pocock-skills/SKILL.md)**: Configure a repo for these skills (issue tracker, triage labels, domain doc layout). Run once per repo.
- **[to-spec](./to-spec/SKILL.md)**: Turn the current conversation into a spec and publish it to the issue tracker.
- **[to-tickets](./to-tickets/SKILL.md)**: Break a plan/spec/conversation into tracer-bullet tickets with blocking edges.
- **[implement](./implement/SKILL.md)**: Build the work described by a spec or tickets (absorbed `implement-spec`), driving TDD at pre-agreed seams and closing with a code review before committing.
- **[wayfinder](./wayfinder/SKILL.md)**: Plan work bigger than one session as a shared map of decision tickets, resolved one at a time.
- **[retro](./retro/SKILL.md)**: Suggest environment improvements after a coding session, most severe first.
- **[research](./research/SKILL.md)**: Investigate against high-trust primary sources; capture a cited Markdown file.
- **[domain-modeling](./domain-modeling/SKILL.md)**: Build/sharpen the project's domain model; update GLOSSARY.md and ADRs inline.
- **[codebase-design](./codebase-design/SKILL.md)**: Vocabulary and discipline for deep modules: small interfaces, clean seams.
- **[wizard](./wizard/SKILL.md)**: Generate an interactive bash wizard for steps only a human can perform.

## Merged into canonical skills (content preserved)

| Former skill | Now lives in |
|---|---|
| tdd | `software-development/test-driven-development` |
| diagnosing-bugs | `software-development/systematic-debugging` |
| code-review | `software-development/requesting-code-review` (`references/merged/matt-code-review.md`) |
| prototype | `software-development/spike` |
| pr | `software-development/github` (PR-body guidance in its references/templates) |
| grill-with-docs | `matt-productivity/grilling` |
| ask-matt (router) | archived — the Hermes skills index is the router |

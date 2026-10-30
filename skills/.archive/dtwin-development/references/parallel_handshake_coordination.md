# DTWIN Parallel-Agent Handshake (Neo/Trinity/Smith)

MARU runs multiple Hermes agents on ONE Mac against `~/DTwin`. The coordination
protocol (authoritative copy `~/DTwin/docs/AGENT_HANDSHAKE.md`) is owned &
maintained by the `parallel-agent-handshake-neo` skill — that skill is
USER-OWNED, so patch it via `hermes curator adopt parallel-agent-handshake-neo`
first, or tell MARU to update it.

Pitfalls confirmed this session:
- Trinity may momentarily DELETE the repo `AGENT_HANDSHAKE.md` while rewriting
  it ("writing the handshake file now into docs/"). If missing: fall back to the
  Obsidian mirror `~/Documents/obsidian_maru_1/Projects/DTwin_Handshake.md` +
  `git log trinity`; re-read the repo copy after she commits. Do NOT recreate
  it from scratch.
- Branch isolation: Neo=`neo`, Trinity=`trinity`, LOCAL-ONLY (no origin).
- Port map: DTWIN server :8753 (ROOT=~/DTwin). TriniD is separate (:9877 free,
  :8787 is Hermes' own msgsrvr — not a DTwin clash).
- Always claim (WORKING) before editing shared DTWIN assets; release (DONE +
  handoff note) when done.

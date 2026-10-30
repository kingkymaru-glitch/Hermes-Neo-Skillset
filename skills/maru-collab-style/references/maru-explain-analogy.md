# MARU analogical-explanation template

Use when MARU asks to "understand properly" / "explain like I'm 15" / "elaborate".
Goal: he must not misunderstand the point, so strip jargon from the picture.

## Method
1. Pick ONE concrete real-world actor per system component (person, object, place).
2. Describe the data/trigger FLOW between them as a plain story — no tech words.
3. Only after the picture is clear, map each actor back to its real component +
   name the technical term once.
4. Close with a one-line translation ("in real terms: X = Y").

## Worked archetype (LUNAV / ROVER-KIT wedge, 2026-08-25 — landed well)
- Jetson / Luna-EDGE = a security guard in a room watching a CCTV screen.
- The detection ("intruder!") = the guard pointing at HIS OWN screen — nobody
  else hears it yet.
- R-Tessera / LunaV = the big screen in the other building that should light up
  red. (Already built + proven; just needs the message.)
- The ADAPTER (G1) = telling the guard "when you see something, shout it down the
  radio to the other building."
- RPi5 / MQTT = a MAILBOX next to the guard: he drops the message in (always
  works), the mailbox saves it and forwards it when the line is clear, and holds
  everything if the far building goes dark for an hour. Many guards can all drop
  into the same mailbox; it lines them up and delivers in order.
- Why Pi5 ≠ Jetson as mailbox: the Jetson is a WEAK guard (slow, legacy) whose
  ONLY job is seeing intruders; making it also the server starves the detection.
  Pi5 is the natural hub (strong, modern). Not mainly cost — duty-separation.

## Anti-patterns
- Do NOT start with "It's a pub/sub broker with an edge inference node..." — that
  is the jargon he asked to avoid.
- Do NOT defend an earlier target if he redirects (e.g. scream → R-Tessera not
  LunaV Solutions). Update the analogy's "far building" and move on.

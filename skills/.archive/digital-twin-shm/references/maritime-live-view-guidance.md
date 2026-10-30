# Maritime Live View Guidance

Policy for MARU demo stability:
- Prefer **one bounded vessel source**, not multiple competing sources shown live.
- If the user wants “live ship tracking,” use the limited existing VesselAPI tile path because it is bounded.
- Do **not** add a second live AIS stream, global ship overlay, or full ocean sweep by default.
- “Small-area / limited view” is the intended demo mode unless the user explicitly asks for wide-area tracking.

What this means for future coding agents:
- No AISStream reopen without explicit user approval.
- No expanding bounding tiles to global tiles.
- If internet/quota fails, show empty/offline state honestly; do not synthesize vessels.

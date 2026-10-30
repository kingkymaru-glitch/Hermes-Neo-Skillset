# Pitfall — never edit Graphify/ notes directly

In this user's vault (`/Users/kamarulhk/Documents/obsidian_maru_1`), the notes
under `Graphify/` are AUTO-GENERATED MIRRORS. Evidence: each carries
`source_file: "..."` in its frontmatter pointing back at the origin note.

- Editing a `Graphify/` mirror is wasted work — the next Graphify re-index
  overwrites your edits from the source.
- Always edit the SOURCE note referenced by `source_file:` (typically under
  `Projects/` for this vault), then let the mirror regenerate.
- LunaV session example: editable source was `Projects/SS Rover Cloud.md`;
  `Graphify/SS Rover Cloud.md` and `Graphify/LunaV Solutions — 3D ... SaaS.md`
  were extracts to leave alone.
- Graphify also auto-creates `HermesProgress.md` / `VAULT MAP.md` mirrors
  under `Graphify/` — the real working copies are the top-level ones. Patch
  the top-level files, not the `Graphify/` copies.

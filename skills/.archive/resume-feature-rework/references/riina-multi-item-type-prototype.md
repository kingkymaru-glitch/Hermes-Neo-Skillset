# RIINA React Prototype Notes

This file records the efficient continuation pattern for this multi-session
Vite+React+TS prototype, especially after an empty assistant turn.

## Preferred continuation after empty assistant output
- Do not re-greet or re-explain the empty turn.
- Publish ONE short paragraph: what is still pending, the next edit target,
  and the exact files/paths involved.
- Then continue with the smallest possible read/patch pair.

## Item type expansion pattern
- Keep one generic detail/edit screen for Task / Initiative / Co-Curricular.
- Add the type discriminator to the shared `itemType` contract and pass it
  through the create/edit route.
- Update empty-state copy once at the list view; do not duplicate copy-per-type.

## Verification priority
- `npm run build` is the meaningful gate.
- Do not use oxlint/npm run lint as a hard stop here because this workspace
  has persistent unmatched-pattern noise unrelated to the changed files.

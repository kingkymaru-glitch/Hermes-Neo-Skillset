---
name: ssr-proposal-docx
description: Use when building SS Rover proposals as .docx.
---

# SS Rover Proposal / RFI Response (.docx)

Build formal client-facing proposals in SS Rover's house style, matching the
Air Selangor ARRAS document and the TNBR/Integrax underwater proposal.

Reference templates (read these to re-derive the look):
- `~/Desktop/SSR/Integrax Underwater Baseline Study Proposal - TNBR-rev1.pdf`
- `~/Desktop/Air Selangor - Prelim Bathy Assessement and Integration POC Report_Rev 0.pdf`

Reusable builders (copy and adapt):
- `~/Desktop/AIR SEL/build_arras_docx.py` — md -> styled docx
- `~/Desktop/AIR SEL/make_diagrams.py` — matplotlib architecture/pipeline figures

## House format

- A4 (21.0 x 29.7 cm), margins 2.2 cm L/R, 2.4 top, 2.0 bottom
- Header: SSR logo (transparent bg) + `SS ROVER SDN BHD  (Company Reg. No: 1403860-M)`
- Footer right: `Page <PAGE field>   |   <Doc Title>  (<Doc No>)`
- Numbered sections: `1.0`, `1.1`, `2.0` ... (not just `##`)
- TOC: insert a real `TOC \o "1-2" \h \z \u` field, never a hand-typed list
- Cover: logo, "PROPOSAL FOR", title, subtitle, doc-control table, confidentiality note
- Body Calibri 10 / headings Arial bold; tables 8.5-9pt with dark header fill

Brand colors (sampled from official artwork — do not guess):
- Blue  `#2AA9E0`   Amber `#F99C1B`   Red `#EE1B24`
- Dark  `#1F2A33`   Grey  `#595F66`

## Extracting the logo from an SSR PDF

```python
import fitz
d = fitz.open(pdf); pg = d[0]
# header logo sits near top-left; find via pg.get_image_rects(xref)
pix = pg.get_pixmap(clip=rect, matrix=fitz.Matrix(6,6)); pix.save("logo.png")
```
SSR artwork has a near-black background (1,5,43). Make it transparent first or
it prints as a black box on a white header:

```python
if r<60 and g<60 and b<90: out.putpixel((x,y),(0,0,0,0))
```

## Pitfalls

- **Word renders a stale cached doc.** When previewing via AppleScript, Word may
  export a previously-open document. Quit Word, delete `~$*.docx` lock files, then
  reopen. Verify the PDF's actual text matches before trusting a preview.
- **`update fields of theDoc` fails** (-1708). Use
  `tell theDoc: update fields of fields of text of it` end tell.
- **Always re-add the column check** before shipping: recompute every CAPEX/OPEX
  total from the line items. Found a double-counted row and a total that wrongly
  absorbed a per-call item in the ARRAS doc.
- Full-scale cost tables must exclude POC-established items (MARU requires this to
  avoid double charging). Say so in a note above the table.
- Keep an infographic/artwork generation brief in an Appendix, not the body.

## Verification before delivery

1. Recompute all money totals in Python; assert against the stated total.
2. Grep for AI tells: delve, tapestry, leverage, cutting-edge, seamlessly.
3. Grep for leftover `[tbd]` (only genuine datasheet blanks like `[kHz]` may remain).
4. Render to PDF and confirm header/footer/page numbers on every page.
5. Check every figure caption matches its image.

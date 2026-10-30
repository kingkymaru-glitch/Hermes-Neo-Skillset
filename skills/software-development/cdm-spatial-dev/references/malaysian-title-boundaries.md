# Malaysian title boundaries (geran tanah / pelan tanah) → geometry

Domain notes for turning a Malaysian land title into a polygon on the globe.
Implemented in CDM as the Plot → **Traverse** method (`lib/traverse.ts`).

## What the document actually contains

A title set is two documents:

- **Borang SEK** (mukim lease) / **Borang B1** (land plan) — the title proper. Identifiers worth
  storing: Hakmilik no., Lot no., Mukim / District / State, tenure + expiry, category
  (Pertanian / Bangunan), **No. Lembaran Piawai** (standard sheet), **No. Pelan Diperakui**
  (certified plan).
- **The plan sheet** — a standard sheet (e.g. `845B&D`) covering MANY lots with shared
  boundaries, each lot carrying its own bearing/distance legs and its own area.

**The load-bearing fact: these define the boundary by BEARINGS and DISTANCES, not by corner
coordinates.** Do not design a coordinate-entry feature around them. They give exact SHAPE and
exact AREA — and NO LOCATION.

**The area is stated — TWICE** (title page and plan sheet). That is the verification anchor; always
capture it.

## Coordinate systems (get this wrong and you are tens of metres out, on the neighbour's lot)

| System | Where | To place on a WGS84 globe |
|---|---|---|
| GDM2000 (lat/lon) | national, modern | effectively WGS84 (cm level) — safe to implement |
| MRSO / RSO (E, N) | Peninsular mapping | needs the RSO projection parameters |
| Cassini Soldner | older cadastral | **STATE-SPECIFIC origin** — parameters per state |
| Timbalai 1948 (BRSO) | Sabah | different projection + datum |
| Timbalai 1948 | Sarawak | different again |

Never infer the system — make the user choose it, and label anything unverified. GDM2000 and UTM
are the ones you can implement and trust immediately; the legacy systems need real parameters
validated against a known point before anyone relies on them.

## The traverse (what to compute)

Local tangent plane, north-up. **This is not a geodetic projection** — fine for a lot of a few
hundred metres, wrong for a large tract. State that limit rather than implying survey precision.

```
dE = distance * sin(bearing)      # bearing = whole-circle azimuth from north
dN = distance * cos(bearing)
```

- Sum from the first corner. A lot boundary closes, so the final computed point should return to
  the origin; the gap is the **misclosure**. Display it — an open traverse means a missing or
  mistyped leg.
- Area = shoelace on the local (E, N) metres.
- Place it on the globe with an **ANCHOR**: one corner's lat/lon.
  `lat = anchorLat + N/111320`, `lon = anchorLon + E/(111320 * cos(anchorLat))`.
  Reuse the same ground scale the box plots use so every layer on the map agrees.

## Verification IS the feature

Compare the computed area with the area the title states. Within ~0.5% is a pass; 0.5–2% is
"close, re-check the legs"; beyond that something is wrong. Render it as a verdict (green / amber /
red), never draw silently. This is what makes a typed boundary defensible — and given CDM's
liability stance (the blame must not land on the tool), an UNVERIFIED polygon is worse than no
polygon at all.

Regression case: a title stating **0.4185 ha** with a 55.90 m x 74.83 m lot computes to
**4,183.0 m² — 0.048% off, closing to 0.00 m**. Keep it as a fixture.

## `lib/traverse.ts` (CDM)

- `parseBearing(str)` — DMS (`86°46'30"`), decimal, `86D46M30S`, and quadrant (`N45E`, `S12W`,
  `N 45 30 E`). Quadrant → azimuth: N+E = x, S+E = 180−x, S+W = 180+x, N+W = 360−x. Reject a
  quadrant value > 90°.
- `parseLegs(text)` — one leg per line. A comma wins as the separator; otherwise the last number
  is the distance. Returns `{legs, errors}` — **always surface the errors and the parsed result.**
  Silently skipping an unreadable line is how a wrong boundary ships.
- `traverse(legs)` → `{points, misclosureM, closed, perimeterM, areaM2}`.
- `localToLonLat(points, lat, lon)`, `areaOfLonLatRing(ring)`.
- `verifyArea(computedM2, statedM2)` → `{diffPct, verdict: 'match' | 'close' | 'mismatch'}`.
- `parseAreaToM2` / `formatArea` / `formatAreaShort`.

Store the ORIGINAL LEGS on the row as well as the ring. A boundary that can be re-opened and
corrected beats one that must be retyped — and the legs are what let you RE-ANCHOR later, once a
surveyed corner coordinate becomes available.

## Pitfalls

- **Strip unit tokens BEFORE reading a number.** `"4185 m2"` parsed as **41852** because the `2`
  in `m2` reads as a digit. Detect the unit first, delete the unit words, then take the first
  number. Same trap for `ft2`, `m²`, `sq m`.
- **Never auto-fill survey numbers from OCR** (mechanism in the debugging section of SKILL.md).
- **A traverse without an anchor is not a location.** Make the anchor an explicit step and refuse
  to save without it, rather than silently falling back to the project site centre.
- **Store the ring OPEN** — do not repeat the first point at the end; the renderer appends the
  closing point.
- **Idealised dimensions are not the title.** A 55.90 x 74.83 m rectangle only approximates a real
  lot — it is a maths fixture, not a survey.

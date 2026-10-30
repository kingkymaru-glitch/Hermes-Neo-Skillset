# Offline / local OSM data for Surroundings

Context: MARU wants NO live third-party API in the Surroundings build path — *"i dont want any
API for this purpose"*. Mirror retries make the build resilient but still lean on a free public
service, which is not acceptable for a client demo or a compliance output. This file is the
verified capability map for going fully local.

STATUS: capability map verified against the installed toolchain (read from source). The local
extract pipeline is **PROPOSED, not implemented** — re-verify before quoting numbers.

## Verified blosm capabilities

Addon dir: `~/Library/Application Support/Blender/5.1/scripts/addons/blosm`

| Question | Answer | Where it lives |
|---|---|---|
| Can it read a local file? | YES — `osmSource = "file"` + `osmFilepath` | `__init__.py` |
| Does file mode still hit the network? | ONLY when relations are incomplete AND `loadMissingMembers` is True (**default True**) — it then calls `loadMissingWays()` against the OSM server | `app/__init__.py` (`loadMissingMembers`, `loadMissingWays`), `parse/osm/relation/multipolygon.py` |
| Can it read `.pbf`? | **NO.** XML only, via `etree.parse(filepath).getroot()`. No pbf/protobuf code anywhere in the addon | `parse/osm/__init__.py` |
| Can it read gzipped / bz2 OSM? | NO — no gzip or bz2 handling. Hand it a plain `.osm` XML | `parse/osm/__init__.py` |
| Does terrain cause downloads? | YES — elevation tiles from `s3.amazonaws.com/elevation-tiles-prod/skadi/...` when terrain is on | `app/blender.py` (`terrainUrl`) |

Two consequences worth stating plainly: the **no-pbf** limit means a raw Geofabrik download cannot
be fed in directly, and `etree.parse` loads the whole file into memory, so never hand it a
country-sized XML.

## The chain that works offline

1. One-time: download a regional extract. Geofabrik
   `asia/malaysia-singapore-brunei-latest.osm.pbf` is ~**239 MB** and rebuilt daily (the URL 302s
   to a dated file — follow redirects).
2. Per build: clip the bbox out of that local `.pbf` and convert to XML with **osmium-tool**.
   `osmium` is NOT preinstalled on macOS; `brew install osmium-tool` (available, 1.19.x).
   Local extraction takes seconds.
3. In `build_surroundings.py`: set `osmSource = "file"`, point `osmFilepath` at the slice, and
   set `loadMissingMembers = False` so nothing reaches out.
4. Keep terrain off, or accept its tile downloads.

## Why this is better for CDM, not merely more reliable

A pinned dataset makes a siting study reproducible and citable — the report can name the data
date. Live data means two runs a week apart can differ. Freshness drops from minutes to daily,
which is irrelevant for a siting study.

## Limits to state honestly

- **One file per region.** A site outside the downloaded region has no surroundings data until
  another extract is added. Extensible, but not unlimited global coverage.
- Datasets describe the built environment, not current conditions.

## Open decisions

- Manual "refresh map data" control vs. auto-download when the local file is older than N days.
  Recommended: manual, plus show the dataset date in the Surroundings panel so a report can cite it.
- **Imagery is the hard case.** The satellite basemap (Esri World Imagery) has no small offline
  substitute — bundling Malaysia imagery is gigabytes. Treat separately from OSM geometry; the
  visible map still needs the network.
- The Cesium CDN load should be bundled locally for the desktop build (cheap win).
- The weather / earthquake / volcano overlays are live third-party feeds with no role in a
  compliance output — candidates for removal.

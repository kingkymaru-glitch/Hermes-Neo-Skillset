# Reverse Engineer tab — Ghidra pipeline

Depth for the dashboard's 🔬 Reverse Engineer tab: how a run flows, what it accepts, where
artifacts land, and the knobs that bound it.

## Flow

1. **Upload** — `POST /api/re/analyze`, `multipart/form-data` with `file`, `place` (where to
   create the folder, default `~/re-reports`) and `name` (folder name; blank ⇒
   `<file-stem>-<timestamp>`).
2. **Stage** — bytes are written to `~/.hermes/re-uploads/<uuid8>_<sanitized-name>`. This is a
   plain copy, so an uploaded file never inherits the source's file flags.
3. **Folder** — `place` and `name` are sanitized (`\` and `/` → `-`, `..` rejected) then
   `mkdir -p`'d. Results land in `<place>/<name>/`.
4. **Stage + thin** — bytes are copied into a fresh `~/ghidra_sessions/ghidra_bridge_*` dir
   (0o700) with `shutil.copyfile` (not `copy2` — see the `EPERM` pitfall in SKILL.md), then, if
   the file is a fat Mach-O, the native slice is extracted with `lipo -thin` and *that* file is
   what gets imported.
5. **Ghidra** — `analyzeHeadless <session-dir> GhidraBridge -import <staged-or-thin>
   -postScript ExtractResults.java <raw> -scriptPath <session-dir> -deleteProject`, with no
   `-processor` flag.
6. **Parse** — the post-script writes a raw dump; the bridge parses it into `analysis.json`.
   The staged binary, the thin slice and the raw dump are then securely wiped and the session
   dir removed.
7. **Render** — `render_re_pipeline_svg()` writes `pipeline.svg` and returns inline SVG for the
   results panel; a team-memory row is appended.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/re/analyze` | Upload + analyze (multipart) |
| GET | `/api/re/status` | `bridge_available`, `recent_analyses[]`, `total_analyses` |
| GET | `/api/re/pipeline.svg?folder=<dir>` | Full-size saved pipeline diagram |

`/api/re/status` scans `~/.hermes/re-output` **and** `~/re-reports` (max 25 dirs, newest first)
and keeps only dirs holding an `analysis.json`. A run written to any other `place` still shows
in the results panel but never reaches Recent Analyses — tell the user which of the two they are
looking at before treating "no history" as a lost run.

## analysis.json shape

Keys: `program_info`, `functions`, `call_graph`, `strings`, `symbols`, `decompilation`,
`disassembly`, `cross_references`, `metadata`.

- `program_info` — `name` is always `input_binary` (the staged filename, not the upload's),
  plus `format`, `language`, `compiler`, `imageBase`, `minAddress`, `maxAddress`, `entryPoints`.
- `functions[]` — `{name, address, size, calling_convention}`; unnamed functions appear as
  `FUN_<addr>`. `size` is `f.getBody().getNumAddresses()`. Parse the raw line with
  `split(":", 4)` — a 3-way split glues size and calling convention into `"96:unknown"` and
  silently breaks every range/containment calculation built on it.
- `call_graph[]` — `{caller, site, callee, callee_entry, type, thunk}`: one entry per call
  instruction in every function body, with the callee resolved to a function. TAB-separated in
  the raw dump, because symbol names legitimately contain colons (C++/Rust mangling). This is
  the sole source for the process tree; the older `cross_references` section records only
  references *to* a function's entry point, so it loses call sites and mis-attributes them
  whenever sizes are unavailable. `thunk: true` marks an imported routine — a stub the target
  calls out to — which the tree draws as a leaf.
- `strings[]` — `{address, value}`. Zero-filled regions get typed as string data and
  `hasStringValue()` is true with an empty value, which once inflated the count to 14,797 of
  14,830 entries on a single arm64 slice — 33 real, identical to the 33 the same binary's x86
  slice reported. Both the Java post-script and `parse_ghidra_output()` now drop
  empty/whitespace-only values, and both are worth keeping: the script filters at the source,
  the parser defends against a raw dump produced by an older script.
- `decompilation` — a **dict keyed by function name**, not a string. The panel's
  `typeof === 'string'` check therefore falls through to `JSON.stringify`, which is why
  decompilation renders as escaped JSON rather than formatted code.
- `metadata` — `binary`, `file_size`, `file_type`, `sha256`, `architecture`,
  `universal_binary`, `slices`, `slice_analyzed`, `analysis_time_seconds`, `ghidra_version`,
  `return_code`. The four arch keys are what let the diagram say which slice was read:
  `slices` is every architecture present, `slice_analyzed` the one actually imported (empty for
  a thin binary), `architecture` mirrors `program_info.language`.

## What it accepts

Magic-byte allowlist only: PE (`MZ`), ELF (`\x7fELF`), Mach-O thin (32/64, both endians) and
fat/universal (`cafebabe` / `bebafeca`), plus `.NET` assemblies (also `MZ`). Everything else
returns `{"error": "Unsupported file type (detected: unknown)"}` — scripts, APKs, JARs, zips,
firmware images and documents all stop here. Adding a format means extending
`ALLOWED_MAGIC_BYTES` **and** giving it an analyzer: Ghidra alone cannot read a zip or a script.

The allowlist covers all four fat/universal headers: 32-bit `cafebabe` / `bebafeca` and 64-bit
`cafebabf` / `bfbafeca`. The 64-bit pair is the one usually forgotten, and omitting it makes a
valid universal binary return `Unsupported file type (detected: unknown)` — add both pairs when
touching `ALLOWED_MAGIC_BYTES`.

## Architecture / slice selection

The bridge passes no `-processor`. That flag cannot select a slice anyway: on a universal binary
Ghidra aborts with `Failed to match the load spec to a Universal Binary Mach-O`. So the bridge
detects a fat Mach-O (`is_fat_macho()`), thins the native slice with `lipo -thin`, and imports
the thin file. A thin arm64 Mach-O reports `AARCH64:LE:64:AppleSilicon`.

The slice is chosen by `pick_slice(slices, host_arch)`: exact match, then a **variant** match,
otherwise the first slice. The variant step is load-bearing — Apple's system binaries ship
`arm64e` (pointer-auth variant), not `arm64`, so `pick_slice(['x86_64','arm64e'], 'arm64')` must
return `arm64e`. An equality test returns `x86_64`, and the analysis then reports Intel code
while looking correctly fixed.

By hand, for a one-off:

```bash
lipo -archs <fat-binary>                      # slice names, e.g. "x86_64 arm64e"
lipo -thin arm64 <fat-binary> -output <thin>  # or arm64e — must be a name lipo printed
python3 <bridge> <thin-binary> -d <out-dir>
```

The thin slice is also faster (~5 s vs ~7 s here) because there is half the image. Always say
which architecture a result came from — on this machine the arm64/arm64e slice is the native one.

### Session path constraints

The session/project dir must be a **real path with no dot-component and no symlink**.
`tempfile.gettempdir()` returns `/var/folders/...` on macOS and `/var` is a symlink to
`/private/var`; Ghidra canonicalises it, then cannot match the `-scriptPath` it was given, so the
postScript silently never runs and the report comes back empty. A dot-component fails loudly:
`Path element starting with '.' is not permitted`. Use `~/ghidra_sessions` (the bridge's
`_safe_session_root()`), and remember the output folder the user picks is unrelated to it.

## Knobs (environment variables)

| Var | Default | Effect |
|---|---|---|
| `GHIDRA_HOME` | `/opt/homebrew/Cellar/ghidra/<ver>/libexec` | Ghidra install; version-pinned, so re-check it after a brew upgrade |
| `GHIDRA_MAX_FILE_SIZE_MB` | 500 | Hard reject above this |
| `GHIDRA_ANALYSIS_TIMEOUT` | 300 | Ghidra subprocess timeout, seconds |
| `GHIDRA_NO_ANALYSIS` | unset | Set to `1` to add `-noanalysis`. Costs roughly 25% of recovered functions/symbols/xrefs — speed-only runs |
| `GHIDRA_SESSION_ROOT` | `~/ghidra_sessions` | Preferred session/project root; must stay a real, dot-free, symlink-free path |

Two independent ceilings exist: the bridge's `GHIDRA_ANALYSIS_TIMEOUT` and the dashboard's own
`subprocess.run(..., timeout=300)`. Raise both or the tighter one wins.

## Cost model

Analysis time tracks binary size closely enough to predict coarsely: a 154 KB Mach-O finishes
in ~8 s, an 11.5 MB app binary does not finish inside 300 s. Treat small binaries as seconds
and real app binaries as needing a raised timeout or a different tool.

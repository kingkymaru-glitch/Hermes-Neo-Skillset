# Rebrand Sweep Checklist (full rename, not part-by-part)

Concrete token list + gotchas from the MARU → R-Tessera sweep (my-digital-twin
fork). Reuse the pattern; swap the literal strings.

## Search tokens (run over whole tree, incl. docs/ and server/)
```
OLD|old|Bangi|Temenggor|Gerik|Perak|DamGate|dam-gate|obsidian_old|DEMO_ASSETS|OLD_LS_KEY
```
Also grep the brand name with case variants: `MARU`, `maru`, `M.A.R.U`,
`Project M.A.R.U`, `MARU LABS`.

## Per-file class cheat sheet
| File class | What to change |
| --- | --- |
| `package.json` | `name`, `version` |
| `README.md` / `ARCHITECTURE.md` / `docs/*.md` | headers + body brand/demo strings (rewrite, don't just sed) |
| `src/**/*.jsx` | brand strings, support email, `Summon <X> AI`, chat persona name (e.g. `Tessera`), modal kicker, `R-Tessera · github.com/<owner>` display |
| `localStorage` keys (`governanceService.js`) | `maru.governance.v1` → `r-tessera.governance.v1` |
| cache prefixes (`LayerManager.js`) | `maru.layer.` → `r-tessera.layer.` |
| `src/context/EdgeDataContext.jsx` | Obsidian vault path comment + SITE_CENTER (generalize to VITE_SITE_LON/LAT/ALT) |
| `server/*.mjs` | banner + log lines + `NODES_DIR` vault path |
| sub-project folders (`docs/maru-shifu/`) | `git mv` the folder AND rewrite README + scripts: MQTT topic `maru/shifu/...` → `r-tessera/shifu/...`, k8s names `edgedevice-marushifu-...` → `edgedevice-rtessera-shifu-...` |

## Demo-data removal specifics
- `DEMO_ASSETS = []` → delete the fallback array; make `loadAssets()` return
  empty when Supabase is unconfigured (no demo coords as a crutch).
- `SITE_CENTER = { lon: 101.773, lat: 2.965, ... }` (Bangi) → replace with
  env-configurable anchor; android mode relabels the phone's edge node.
- Remove clickable demo pins + their viewer modals (e.g. DamGateViewerModal)
  AND the orphaned `.dam-gate-modal` CSS block in `App.css`.
- Any standalone demo HTML (`public/models/dam-gate-3d.html`) — note it; decide
  keep/remove with the user.

## Intentional survivors (do NOT "fix")
- The real GitHub repo owner in the URL/href: `github.com/kingkymaru-glitch`.
  Keep it; only the *display* text gets the `R-Tessera ·` prefix.
- The configured Obsidian vault path (`~/Documents/obsidian_r_tessera/DT Nodes`)
  — consistent across App.jsx + server; only changes if the user moves the vault.

## End-of-sweep verification
```
npm run lint   # 0 errors (pre-existing warnings OK)
npm run build  # clean; report package-name line
search_files 'MARU|maru|Bangi|Temenggor|DamGate|dam-gate|obsidian_maru|M\.A\.R\.U|DEMO_ASSETS'  # whole tree
# expect only: github.com/<owner> (URL) + vault path
```

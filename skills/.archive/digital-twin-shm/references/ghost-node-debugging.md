# Ghost node debugging — marker renders but isn't in source or the intended vault

## Symptom
A map node/marker (e.g. "Temenggor Dam Gate") shows on the globe, but:
- `grep -rIl` across `src/`, `public/`, `server/` returns nothing for its name/coords.
- The intended Obsidian vault (`Obsidian/DT Nodes`) is empty (`ls -A` empty).
Yet the running app clearly renders it.

## Root cause class
Data is served by a **stray bridge process** on a port the current code does not
even target. Easy to create when both the OLD repo (`my-digital-twin`, reading
`obsidian_maru_1/DT Nodes`) and the NEW fork (R-Tessera, reading
`Obsidian/DT Nodes`) are checked out and you've started a dev server / bridge in
each. Two `nodes-bridge.mjs` instances run on different ports reading different
vaults, and a `NODES_API`→port mismatch masks which one the UI actually loads.

## Diagnosis (run in order)
1. **Confirm it's external.** Grep source + both vaults for the node name and
   its lat/lon. If nothing, the data is coming from a live bridge, not code.
2. **Probe every candidate port:**
   ```sh
   for p in 8799 8899; do echo "== $p =="; curl -s --max-time 3 http://localhost:$p/api/nodes; echo; done
   ```
   The port returning the rogue node is the stray bridge.
3. **Identify which repo each listening PID serves** (cwd reveals the checkout):
   ```sh
   lsof -nP -iTCP:8799 -iTCP:8899 2>/dev/null | grep LISTEN
   # for each PID:
   lsof -p <pid> 2>/dev/null | grep -i cwd      # shows /Users/.../my-digital-twin vs /.../R-Tessera
   ps -o command= -p <pid>                       # shows launch args / env
   ```
4. **Check the port contract.** Read `NODES_API` in `App.jsx` and compare to the
   bridge's real port. Mismatch (code 8899, bridge 8799) = the UI loads an empty
   source while a stray bridge feeds the visible node.

## Fix
1. **Kill the stray bridge(s)** from the OLD repo:
   ```sh
   kill <stray_pid>          # e.g. the my-digital-twin bridge on 8799
   ```
2. **Delete the rogue node `.md`** from wherever the stray bridge was reading:
   ```sh
   rm -f "/Users/kamarulhk/Documents/obsidian_maru_1/DT Nodes/Temenggor Dam Gate.md"
   ```
3. **Align the port** so code and bridge agree, and restart the intended bridge
   pointing at the correct (empty) vault:
   ```sh
   # in NODES_API (App.jsx): use 8799 to match the bridge default
   R_TESSERA_NODES_DIR="/Users/kamarulhk/Documents/Obsidian/DT Nodes" \
   R_TESSERA_NODES_PORT=8799 node server/nodes-bridge.mjs
   ```
4. **Verify:** `curl -s http://localhost:8799/api/nodes` returns `[]` and the map
   shows no marker. `npm run lint` stays green; dev server (e.g. :5175) returns 200.

## Reusable lesson
When a node "shouldn't exist," suspect **process / port / vault mismatch** before
suspecting code. Keep the port in exactly two places and in sync:
`R_TESSERA_NODES_PORT` (server) ↔ `NODES_API` (App.jsx). After any fork/cleanup,
kill leftover bridges from the previous checkout so only one bridge serves one vault.

## UI-overlap disambiguation tip
When the user reports "X and Y buttons overlap" but you can't find a second
control in code, **`vision_analyze` the screenshot** to identify the exact
elements before editing. In one case the reported "homing button" overlapping the
bottom-left layer control was actually the **left-edge `.cmd-trigger` chevron**
(a separate affordance), not a second bottom-left button. Removing `.cmd-trigger`
and making the brand header open the drawer resolved it; the layer cluster
(`.map-ctl-cluster`) then shifts clear of the open drawer via a `.shifted` class
(`left: 440px` to clear a 420px-wide `.cmd-drawer`).

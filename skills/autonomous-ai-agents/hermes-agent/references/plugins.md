# Hermes Plugins — Install, Repair, and the MCP Fallback

Covers "install plugin X", "the plugin install was blocked", "plugin installed but disabled",
"plugin dependency conflict", and "the vendor ships both a plugin and an MCP server".

## Procedure

1. **Search the curated catalog first.**
   ```bash
   hermes plugins search <name>     # name, category, TIER, pinned version@sha, capabilities
   hermes plugins browse            # every catalog entry
   ```
   The tier column is the decision input: `verified` / `community` / labs. A cataloged plugin is
   pinned to a reviewed commit — installing it by name gets you that commit.

2. **Install a cataloged plugin by NAME.**
   ```bash
   hermes plugins install <name> --yes-deps --enable
   ```

3. **Only fall back to a Git URL when the catalog has no entry.**
   ```bash
   hermes plugins install https://github.com/<owner>/<repo> --yes-deps --enable
   ```

4. **Verify what actually landed.**
   ```bash
   hermes plugins list              # Status: enabled / disabled
   hermes plugins capabilities      # declared vs granted
   hermes plugins doctor <dir>      # real runtime contracts
   ```

5. **Keep it current.** `hermes plugins check-updates` (read-only) → `hermes plugins update`
   with no name updates every plugin that has one; Desktop shows an Update button for
   git-installed plugins.

## Pitfalls

- **Install a cataloged plugin by NAME, never by its Git URL.** The same plugin fetched by URL is
  scanned as an unknown "community source" and can return
  `Decision: BLOCKED — community source + caution verdict` on findings that are all in `tests/`
  and `README` (a `subprocess.run` in a test fixture, escape sequences in expected output, a
  README line about MCP). The name route uses the reviewed pin and skips that gate entirely.
  When a URL install is blocked, the next move is `hermes plugins search`, not `--force`.
- **`--force` is not the fix for a scanner block.** It overrides a security verdict. Reserve it
  for an uncataloged plugin the user has explicitly approved after reading the findings, and say
  which findings you accepted.
- **Non-interactive install needs BOTH flags.** `--yes-deps` answers the Python dependency
  consent, `--enable` skips the enable prompt. With neither, a non-TTY install refuses; with
  only `--yes-deps` it lands disabled.
- **A dependency pin older than the running Python leaves the plugin installed-but-disabled.**
  The symptom is a uv resolver error naming a version range plus "no wheels for
  python_full_version >= X", then "the plugin stays installed but disabled". Read the pin in the
  plugin's `pyproject.toml` `dependencies` and compare it with `python -V` before touching
  anything: if no wheel exists for that Python and the pin has no newer release, there is no
  local fix — do not `--force`, downgrade Python, or hand-edit the pin. Take the vendor's other
  install route (below) and report the pin as an upstream bug.
- **A plugin and an MCP server are two install routes to the same capability.** Vendors that ship
  a Hermes plugin usually also ship an MCP-server mode (the plugin README documents it). When the
  plugin is blocked by a pin or the scanner, `hermes mcp add` gives the same backend with no
  Python dependency — the difference is that the plugin auto-routes `terminal.backend` while MCP
  exposes tools you call explicitly. Setup for that route: `references/native-mcp.md`.
- **Enabling a plugin reloads plugins but not MCP tools.** MCP tools need a new session or
  `/reload-mcp`; a plugin that only hooks lifecycle events takes effect immediately.
- **Removing is `hermes plugins remove <name>`.** To inspect before trusting, install with
  `--no-enable` and read the tree first.

## Worked example — Cua Spaces

A `verified` catalog plugin (`cua-spaces`) whose pin cannot resolve on Python 3.14, plus a
working MCP route. Full recipe: `references/cua-spaces.md`.

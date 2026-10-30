# Cua Spaces — an isolated machine for agent work

Giving the agent its own Linux (Ubuntu desktop) or Windows machine, on your hardware or in your
own cloud account, so terminal/file/code work happens off the host. Vendor: trycua. Two install
routes — the `cua-spaces` plugin (auto-routes the terminal backend) and `cua mcp` (tools the
agent calls explicitly).

Local Spaces need **no account**; sign-in is only for cloud/relay Spaces.

## Install the CLI

```bash
curl -fsSL https://cua.ai/install.sh -o /tmp/cua-install.sh
sh /tmp/cua-install.sh --cli-only --yes     # --cli-only skips the Spaces app and the interactive checklist
cua --version                               # installs to ~/.local/bin
cua doctor                                  # host.* checks; a healthy local runtime means local Spaces will work
```

## Route A — MCP tools (use this when the plugin's pin will not resolve)

```bash
hermes mcp add cua --command "$HOME/.local/bin/cua" --args mcp --permissions sandbox:all
```

- Pipe `yes |` when not in a TTY (the tool-enable prompt cancels otherwise).
- `sandbox:all` → 14 lifecycle tools (list / create / start / stop / suspend / delete / view /
  open_browser). It has **no exec** — run commands through the CLI below. Omitting
  `--permissions` advertises ~156 tools including `computer_*` and `skills_*`.
- New tools appear after a new session or `/reload-mcp`.

## Route B — the plugin (auto-routes the terminal)

```bash
hermes plugins install cua-spaces --yes-deps --enable
hermes config set terminal.backend cua
```

Settings live under `plugins.entries.cua-spaces.settings.*`:

| key | default | meaning |
|---|---|---|
| `space` | `create` | `create` = throwaway per run; a name/id reuses that Space |
| `on` | Cua default | `local`, `cloud`, `host:<machine>` |
| `image` | `linux` | `linux` (Ubuntu + desktop) or `windows` |
| `desktop` | `false` | install the VNC/Playwright/driver stack a Linux Space needs for browser + `computer_use` |
| `delete_on_exit` | `true` | keep the Space between sessions by setting false |
| `create_timeout` | `600` | seconds to wait for a new Space |

Default behaviour: one throwaway Space per run, deleted on exit, risky-command prompts skipped
because the Space is disposable. A **named** Space is never deleted and keeps the prompts.

**Pin caveat:** the plugin declares `cua>=0.5.0,<0.8`. On Python 3.14 only `cua>=0.8` has
wheels, so the install lands enabled=no with a uv resolver error. That is a dependency pin, not
a broken install — use Route A and report the pin upstream.

## Working commands (cua 0.9.x)

```bash
cua spaces ls
cua spaces create linux --name <name> --cpus 2 --memory-mb 3072   # first one ~9 min (downloads runtime + image)
cua sandbox exec <name> -- bash -c 'hostname; head -3 /etc/os-release'
cua sandbox screenshot --output /tmp/space.png <name>              # flag is --output, not --out
cua sandbox view <name>                                            # opens the HTML5 desktop viewer
cua sandbox cp <name>:/guest/path .                                # file transfer in/out
cua spaces stop|start|delete <name>
```

- **The subcommands are split across two families.** `cua spaces` = lifecycle (ls / create /
  stop / start / delete / share); `cua sandbox` = work (exec / view / screenshot / cp / url /
  port-forward). `cua spaces exec` and `cua spaces view` do not exist — check
  `cua sandbox --help` before guessing, a wrong guess costs a round trip.
- **The viewer URL is redacted in stdout**, in plain and `--json` output alike
  (`#ticket=v1.eyJzIj...2A80`), so you can never read it back and must not retype it.
  `cua sandbox view <name>` is supposed to open the real link itself, but when it runs from a
  backgrounded/detached shell the open never reaches the user's GUI session — it prints the URL
  and exits and the user sees nothing. Pass the link through a pipe instead of through your own
  eyes: `URL=$(cua sandbox view <name> --no-open --ttl 2h | sed -n 's/^Viewer for [^:]*: //p' | tail -1); open "$URL"`.
  The redaction is display-only, so the ticket survives the pipe intact.
- **Confirm the viewer before telling the user to look.** The viewer port answering
  `curl -s -o /dev/null -w '%{http_code}'` → 200 together with `cua sandbox info <name>` reporting
  `Status: ready` is what proves the window they are hunting for has something behind it.
- **Prove the isolation before claiming it.** Ask for `hostname` and `/etc/os-release` inside the
  Space — expect the Space's own id and Ubuntu, not the host's name and macOS.
- **Budget disk before creating.** The first Linux Space is roughly 5.5 GB under `~/.cua`
  (runtime + image + disk). Check `df -h /` first. Cua's "this Mac is almost out of space"
  warning can fire on a volume with tens of GB free — verify before relaying it as fact.
- **A Space starts empty.** No host files, no Hermes skills, no credentials — it has only what
  its image has. It is for throwaway or cloned work, not for editing the user's existing project
  checkout in place; say so before promising a "safe" version of that workflow.
- **Browser / `computer_use` / Bot Desktop do not automatically follow.** They move into a Linux
  Space only on a Hermes build with the Space placement support plus the desktop stack installed
  in the Space (`desktop: true`); otherwise they keep running on the host.

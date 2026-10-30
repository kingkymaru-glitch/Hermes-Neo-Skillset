---
name: remote-machine-access
description: "Use when running code on a remote SSH/Tailscale machine."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [SSH, Tailscale, Remote, Recon, VPS, macOS]
    related_skills: [github-auth]
---

# Remote Machine Access

The class of task: the user wants something built locally and then run on a machine
that is not this one — an office PC, a VPS, a home server — usually over Tailscale.

**Report feasibility, do not promise capability.** The whole value of this skill is
separating "the network path exists" from "we can actually log in". Those are different
facts and conflating them burns the user's trust. Never say "yes, I can run it there"
until you have shown the auth method is usable.

## Gate before touching anything

A request to build-and-run remotely is new work. Report the verdict plus the ONE
blocker and the named routes, then wait for the user to pick a route. Do not start
writing code, generating keys, or editing configs before that pick. MARU enforces this
as a hard gate and will interrupt mid-build.

Also confirm the user can open a terminal on the target *at all*. "A server in my
office" often means nobody on hand can run a command on it — ask before designing
a setup that needs one line run over there.

## Step 1 — Establish the tunnel state before believing any peer list

```bash
tailscale status --json > /tmp/ts.json
```

Read `BackendState` first. Anything other than `Running` means nothing is reachable,
no matter how healthy the peer list looks.

- **PITFALL: peer data is from the last-fetched netmap, so it survives a dead backend.**
  With `BackendState: Stopped` you still get a full `Peer` map with per-peer `Online:
  true` and `LastSeen` of `0001-01-01T00:00:00Z`. Those placeholders mean "no live data",
  not "seen at year zero". Gate every conclusion on `BackendState` and on `Health`.
- `Health` explains the cause (stopped, relay unreachable, still starting). Print it.
- A real `LastSeen` timestamp (not the zero value) on an offline peer is genuine and
  tells you how long it has been gone.

Per-peer fields worth extracting: `HostName`, `OS`, `TailscaleIPs`, `Online`, `Relay`
(relay vs `direct` = throughput), `Tags`, and **`sshHostKeys`** (see Step 3).

### Starting it on macOS

The App Store / standalone macsys build does **not** come up via `tailscale up`. Launch
the GUI and re-read status:

```bash
open -a Tailscale && sleep 8
tailscale status --json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['BackendState'], d.get('Health'))"
```

`BackendState: Running` with `Health: []` is the green light.

### Reading state without the GUI when it is broken

- State dir is `/Library/Tailscale` (root-owned — needs `sudo` to list). `ipn.log*` files
  of size 0 mean the backend never got far enough to log.
- The `ipnport` symlink mtime and `sameuserproof-<port>` tell you when the daemon last
  restarted — useful to prove "something brought it up but it never went online".
- Logged-in tailnet / identity / MagicDNS name live in the prefs blob, not in a readable
  file. Decode it instead of guessing:

```bash
defaults export io.tailscale.ipn.macsys /tmp/ts_prefs.plist && plutil -convert xml1 /tmp/ts_prefs.plist
# then plistlib.load(...) and read com.tailscale.cached.currentProfile / cached.profiles
```

That blob yields the login name, tailnet `DomainName`, and `MagicDNSName`.

## Step 2 — Prove the network path, non-destructively

`ping` proves the tunnel; port probes prove a service is listening. Batch them:

```bash
for h in <ip> <ip>; do printf "%-16s " $h
  ping -c1 -W 1500 $h >/dev/null 2>&1 && printf "ping:OK " || printf "ping:-- "
  for p in 22 3389 80 443 8000; do nc -z -G 2 $h $p 2>/dev/null && printf "%s:open " $p; done; echo
done
```

`-G` is the connection timeout on macOS `nc` (GNU uses `-w`). Port 22 = SSH, 3389 = RDP
(so the user may have a GUI route to that box even with no SSH access), 80/443 = an app.

## Step 3 — Decide feasibility WITHOUT any credential

This is the key move. sshd advertises its accepted auth methods before you authenticate:

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/tmp/kh_test \
    -o PreferredAuthentications=none -o BatchMode=yes -o ConnectTimeout=6 \
    test@<host> 2>&1 | grep -iE "permission denied|authentications|refused|timed out"
```

Interpret the parenthetical:

| Result | Meaning | Route |
|---|---|---|
| `Permission denied (publickey)` | key-only, password disabled | Needs a **one-time on-machine action** (install a key, or enable Tailscale SSH). Unreachable from here until someone touches that box. |
| `Permission denied (publickey,password)` | password auth enabled | Usable now if the user knows the login. |
| `(...,keyboard-interactive)` | interactive auth allowed | Same as above. |
| no output / hang | Tailscale SSH path — see below | |

### When the user hands you a password for a key-only host

A password offer does not make the host reachable. Establish whether sshd advertises
password auth *before* saying anything about the password, and keep the two facts
separate:

```bash
# does sshd even offer password auth? read the parenthetical
ssh -o PreferredAuthentications=none -o BatchMode=yes -o ConnectTimeout=6 <user>@<host> 2>&1 | grep -i authentications
# force password auth to prove it is refused, not merely untried
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o BatchMode=yes -o ConnectTimeout=6 <user>@<host> 2>&1 | tail -1
```

Probe several likely usernames (`root`, `admin`, the user's own name, the host name). The
parenthetical is effectively username-independent here, but repeating the probe confirms
the host is up and sshd is the component refusing.

Report it as **"the password is untestable, not wrong."** "Wrong password" implies a
working path that does not exist, and the user will keep hunting for the right one.
Then give the ports: if 3389 is open, that password is probably the RDP/console
credential — a genuinely different route, and one you cannot drive for him (he clicks
it). A short dictionary password handed over in chat, especially one that may also be
live on other tailnet boxes, is worth exactly one plain sentence of risk — not a
lecture. It is also worth asking why the password exists at all when sshd refuses
passwords: it is nearly always for a different service on that host.

Check what this machine already has before assuming a setup step is needed:

```bash
ls -la ~/.ssh/; ssh-add -l; cat ~/.ssh/config 2>/dev/null; wc -l ~/.zsh_history
grep -iE "^ssh |^scp |^rsync " ~/.zsh_history | tail   # has this Mac ever SSH'd anywhere?
```

An empty `~/.ssh`, an agent with no identities, and zero ssh commands in shell history
mean there is no pre-existing credential to reuse — say so plainly rather than hunting.

### Step 3.5 — Getting in when password auth IS the route

When the parenthetical reads `publickey,password` and the user supplies the login, log in
with **expect** (macOS ships `/usr/bin/expect`; there is no `sshpass` by default). Full
recipes for login, sudo, and key installation: `references/password-ssh-from-macos.md`.

The rules that matter most:

- **Guess the login as the hostname first.** Host `pc2` → user `pc2`. Then root / admin /
  user / ubuntu and the user's own first name. A tailnet login email (`someone@gmail.com`)
  is never a shell username — do not spend calls on it.
- **One username per invocation, `-o NumberOfPasswordPrompts=1`.** sshd's default is three
  attempts; a loop that lets each guess retry three times can trip lockout on the account.
- **Install our public key the moment a login succeeds**, then add a `~/.ssh/config` alias.
  The password is then used exactly once and never stored or reused. Re-verify with a
  `BatchMode=yes` connection that prints a marker — that is the proof it is keyless.
- **sudo on these boxes usually takes the same password.** Use `sudo -S -p PWPROMPT` and
  match that custom prompt in expect; ssh's own `password:` prompt and sudo's appear in the
  same stream, so a distinct prompt string is what keeps them apart.
- **Report the box's real state before proposing any build**: host, GPU (`nvidia-smi`),
  what is already resident and what is already installed. Do not change a password or any
  system config without an explicit instruction — flag it as a risk instead.
- **The user's hardware claim may be wrong.** They may say "RTX 4060" for a box that is a
  4070. Report what `nvidia-smi` actually says rather than echoing the claim back.
- **Run remote scripts through `scripts/remote-run.sh`, not an inline ssh one-liner.** A
  multi-line body inlined in `ssh host "..."` collides with ssh's own quoting: any
  parenthesis or nested quote dies with `bash: -c: line 1: syntax error near unexpected
  token '('`, and each retry burns a round trip. The wrapper base64-encodes the script and
  decodes it on the far side, so the payload is quote-inert and streams without touching
  the remote disk. It handles plain, sudo, and password-sudo.
- **A long `sudo` install finishes long before its expect session does.** `apt-get`
  restarts services and the expect `spawn` can sit on a dead stream, so the local log
  freezes while the remote work is already done. Before concluding anything from a frozen
  log, verify the remote side directly: `dpkg`/`command -v` for what landed, `pgrep` for
  whether anything is still running, and compare local log mtime against the remote
  binary's mtime. When the remote state is complete, kill the hung wrapper and move on.
- **Never `pkill -f <name>` when the wrapper script's own path contains that name.**
  Killing "exo" from a script called `pc2_exo.sh` matches the script's own process and
  takes down the session mid-run — the connection drops and the log stops with no error.
  Match something unique to the target (`pkill -f 'bin/exo'`), or exclude self with
  `pkill -f <name> -v $$`.

### Tailscale SSH (the keyless route)

If `sshHostKeys` for that peer is non-empty in `status --json`, the target runs the
Tailscale SSH server and you can auth by tailnet identity — no keys, no passwords.

- `No ED25519 host key is known for <host> ... you have requested strict checking`
  → the **target is not advertising a host key**, i.e. Tailscale SSH is not enabled
  there. Fix on the target: `sudo tailscale up --ssh`.
- `tailnet policy does not permit you to SSH as user "<name>"`
  → the server is on and reachable, but the **ACL blocks it**. Fix in the admin console
  policy file (browser at login.tailscale.com — no terminal on any PC needed). Default
  ACL only grants `root`/non-root for same-user devices, and the requested SSH user must
  exist as a local account on the target.

An ACL-only blocker is the best case: it is fixable entirely from the user's browser and
leaves passwordless, keyless access behind. Recommend it over handing over passwords.

## Step 4 — Pitfalls that cost a whole call

- **`tailscale ssh <user>@<host>` can hang indefinitely** waiting on a browser check-mode
  approval, with no output. Never put it in a `for` loop or a short-alarm wrapper — it
  swallows the entire call's timeout and you lose the other iterations' results. Run it
  once, in the background or redirected to a file, then read the file.
- **macOS has no `timeout`.** Use `perl -e 'alarm N; exec @ARGV' -- <cmd>`. `gtimeout`
  only exists with coreutils.
- Kill stray sessions when you abandon a probe (`pkill -f "tailscale ssh"`); a hung child
  otherwise keeps the process table dirty across calls.
- The `-o StrictHostKeyChecking=no` + throwaway `UserKnownHostsFile` combination matters
  for probes — TUN hostnames change and you do not want to pollute the user's
  `known_hosts` while reconning.

## Presenting the result

Give: the verified network facts, the ONE blocker, and 2-3 named routes with a
recommendation — then stop. Plain text, no markdown formatting (CLI). Rank routes by
what the user has to do, not by what is elegant: "switch target to a box with password
auth" beats "you fetch me the login" beats "someone must go run a line on that machine".

See `references/office-tailnet-inventory.md` for MARU's office tailnet: machines, roles,
and what each one accepts.

Offloading a long-running DB/job worker from this Mac onto a remote GPU box (rather than
editing that box's code in place) is a different shape of the same class — see
`references/remote-worker-offload.md`. Provisioning that box to actually accept GPU
workloads (Docker-GPU runtime, python/venv, node, and the verification that proves each)
is `references/gpu-box-provisioning.md`; the quote-safe remote exec wrapper is
`scripts/remote-run.sh`.

Letting a **cloud-hosted webapp** start those jobs, rather than only the Mac, is the same
architecture with a second door: everything writes job rows to one table and the remote box
pulls. See `references/webapp-job-queue.md` for the topology, the object-store choice and
its credential trap, the worker-key privilege split, the queue/worker/file-naming pitfalls,
and the ordering that makes a job table safe to introduce.

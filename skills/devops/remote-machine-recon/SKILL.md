---
name: remote-machine-recon
description: Use when scoping which remote machines can run a job.
version: 1.0.0
tags: [remote, ssh, tailscale, vpn, hardware-inventory, gpu, reconnaissance]
license: MIT
---

# Remote machine recon

Establish ground truth about machines the user owns but is not sitting at, BEFORE planning
any work around them.

## When this applies

"I have three computers that run as servers" · "can this run on one of my PCs" · "what
hardware do I have" · "check what can actually be used for this".

## The hard rule

**Never state what a remote machine can do from its hostname, a vault note, or the user's
memory of it.** Hostnames are labels — `gdev-r` tells you nothing about the GPU. The user's
recollection of their own fleet is routinely wrong (a note said "idle RTX 5090"; the user said
"one NVIDIA, two Radeon"; neither matched a verified reading). Confirm from the machine, and
where you cannot, say the answer is unknown rather than implying completeness.

## Procedure

### 1. Get the mesh actually up, then read its state

For Tailscale, an installed app often has a **stopped backend**. `tailscale status` returning
"Tailscale is stopped" is a state, not an error — but `tailscale ip -4` may still return a
cached address, so never use the IP alone as proof the tunnel is live. Read
`tailscale status --json` → `BackendState`, and launch the app if it is Stopped. Confirm
`Health` is empty afterwards.

### 2. Enumerate the peers

From `status --json`: peer hostname, `OS`, `Online`, `LastSeen`, `Relay`, whether the
connection is **direct or relayed**, and `sshHostKeys` presence. Peers seen weeks ago vs now
tell you which part of the fleet is actually a fleet.

### 3. Fingerprint services by port — this is how you learn what a box DOES without logging in

| port | service |
|---|---|
| 22 | SSH (grab the banner for distro/version) |
| 3389 | RDP / xrdp — a Linux box can expose this, so do not read it as Windows |
| 6443 | Kubernetes API server |
| 10250 | kubelet — the box is a k8s **worker** |
| 11434 | Ollama (`/api/tags` lists models unauthenticated) |
| 8080 / 8081 / 8082 | llama.cpp server — `/props` and `/v1/models` leak the model path and alias |
| 4000 | LiteLLM gateway (Swagger UI at `/`) |
| 80 / 443 | generic web — read the `<title>`: Jupyter, Gitea, Grafana, Portainer, code-server |
| 5900 | VNC |

Read the BODY, not just the status code. `:6443` returning 401 with a `{"kind":"Status"...}`
body is a real apiserver; a `503 apiserver not ready` means the cluster is broken right now —
report that, it is a live outage the owner may not know about.

### 4. Determine SSH auth mode WITHOUT credentials

The decisive probe, no password required:

```bash
ssh -o PreferredAuthentications=none -o BatchMode=yes \
    -o StrictHostKeyChecking=no -o ConnectTimeout=6 <user>@<host>
```

The `Permission denied (...)` line names the accepted methods:

- `(publickey)` — **key-only.** Nothing gets in without a key already installed on that box.
  No password, no fallback. A one-time action ON the machine is unavoidable.
- `(publickey,password)` — a one-time password gets you keyless access from then on.

Also check whether a keyless path already exists: `tailscale ssh <host>` uses tailnet
identity with no keys. If the destination does not advertise `sshHostKeys`, the Tailscale SSH
server is not enabled there. An ACL denial reads as *"tailnet policy does not permit you to SSH
as user X"* — that is fixed in the admin console **from a browser**, no terminal on the box
needed. Do not report an ACL denial as a network problem.

**When password auth IS advertised, try the password the user already holds — the username
is usually the blocker, not the password.** `Permission denied (publickey,password)` tells
you the server will accept a password, but not which account it belongs to. The working
username is frequently the machine's own hostname or the short name the user calls the box,
NOT `root`/`admin`/`ubuntu`/the owner's first name. Sweep plausible usernames against the
one password you have:

```bash
for u in root admin <short-hostname> <owner-name>; do
  printf '%-10s ' "$u"
  ssh -o PreferredAuthentications=none -o BatchMode=yes -o ConnectTimeout=6 "$u@$host" 2>&1 \
    | grep -oiE 'permission denied \([a-z,]*\)'
done
```

Then authenticate once per candidate with the password on stdin. Do not install a
password-prompt helper — `expect` ships with macOS at `/usr/bin/expect` and is enough:

```bash
spawn ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no \
          -o NumberOfPasswordPrompts=1 <user>@<host> "<probe command>"
expect { -re "(?i)assword:" { send "$pass\r"; exp_continue } eof }
```

Two traps when doing this:

- **`sudo -S` cannot be driven through a non-interactive ssh channel.** `ssh host "echo pw |
  sudo -S ..."` fails to reach the prompt. Wrap the remote command in a PTY (`ssh -tt`) and
  feed the password on the same expect branch that matches the sudo prompt.
- **Quote-escaping through ssh → bash is a trap.** Heredocs, `awk`, and parentheses get
  mangled by the double layer. Write the remote script to a LOCAL file, `scp` it over, and
  run `bash /path/script.sh` — one layer of quoting, and the script is re-runnable.

Once in, install your key so the password is not needed again — a one-time password is a
bootstrap, never the steady state.

### 5. Look for EXISTING credentials before asking the user for one

Check for private keys, `~/.ssh/config`, ssh-agent identities, and shell history containing
`ssh`/`scp`/`rsync`. Finding none is itself the finding: it turns the answer from "give me a
password" into "someone must run one command on that box".

### 6. Report per machine, and name the unknown

For each host: reachable?, OS, confirmed services, SSH auth mode, verdict, **and what is still
unknown**. Then the single blocking action and who must perform it. Half the value of this task
is naming the unknown explicitly.

## Pitfalls

- **A GPU cannot be confirmed over the network.** With no DCGM (`:9400`), node-exporter
  (`:9100`) or metrics endpoint, presence of a card is unverifiable without a login. Do not
  infer a GPU from "it runs Ollama/llama.cpp" — those run CPU-only on big-RAM machines, and
  both serving boxes here ran 27B models with no GPU evidence. Inside the container/machine the
  settling command is `nvidia-smi` / `rocminfo | grep gfx` / `clinfo` / `grep -i runtime`.
- **Run the vendor sanity check before accepting any spec.** "Nvidia 9070" is not a product —
  9070 is an AMD Radeon RDNA4 part. A wrong vendor name silently invalidates an entire
  CUDA/TensorRT plan, so verify vendor **and** model together and say so out loud.
- **A closed port is evidence of nothing; an open port is evidence of something.** Services
  bound to localhost never appear. Never conclude a capability is absent from a scan.
- **Do not infer the OS from the port set.** xrdp on 3389 is common on Linux servers.
- **macOS has no `timeout`.** Bound every probe with
  `perl -e 'alarm N; exec @ARGV' -- <cmd>`, or one hanging host stalls the whole sweep.
- **A hanging `tailscale ssh` is usually an auth/check prompt, not a dead host.** Do not report
  it as unreachable; re-run it so the prompt is visible, or bound it and say it needs approval.
- **Clean up probe stragglers** after a sweep (`pkill -f "tailscale ssh"`) — orphaned SSH
  processes linger and confuse the next attempt.

## Mapping a workload onto the fleet

Translate the job's real constraint onto the machines, and say plainly when nothing matches:

- CUDA / cuDNN / TensorRT are **NVIDIA-only**. Radeon needs ROCm (Linux) or DirectML (Windows),
  and OpenCV built `WITH_CUDA` will not build against it.
- A Kubernetes cluster is a **deployment substrate**, not a GPU. Do not count nodes as compute
  capacity.
- A small VPS almost never has a usable GPU.
- A dev laptop (Apple Silicon) has no CUDA **ever**; Docker Desktop on macOS has no GPU
  passthrough. It is a correctness/baseline machine, never a deployment target.
- If the requirement is a GPU and none is confirmed, the honest deliverable is "not yet known"
  plus the one command that settles it — not a plan built on an assumption.

When the target turns out to be unconfirmed, design the work so the **backend resolves at
runtime** and no layer imports a vendor API. Then the plan stays correct whichever way the
hardware answer lands, and the port is a build change rather than a rewrite.

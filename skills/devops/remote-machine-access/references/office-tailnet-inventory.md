# MARU's office tailnet — inventory

Rebuild it rather than trusting this file when it matters: re-run the Step 1-3 probes.
Treat the table as stale the moment a probe disagrees.

## Tailnet

- Login identity: `roverr.group@gmail.com` (display "rover -r"), owner/admin
- Tailnet: `tailc5e7bb.ts.net`, MagicDNS enabled
- This Mac: `kamaruls-macbook-pro` = `100.74.236.5`
- Install: standalone **macsys** build; GUI at `/Applications/Tailscale.app` (also the
  `tailscale` CLI at `/usr/local/bin/tailscale`)
- `TailscaleStartOnLogin = 1` — if it reads as `Stopped`, it was stopped by hand or the
  backend failed, not because it is unconfigured

## Machines

| Node | OS | Role / notes | RDP | SSH accepted |
|---|---|---|---|---|
| `pc1` | linux | office server; `100.96.29.87` | 3389 open | **publickey ONLY** — no password auth |
| `pc2` | linux | **GPU worker candidate**, `100.95.227.26`, hostname `pc2-MS-7E32` | — (22 only) | publickey + password; **our key installed** (user `pc2`) → keyless |
| `gdev-r` | linux | dev box, serves 80/443 | 3389 open | publickey + password |
| `vps-33d29325` | linux | VPS; runs the **Tailscale SSH server** (`sshHostKeys` present) | 3389 open | Tailscale SSH — ACL was the only blocker |
| `roverr-group` | windows | | | publickey + password + keyboard-interactive |
| `gacc-r`, `gcrm-r`, `ghrm-r`, `gitis-r`, `gops-r` | windows | Unconfirmed but the naming reads as one business suite (Accounts / CRM / HRM / ITIS / OPS) | 3389 open | `gacc-r`: **nothing listening on 22** (RDP only) |
| `homebase`, `n8n` | win / linux | `n8n` is an automation host | | offline when last checked |

## `pc2` — verified detail (the GPU box)

- Ubuntu 26.04.1 LTS, kernel 7.x, 20 cores, 60GB RAM, 915GB disk (8% used)
- **RTX 4070 SUPER, 12.44GB VRAM**, driver 595.91.07, CUDA 13.2, `nvcc` present
  (the user described it as a 4060 — `nvidia-smi` is authoritative)
- **Provisioned for GPU work:** `nvidia-container-toolkit` + `nvidia` docker runtime,
  `python3-pip`/`python3-venv`, `nodejs` 22 / `npm` 9, `jq`, `colmap`
  (installed but broken out of the box — `colmap --version` fails on a missing
  `libPoseLib.so`; irrelevant to ODM, which is containerised, but it matters for any
  host-side SfM stage). `pc2` is in the `docker` group.
- **ODM GPU image pulled:** `opendronemap/odm:3.6.1-gpu`. The plain `:3.6.1` tag is
  CPU-only and ignores the card even with `--gpus all`.
- **Working venv:** `/home/pc2/lunav-test/venvs/edge` — torch 2.14.1+cu130 (CUDA 13.0),
  ultralytics, opencv. Test material under `/home/pc2/lunav-test/`.
- **Already resident and consuming the GPU:** `exo` (a distributed LLM cluster,
  ~7.5GB of 12.4GB VRAM, set up to auto-start with sudo), `ollama` (active, no models
  pulled). Desktop session + firefox hold small allocations on top.
- **Tailnet throughput to this box is RELAYED, not direct** — measured ~155 KB/s on a
  small file transfer. Fine for tests, painful for real payloads; a direct path is worth
  fixing before any pipeline that moves gigabytes.
- `hermes-gateway.service` runs on the box: `:8842` and **`:9900` bound to `0.0.0.0`**
  (reachable from every tailnet peer, and beyond depending on the firewall).
- The login password is also the **sudo** password and the user is in the `sudo` group.
  Same password on other tailnet boxes is a real risk — flag it, do not change it
  unprompted.
- `~/exo`, `~/hive-swarm`, `~/HIVE-SWARM` exist; the box is an AI-lab node, not idle.

## Why `pc1` is the worst default target

It is key-only: sshd accepts `publickey` and nothing else, and this Mac has never held an
SSH key or run an ssh command. There is no path in from here without a first-time action
performed on `pc1` itself. When the user names `pc1`, surface that before discussing
what to build.

Re-verified: pc1 is online, port 22 and 3389 open, `sshHostKeys` empty (no Tailscale SSH
server there). Every username probed returns `Permission denied (publickey)`, and forcing
`PreferredAuthentications=password` is refused the same way. A team-supplied password for
pc1 is therefore **untestable over SSH, not wrong** — it is most likely the RDP/console
credential for the open 3389 port. Do not let the user chase "the right password".

## Route ranking for this tailnet

1. **Target `pc2` or `gdev-r`** — password auth is on; one-time login, install our key,
   keyless forever after.
2. **Fix the `vps-33d29325` ACL** from the admin console in the browser — no passwords
   stored, no terminal on any PC, ends with passwordless access.
3. **`pc1`** — requires handing the office `sudo tailscale up --ssh`, or an
   `authorized_keys` install, on the machine itself.

## Access the user has

No RDP client installed, no saved RDP connections, no `~/.ssh/config`, no keys, no ssh
history. Assume a **screen-explicit walkthrough** is required for any GUI or terminal
step on his side; he does not drive SSH from this Mac himself.

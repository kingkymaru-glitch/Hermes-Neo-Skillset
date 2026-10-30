# Provisioning a Linux GPU box to actually run compute workloads

Use when the remote tailnet box HAS the GPU and you need it to run the real work
(ODM reconstruction, YOLO inference, 3DGS training). Reachability, the survey, and
the pull-worker architecture are in `remote-worker-offload.md`; this file is the box
prep that follows it.

Order matters. Verify the GPU is visible to the RUNTIME before installing any
workload's dependencies, so a later failure is unambiguously the workload and not the
plumbing underneath it.

## 0 — Survey first, never skip

```bash
nvidia-smi                                                   # driver + VRAM
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv   # who owns the card
systemctl list-units --type=service --state=running          # resident services
ss -tlnp                                                     # anything bound 0.0.0.0
for c in ffmpeg git docker nvcc blender node python3; do printf '%-9s ' $c; command -v $c || echo -; done
df -h /
```

A GPU box in an AI lab is rarely idle: an LLM server or a desktop session may already
hold most of the VRAM. Establish the free headroom before promising a workload fits —
see the VRAM contention section below.

## 1 — Docker GPU runtime (`nvidia-container-toolkit`)

Any containerised GPU workload needs this. ODM is one: it ships as a Docker image, and
without the toolkit the container sees **no GPU at all** regardless of what the host has.
A host `nvidia-smi` that works proves nothing about the container runtime.

```bash
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verification is this line, and only this line — it must print the actual card:

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

A newer host driver runs older CUDA base images fine (backward compatible), so pick a
base tag at or below the host's CUDA version rather than the newest available.

Confirm the runtime registered too: `docker info | grep -A3 Runtimes` should now list
`nvidia` alongside `runc`.

### A container image can be CPU-only even when the host has a GPU

The toolkit only makes the device *visible*. Whether the image's own binaries use it is a
separate fact, and some projects publish the GPU build as a **different tag of the same
version** — so the tag you pulled decides this, not the flag. OpenDroneMap is the concrete
case: `opendronemap/odm:<ver>` is CPU-only and `opendronemap/odm:<ver>-gpu` is the CUDA
build. List the registry's tags before assuming yours is the accelerated one:

```bash
curl -s "https://hub.docker.com/v2/repositories/<org>/<repo>/tags?page_size=100" \
  | grep -o '"name":"[^"]*"' | grep -i gpu
```

`--gpus all` on a CPU-only image runs happily and silently uses the CPU. Keep the CPU tag
as the default so existing non-GPU hosts (a Mac, a laptop) are unaffected, and select the
GPU tag only where the toolkit is installed.

## 2 — Python (pip + venv)

Modern Ubuntu ships `python3` **without pip**, and no venv module either. This is not a
broken box; it is the split-package default.

```bash
sudo apt-get install -y python3-pip python3-venv
python3 -m venv --help >/dev/null && echo "venv OK"
```

Never bootstrap pip with `get-pip.py` when the distro package exists — it bypasses apt's
upgrade path and lands outside the system's expectations.

Prefer a per-workload venv (`python3 -m venv ~/work/<job>/.venv`) over system packages,
especially for torch: the CUDA wheel and the system python can disagree about versions.

## 3 — Node (only when the workload shells out to it)

LUNASCAN's Batch 5 GLB optimizer (`tools/3d-optimize/optimize.mjs`) requires `node` on
PATH; `optimize.py` degrades gracefully and keeps the raw glb when it is absent. Install
only if that stage is in scope:

```bash
sudo apt-get install -y nodejs npm
```

## 4 — VRAM contention is a scheduling decision

If a resident service already owns most of the card, the worker and that service cannot
both have it. Surface this to the user as an explicit either/or before running anything —
keep the resident service and run workers in the remaining headroom, or stop it while
workers run. Sizing guidance: small detector inference (YOLO-nano/small) fits in a few GB;
photogrammetry and 3DGS training want the whole card. Do not stop a service the user
considers load-bearing, and do not plan around it silently.

## 5 — Prove the accelerator is actually working, not merely present

A `--gpus all` run that completes without error proves the device is *visible*. It does
not prove the workload used it. Two independent checks, both cheap:

1. **Sample during the run.** Loop
   `nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader` beside the job.
   Rising VRAM plus a non-zero utilization peak is the evidence. A container that starts
   cleanly and leaves utilization at 0% for the whole run is executing on the CPU.
2. **Compare the artifacts, not just the wall-clock.** Assert the accelerated run produced
   the same class of output — for a reconstruction, mesh / material / vertex counts within a
   percent or two. A large speedup with a visibly thinner output is a settings difference,
   not a win.

A fair benchmark holds the input, the flags, and the stage identical on both machines, and
changes one variable at a time. A multi-core CPU baseline may already be well tuned, so
quote the measured ratio rather than an expectation — and when the slow side took a long
tuning session to get there while the fast side needed none, say so, because that is part
of the result.

## Pitfalls

- **Adding a user to the `docker` group does not affect sessions that are already open.**
  The new group set applies at the next login. Either wrap the call (`sg docker -c '<cmd>'`),
  reconnect, or keep prefixing `sudo` — do not conclude the group change failed.
- **An empty `docker` group means every docker call needs sudo.** `getent group docker`
  returning `docker:x:973:` with no members is the tell. Either prefix `sudo` or add the
  user to the group — but adding to the group is a security-relevant change on a
  shared box; ask first.
- **`nvidia-smi` on the host is not proof a container can see the GPU.** Only the
  `docker run --gpus all` check is. And that check is not proof the workload *used* it — see
  section 5.
- **Installing a workload's deps before proving the runtime wastes the debugging budget.**
  When a GPU workload then fails, you cannot tell whether it is the workload or the
  container plumbing. Prove the runtime first, in isolation, every time.
- **Do not change passwords, stop services, or edit system config unprompted.** Report the
  finding and let the user decide.
- **Report the box's measured state, not the user's recollection of it.** They may name a
  different GPU model or VRAM than `nvidia-smi` reports.

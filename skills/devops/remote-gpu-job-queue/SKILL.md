---
name: remote-gpu-job-queue
description: Webapp triggers GPU work on a NAT'd box via job queue.
---

# Remote GPU Job Queue (webapp → NAT'd GPU box)

## When to use
A hosted webapp (Vercel) must run heavy compute (photogrammetry, YOLO, splat
training) on a workstation behind NAT/Tailscale. The founder also wants a
visible "is the worker alive" indicator in the header.

## The one constraint that decides the design
**Vercel cannot reach a NAT'd box. Ever.** Not a config problem — a network
fact. Therefore the remote machine **pulls** work; nothing pushes to it.

```
  Any client ─► INSERT job row ─► Supabase ◄─┐
  (browser,                        │        │
   Mac app)                        │   worker polls
                                   │   (claim_gpu_job)
                                   ▼
                          runs on GPU, uploads to R2
                                   │
                          finish_gpu_job → row DONE
```
Supabase is the meeting point. Consequence: "trigger from the Mac" and
"trigger from the webapp" become the SAME code path — one queue, many doors.

## Schema shape that works
- `gpu_jobs` — one table, a `kind` column (`odm`/`splat`/`yolo`), status
  CHECK (QUEUED/RUNNING/DONE/FAILED/CANCELLED), params jsonb, input_key /
  output_key (R2), progress, stage, error, result jsonb, created_by, timestamps.
- `gpu_workers` — heartbeat: hostname, gpu_name, vram_total/used, online,
  current_job, version, `last_heartbeat`.
- Per-account permission column on `profiles` + a `can_use_gpu()` helper.

## Atomic claim — the non-negotiable bit
Two workers must never take the same job. One statement does it:
```sql
select * into j from gpu_jobs where status='QUEUED'
 order by created_at for update skip locked limit 1;
```
`FOR UPDATE SKIP LOCKED` is what makes it safe. Do not hand-roll
select-then-update.

## Privilege split (do this from the start)
Claim/heartbeat/finish are **service_role only** — `revoke all ... from public,
anon, authenticated; grant execute ... to service_role;`. The browser never
needs them. Owner/admin RPCs (`cancel_gpu_job`, `set_gpu_access`) are
granted to `authenticated` with an internal guard.

## PITFALL — Python 3.14 + ultralytics dataloader workers crash training
On a Python 3.14 worker host, `model.train(...)` with the default `workers=8`
dies with `ConnectionResetError: [Errno 104] Connection reset by peer` raised
from `multiprocessing/connection.py` inside the forkserver — the run aborts
before the first epoch. The CUDA device initialises fine, so the log looks
healthy right up to the crash.

Fix: pass **`workers=0`** in the train call. Any training executor on a 3.14
box must set it. (Measured: 10 epochs, 111 images, yolov8n — 8.7s with
`workers=0` vs an outright crash with the default.)

## Benchmark — train on the GPU box, not the laptop
Same dataset (111 auto-labelled frames, 89 train / 22 val, yolov8n, 10 epochs,
imgsz=640):

| Host | Device | Time | Per epoch |
|---|---|---|---|
| Mac M1 Pro | MPS | 158.1 s | 15.8 s |
| RTX 4070S | CUDA | 8.7 s | 0.9 s |

**18x.** The gap is far wider than inference (12.6x) because PyTorch's MPS
backend silently falls back to CPU for unimplemented ops — the Mac even logged
`NMS time limit 3.100s exceeded` during validation where CUDA did not. Training
is the workload where Apple GPUs lose most; recommend the CUDA box for any
fine-tuning, and keep capture/augmentation local.

## Dataset size vs the upload cap
A raw auto-labelled dataset was 182 MB; downscaling images to 640px and JPEG
q70 made it 4.6 MB with no loss, because training at `imgsz=640` cannot use more
resolution anyway. Do this BEFORE designing any transfer step — it usually
removes the need for chunking or a paid plan entirely.

## PITFALL — COLMAP flag names differ by BUILD, and the GPU flags may not exist
SIFT flag names flip between COLMAP versions AND the distro package may be a
CPU-only build:
- COLMAP 4.x (Homebrew/macOS): `--FeatureExtraction.use_gpu`, `--FeatureMatching.use_gpu`
- COLMAP 3.12 (Ubuntu package): `--SiftExtraction.use_gpu`, `--SiftMatching.use_gpu`

Using the wrong family aborts the step with `unrecognised option`, and the
subsequent `mapper` then fails with the misleading `No images with matches found
in the database` — which reads like a data problem, not a flag problem. Always
`colmap <subcmd> --help | grep -i use_gpu` on the target machine first.

Also: the Ubuntu `colmap` package needs `libposelib` installed or the binary
dies with `error while loading shared libraries: libPoseLib.so`. And note
`colmap --version` is not a valid flag (use `colmap help`) — an "unrecognised
option" there is a sign the binary WORKS, not that it is broken.

## PITFALL — object-storage upload caps can bite before your own bucket limit
Supabase free tier rejects uploads above ~50MB with HTTP **413 EntityTooLarge**
(even though `storage.buckets.file_size_limit` reads `null` — the ceiling is
project-level). Symptom: the upload returns 400/413 and the queued job then
fails with `Object not found` because the input never landed.

Consequence for design: **do not assume large inputs can be uploaded from the
client.** If a pipeline needs a big dataset (e.g. a COLMAP model for splat
training), generate or stage it ON the worker machine and keep the uploaded
payload small. Check the real ceiling empirically before designing the flow.

## PITFALL — the worker's download target must keep its file extension
Naming a downloaded input `input` (no suffix) means any `Path.suffix` branch
silently misfires: videos get routed into `shutil.unpack_archive` and fail
with `ReadError: Unknown archive format`. Derive the extension from the key:
```python
ext = Path(job["input_key"]).suffix.lower() or ".bin"
src = work / f"input{ext}"
```
Symptom: job fails in <1s with an archive-format error on a video.

## PITFALL — Docker writes root-owned output; cleanup needs sudo
ODM (and any `docker run` as root) leaves root-owned files under the mount.
`rm -rf` as the normal user fails with a wall of `Permission denied`. Either
run the container with `--user $(id -u):$(id -g)`, or accept that cleanup is
`sudo rm -rf`. Do not conclude "the disk is stuck" — it is a UID mismatch.

## PITFALL — VRAM contention with an always-on co-tenant
If something else permanently holds VRAM (an LLM server, a desktop session),
small models coexist but large ones do not. Sample
`nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader`
DURING the run to prove the GPU is engaged (a jump + nonzero util), rather
than assuming presence == usage. Budget the job's VRAM against what is
already committed and tell the user BEFORE the run, not after it OOMs.

## Worker status indicator (the header chip)
Mirror whatever local indicator the user already trusts. Three states:
- green = live and idle
- blue = live, running a job (show %)
- amber = not reporting (jobs still queue; say so explicitly)

Liveness = `online && now - last_heartbeat < 30s`. Expose hostname, GPU,
VRAM used/total, heartbeat age, jobs done, worker version. The amber state
must say jobs will WAIT, not that they failed — otherwise the user thinks
work was lost.

## Verify in this order (each step proves the next is worth doing)
1. **Direct executor test** — stub Supabase and R2, call the job function with
   a local file. Proves the GPU pipeline before any queue exists. This is
   where the extension bug above surfaced; do not skip it.
2. Then wire the queue and run one real job end-to-end.

Do NOT claim the pipeline works from a green build. A compile-green UI with
an unexercised executor is unverified.

## Secrets reality check
`service_role` and R2 keys usually live ONLY in the Supabase dashboard — not
in the repo, not on the dev Mac, not in Vercel env (which typically holds just
the two `NEXT_PUBLIC_*` public vars). `supabase secrets list` may 403 on a
non-owner account. Do not burn turns hunting the filesystem; ask the user for
the values, or give them the file path + line numbers so they paste it
themselves. Offer the self-paste option for god-keys — it keeps them out of
the chat transcript.

# Offloading a worker from this Mac to a remote GPU box

The shape: a job worker (Blender/OSM surroundings, YOLO inference, ffmpeg transcode) runs
on this Mac today and should run on a stronger box on the tailnet. The Mac keeps the
website and the API; the remote box does the heavy work.

This is the *other* half of remote-machine-access: not "edit code on that machine", but
"relocate a long-running process onto it". Reachability rules are identical — do Step 1-3
recon first, and settle the access route before designing anything.

## The pattern: pull-based worker

A worker is a loop, nothing more:

1. ask the DB for a QUEUED job
2. atomically claim it, mark RUNNING
3. do the work, write the result, mark DONE
4. nothing to do → sleep, repeat

Because the worker talks only to Supabase (already cloud-hosted), it does not need to be
on the same machine as the app. The remote box makes **outbound HTTPS only** — no open
ports, no inbound firewall rule, no VPN beyond the tailnet that already exists. The app
never contacts the worker; the worker pulls work.

```
  Mac (website + API)                Remote GPU box
  click "Run" -> INSERT job row      worker loop
        |                                  |  polls jobs table
        v                                  v
      Supabase  <---- claim job ------- Supabase
        |                                  |
        +---- job DONE, result ------------+
```

Say this plainly when explaining it: the only thing tying a worker to this Mac today is
that it reads and writes **local disk**. Move the files to a shared store (R2 / Supabase
storage) and the worker becomes location-independent. That is the whole migration.

## Four conditions for this to be safe

1. **Atomic claim.** One SQL statement, not read-then-write:
   `UPDATE jobs SET status='RUNNING', claimed_by=$1 WHERE id = (SELECT id FROM jobs WHERE
   status='QUEUED' ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING id`.
   Two workers must never take the same row.
2. **Heartbeat + reclaim.** The worker updates a `last_seen`/`updated_at` column each
   cycle so a crashed worker's rows can be reclaimed after a timeout. The CDM Blender
   worker already reclaims BUILDING rows older than 10 min — reuse that mechanism.
3. **Files over the network.** Inputs pulled from R2/storage, outputs pushed back. This is
   the real work of the migration — the polling loop is the easy part. Two things to get
   right early:
   - **`rsync` does not create the destination's final path component.** Pushing to a
     directory that does not exist yet fails with `change_dir#3 ... No such file or
     directory` and `rsync error ... (code 3)`, which reads like a network fault and is not
     one. `ssh <host> 'mkdir -p <dir>'` first, or send to a parent that exists.
   - **Measure the link before designing around it.** Check whether the tailnet path is
     `direct` or relayed and time a real transfer; a relayed path can be an order of
     magnitude slower, which is fine for a test clip and fatal for a pipeline moving
     gigabytes. Report the measured rate rather than assuming LAN speed.
4. **Verify the result, never trust DONE.** Check the output exists and is non-empty
   before marking complete. A worker that exits 0 having written nothing produces an
   opaque downstream ENOENT — the same failure class already seen in the CDM pipeline.

## What actually changes in the app

Today the API route spawns the worker locally (detached, one-shot, exits when drained).
After: the API route only INSERTs a job row. The Mac stops doing the work entirely.

## Survey the target before you design anything

Once you can log in, inventory the box before proposing a build. Four facts decide the
design, and guessing any of them wastes a round trip:

1. **The GPU is what `nvidia-smi` says, not what the user said.** They may name a 4060
   for a box holding a 4070. Report the actual model and VRAM — it changes what fits.
2. **What is ALREADY resident and holding VRAM.** Check
   `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv` and
   `systemctl list-units --type=service --state=running`. An LLM server or desktop session
   may already own most of the card. A GPU box in an AI lab is rarely idle.
3. **What is installed vs absent** (`ffmpeg`, `blender`, `docker`, `nvcc`, python, node).
   Missing tooling is a setup step, not a blocker — but do not promise a workload before
   confirming its runtime is there.
4. **Whether sudo needs a password, and whether the box already exposes services**
   (`ss -tlnp`). A listener bound to `0.0.0.0` is reachable by every tailnet peer.

### VRAM contention is a scheduling decision, not a detail

If a resident service already owns most of the card, the worker and that service cannot
both have it. Put this to the user as an explicit either/or — keep the resident service
and run workers in the remaining headroom, or stop it while workers run. Do not silently
plan around a service the user considers load-bearing, and do not stop it on your own.

## Presenting it

MARU's decisions here: he owns the hardware choice, and he wants the concept understood
before any code exists. Explain the loop and the pull model first, name the one blocker
(access to the target), ask which single workload to move first — not all of them — and
confirm the target box actually has the GPU before designing around it. Do not start
writing the worker until he picks the target and the workload.

The survey in the previous section becomes the agenda: the GPU verdict, what already owns
it, and the one contention decision — then ask which single workload moves first. Report
the box's state before any build, and never change a password or stop a service without an
explicit instruction; raise it as a risk instead.

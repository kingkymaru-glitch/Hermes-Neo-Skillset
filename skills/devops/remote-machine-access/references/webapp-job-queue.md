# Triggering remote GPU jobs from a cloud-hosted webapp

The ask: the heavy work already runs on a remote GPU box, but the trigger should come
from a deployed webapp as well as from the local machine. One queue, two doors.

Read `remote-worker-offload.md` first — the pull-based worker and the four safety
conditions there are the foundation. This file is the part that changes when a
cloud-hosted app is one of the producers.

## The constraint that decides the whole design

The webapp runs in a cloud (Vercel or similar). The GPU box sits behind NAT on a
tailnet. **The cloud can never reach the box.** This is a network fact, not a config
problem — no port opening, no VPN into the cloud, no inbound anything fixes it.

Therefore the box only ever PULLS. Every producer writes to the queue; the box is the
only consumer. Once that is fixed, the rest follows mechanically:

```
  Mac GUI ──────┐
                ├──► INSERT job row ──► Supabase ──► box polls, claims, runs
  Webapp ───────┘                          ▲                │
                                           │                │ result -> object store
                                           └── DONE ────────┘
```

The useful consequence to tell the user: the Mac is not special. "From the Mac AND from
the webapp" is one code path, not two — both insert a row. Nothing on the box changes
when a second producer appears.

## One table, a `kind` column

Do not build a queue per workload. One table with `kind` discriminates:

- `kind` — which pipeline (reconstruction, masking, splat training, detector run)
- `status` — QUEUED / RUNNING / DONE / FAILED
- `params` — jsonb, the per-kind knobs
- `input_key` / `output_key` — object-store keys, never local paths
- `progress`, `error`, `claimed_by`, `heartbeat_at`
- `created_by`, `created_at`, `started_at`, `finished_at`

Adding a capability later is a new `kind` value, not a new subsystem. Say this when
scoping — it is what makes "start with one kind" cheap instead of throwaway.

Keep the queue table separate from the asset tables. Do NOT bolt job columns onto the
`models` / project tables; a job has a different lifecycle and will otherwise couple
migration risk into the schema the live app already depends on.

## Files: object storage is the interface

The job row carries **keys, not paths**. The box downloads from the object store, works
in its own scratch, uploads the result, and writes the output key back. This is what
makes the worker location-independent, and it is the real work of the migration — the
polling loop is trivial by comparison.

### Pick the store whose credentials you can actually obtain

"Reuse the bucket the app already talks to" is the right instinct but it fails when that
bucket's credentials are not reachable: an R2 key lives in a different console from the
queue's, and the Supabase CLI may 403 on a non-owner account, so neither the repo, the
dev machine, nor the cloud env holds it.

When that happens, **Supabase Storage is the unblock** — the worker already needs the
service-role key for the queue, so it needs no second credential at all. Make the
backend switchable rather than hard-wired:

```
STORAGE_BACKEND=supabase|r2     STORAGE_BUCKET=<bucket>
```

with thin `storage_download` / `storage_upload` wrappers, so moving to R2 later is a
config change and not a rewrite. Say the tradeoff plainly: free-tier Supabase Storage is
~1 GB with limited egress — fine for a few-MB `.glb`/`.ply`, wrong for large datasets.

Supabase Storage REST shape (no SDK needed):

- create bucket — `POST /storage/v1/bucket` `{id,name,public}`. Omit `file_size_limit`;
  on free tier it is rejected with `413 EntityTooLarge`.
- upload — `POST /storage/v1/object/<bucket>/<key>` with header `x-upsert: true`
- authenticated download — `GET /storage/v1/object/<bucket>/<key>`
- public read (no auth header) — `GET /storage/v1/object/public/<bucket>/<key>`

## PITFALL — storage keys are BUCKET-RELATIVE; never double-prefix

A key that already begins with the bucket name (`gpu-jobs/<id>/out.glb`) builds the path
`<bucket>/<bucket>/<id>/out.glb` and uploads to the wrong place. Nothing complains: the
job still reports DONE and the row still records the key. Only fetching the object back
reveals it. Normalise before every call:

```python
def bucket_relative(key, bucket):
    prefix = f"{bucket}/"
    while key.startswith(prefix):
        key = key[len(prefix):]
    return key
```

## PITFALL — result filenames must be URL-SAFE (underscores, never spaces)

The object key travels through a URL on the publish path (sign → fetch → re-upload). A
space in the filename fails there silently — the fetch cannot read the file and the
upload never happens, with no error at the queue layer. Build names from an allowlist and
collapse the separators:

```python
safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in title)
safe = "_".join(filter(None, safe.split("_")))[:60] or "job"
```

A dated, machine-prefixed convention (`BOX_<YYYY-MM-DD>_<HHMM>_<title>.<ext>`) pays for
itself twice: GPU artifacts are instantly distinguishable from user uploads in a shared
library, and the names sort chronologically. Record the chosen name on the job row
(`artifact_name`, `produced_at`) and **reuse it at publish time** — renaming on publish
leaves the storage object, the library entry, and any downloaded copy disagreeing.

## PITFALL — an empty queue returns a row of NULLs, not SQL NULL

A `returns <table>` plpgsql function that finds no work returns a COMPOSITE row with
every column NULL. Over PostgREST that is a truthy dict, so `if job:` is True and the
worker tries to run a job whose `id` is None — crashing on the first `job["id"][:8]`.
Guard on the identity field: `if job and job.get("id"):`.

## PITFALL — a stale heartbeat row makes a live worker look offline

Any row in the workers table is a candidate for a bare `select ... limit 1`. A leftover
probe row (or a long-dead worker) can sort first and make the UI report "unreachable"
while the real worker heartbeats fine. Always `order by last_heartbeat desc`, and treat
liveness as `online && now - last_heartbeat < 30s`. When a status indicator disagrees
with reality, dump the whole table and look for junk rows before debugging the worker —
the indicator is usually reading the wrong row.

## The worker's DB key is a god key — scope it

The box needs to claim jobs and write results. Reaching for the service-role key is the
default and it is the wrong default: that key can read and write every table in the
project, and it would be sitting on an office machine.

Scope it down to the minimum that does the job:

- a dedicated DB role that can `SELECT` and `UPDATE` on the jobs table only
- insert/update rights on the result rows the job actually produces
- no access to auth/users, no DDL, nothing else

Raise this as an explicit decision with the user rather than silently shipping a
service-role key. It is a real security tradeoff, not a config detail, and the user
being liability-averse makes it worth one plain sentence.

If a god key is unavoidable, put it in a `chmod 600` env file on the box — never in the
repo, never in the cloud env, never echoed into a chat transcript.

## RLS: the worker has no end-user session

A row created by an authenticated user is normally invisible to another role. A worker
authenticating as its own DB role will therefore see **nothing** unless the policy allows
it — the classic symptom is a worker that runs, finds no jobs, and exits silently.

Give the jobs table an explicit policy for the worker role (and for the producers). Do
not weaken the policies on the existing asset tables to make this work; the queue is a
new table precisely so its policies can be written for this purpose.

Also split the RPC privileges: claim / heartbeat / finish are worker-only
(`revoke all ... from public, anon, authenticated; grant execute ... to service_role;`),
while cancel / grant-access are `authenticated` with an internal guard. The browser
never needs the claim functions.

## Order of operations — the queue ships before the consumer exists

There is a specific ordering trap. The webapp must be able to INSERT a job row before the
box can consume one, and the safest sequence is:

1. Ship the job table + its policies + the insert path (webapp can enqueue).
2. Ship the status surface (see below).
3. Ship the box's poller last, once there is something in the table to consume.

If the poller ships first it polls an empty table and there is no way to tell "no jobs"
from "broken auth". If the insert path ships without the status surface, the user has no
way to see their job is queued and will assume the button is dead.

## The status surface is part of the feature, not polish

The box is a pull worker: if it is off, jobs sit in QUEUED forever and the UI looks
broken. That is a design property, not a bug to explain later.

So the enqueue surface must carry, in the same panel:

- **worker liveness** — derived from the heartbeat column's age ("online / last seen
  2m ago"), not from a probe the cloud cannot make
- the job's own status and progress
- the failure reason when a job FAILED

Deriving liveness from `heartbeat_at` is the whole trick — it needs no new endpoint and
no inbound connectivity. A stale heartbeat is the honest answer to "is it connected".

Give the indicator three states, mirroring whatever local indicator the user already
trusts: live+idle, live+running (with %), and not-reporting. The not-reporting state must
say jobs will WAIT, not that they failed — otherwise the user thinks work was lost.

## Model the producer, not just the job

Two different output shapes will show up in the same queue and they should not be forced
into one:

- **asset-producing jobs** (reconstruction, splat) → a file lands in the object store and
  the natural follow-up is "attach this to the project"
- **analysis jobs** (detector runs) → rows of findings, not a model; they render as
  markers/records, not as a downloadable asset

Design the job row so `kind` can carry both, but do not promise the same result UI for
both. Say which shape each kind has when scoping.

## Publishing a result into a shared library

A private results bucket is not viewable — a 3D viewer needs an unauthenticated URL. So
"publish" is a deliberate second step, and it should be one action in the UI, not a
manual copy:

1. sign the private object (short expiry), fetch it, re-upload into a **public** bucket
2. insert the row the viewer reads, carrying the job id for traceability
3. stamp the job so the UI shows it as already published instead of offering the button

Keep the private and public buckets separate. Results stay private until someone
chooses to publish; that choice is the audit trail.

## Verify by fetching the artifact, not by reading the status

A DONE row is not evidence the file is reachable — the double-prefix bug above produced a
DONE row pointing at an object that did not exist. After the first real run, download the
result from its public URL with **no auth header**, confirm HTTP 200, and check the bytes
(hash compare, or validate the file header: glTF magic + declared length). Then confirm
the library query actually returns the row.

State which links you proved and which you did not. A compile-green UI with an exercised
executor but an unclicked button is still unverified — say so rather than implying the
whole chain works.

## Never write to another account's data

When a test artifact has to land somewhere, create a throwaway target or ask — do NOT
attach it to whichever project a query happened to return first. If it does land in
someone else's project, **duplicate** it to the right place rather than deleting the
original: you cannot judge whether that account still needs it, and a delete is
irreversible. Report the ownership you verified and let the owner remove it.

## Scoping it with the user

Prove the whole loop with ONE kind before adding the others. The plumbing — queue,
storage, liveness, auth scoping — is the hard and reusable part; the second and third
kinds are then small. A plan that starts with all kinds at once tests the plumbing and
four pipelines simultaneously, and a failure tells you nothing about which layer broke.

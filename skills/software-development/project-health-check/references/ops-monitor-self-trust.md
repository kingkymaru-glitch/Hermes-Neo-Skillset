# When a scheduled health digest lies — self-trust before trusting a monitor

A health collector (cron job, script, scheduled agent) is a piece of infrastructure with
its own failure modes. Its verdict about the site and its own correctness are separate
questions; a bad collector is indistinguishable from a bad site unless you separate them.

## The signature of a broken collector (vs a real outage)

| Reading | Meaning |
|---|---|
| Every URL returns `status: 0` (uniform, not a mix) | Probe-side failure — the collector cannot reach the network at all |
| A companion "deploy error" with a Node/Python stack trace | The collector's own runtime broke, not the site |
| Some routes 200, some 500/502 | Could be a real partial outage — investigate normally |
| Manual `curl` of the same URLs returns 200 | The collector is lying; do not report the outage |

A real outage degrades unevenly (one region, one route, one dependency). A broken probe
fails UNIFORMLY, because it never actually made the request.

## Root cause: the collector's cwd is gone

The single most common mechanism, seen with a `python3 collect.py`-style digest:

1. The collector spawns a helper (`subprocess.run([vercel, "ls", ...], cwd=REPO)`).
2. The process was started from a directory that has since been deleted, moved, or is
   otherwise unresolvable.
3. The OS refuses to resolve `getcwd()` for the child → Node emits
   `Error: EPERM: process.cwd failed with error operation not permitted, uv_cwd`
   and Python equivalents fail the same way.
4. Every probe that depends on that child inherits the failure → all routes record
   `status: 0` → the digest reports the whole site DOWN and publishes that to a DB.

The stack trace names the mechanism. Read it before believing the digest.

## Diagnose

Run the collector MANUALLY from its own directory and read the raw JSON:

```bash
cd <collector-dir> && python3 collect.py --pretty
# or, to isolate one signal:
python3 -c "import importlib.util, json
spec = importlib.util.spec_from_file_location('c','collect.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(json.dumps(m.signal_uptime(), indent=2))"
```

- Healthy output here = the script is fine; only its execution context is wrong.
- Compare the collector's verdict against a direct probe of the same URLs in the same turn.
  They must agree; when they don't, the direct probe wins.

## Fix

- **Pin the working directory in the invoking config** — `cwd: <repo>` on a cron/script job,
  an absolute path in the script's own `subprocess` call, or a `os.chdir(...)` guard at the
  top of the script. Do not rely on "whatever directory the runner happens to be in".
- **Make the collector fail safe, not loud.** If it cannot reach the network or resolve its
  cwd, it must NOT publish a "down" record — publishing on failure is how a broken monitor
  corrupts the live health record and produces a false outage that gets acted on.
- **Add a self-check to the digest**: compare its own route sweep against a single known-good
  control URL. If the control also fails, emit `probe_error`, not `site_down`.

## Rule

Never propagate a "down" verdict from a monitor you have not re-run yourself. Re-run it
interactively, report the manual result as the verdict, and file the monitor's defect as a
SEPARATE finding with its own root cause. A false outage alarms the founder and sends him
chasing a healthy site — worse than the monitor being quietly broken.

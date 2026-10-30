# Doctor findings and state.db maintenance

For the non-update findings `hermes doctor` reports: legacy config drift, an oversized
`state.db`, and a runaway WAL. The update half is in SKILL.md.

## Triage order

1. `hermes doctor` — read-only findings, nothing applied.
2. Fix what is safe from inside the session (config drift).
3. Report what needs a quiet store, with the exact command the user must run.

`hermes doctor --fix` only takes the paths that can grab an exclusive guard (the WAL
checkpoint). It cannot run while anything holds the store, so on a live install it changes
little — do not promise it will clear the findings.

Doctor inspects the ACTIVE profile's config only. Drift flagged in `~/.hermes/config.yaml`
usually also exists in every other profile's own `config.yaml` and is invisible to the check.
Verify each profile separately instead of assuming one fix covers the fleet.

## Editing config.yaml

The file-editing tools refuse `~/.hermes/config.yaml` outright ("security-sensitive
configuration"). Route every change through the CLI:

```bash
hermes config set providers.<slug>.api <base_url>
hermes config set providers.<slug>.name <display>
hermes config set providers.<slug>.key_env <ENV_VAR>
hermes config set providers.<slug>.default_model <model>
hermes config set providers.<slug>.models_discovered true
hermes config unset custom_providers
```

Verify with `hermes config get providers`. The CLI appends a new top-level block at the END
of the file, so grep for the key rather than reading a fixed line range.

## Legacy `custom_providers:` drift

Doctor: "Legacy custom_providers entry 'X' has no providers: twin".

The v11→v12 migration moved the list into `providers:` ONCE, at the version bump, and does
not re-fire. Any entry written after it lives in the retired list store — still dual-read by
the model picker, but no other surface edits it.

Field mapping when moving an entry:

| legacy list | `providers:` map |
|---|---|
| `base_url` | `api` |
| `model` | `default_model` |
| `name` | `name` — keep it |
| `key_env`, `models`, `models_discovered`, `context_length`, `extra_headers`, … | unchanged |

Keep the display name. A keyed `providers:` entry takes its `custom:<slug>` identity from the
config key; a legacy entry took it from the normalized display name. Setting the same `name`
keeps the slug — and therefore the model id in pickers — unchanged.

Confirm the affected profile still resolves its model afterwards:

```bash
hermes --profile <name> config get model
```

A profile configured as `model.provider: custom` with an inline `model.base_url` routes off
that inline URL, not off the list — so moving the entry changes where the picker reads it
from, never where requests go.

## Why `state.db` is large

Measure before blaming the session count:

```bash
sqlite3 "file:$HOME/.hermes/state.db?mode=ro" \
  "select name, sum(pgsize) s from dbstat group by name order by s desc limit 12"
```

The usual answer is the search index, not the messages. The FTS trigram tables
(`messages_fts_trigram_data` / `_content`) plus the base `messages_fts_*` tables routinely
dwarf the `messages` table — a 1.4 GB store can hold only ~125k messages.

Doctor's threshold is 1 GiB logical size. Also useful:

```sql
pragma page_count; pragma freelist_count; pragma page_size;
```

`freelist_count` is space VACUUM returns to the OS.

The stale-layout marker lives in the `state_meta` table: no `fts_storage_version` row while
the code's `FTS_STORAGE_VERSION` is 3. Doctor then appends "run 'hermes sessions
optimize-storage' offline" to the "state.db is large" finding.

## `hermes sessions optimize-storage` — and the holder wall

```bash
hermes sessions optimize-storage --yes
```

Rebuilds the FTS index into the compact layout and VACUUMs. Changes no conversation data —
only the search index. Resumes if interrupted. Preflights free disk at ~1x the current DB
size, because VACUUM needs a second copy.

**An agent cannot run this from inside its own session.** The command refuses while any
process holds `state.db`, and the agent's own session is one of them. The refusal names the
PID; if it is the session you are running in, stop — hand the command to the user.

Do not reach for `--force`. It rewrites the store under a live writer, which is the class of
bug that leaves every agent refusing turns with the "retired state.db-wal" error. Hand over
the sequence instead:

```bash
hermes gateway stop && hermes sessions optimize-storage --yes && hermes gateway start
```

`hermes gateway stop` unloads the launchd job. `hermes gateway start` may print "launchd job
was unloaded; reloading service definition" before reporting success — expected, not a
failure.

Other profiles' gateways are unaffected: each profile has its own `state.db` under
`profiles/<name>/`.

Inspecting holders from code, when you need the PIDs:

```python
from hermes_state_holders import foreign_state_db_holders
from hermes_state_dbfile import count_db_holders
foreign_state_db_holders(Path.home() / ".hermes/state.db")
```

## The WAL finding

Above 50 MB doctor warns and offers a `--fix` checkpoint. The checkpoint takes an exclusive
guard, so it also cannot run while a gateway or session holds the store — on a live install
the finding stays. `optimize-storage`'s own VACUUM plus a PASSIVE checkpoint (never TRUNCATE,
by design) settles it.

## Verify

```bash
hermes doctor                              # issue count should drop
hermes config get providers                # entry present
hermes --profile <name> config get model   # model resolution unchanged
```

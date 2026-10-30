---
name: macos-performance-diagnosis
description: Use when the Mac feels slow or sluggish.
---

# macOS performance / sluggishness diagnosis

"My Mac feels sluggish — why?" This is almost always **memory pressure**, not a
virus, not disk, and not the app the user is blaming. Diagnose in this order and
report the numbers with the verdict.

## 1. Measure, in one batch

```
uptime                                   # load averages (compare to cores)
sysctl -n hw.ncpu hw.model               # core count + model
memory_pressure                          # "System-wide memory free percentage"
sysctl vm.swapusage                      # swap used vs total
top -l 1 -n 0 | grep PhysMem             # used / wired / compressor / unused
df -h /System/Volumes/Data               # disk near-full also throttles
```

**The verdict rule:** near-zero free RAM + swap in use + a large compressor =
memory pressure. macOS is compressing and paging to disk, and *that* SSD thrashing
is the sluggishness the user feels. Say this plainly — it is the answer far more
often than "a runaway process".

## 2. Attribute memory to apps (RSS summed per app)

```
ps -Ao rss,command | awk '
/Google Chrome/ {c+=$1} /WebKit/ {k+=$1} /Mail\.app/ {m+=$1}
END { printf "Chrome %.0f MB\nWebKit %.0f MB\nMail %.0f MB\n", c/1024, k/1024, m/1024 }'
```

Also list the biggest single processes: `ps -Ao rss,pid,command | sort -rn | head -8`.
Electron apps and long-lived browser leaks are the usual offenders.

## 3. Count real background processes — carefully

`pgrep -fc <pattern>` can return 0 spuriously in a shell pipeline. Prefer
`ps -Ao command | grep -c '[B]lender'` — and remember the bracket trick does NOT
protect you when **your own shell command line contains the search word**: a
`grep -c '[C]oinbase'` will happily count the `bash -c` running that very command.
Exclude your own shell, or you will report phantom processes and then "fail" to
kill something that was never there.

## 3.5 Dev servers and ML workers — the MARU pattern

The user runs multiple long-lived dev servers and ML workers locally:
- `~/luna-edge/app.py` — Luna-EDGE local webapp (YOLO + torch detection engine)
- `~/CDM/scripts/surroundings_worker.mjs` — CDM surroundings builder
- `~/CDM/scripts/simulation_worker.mjs` — CDM simulation worker
- `~/CDM/node_modules/.bin/next dev` — CDM dev server

A dev server with a loaded ML model (torch, ultralytics, YOLO) will sit at
high CPU (800%+) even when idle — it is not hung, it is the model resident in
memory. Check with `ps -p <pid> -o pid,pcpu,pmem,etime,rss` — if ELAPSED is
long and RSS is stable, it is a long-running server, not a runaway loop.

**Killing dev servers**: SIGTERM first; if it survives, SIGKILL. Verify with
`ps -p <pid> -o pid` after a 1s sleep — do not assume the kill landed. Report
the CPU drop (before/after `top -l 1 -n 0 | head -3`) so the user sees the
effect. Ask before killing if the server is serving an active user workflow;
the Luna-EDGE, CDM workers, and CDM dev server are safe to kill when the user
is not actively running a build.

## 4. Background services that quietly burn CPU

- **Dictation enabled** keeps speech-recognition XPC services running and cycling
  for no reason:
  `defaults read com.apple.HIToolbox AppleDictationAutoEnable` → `1` means ON.
  Turn it off: `defaults write com.apple.HIToolbox AppleDictationAutoEnable -int 0`
  and `defaults write com.apple.assistant.support "Dictation Enabled" -bool false`.
- **Killing those XPC services does not stick** — launchd respawns them instantly
  (they returned with new PIDs at higher CPU). So if they come back *after*
  Dictation is off, something else is actively requesting the Speech framework: an
  app doing transcription (Voice Memos), a browser tab on the Web Speech API, or
  Siri. Report that as a separate client to hunt; do not keep SIGKILLing in a loop.
- Thermal throttling: `pmset -g therm` needs sudo — skip it if refused rather than
  claiming there is no throttle data.

## 5. Report and recommend, ranked by impact

1. **Reboot** is the single biggest win once uptime is long and swap is large — it
   clears accumulated swap and memory fragmentation. Lead with it.
2. Turn off Dictation / quit stray background apps.
3. Restart the browser to reclaim long-run leaks.

**Do NOT kill the user's apps without asking.** Identify, quantify, then offer.

## Pitfalls

- **Your own heavy work can BE the load spike** (geometry builds, dev servers).
  Check whether the spike you are reporting corresponds to work you just ran, and
  say so — it changes what they should do about it.
- **Your own agent runtime can be among the top CPU consumers.** Long-lived agent
  venv processes showed up at double-digit CPU with multi-day uptimes. Identify
  them before blaming the user's apps — and do not kill them, since they may be the
  session you are running in.
- A long uptime is a finding, not trivia: quote it in the report.
- Two cleanups that each free 100–400 MB will NOT fix a machine that is 15 GB into
  RAM with swap full — be honest that they help at the margin and the reboot is the
  fix. Do not present partial cleanups as the resolution.

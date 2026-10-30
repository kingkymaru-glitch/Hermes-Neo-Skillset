---
name: macos-performance-triage
description: Use when a Mac feels sluggish — find the real cause.
---

# macOS performance triage — "why is my Mac slow?"

Use when the user says the machine is sluggish, beachballing, or "feeling slow". This is a
DIAGNOSIS task: gather evidence, name the bottleneck, then give a ranked fix list. Do not guess
from one number.

## The core insight

**Sluggishness is usually MEMORY PRESSURE, and memory pressure does NOT show up as high CPU.**
When free RAM hits ~zero, macOS compresses memory and swaps to disk continuously; every app
switch and keystroke waits on the SSD. A machine can feel awful at 10% CPU. If you only look at
top-CPU you will diagnose the wrong layer.

## Procedure

Run these together (one batched call) and read them as a set.

1. **Load vs cores.**
   ```
   uptime; sysctl -n hw.ncpu hw.model
   ```
   Load average ÷ core count > ~1.0 on the 15-min figure means sustained saturation. A high
   15-min average with a low 1-min average means the heavy work has ALREADY finished — say so
   rather than blaming the present.

2. **Memory — the primary signal.**
   ```
   memory_pressure | tail -6            # 'free percentage'
   sysctl -n vm.swapusage               # total / used / free
   top -l 1 -n 0 | grep PhysMem         # used / wired / compressor
   ```
   Red flags: free RAM near 0, swap used multi-GB, compressor multi-GB. Together = the machine
   is thrashing to keep up.

3. **Who is using memory — aggregate by APP, not by process.**
   ```
   ps -Ao rss,command | awk '/<AppName>/ {s+=$1} END {printf "%6.0f MB\n", s/1024}'
   ```
   An app with 19 helper processes is invisible in `top` but obvious when summed. Then the
   biggest single processes: `ps -Ao rss,pid,command | sort -rn | head -8`.

4. **Who is using CPU.** `ps aux | sort -nrk 3 | head -12`.

5. **Long-lived strays.**
   ```
   ps -Ao pid,pcpu,pmem,etime,command
   ```
   The `etime` column is the tell: an Electron/background app that has been running for DAYS
   (idle, often in a temp `Wrapper/` dir) is pure waste. Compare each process's age against what
   it should be doing.

6. **Dictation is a silent CPU/RAM drain.**
   ```
   defaults read com.apple.HIToolbox AppleDictationAutoEnable   # 1 = ON
   ```
   When ON, `SpeechRecognitionCore` + `localspeechrecognition` XPC services run continuously
   (tens of % CPU, hundreds of MB). Turn it off and stop the services:
   ```
   defaults write com.apple.HIToolbox AppleDictationAutoEnable -int 0
   defaults write com.apple.assistant.support "Dictation Enabled" -bool false
   for p in $(ps -Ao pid,command | grep -E "[l]ocalspeechrecognition|[S]peechRecognitionCore" | awk '{print $1}'); do kill -9 "$p"; done
   ```

7. **Thermal throttling** (only if the above are clean and it is still slow):
   `pmset -g therm` needs sudo — if you cannot read it, say so rather than inventing a throttle
   verdict.

## Ranked fixes to hand back

Order by impact, not by ease:

1. **Reboot** when uptime is long (weeks) AND swap is multi-GB. This clears accumulated swap and
   fragmentation and is the single biggest win. Marginal app cleanups do NOT fix this.
2. **Turn off Dictation** if it is ON (reclaims CPU + RAM immediately).
3. **Quit stray long-lived apps** (multi-day idle Electron/background apps).
4. **Restart the browser** — long-running Chrome/WebKit leaks GB; summing per-app RSS makes this
   concrete.
5. Close unused heavyweight apps.

Report before/after numbers (free RAM, load, swap) so the effect of each cleanup is visible.

## Pitfalls

- **Do not conclude from CPU% alone.** Zero free RAM + swap > 0 explains "sluggish" even at low
  CPU. Lead with the memory picture.
- **`ps -Ao command | grep -c PATTERN` counts YOUR OWN shell.** The command line of the shell
  running your script contains PATTERN, so the count is inflated and "2 remaining" / "8
  remaining" are false positives. Verify a kill by matching a process-SPECIFIC path
  (e.g. `Coinbase.app`) and excluding your wrapper (`grep -v hermes-snap`), or keep the brackets
  in the pattern AND still exclude the wrapper. Check the PIDs, not just a count.
- **XPC services respawn instantly if their CAUSE is still present.** Killing the speech services
  succeeds, then new PIDs appear seconds later — that proves something else is still driving them
  (Voice Memos transcription, a browser tab using the Web Speech API, Siri). Fixing the setting
  stops the cause; it does not retroactively stop a service another client keeps requesting.
  Say this instead of claiming the kill worked.
- **Do not kill the user's apps or your own agent's processes without asking.** Identify and
  report; offer to quit specific ones; let the user approve. Two of the top CPU consumers may be
  your own runtime's processes — killing them is self-harm.
- **Distinguish your own footprint from the user's.** Long-running dev servers / build tools you
  spawned are yours to clean up, and saying so explicitly ("one dev server, no leftover builds")
  is honest and useful. Do not let your own heavy session be invisible when explaining a load
  spike.

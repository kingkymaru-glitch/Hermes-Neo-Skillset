#!/bin/bash
# Close monitor for a DTwin pipeline run: records stage transitions + every
# error/warning to a log until the pipeline exits. Run via terminal(background=true).
# Usage: monitor_pipeline.sh <pipeline_log> <record_log>
LOG="${1:-/tmp/pipeline_701.log}"
REC="${2:-/tmp/pipeline_701_record.log}"
echo "MONITOR START $(date '+%H:%M:%S')" > "$REC"
echo "--- stage transitions (>> markers) ---" >> "$REC"
echo "--- errors/warnings (ERROR|FAIL|WARN|NaN|Killed|Abort) ---" >> "$REC"
LAST_STAGE=""
LAST_ERRCOUNT=0
while pgrep -f "pipeline.sh" >/dev/null; do
  CUR=$(grep -E "^>>" "$LOG" 2>/dev/null | tail -1)
  if [[ -n "$CUR" && "$CUR" != "$LAST_STAGE" ]]; then
    echo "[$(date '+%H:%M:%S')] STAGE: $CUR" >> "$REC"
    LAST_STAGE="$CUR"
  fi
  ERR=$(grep -niE "error|fail|exception|traceback|killed|segfault|abort|diverg|NaN|warn" "$LOG" 2>/dev/null | grep -viE "num_reg_frames|maximum number of threads")
  EC=$(echo "$ERR" | grep -c . )
  if [[ "$EC" -gt "$LAST_ERRCOUNT" ]]; then
    echo "[$(date '+%H:%M:%S')] NEW ERROR/WARN (#$EC):" >> "$REC"
    echo "$ERR" | tail -$((EC-LAST_ERRCOUNT)) >> "$REC"
    LAST_ERRCOUNT="$EC"
  fi
  sleep 15
done
echo "MONITOR END (pipeline exited) $(date '+%H:%M:%S')" >> "$REC"
echo "--- final artifacts ---" >> "$REC"
ls -la /Users/kamarulhk/DTwin/web/assets/*/ 2>/dev/null >> "$REC"
echo "--- last 15 log lines ---" >> "$REC"
tail -15 "$LOG" >> "$REC"

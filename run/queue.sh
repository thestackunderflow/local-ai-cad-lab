#!/usr/bin/env bash
# Run a list of la runs one at a time (Task Scheduler entry point: run/queue.cmd LIST). LIST lines:
#   RUN APP TASK MODEL [NET] [K=V ...]      (# comments ok). Stops the queue on a host stop rule (one.sh exit 5).
# Needs the render lock held by the la lab (Refream-Canvas/.render-lock/owner.txt says "la lab").
cd "$(dirname "$0")/.."
LIST=${1:?list}; LOG=out/queue.log
grep -q "la lab" ../Refream-Canvas/.render-lock/owner.txt 2>/dev/null || { echo "$(date -u +%FT%TZ) no la lock: stop" >> $LOG; exit 2; }
rm -f out/queue.DONE
echo "$(date -u +%FT%TZ) queue start $LIST" >> $LOG
while read -r run app task model net rest; do
  case "$run" in ''|\#*) continue ;; esac
  [ -e "out/runs/$run/stream.jsonl" ] && { echo "$(date -u +%FT%TZ) skip $run (exists)" >> $LOG; continue; }
  echo "$(date -u +%FT%TZ) start $run" >> $LOG
  ( for kv in $rest; do export "$kv"; done; bash run/one.sh "$run" "$app" "$task" "$model" "${net:-la-net}" ) > "out/runs-$run.host.log" 2>&1
  rc=$?
  echo "$(date -u +%FT%TZ) end $run rc $rc: $(grep '^LA ' out/runs-$run.host.log | tail -1)" >> $LOG
  [ $rc = 5 ] && { echo "$(date -u +%FT%TZ) STOP rule, queue halted" >> $LOG; break; }
done < "$LIST"
echo "$(date -u +%FT%TZ) queue end" >> $LOG
date -u +%FT%TZ > out/queue.DONE

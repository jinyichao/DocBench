#!/bin/bash
# Self-healing runner: restarts run_infer on no-progress (DashScope stalls on large
# upscaled payloads) until every page in the pages-file is done.
# Usage: run_until_done.sh <run_name> <pages_file> <backend> [concurrency]
set -u
cd "$(dirname "$0")/.."
RUN="$1"; PF="$2"; BACKEND="${3:-qwen}"; CC="${4:-6}"
target=$(grep -c . "$PF")
while true; do
  n=$(find "outputs/$RUN/mds" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" -ge "$target" ] && { echo "ALL DONE: $n/$target"; break; }
  prev=$n
  python3 src/run_infer.py --split test --backend "$BACKEND" --run "$RUN" \
      --pages-file "$PF" --concurrency "$CC" >> "outputs/${RUN}.log" 2>&1 &
  pid=$!
  while kill -0 $pid 2>/dev/null; do
    sleep 75
    m=$(find "outputs/$RUN/mds" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    [ "$m" -ge "$target" ] && { kill $pid 2>/dev/null; break; }
    if [ "$m" -le "$((prev+3))" ]; then echo "stall $m -> restart"; kill $pid 2>/dev/null; sleep 3; break; fi
    prev=$m
  done
done

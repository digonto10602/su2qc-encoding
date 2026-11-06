#!/bin/bash
# samples every 10 s: time, loadavg, total CPU% of the 5 busiest processes (to detect foreign load, e.g. su2qc-worker)
out=$1
while true; do
  echo "$(date +%T) load=$(cut -d' ' -f1-3 /proc/loadavg) top=$(ps -eo pcpu,rss,comm --sort=-pcpu --no-headers | head -3 | tr -s ' ' | tr '\n' ';')" >> "$out"
  sleep 10
done

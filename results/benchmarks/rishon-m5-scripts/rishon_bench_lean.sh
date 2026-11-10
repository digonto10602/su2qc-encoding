#!/bin/bash
# Lean timings (cached lake build, from-source `lake env lean`, 3 repeats where short). Output: raw lines to $1.
# never touches lean/Su2Plaq/Structure/Counts.lean (only imports its .olean)
out=$(realpath -m $1); cd ~/Projects/su2qc-rishon/lean
source ~/.elan/env
run() { # label, command...
  label=$1; shift
  /usr/bin/time -f "%e s wall, %M KB maxrss, exit %x" -o /tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/rishonbench/lean.time taskset -c 10-19 "$@" > /tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/rishonbench/lean.out 2>&1
  echo "$label | $(cat /tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/rishonbench/lean.time | tail -1) | $(tail -2 /tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/rishonbench/lean.out | tr '\n' ' ' | cut -c1-200)" >> $out
}
for i in 1 2 3; do run "lake build Su2Plaq.Rishon.Counts (cached) rep$i" lake build Su2Plaq.Rishon.Counts; done
for i in 1 2 3; do run "lake build Su2Plaq.Rishon.JW (cached) rep$i" lake build Su2Plaq.Rishon.JW; done
run "lake build +Su2PlaqCert.Rishon.HB (cached)" lake build +Su2PlaqCert.Rishon.HB
for i in 1 2 3; do run "lake env lean Rishon/Counts.lean (from source) rep$i" lake env lean Su2Plaq/Rishon/Counts.lean; done
for i in 1 2; do run "lake env lean Rishon/JW.lean (from source) rep$i" lake env lean Su2Plaq/Rishon/JW.lean; done

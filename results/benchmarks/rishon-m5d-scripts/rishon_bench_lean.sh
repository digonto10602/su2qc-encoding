#!/bin/bash
# Lean timings (cached lake build, from-source `lake env lean`, 3 repeats where short). Output: raw lines to $1.
# never touches lean/Su2Plaq/Structure/Counts.lean (only imports its .olean)
out=$(realpath -m $1); mkdir -p /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-raw/leantmp; cd /home/digimonk/Projects/su2qc-encoding/lean
source ~/.elan/env
run() { # label, command...
  label=$1; shift
  python /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-scripts/timev.py -f "%e s wall, %M KB maxrss, exit %x" -o /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-raw/leantmp/lean.time taskset -c 14-19 /home/digimonk/Projects/su2qc-encoding/tools/run-capped "$@" > /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-raw/leantmp/lean.out 2>&1
  echo "$label | $(cat /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-raw/leantmp/lean.time | tail -1) | $(tail -2 /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-raw/leantmp/lean.out | tr '\n' ' ' | cut -c1-200)" >> $out
}
for i in 1 2 3; do run "lake build Su2Plaq.Rishon.Counts (cached) rep$i" lake build Su2Plaq.Rishon.Counts; done
for i in 1 2 3; do run "lake build Su2Plaq.Rishon.JW (cached) rep$i" lake build Su2Plaq.Rishon.JW; done
run "lake build +Su2PlaqCert.Rishon.HB (cached)" lake build +Su2PlaqCert.Rishon.HB
for i in 1 2 3; do run "lake env lean Rishon/Counts.lean (from source) rep$i" lake env lean Su2Plaq/Rishon/Counts.lean; done
for i in 1 2; do run "lake env lean Rishon/JW.lean (from source) rep$i" lake env lean Su2Plaq/Rishon/JW.lean; done

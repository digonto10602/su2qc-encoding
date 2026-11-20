#!/usr/bin/env bash
# usage: run_streams.sh <stream> <items...>   item = acceptance dir name or "unit" or "m2c"/"m11" etc
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=results/tester/445/raw
for m in "$@"; do
  if [ "$m" = unit ]; then path=tests/unit; else path=tests/acceptance/$m; fi
  s=$(date +%s)
  taskset -c 0-7 tools/pytest-safe -n 4 "$path" -p no:cacheprovider -q -rfEs --durations=5 --junitxml=$R/$m.xml > $R/$m.log 2>&1
  rc=$?
  e=$(date +%s)
  echo "$m rc=$rc wall=$((e-s))s" >> $R/summary.txt
done

#!/usr/bin/env bash
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=results/tester/445/raw
run() { name=$1; shift; s=$(date +%s); taskset -c 0-7 tools/pytest-safe "$@" -p no:cacheprovider -q -rfEs --durations=5 --junitxml=$R/$name.xml > $R/$name.log 2>&1; echo "$name rc=$? wall=$(( $(date +%s)-s ))s" >> $R/summary.txt; }
run rerun-m2 -n 4 tests/acceptance/m2
run rerun-unit-lean -n 2 tests/unit/test_lean_project_unit.py tests/unit/test_lean_round_unit.py
run rerun-m9-C1 -n 2 tests/acceptance/m9/test_fuzzy_codec_gauss.py

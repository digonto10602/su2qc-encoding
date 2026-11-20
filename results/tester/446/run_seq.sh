#!/bin/bash
# sequential: m8, m7, unit (one pytest stream)
cd /home/digimonk/Projects/su2qc-encoding
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p results/tester/446/raw2
s=$(date +%s); taskset -c 0-7 tools/pytest-safe -n 2 tests/acceptance/m8 -m "slow or not slow" -q -rfEs --durations=8 --junitxml=results/tester/446/raw2/m8.xml > results/tester/446/raw2/m8.log 2> results/tester/446/raw2/m8.time; echo "m8 $(( $(date +%s)-s )) s" >> results/tester/446/raw2/wall.txt
s=$(date +%s); taskset -c 0-7 tools/pytest-safe -n 2 tests/acceptance/m7 -q -rfEs --junitxml=results/tester/446/raw2/m7.xml > results/tester/446/raw2/m7.log 2>&1; echo "m7 $(( $(date +%s)-s )) s" >> results/tester/446/raw2/wall.txt
s=$(date +%s); taskset -c 0-7 tools/pytest-safe -n 2 tests/unit -k "lsh or m8" -q -rfEs --junitxml=results/tester/446/raw2/unit.xml > results/tester/446/raw2/unit.log 2>&1; echo "unit $(( $(date +%s)-s )) s" >> results/tester/446/raw2/wall.txt
echo done >> results/tester/446/raw2/wall.txt

#!/bin/bash
cd /home/digimonk/Projects/su2qc-encoding
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
M=results/tester/448/mem
m(){ n=$1; shift; taskset -c 0-6 python results/tester/448/memwall.py tools/pytest-safe -n 0 "$@" -q -m "slow or not slow" > $M/$n.log 2>&1; echo "$n $(tail -1 $M/$n.log)" >> $M/summary.txt; }
m m3_all tests/acceptance/m3
m m9_S1_step_orders "tests/acceptance/m9/test_fuzzy_circuits.py" -k test_M9_S1_step_orders
m m1_all tests/acceptance/m1
m m2_all tests/acceptance/m2
m m9_C1 tests/acceptance/m9/test_fuzzy_codec_gauss.py -k test_M9_C1
echo done >> $M/summary.txt

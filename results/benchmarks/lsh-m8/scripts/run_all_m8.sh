#!/bin/bash
# LSH M8 benchmark chain (tester, reports/benchmarks/306): one timed job at a time, phases in order.
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104 PYTHONPATH=src
cd /home/digimonk/Projects/su2qc-encoding
S=${BENCH_RUN:-scratch/bench-m8/run1}; mkdir -p $S
for ph in "$@"; do
  echo "=== $ph $(date +%T) load $(cat /proc/loadavg)"
  python results/benchmarks/lsh-m8/scripts/bench_driver_m8.py $ph $S > $S/log_$ph.txt 2>&1
  echo "rc $? $(date +%T) load $(cat /proc/loadavg)"
done
echo ALLDONE

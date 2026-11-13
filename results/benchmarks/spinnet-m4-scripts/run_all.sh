#!/bin/bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104
cd /home/digimonk/Projects/su2qc-encoding
S=scratch/bench-m4m7
for ph in tasksA tasksB round scripts suites_m4 suites_m7 suites_unit; do
  echo "=== $ph $(date +%T) load $(cat /proc/loadavg)"
  python results/benchmarks/spinnet-m4-scripts/bench_driver_m4.py $ph $S > $S/log_$ph.txt 2>&1
  echo "rc $? $(date +%T)"
done
echo ALLDONE

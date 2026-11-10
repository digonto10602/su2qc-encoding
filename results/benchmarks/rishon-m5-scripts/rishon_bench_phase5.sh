#!/bin/bash
# phase 5: T1[step] alone on one P-core thread (cpu 12) and, concurrently on a different physical core, on one E-core (cpu 18)
cd ~/Projects/su2qc-rishon
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104
R=results/benchmarks/rishon-m5-raw
for c in 12 18; do
  ( /usr/bin/time -v -o $R/pytest_m5_T1step_cpu$c.time taskset -c $c pytest -k "T1 and step" tests/acceptance/m5 --junitxml=$R/pytest_m5_T1step_cpu$c.xml -q --durations=0 > $R/pytest_m5_T1step_cpu$c.log 2>&1 ) &
done
wait
touch $R/phase5.done

#!/bin/bash
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
cd /home/digimonk/Projects/su2qc-encoding/results/tester/433
export PYTHONPATH=/home/digimonk/Projects/su2qc-encoding/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
date +%s > 433-aer-all.begin
for cid in r06-F3-006 r06-F1-006; do
  taskset -c 0-3 python 433-aer-run.py $cid 0.37 0.61 16 24 4 433-aer-$cid-nominal.npz > 433-aer-$cid-nominal.log 2>&1
  taskset -c 0-3 python 433-aer-run.py $cid 0.91 0.23 16 24 4 433-aer-$cid-alt1.npz 80 > 433-aer-$cid-alt1.log 2>&1
  taskset -c 0-3 python 433-aer-run.py $cid 1.7 1.0 16 24 4 433-aer-$cid-alt2.npz 80 > 433-aer-$cid-alt2.log 2>&1
done
date +%s > 433-aer-all.end; echo ALLDONE > 433-aer-all.done

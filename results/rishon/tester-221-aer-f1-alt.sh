#!/bin/bash
# Tester 221: Aer alternate pairs for r04-F1-004 (separate script after the crash restart), 2 workers on cores 12-13
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=results/rishon; cid=r04-F1-004
nice -n 10 taskset -c 12,13 python $R/tester-221-aer-run.py $cid 0.91 0.23 16 22 2 $R/tester-221-aer-$cid-alt1.npz 80 > $R/tester-221-aer-$cid-alt1.log 2>&1
nice -n 10 taskset -c 12,13 python $R/tester-221-aer-run.py $cid 1.7 1.0 16 22 2 $R/tester-221-aer-$cid-alt2.npz 80 > $R/tester-221-aer-$cid-alt2.log 2>&1
echo done > $R/tester-221-aer-f1-alt.done

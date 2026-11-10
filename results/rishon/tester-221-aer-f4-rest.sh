#!/bin/bash
# Tester 221: Aer alternate pairs + 25-qubit class for r04-F4-004 (the first aer-all.sh was cut after its nominal loop), cores 6-9 (nice)
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=results/rishon; cid=r04-F4-004
nice -n 10 taskset -c 6-9 python $R/tester-221-aer-run.py $cid 0.91 0.23 16 22 4 $R/tester-221-aer-$cid-alt1.npz 80 > $R/tester-221-aer-$cid-alt1.log 2>&1
nice -n 10 taskset -c 6-9 python $R/tester-221-aer-run.py $cid 1.7 1.0 16 22 4 $R/tester-221-aer-$cid-alt2.npz 80 > $R/tester-221-aer-$cid-alt2.log 2>&1
nice -n 10 taskset -c 6-9 python $R/tester-221-aer-run.py $cid 0.37 0.61 25 26 2 $R/tester-221-aer-$cid-big.npz 8 > $R/tester-221-aer-$cid-big.log 2>&1
echo done > $R/tester-221-aer-f4-rest.done

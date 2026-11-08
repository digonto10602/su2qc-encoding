#!/bin/bash
# Tester 220: Aer runs, 4 workers on cores 10-13 (nice). F3 nominal was run first with 1 worker (all 1296 codes).
cd ~/Projects/su2qc-rishon
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=/home/digonto/anaconda3/envs/su2qc-coding/bin/python
R=results/rishon
for cid in r03-F1-003 r03-F4-003; do
  /usr/bin/time -v nice -n 10 taskset -c 10-13 $PY $R/tester-220-aer-run.py $cid 0.37 0.61 16 24 4 $R/tester-220-aer-$cid-nominal.npz > $R/tester-220-aer-$cid-nominal.log 2> $R/tester-220-aer-$cid-nominal.time
done
for cid in r03-F3-002 r03-F1-003 r03-F4-003; do
  nice -n 10 taskset -c 10-13 $PY $R/tester-220-aer-run.py $cid 0.91 0.23 16 22 4 $R/tester-220-aer-$cid-alt1.npz 80 > $R/tester-220-aer-$cid-alt1.log 2>&1
  nice -n 10 taskset -c 10-13 $PY $R/tester-220-aer-run.py $cid 1.7 1.0 16 22 4 $R/tester-220-aer-$cid-alt2.npz 80 > $R/tester-220-aer-$cid-alt2.log 2>&1
done
nice -n 10 taskset -c 10-13 $PY $R/tester-220-aer-run.py r03-F4-003 0.37 0.61 25 26 2 $R/tester-220-aer-r03-F4-003-big.npz 8 > $R/tester-220-aer-r03-F4-003-big.log 2>&1
echo ALLDONE > $R/tester-220-aer-all.done

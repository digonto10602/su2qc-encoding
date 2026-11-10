#!/bin/bash
# Tester 218: Aer runs, 4 workers on cores 10-13 (nice).  nominal pair: all codes with nq<=24; alt pairs: 80 sampled codes with nq<=22; 25-26 qubit class: 8 sampled codes (2 workers)
cd ~/Projects/su2qc-rishon
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=/home/digonto/anaconda3/envs/su2qc-coding/bin/python
R=results/rishon
for cid in r01-F5-001 r01-F1-001 r01-F2-001 r01-F4-001; do
  nice -n 10 taskset -c 10-13 $PY $R/tester-218-aer-run.py $cid 0.37 0.61 16 24 4 $R/tester-218-aer-$cid-nominal.npz > $R/tester-218-aer-$cid-nominal.log 2>&1
done
for cid in r01-F5-001 r01-F1-001 r01-F2-001 r01-F4-001; do
  nice -n 10 taskset -c 10-13 $PY $R/tester-218-aer-run.py $cid 0.91 0.23 16 22 4 $R/tester-218-aer-$cid-alt1.npz 80 > $R/tester-218-aer-$cid-alt1.log 2>&1
  nice -n 10 taskset -c 10-13 $PY $R/tester-218-aer-run.py $cid 1.7 1.0 16 22 4 $R/tester-218-aer-$cid-alt2.npz 80 > $R/tester-218-aer-$cid-alt2.log 2>&1
done
for cid in r01-F1-001 r01-F2-001 r01-F4-001; do
  nice -n 10 taskset -c 10-13 $PY $R/tester-218-aer-run.py $cid 0.37 0.61 25 26 2 $R/tester-218-aer-$cid-big.npz 8 > $R/tester-218-aer-$cid-big.log 2>&1
done
echo ALLDONE > $R/tester-218-aer-all.done

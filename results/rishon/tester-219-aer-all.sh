#!/bin/bash
# Tester 219: Aer runs, 4 workers on cores 10-13 (nice).  nominal pair: all codes with nq<=24 (F2 identical to F1: 160-code sample); alt pairs: 80 sampled codes nq<=22; F4 25-26 qubit class: 8 codes
cd ~/Projects/su2qc-rishon
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=/home/digonto/anaconda3/envs/su2qc-coding/bin/python
R=results/rishon
for cid in r02-F3-001 r02-F1-002 r02-F4-002; do
  /usr/bin/time -v nice -n 10 taskset -c 10-13 $PY $R/tester-219-aer-run.py $cid 0.37 0.61 16 24 4 $R/tester-219-aer-$cid-nominal.npz > $R/tester-219-aer-$cid-nominal.log 2> $R/tester-219-aer-$cid-nominal.time
done
nice -n 10 taskset -c 10-13 $PY $R/tester-219-aer-run.py r02-F2-002 0.37 0.61 16 24 4 $R/tester-219-aer-r02-F2-002-nominal.npz 160 > $R/tester-219-aer-r02-F2-002-nominal.log 2>&1
for cid in r02-F3-001 r02-F1-002 r02-F2-002 r02-F4-002; do
  nice -n 10 taskset -c 10-13 $PY $R/tester-219-aer-run.py $cid 0.91 0.23 16 22 4 $R/tester-219-aer-$cid-alt1.npz 80 > $R/tester-219-aer-$cid-alt1.log 2>&1
  nice -n 10 taskset -c 10-13 $PY $R/tester-219-aer-run.py $cid 1.7 1.0 16 22 4 $R/tester-219-aer-$cid-alt2.npz 80 > $R/tester-219-aer-$cid-alt2.log 2>&1
done
nice -n 10 taskset -c 10-13 $PY $R/tester-219-aer-run.py r02-F4-002 0.37 0.61 25 26 2 $R/tester-219-aer-r02-F4-002-big.npz 8 > $R/tester-219-aer-r02-F4-002-big.log 2>&1
echo ALLDONE > $R/tester-219-aer-all.done

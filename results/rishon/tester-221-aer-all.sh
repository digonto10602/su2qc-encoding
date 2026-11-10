#!/bin/bash
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
# (restart after the 13:49 crash: F1-004 nominal kept from the first run)
date +%s > results/rishon/tester-221-aer-all.begin
# Tester 221: Aer runs, 4 workers on cores 6-9 (nice); F3-003 is gate-for-gate identical to F1-004 (tester-221-samecircuit), so only F1-004 and F4-004 are run.
cd /home/digimonk/Projects/su2qc-encoding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
PY=python
R=results/rishon
for cid in r04-F4-004; do date +%s > $R/tester-221-aer-$cid.start
  nice -n 10 taskset -c 6-9 $PY $R/tester-221-aer-run.py $cid 0.37 0.61 16 24 4 $R/tester-221-aer-$cid-nominal.npz > $R/tester-221-aer-$cid-nominal.log 2> $R/tester-221-aer-$cid-nominal.time
done
for cid in r04-F4-004; do date +%s > $R/tester-221-aer-$cid.start
  nice -n 10 taskset -c 6-9 $PY $R/tester-221-aer-run.py $cid 0.91 0.23 16 22 4 $R/tester-221-aer-$cid-alt1.npz 80 > $R/tester-221-aer-$cid-alt1.log 2>&1
  nice -n 10 taskset -c 6-9 $PY $R/tester-221-aer-run.py $cid 1.7 1.0 16 22 4 $R/tester-221-aer-$cid-alt2.npz 80 > $R/tester-221-aer-$cid-alt2.log 2>&1
done
nice -n 10 taskset -c 6-9 $PY $R/tester-221-aer-run.py r04-F4-004 0.37 0.61 25 26 2 $R/tester-221-aer-r04-F4-004-big.npz 8 > $R/tester-221-aer-r04-F4-004-big.log 2>&1
date +%s > $R/tester-221-aer-all.end; echo ALLDONE > $R/tester-221-aer-all.done

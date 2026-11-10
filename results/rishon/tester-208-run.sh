#!/bin/bash
cd ~/Projects/su2qc-rishon
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source ~/.elan/env 2>/dev/null
for t in unit m0 m1 m5; do
  p=tests/acceptance/$t; [ $t = unit ] && p=tests/unit
  /usr/bin/time -v -o results/rishon/tester-208-$t.time taskset -c 10-19 pytest -n 10 $p --junitxml=results/rishon/tester-208-$t.xml -q -rA > results/rishon/tester-208-$t.log 2>&1
done
~/.claude/bin/acceptance-check > results/rishon/tester-208-acceptance-check.log 2>&1; echo "exit $?" >> results/rishon/tester-208-acceptance-check.log
python tools/check_lock.py > results/rishon/tester-208-check-lock.log 2>&1
touch results/rishon/tester-208-all.done

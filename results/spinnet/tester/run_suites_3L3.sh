#!/bin/bash
cd ~/Projects/su2qc-spinnet
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
O=results/spinnet/tester/3L3
mkdir -p $O
for s in m3 m3x; do
  /usr/bin/time -v taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q -rfEs --durations=5 tests/acceptance/$s > $O/acc_$s.txt 2>&1
done
/usr/bin/time -v taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q -rfEs --durations=8 tests/unit > $O/unit.txt 2>&1
python tools/check_lock.py > $O/check_lock.txt 2>&1; echo "exit $?" >> $O/check_lock.txt
~/.claude/bin/acceptance-check > $O/acceptance_check.txt 2>&1; echo "exit $?" >> $O/acceptance_check.txt
echo done > $O/DONE

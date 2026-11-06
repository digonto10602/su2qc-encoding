#!/bin/bash
cd ~/Projects/su2qc-spinnet
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
O=results/spinnet/tester/3L3
for s in m0 m1 m2; do
  /usr/bin/time -v taskset -c 0-9 pytest -n 10 -p no:cacheprovider -q -rfEs tests/acceptance/$s > $O/acc_$s.txt 2>&1
done
echo done > $O/DONE_reg

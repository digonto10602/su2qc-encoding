#!/bin/bash
# benchmark 307: breakdown + LSH evaluator regression guard.  Worktree = $1, out dir = $2
WT=$1; OUT=$2; S=/home/digimonk/Projects/su2qc-encoding/results/benchmarks/m11/scripts
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export BENCH_ROOT=$WT PYTHONPATH=$WT/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104 BENCH_SCR=$OUT
cd $WT
for i in 1 2 3; do echo "load $(cut -d' ' -f1-3 /proc/loadavg)"; taskset -c 2 python $S/w_cross.py $OUT/cross_$i.json | grep RESULT | cut -c8- > $OUT/cross_$i.json; done
for prog in compress/programs/lsh/F3/005-alpha-early-walk22.py compress/programs/lsh/seed/005-wrap_sn_headline.py compress/programs/lsh/seed/000-general.py; do
  n=$(basename $prog .py)
  for i in 1 2 3 4 5; do echo "load $(cut -d' ' -f1-3 /proc/loadavg) eval $n $i"; taskset -c 2 python $S/w_eval.py eval $prog 5 | grep RESULT | cut -c8- > $OUT/eval_${n}_$i.json; done
done
for i in 1 2 3 4 5; do taskset -c 2 python $S/w_eval.py robust compress/programs/lsh/F3/005-alpha-early-walk22.py 5 | grep RESULT | cut -c8- > $OUT/robust_$i.json; done
taskset -c 2 python $S/w_eval.py eval compress/programs/lsh/F3/005-alpha-early-walk22.py 5 cold | grep RESULT | cut -c8- > $OUT/eval_cold_1.json
echo DONE

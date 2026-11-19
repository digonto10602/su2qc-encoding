#!/bin/bash
# usage: runmut.sh <mutdir> <core>; control first, then every mutant, production evaluator --full
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
export PYTHONPATH=/home/digimonk/Projects/su2qc-encoding/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd /home/digimonk/Projects/su2qc-encoding
D=$1; core=$2
for f in compress/programs/rishon/F3/006-closed-mark-in-restore.py $D/N*.py; do
  n=$(basename $f .py); echo "=== $n"; taskset -c $core python -m su2plaq.rishon.compress.run_candidate $f --full --json $D/$n.json 2>&1 | grep -E "^(valid|invalid)|op_norm_error|metrics:" | cut -c1-200
done
echo ALLDONE

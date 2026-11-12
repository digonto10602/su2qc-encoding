#!/usr/bin/env bash
# usage: run_one.sh <mutant> <core> <pytest args...>
M=$1; CORE=$2; shift 2
SP=/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad
source /home/digimonk/miniforge3/etc/profile.d/conda.sh; conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MUT223=$M PYTHONPATH=src:$SP/mut
PYTEST_MEM_MAX=4G taskset -c $CORE tools/pytest-safe -p mut223 -q -rf -p no:cacheprovider "$@" > $SP/mut/$M.log 2>&1
echo "$M rc=$?" >> $SP/mut/summary.txt

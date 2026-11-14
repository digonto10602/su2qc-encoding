#!/bin/bash
# phase 4: JW 3rd rep, then T1 tests standalone (-n 3, one worker per kind), then touch done
cd ~/Projects/su2qc-rishon
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104
source ~/.elan/env
R=results/benchmarks/rishon-m5-raw
SC=/tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/rishonbench
( cd lean && /usr/bin/time -f "%e s wall, %M KB maxrss, exit %x" -o $SC/jw3.time taskset -c 10-19 lake env lean Su2Plaq/Rishon/JW.lean > $SC/jw3.out 2>&1; echo "lake env lean Rishon/JW.lean (from source) rep3 | $(tail -1 $SC/jw3.time) |" >> ../$R/lean.txt )
/usr/bin/time -v -o $R/pytest_m5_T1_n3.time taskset -c 10-19 pytest -n 3 -k "T1" tests/acceptance/m5 --junitxml=$R/pytest_m5_T1_n3.xml -q --durations=0 > $R/pytest_m5_T1_n3.log 2>&1
touch $R/phase4.done

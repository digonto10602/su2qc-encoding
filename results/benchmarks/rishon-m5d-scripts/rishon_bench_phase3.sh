#!/bin/bash
# phase 3: pytest (m5 non-slow incl. T1 x1; m5 not-slow-not-T1 x3; slow L3 x1), then Lean + L3 certificate timings.  Sequential, nothing else running.
cd ~/Projects/su2qc-rishon
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104
source ~/.elan/env
R=results/benchmarks/rishon-m5-raw
S=results/benchmarks/rishon-m5-scripts
# summed RSS sampler of all python processes
( while true; do echo "$(date +%T) $(ps -eo rss,comm | awk '/python|pytest/{s+=$1} END{print s/1024}') MB" >> $R/pytest-rss.log; sleep 5; done ) &
SAMP=$!
/usr/bin/time -v -o $R/pytest_m5_notslow.time taskset -c 10-19 pytest -n 10 -m "not slow" tests/acceptance/m5 --junitxml=$R/pytest_m5_notslow.xml -q --durations=0 > $R/pytest_m5_notslow.log 2>&1
for i in 1 2 3; do
  /usr/bin/time -v -o $R/pytest_m5_notT1_$i.time taskset -c 10-19 pytest -n 10 -m "not slow" -k "not T1" tests/acceptance/m5 --junitxml=$R/pytest_m5_notT1_$i.xml -q > $R/pytest_m5_notT1_$i.log 2>&1
done
/usr/bin/time -v -o $R/pytest_m5_L3.time taskset -c 10-19 pytest -m slow tests/acceptance/m5 --junitxml=$R/pytest_m5_L3.xml -q --durations=0 > $R/pytest_m5_L3.log 2>&1
kill $SAMP
bash $S/rishon_bench_lean.sh $R/lean.txt
/usr/bin/time -v -o $R/l3.time taskset -c 10-19 python $S/rishon_bench_l3.py /tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/l3 > $R/l3.out 2>&1
touch $R/phase3.done

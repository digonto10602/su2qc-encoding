#!/bin/bash
# phase 2: pytest m5 (not slow x1; not slow, not T1 x3; slow x1), Lean timings, L3 certificate timings. Sequential, cores 14-19.
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src PYTHONHASHSEED=20261104
export PATH="$HOME/.elan/bin:$PATH"
D=results/benchmarks/rishon-m5d-scripts; R=results/benchmarks/rishon-m5d-raw
bash $D/rishon_monitor.sh $R/monitor2.log & MON=$!
( while true; do echo "$(date +%T) $(ps -eo rss,comm | awk '/python|pytest/{s+=$1} END{print s/1024}') MB" >> $R/pytest-rss.log; sleep 5; done ) & SAMP=$!
python /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-scripts/timev.py -v -o $R/pytest_m5_notslow.time taskset -c 14-19 tools/pytest-safe -n 6 -m "not slow" tests/acceptance/m5 --junitxml=$R/pytest_m5_notslow.xml -q --durations=0 > $R/pytest_m5_notslow.log 2>&1
for i in 1 2 3; do
  python /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-scripts/timev.py -v -o $R/pytest_m5_notT1_$i.time taskset -c 14-19 tools/pytest-safe -n 6 -m "not slow" -k "not T1" tests/acceptance/m5 --junitxml=$R/pytest_m5_notT1_$i.xml -q > $R/pytest_m5_notT1_$i.log 2>&1
done
python /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-scripts/timev.py -v -o $R/pytest_m5_slow.time taskset -c 14-19 tools/pytest-safe -n 2 -m slow tests/acceptance/m5 --junitxml=$R/pytest_m5_slow.xml -q --durations=0 > $R/pytest_m5_slow.log 2>&1
kill $SAMP
bash $D/rishon_bench_lean.sh $R/lean.txt
python /home/digimonk/Projects/su2qc-encoding/results/benchmarks/rishon-m5d-scripts/timev.py -v -o $R/l3.time taskset -c 14 tools/run-capped python $D/rishon_bench_l3.py $R/l3tmp > $R/l3.out 2>&1
kill $MON
touch $R/phase2.done

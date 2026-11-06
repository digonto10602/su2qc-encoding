#!/bin/bash
cd ~/Projects/su2qc-rishon
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
source ~/.elan/env 2>/dev/null
R=results/rishon/tester-212
( while [ ! -f $R-all.done ]; do echo "$(date +%s) $(ps -eo rss,comm | awk '/python|lean|lake/{s+=$1} END{print s/1048576}')" >> $R-rss.log; sleep 5; done ) &
run() { name=$1; shift; /usr/bin/time -v -o $R-$name.time taskset -c 10-19 "$@" --junitxml=$R-$name.xml -q -rA > $R-$name.log 2>&1; echo "$name exit $?" >> $R-exits.log; }
run m0 pytest -n 10 tests/acceptance/m0
run m1 pytest -n 10 tests/acceptance/m1
run m5x pytest -n 1 tests/acceptance/m5x
run m5 pytest -n 10 tests/acceptance/m5
run unit pytest -n 10 tests/unit
run m2 pytest -n 10 tests/acceptance/m2
~/.claude/bin/acceptance-check > $R-acceptance-check.log 2>&1; echo "exit $?" >> $R-acceptance-check.log
python tools/check_lock.py > $R-check-lock.log 2>&1; echo "exit $?" >> $R-check-lock.log
touch $R-pytest.done

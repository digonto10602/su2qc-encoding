#!/bin/bash
# sequential acceptance, milestone by milestone, one pytest stream, cores 0-6, -n 3
cd /home/digimonk/Projects/su2qc-encoding
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
R=results/tester/448/raw; mkdir -p $R
for m in m0 m1 m2 m2c m3 m3x m4 m5 m5x m6 m7 m8 m9 m10 m11; do
  taskset -c 0-6 python results/tester/448/memwall.py tools/pytest-safe -n 3 tests/acceptance/$m -m "slow or not slow" -q -rfEs --durations=5 --junitxml=$R/$m.xml > $R/$m.log 2> $R/$m.mem
  echo "$m rc=$? $(cat $R/$m.mem | tail -1)" >> $R/wall.txt
done
echo done >> $R/wall.txt

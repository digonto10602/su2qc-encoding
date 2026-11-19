#!/bin/bash
source ~/miniforge3/etc/profile.d/conda.sh; conda activate coding
export PYTHONPATH=/home/digimonk/Projects/su2qc-encoding/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd /home/digimonk/Projects/su2qc-encoding
# unmutated control first
for f in /home/digimonk/Projects/su2qc-encoding/compress/programs/rishon/F3/005-loop-skips-c0-c2h.py /tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/mut/M*.py; do
  n=$(basename $f .py); echo "=== $n"; taskset -c 7 python -m su2plaq.rishon.compress.run_candidate $f --full --json /tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/mut/$n.json 2>&1 | tail -n 8
done
echo ALLDONE

#!/bin/bash
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104 BENCH_CPU=4
python results/benchmarks/c5-scripts/rss_wrap.py
touch results/benchmarks/c5-raw/done_rss

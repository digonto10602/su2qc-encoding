#!/bin/bash
# control A/B: same worker script, old tree (86fda8e = report 200 commit, detached worktree) vs HEAD, interleaved, cpu 14.
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH= PYTHONHASHSEED=20261104
D=results/benchmarks/rishon-m5d-scripts; R=results/benchmarks/rishon-m5d-raw/ctl
export BENCH_CPU=14
OLD=/home/digimonk/Projects/su2qc-ctl-86fda8e; NEW=/home/digimonk/Projects/su2qc-encoding
for task in inner build ttable_UB ttable_step verify_UB verify_step basis; do
  for rep in 1 2 3; do
    for arm in old new; do
      root=$OLD; [ $arm = new ] && root=$NEW
      BENCH_ROOT=$root python $D/ctl_bench_driver.py $R/$arm.jsonl $task:1 > /dev/null
    done
  done
done
for arm in old new; do root=$OLD; [ $arm = new ] && root=$NEW; BENCH_ROOT=$root python $D/ctl_bench_driver.py $R/$arm.jsonl synth_UB_1e-6:1 > /dev/null; done
RISHON_WORKER=ctl_bench_twelve_worker.py; for rep in 1 2 3; do for arm in old new; do root=$OLD; [ $arm = new ] && root=$NEW; BENCH_ROOT=$root RISHON_WORKER=ctl_bench_twelve_worker.py python $D/ctl_bench_driver.py $R/${arm}_twelve.jsonl eval_UB:1 > /dev/null; done; done
touch $R/ctl.done

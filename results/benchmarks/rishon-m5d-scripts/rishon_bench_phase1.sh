#!/bin/bash
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src PYTHONHASHSEED=20261104
D=results/benchmarks/rishon-m5d-scripts; R=results/benchmarks/rishon-m5d-raw
export BENCH_CPU=14
bash $D/rishon_monitor.sh $R/monitor.log & MON=$!
python $D/rishon_bench_driver.py $R/rishon.jsonl import:3 basis:3 inner:3 build:3 ttable_UE:3 ttable_UB:3 ttable_step:3 ttable_step2:3 ttable_UE_outer_row:3 verify_UE:3 verify_UB:3 verify_step:3 verify_step2:3 synth_UE_1e-6:3 synth_UB_1e-6:1 build_det:3 ttable_UD:3 ttable_step3:3 verifydet_UD:3 verifydet_step3:3 verifydet_step3_order2:3 synthdet_UD_1e-6:3 threelayer:3
RISHON_WORKER=rishon_bench_twelve_worker.py python $D/rishon_bench_driver.py $R/twelve.jsonl m1_build:3 eval_UE:3 eval_UB:3 eval_step1:3 ttable_UE:3 ttable_UB:3 ttable_step1:3 synth_UB:3 paulo_m1:1
kill $MON
touch $R/phase1.done

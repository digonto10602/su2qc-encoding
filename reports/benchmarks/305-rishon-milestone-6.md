# Benchmark report 305 - rishon milestone 6 gate, mode benchmark (gate step 3)

- Date: 2026-11-19. Tester: Sonnet 5.5. Commit at the end of the session: `95a1223` (HEAD; `git diff aaa802e HEAD -- src lean compress/programs tests` is empty, so the code measured is the code of `aaa802e`). Two clean `git archive` snapshots were timed, not the working tree: `c5f31e4` = the code the gate tester (reports/tests/435) and auditor (reports/audits/307) judged, and `aaa802e` = HEAD after audit-307 notes N1-N3 (`lean_cert.py` cross-check, regenerated theorem files). Differences between the two are listed in section 3.
- Prompt in force: `prompts/205` on `204` on `203` (row 6.8: "trial/full evaluation time of the general program and of the best, round-0 wall, certificate time"). Gate: tester full PASS `reports/tests/435`, audit PASS WITH NOTES `reports/audits/307`. `python tools/check_lock.py`: LOCK OK; `~/.claude/bin/acceptance-check`: PASS (acceptance-v22), both run at the end.
- Baselines: `reports/benchmarks/200-m5-rishon.md` (old install), `303-rishon-milestone-5d.md` (omnicommander CPU 14, load about 2), `304-milestone-2c-consolidation.md` (A/B method, CPU 4, load at most 2.56, HEAD `ca68875`). Recorded round walls: `results/compress/rishon/pre-204/round-000.json` (1317.1 s) and `results/compress/rishon/round-000.json` (replay under 204, 1633.5 s).
- Raw numbers: `results/benchmarks/rishon-m6.json` (all summaries, round-0 timeline, metadata), `results/tester/benchmark-305-summary*.json` (per-batch medians and per-run values), per-process records `results/benchmarks/rishon-m6-raw/*.jsonl` and logs; scripts `results/benchmarks/rishon-m6-scripts/` (`driver.py`, `cert_worker.py`, `make_jobs*.py`, `analyze.py`, job lists).
- Related: `reports/tests/434` (Lean checker, builder/tester certificate seconds), `reports/tests/427` (replay and the L3 seed), `reports/benchmarks/304`.

## Verdict

**PASS. No code regression; physics output reproduced to every printed digit; every delta above 10 % is explained.** The rishon evaluator files are byte-identical to the ones of report 304 (`git diff ca68875 HEAD` over the 31 `RISHON_EVALUATOR_FILES` is empty; evaluator hash `5f5decfa...` unchanged), so the span-leak block (which rishon skips through the full-space shortcut; 304: ratio 0.99-1.01) and the 10 % prune-cap re-judge (303: 0.96-1.00) cannot have changed any evaluation time. Three things need the coordinator's attention:

1. **The machine was loaded the whole time** (1-minute load average 4-39, median 14-24; other agents on CPUs 7-17). Absolute times of unchanged code are 29-36 % above report 304 (control, section 1). Pinned CPUs were 94-100 % mine, SMT sibling mostly idle, but the load rule ("repeat if > 9") could not be met; I repeated the whole batch once (batch B, other core) and it agrees (section 0).
2. **Round 0 (fresh run on a temp root): 1789.2 s, +9.5 % over the recorded replay (1633.5 s)**, i.e. 0.5 percentage points under the 10 % threshold, and +36 % over pre-204 (1317 s). Both are explained (section 2), but the 9.5 % is mostly the loaded machine, not code.
3. **Lean certificate: the new HEAD (`aaa802e`) is 17-22 % slower than the gate snapshot** (general step 41.0 s vs 35.2 s, headline 31.5 s vs 25.8 s, 1 CPU) because audit-307 N1 made the exact-target cross-check evaluate five angle pairs instead of one (+5-6 s per certificate in `exact_target`). The Lean checker itself is unchanged (sha256 `6c3c62be...`, 29.5 s / 16.9 s).

## 0. Machine, protocol, load

- `omnicommander`, i7-12700KF, 20 threads, 31 GiB, no GPU; python 3.12.16, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0; `OMP/OPENBLAS/MKL_NUM_THREADS=1`; `PYTHONHASHSEED=20261104`; Gauss-sample seed 20261104, `ct_compile` seed 12345 (library defaults; no stochastic quantity is timed). CPU governor `powersave` with EPP `performance`, all cores at 4.70 GHz when sampled.
- Pinning: single-core python jobs on CPU 0 (batch A) and CPU 2 (batch B, HEAD certificates); Lean theorem files and the 4-CPU certificate runs on CPUs 0-3 (batch B Lean jobs on CPUs 2-3 = one physical core, so they are 2x slower and not used for comparison). Another tester and a proposer worked on CPUs 4-8; chrome ran on CPUs 2/5 for stretches. Each job: `taskset -c <cpus> ... ` inside `tools/run-capped` (shared memory-capped slice, 11 GB per job); `driver.py` records wall (`perf_counter`), child user+system CPU, peak RSS (`wait4`), the 1-minute load average before and after, and the busy fraction of every pinned CPU and of its SMT sibling from `/proc/stat`.
- Protocol: one fresh process per run. Batch A: 4 repetitions per job, repetition 0 is a warm-up (first use of the freshly unpacked tree: cold file cache) and is excluded; medians [min, max] over repetitions 1-3. Batch B: 3 repetitions, no warm-up. Batches interleave jobs in rotating order. `uptime` before/after and at each phase start: `results/benchmarks/rishon-m6-raw/uptime.log`.
- Load actually seen (1-minute average at the start of each run): batch A 7.5-39.2 (median 24.0), batch B 3.7-23.2 (median 14.2), HEAD certificates 4.3-20.1 (17.2), Lean/4-CPU runs 12-28. The pinned CPU was 94-100 % busy with my own process in every run; foreign load on the SMT sibling was at most 0.48 (batch A), 0.40 (batch B), 0.04 (HEAD certificates). CPU time equals wall time within 1 %. So the machine was shared at the level of L3 cache, memory bandwidth and power budget, not at the level of my core.
- Commands (all with `source .../conda.sh && conda activate coding; export PYTHONPATH=<snapshot>/src ...`):
```
python results/benchmarks/rishon-m6-scripts/make_jobs.py 3 jobs.json          # batch A (CPU 0), snapshot scratch/bench305/head = c5f31e4
TAG=B CPU=2 CPUL=2-3 python results/benchmarks/rishon-m6-scripts/make_jobs_b.py 3 jobs_b.json   # batch B (CPU 2), same snapshot, rep 0 dropped
tools/run-capped python results/benchmarks/rishon-m6-scripts/driver.py jobs.json results/benchmarks/rishon-m6-raw/jobs.jsonl
# per job (cwd = snapshot):
python -m su2plaq.rishon.compress.run_candidate compress/programs/rishon/seed/000-general.py --kind step --trial|--full
python -m su2plaq.rishon.compress.run_candidate compress/programs/rishon/F3/006-closed-mark-in-restore.py --kind step --trial|--full
python -m su2plaq.rishon.compress.run_candidate compress/programs/rishon/F1/004-pz-selector-walsh6.py --kind step --full   # control of report 304
python -m su2plaq.rishon.compress.three_layer --out <tmp>.json [--entry r04-F1-004]
python cert_worker.py general|headline|det <snapshot> <outdir>     # rishon.lean_cert.certify_circuit / round._certify (angle-fit rule) / certify_det_layer, with per-function timers
cd <snapshot>/lean && lake env lean certs/rishon-best-step.lean | certs/rishon-general-step.lean
# round 0 (temp root with empty archive, no Lean, CPU 0, load 5.4 at start):
python -m su2plaq.rishon.compress.round --seed --evaluate --no-lean --root scratch/bench305/round0root
# HEAD certificates: same cert_worker / lake jobs on scratch/bench305/head2 = aaa802e (make_jobs_head2.py, jobs_h2_*.json)
```
- Not run: no dry round 0 on the repo (the recorded `round-000.json` is untouched); the only round-0 run was on a temp root (section 2).

## 1. Evaluation time (`run_candidate`) and three-layer verification

Medians [min, max] over 6 runs (batch A rep 1-3 + batch B), wall seconds; A and B medians in the last columns. "Control" = `F1/004-pz-selector-walsh6` (CX 228), the program of report 304, with the same evaluator code (hash `5f5decfa...`), so any change against 304 is the environment.

| quantity | median [min, max], n=6 | batch A (CPU 0) | batch B (CPU 2) | peak RSS | baseline (report) | change vs baseline | verdict |
|---|---|---|---|---|---|---|---|
| general `seed/000-general.py` `--trial` | 5.97 s [5.47, 7.12] | 5.57 | 6.53 | 360 MB | 6.9 s (reports/tests/216, CLI wall) | -13 % | PASS |
| general `--full` (1296 codes, 3 angle pairs, Gauss, T) | 36.3 s [29.9, 44.0] | 38.4 | 34.1 | 819 MB | - (round-0 record: 25.3 s, pre-204 28.4 s, my round-0 run 27.6 s) | see note | PASS |
| headline `F3/006` `--trial` | 5.76 s [4.79, 6.80] | 5.01 | 5.85 | 353 MB | none (first measurement) | - | PASS |
| headline `F3/006` `--full` | 32.5 s [27.5, 36.5] | 32.5 | 32.6 | 844 MB | none | - | PASS |
| control `F1/004` `--full` | 30.6 s [28.3, 37.8] | 29.8 | 31.3 | 843 MB | 23.05 s [22.93, 23.16], 863 MB (304, CPU 4, load <= 2.6) | **+33 % [+23, +64]**, RSS -2 % | environment (code identical) |
| three-layer verification of the headline `r06-F3-006` (3 verifications, `three_layer`) | 35.5 s [31.9, 38.9] | 33.1 | 36.6 | 760 MB | none for this entry | - | PASS |
| three-layer verification of the old headline `r04-F1-004` (control) | 34.0 s [30.2, 38.1] | 33.1 | 36.8 | 760 MB | 24.93 s (304), 28.21 s + 0.41 s (303) | **+36 %** vs 304 | environment |
| same quantity, headline / control ratio, `--full` | 1.06 [A 1.09, B 1.04] | | | | - | - | the new headline costs the same as the old one |
| same quantity, three-layer headline / control | 1.04 [A 1.00, B 0.99] | | | | - | - | |

Reading:
- Report 304 measured the control at 23.05 s at load <= 2.6; today at load 4-39 the same code takes 28.3-37.8 s. The spread within today's six runs is 29 %, larger than between A and B, which is the load pattern, not the core. The headline program is 1.04-1.09 times the control in the same conditions (it has 216 instead of 228 CX but ten rotations and the F3 frame; its recorded round-6 wall in the archive is 15.9 s on a quiet machine, the control's 17.3 s, ratio 0.92, so the ratio is stable around 1). I did not find a code reason for the +33 % (no rishon evaluator file changed since 304, and 303 showed the same environment effect, +15-25 %), and because the load rule could not be met I do not claim an exact environment factor.
- The general program `--full` cannot be compared to a previous benchmark (none exists); against the recorded candidate walls of round 0 it is 1.1-1.4 times slower today, the same order as the control.
- The three-layer step of the headline is identical to `results/compress/rishon/three-layer.json` in every number (below).
- Warm-up (first run in a fresh tree) was 40-50 s for the full runs and three-layer runs and is excluded; this is the cold-start effect already seen in report 304 (F5).

Physics output (identical in all repetitions; stored values from the archive entries and `three-layer.json`):

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| general `--full`: op-norm, block, Gauss, key | `r00-seed-000`: $4.1252\times10^{-13}$, key (10102, 20650, 35639, 58) | $4.125\times10^{-13}$, block $4.495\times10^{-14}$, Gauss $2.660\times10^{-15}$, CX 10102, $T_{\rm fixed}$ 10218, $N_{\rm rot}$ 166, $T_\varepsilon$ 20650, depth$_{CT}$ 35639, 58 qubits; alt-pair errors $3.55\times10^{-13}$, $4.28\times10^{-13}$, skeleton equal | $10^{-10}$ (spec) | PASS |
| headline `--full` | `r06-F3-006`: $1.3485\times10^{-13}$, Gauss $7.358\times10^{-16}$, key (216, 832, 1350, 52) | $1.348\times10^{-13}$, Gauss $7.358\times10^{-16}$, block $1.366\times10^{-14}$, CX 216, $T_{\rm fixed}$ 196, $N_{\rm rot}$ 10, $T_\varepsilon$ 832, depth$_{CT}$ 1350, 52 qubits, skeleton equal, certified | same | PASS |
| control `--full` | `r04-F1-004`: $1.4509\times10^{-13}$, (228, 846, 1417, 53) | $1.451\times10^{-13}$, certified | same | PASS |
| three-layer of the headline | `three-layer.json`: unit (216, 832, 1350, 52), det (32, 496, 326, 48), three-layer (248, 1328, 1676, 52), op-norm $1.5354\times10^{-13}$ / $1.5923\times10^{-13}$ / $1.5713\times10^{-13}$ | identical to all digits, `ok` True, skeleton equal | exact | PASS |
| three-layer of `r04-F1-004` | (260, 1342, 1743, 53) (report 303) | identical, `ok` True | exact | PASS |

## 2. Round-0 wall time

Recorded walls (not re-run on the repo): **pre-204 1317.1 s**; **replay under 204 1633.5 s** (`results/compress/rishon/round-000.json`, written 2026-11-18, one pinned core, quiet-machine conditions of prompts/205 section 6; reports/tests/427 O5).

Fresh run of the same round on a temp root (empty archive, `--seed --evaluate --no-lean`, CPU 0, load 5.4 at start and 20 at the end; Lean off as in the recorded round; this is a real round 0, not `--dry-run`, so it pays the evaluation cache exactly as the replay did): **wall_s 1789.2 s (process 1789.5 s, CPU 1783 s)**, 4 valid, 1 invalid (`qiskit_l3`: `eval_budget`), best (6874, 17694, 31954, 58) = `r00-seed-001`, headline robust key and synthesis verdict (op-norm $1.8995\times10^{-5}$, 166 rot, certified) equal to the recorded round.

Stage split (my run; the candidate walls are the `wall_s` of the feedback files; stage times from file mtimes):

| stage | pre-204 (recorded) | replay (recorded) | my run | note |
|---|---|---|---|---|
| five seeds evaluated (`--full`) | 201.5 s | 352.9 s | 389 s (stage 398 s) | see candidate rows |
| - `000-general` | 28.4 s | 25.3 s | 27.6 s | same code, same result |
| - `010-general_polish` | 21.8 s | 18.4 s | 24.3 s | |
| - `001-general-rccx` | 12.8 s (`pruning_bound`, early reject) | 33.3 s (valid) | 37.2 s (valid) | now valid: the 10 % cap re-judge (cap $10^{-11}$) lets it through |
| - `002-general-mcx` | 12.4 s (`pruning_bound`) | 33.3 s (valid) | 35.6 s (valid) | same |
| - `qiskit_l3` seed | 126.2 s (`pruning_bound`) | 242.7 s (`eval_budget`) | 264.7 s (`eval_budget`) | now runs the exact verdict until the time budget (nominal 300 s / alternates 120 s) instead of failing at the cap |
| Clifford+T synthesis verification of the round best + archive save | about 1115 s (rest of the round, entry 000) | about 1281 s (rest, entry 001) | 1323 s | the best is now the rccx circuit `001` (6874 CX) instead of `000` (10 102 CX) |
| headline robust metrics + round file | (inside "rest") | (inside "rest") | 68 s | |
| **round wall** | **1317.1 s** | **1633.5 s** | **1789.2 s** | |

Comparison and explanation:
- Against the recorded replay: +155.7 s = **+9.5 %**, inside the 10 % threshold. The evaluation stage is +10 % (389 vs 353 s), the synthesis-plus-robust remainder +8.6 % (1391 vs 1281 s). Control from section 1 (same code, same machine state): +30 % slower than report 304 at load 4-39, so a +9.5 % round wall on identical code is consistent with the environment (the replay ran under the quiet-machine rule). Not a code regression.
- Against pre-204: +472 s = +36 %. Explained by work that did not exist before: (a) two seeds (`001`, `002`) are now valid and fully evaluated (+21 s each over their early rejects); (b) the L3 seed now runs to the evaluation budget (+116 s to +139 s over a rejection at the old $10^{-12}$ cap); (c) the synthesis verification is of a different best circuit; (d) the old round was timed on the pre-reinstall machine state (303/304: +15-25 % for the same code on the new install). The pre-204 round 0 did the same amount of synthesis work on 000.
- Hot spot to remember: 74 % of round 0 is the Clifford+T synthesis verification of the round best (1323 s), 22 % evaluation; later rounds (recorded 92-126 s) have no synthesis stage.

## 3. Lean certificates and theorem files

Exact export (`certify_circuit` = exact-target build + cross-check, circuit export, compiled checker `su2plaq_rishon_cert`, sha256 `6c3c62be...` unchanged since reports/tests/434) in a fresh process, 1 CPU, medians over 3 (+1 warm-up):

| quantity | gate snapshot `c5f31e4` (batch A, B pooled, CPU 0 / 2) | HEAD `aaa802e` (CPU 2) | change | where the time goes |
|---|---|---|---|---|
| certify general step (4289 gates in the circuit, 26 qubits), total | 35.17 s [35.01, 38.07] (A 35.19, B 35.15) | **41.01 s** [40.45, 41.08] | **+16.6 %** | exact target + cross-check 1.8-1.9 s (A) / 7.2-8.0 s (HEAD); checker 29.3-29.9 s in both |
| certify headline `r06-F3-006` through `round._certify` (angle-fit rule of 204 section 6.4 + certificate; 406 gates) | 25.76 s [25.45, 29.53] (A 25.47, B 25.84) | **31.52 s** [30.76, 31.79] | **+22.4 %** | angle-fit confirmation 2.2-3.0 s; exact target 2.1-2.6 s (A) / 7.6-8.3 s (HEAD); checker 16.9-17.1 s in both |
| certify det layer $U_D(\eta=0.29)$ (56 gates) | 2.61 s [2.33, 2.81] | 2.45 s [2.44, 2.54] | -6 % (noise) | checker 1.0 s |
| certify general step, 4 CPUs (0-3), HEAD | - | 21.87 s [21.74, 27.46], CPU 55 s | -47 % vs 1 CPU | the checker is multi-threaded |
| certify headline, 4 CPUs (0-3), HEAD | - | 20.77 s [19.41, 23.57], CPU 40 s | -34 % vs 1 CPU | |
| theorem file `lean/certs/rishon-best-step.lean` (369 KB, `lake env lean`, `native_decide`), 4 CPUs | 21.35 s [21.22, 21.64] | **21.31 s** [21.23, 21.61] | 0 % | RSS 0.8 GB; axioms: `propext`, `Classical.choice`, `Quot.sound`, one `native_decide` axiom |
| theorem file `lean/certs/rishon-general-step.lean` (517 KB), 4 CPUs | 38.16 s [37.98, 38.59] (434: 42.3 s on 3 cores) | 38.51 s [38.21, 38.69] | +0.9 % | same four axioms |

Notes:
- The **+17 % / +22 %** of HEAD over the gate snapshot is audit-307 N1: `_check_cross` now compares the exact target with `operators.inner_target` at five pairs (nominal, the two alternates, one irrational-beta pair) instead of one, each a dense $1296\times1296$ target; `exact_target` rose from 1.8-2.6 s to 7.2-8.3 s (time per certificate +5-6 s). The checker's own time is unchanged to 1 % (29.3-29.9 s and 16.8-17.1 s) and the theorem-file elaboration is unchanged, since only six comment lines changed in the two files. Cost per round in the loop: one certificate of the best plus one of the headline (about 41 + 32 s on one CPU, 22 + 21 s on four).
- The new Lean checker did not exist at the time of reports 200/303, so there is no older timing of it. Compared with reports/tests/434 (builder 21 s, tester 10.2 s for the general step, tester 4.6 s for the headline, 3 cores): mine is 2.1x / 4.5x slower with 4 CPUs (21.9 s / 20.8 s) at load 17-26. The 434 numbers are `cert.seconds` from a quiet machine; I cannot say how much of the factor is load and how much is that 434 had a warm exporter cache; guess: the checker is allocation heavy and the CPU-time of the checker (about 30 s and 17 s on one CPU) is the stable quantity.
- Certificate results: every run `certified`; the tampered-theorem negative control was not re-run (reports/tests/434 did it: rejected in 1.5 s).
- Peak RSS 0.8 GB for all certificate and theorem runs (limit 600 s / 15 GB in the plan; met by a factor 15 in time).

## 4. Flags and notes for the coordinator

| # | flag | numbers | cause |
|---|---|---|---|
| F1 | Control `F1/004 --full` +33 % and three-layer (old headline) +36 % over report 304 | 30.6 vs 23.05 s; 34.0 vs 24.93 s | environment: evaluator files byte-identical to 304; today's load 4-39 (median 14-24) against <= 2.6; guess: shared L3/memory bandwidth and power budget of the 12700KF at 8-16 busy cores; not code |
| F2 | Load rule not satisfiable | batch A 7.5-39, B 3.7-23, HEAD certificates 4.3-20 | other agents' jobs on CPUs 7-17 (and chrome on 2/5); whole batch repeated once on another core, agrees within 1-3 % |
| F3 | Round 0 +9.5 % over the recorded replay | 1789.2 vs 1633.5 s | 0.5 points under the threshold; evaluation stage +10 %, synthesis-plus-robust remainder +8.6 %; environment (F1); a rerun on a quiet machine would be the clean test, I cannot get one |
| F4 | Round 0 +36 % over pre-204 | 1789.2 vs 1317.1 s | two more valid seeds, L3 seed runs to `eval_budget` instead of failing at the cap, different synthesis-verified best, environment |
| F5 | Certificate on HEAD +17 % / +22 % over the gate snapshot | 41.0 vs 35.2 s; 31.5 vs 25.8 s | audit-307 N1 multi-pair exact-target cross-check (+5-6 s); checker unchanged; intended, not a regression |
| F6 | Round 0 is 74 % synthesis verification (1323 s) | | pre-existing (Clifford+T verification of the best on all 1296 codes); only round 0 pays it in full |
| F7 | `compress/` per-candidate `wall_s` in archive entries is not comparable between sessions | `r06-F3-006` 15.9 s recorded vs 32.5 s today; `r04-F1-004` 17.3 vs 29.8 s | machine state at recording time; cite it only next to a control |

Not tested here: pytest suite wall times (full run: reports/tests/435), `scripts/m6_results.py`, rounds 1-6 re-evaluations, memory above 1 GB (none seen: everything peaked at 0.76-0.84 GB per process; the 304 control had 863 MB).

## 5. Files touched

- Created, untracked: `results/benchmarks/rishon-m6.json`, `results/benchmarks/rishon-m6-raw/`, `results/benchmarks/rishon-m6-scripts/`, `results/tester/benchmark-305-summary{,-B,-H2cert,-H2cert4,-H2lean}.json`, this report. Scratch (gitignored): `scratch/bench305/{head,head2,round0root,tmp}` (two source snapshots with `lean/.lake` symlinked to the real build directory, the round-0 temp root, certificate outputs); `rm -rf` is denied, so they stay.
- Tracked files rewritten by the benchmark: none (`git status` shows only the untracked items above and other agents' LSH files, which I did not touch); nothing to restore. `compress/cache/gridsynth` (gitignored) is unchanged (copied into the snapshots). No file under `src/`, `tests/`, `prompts/`, `lean/` was edited. `graphify update .` run at the start (no source change by me).

VERDICT: PASS (no code regression; deltas above 10 % are environment load, intended new work in round 0, or the audit-307 N1 cross-check; physics bit-identical to the stored archive and `three-layer.json`).

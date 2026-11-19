# Benchmark report 304 - milestone 2c (consolidation 008), mode benchmark, gate step C5 part 3

- Date: 2026-11-19. Commit: `ca68875` (HEAD, clean tree before the run; the only new files are untracked `results/benchmarks/c5-raw/`, `results/benchmarks/c5-scripts/`, `results/tester/benchmark-304.json` and this report). Tester: Sonnet 5.5.
- Prompt in force: `prompts/008-merged-repo-consolidation.md` (section 12 = expected cost; step C5). Gate state: tester full PASS `reports/tests/430`, auditor PASS WITH NOTES `reports/audits/305`. `python tools/check_lock.py`: LOCK OK; `~/.claude/bin/acceptance-check`: PASS (acceptance-v22), both run at the end.
- Baselines named by the caller: `reports/benchmarks/003-m2-benchmark.md` (main) and `100, 200, 300, 301, 302, 303`. They come from five different machine states (laptop i7-8750H; old SupremeCommander install; Threadripper; omnicommander on CPUs 14-19 under load 3). Reports 301 and 303 already showed that such cross-state numbers move by 15-25 % with no code change. **So the primary comparison here is a controlled A/B on one machine**: the code of tag `pre-consolidation-008` (commit `ed4d18a`, taken with `git archive` into `scratch/bench304/old-pre008`) against HEAD, same worker scripts, fresh process per run, old and new interleaved. Section 4 then puts the new absolute numbers next to the old reports.
- Machine: `omnicommander`, Intel i7-12700KF, 31 GiB, no GPU. python 3.12.16, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 (same as reports 301-303). `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`.
- Pinning and load: driver and children inside `taskset -c 0-8` and `tools/run-capped` (11 GB per job); every timed process on CPU 4 (one P-core thread, the same for old and new). `uptime` before the first run `04:03:40 load average: 0.76, 0.56, 1.18`; after batch 1 `04:40:09 ... 1.04, 1.20, 1.14`; after the scripts batch `04:50:11 ... 1.22, 1.21, 1.18`. The 1-minute load average before and after every one of the 392 timed processes is stored in the raw records: **maximum 2.56** (limit for a repeat was 9, never reached; the driver would have waited).
- Seeds: no stochastic call is timed (Gauss sample seed 20261104 and `ct_compile` seed 12345 are library defaults inside the tested code).
- Statistic: median [min, max] over processes. "first" = first call in a fresh process (cold), "later" = pooled remaining calls. 3 processes per job (5 for jobs under 3 s), old and new alternating, order flipped every repetition. Threshold 10 %.
- Raw numbers: `results/tester/benchmark-304.json` (summary, RSS, metadata) and per-process records `results/benchmarks/c5-raw/*.jsonl`. Scripts: `results/benchmarks/c5-scripts/` (`c5_driver.py` = driver and job list, `w_twelve0.py`, `w_twelve1.py`, `w_sl.py`, `w_rishon.py` = copies of the report 003 / 301-302 / 303 workers with the source root selectable by `BENCH_ROOT`; `w_fuzzy.py` = the report 300 tasks; `make_root.py` = the report 301 scratch-root builder; `c5_analyze.py`, `c5_physdiff.py`, `rss_wrap.py`, `run_*.sh`).

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding; cd /home/digimonk/Projects/su2qc-encoding
mkdir -p scratch/bench304/old-pre008 && git archive pre-consolidation-008 | tar -x -C scratch/bench304/old-pre008   # old tree; pycache + gridsynth cache synced to the same warm state
PER_JOB_MEM=11G tools/run-capped taskset -c 0-8 results/benchmarks/c5-scripts/run_all.sh fuzzy lsh spinnet rishon twelve   # workers, run_candidate --full, round re-evaluations
PER_JOB_MEM=11G tools/run-capped taskset -c 0-8 results/benchmarks/c5-scripts/run_scripts.sh   # m3/m4/m7/m1_results.py --out <scratch>
PER_JOB_MEM=11G tools/run-capped taskset -c 0-8 results/benchmarks/c5-scripts/run_m4.sh       # m4_results again, see section 7
PER_JOB_MEM=11G tools/run-capped taskset -c 0-8 results/benchmarks/c5-scripts/run_rss.sh      # peak RSS of the CLI jobs
python results/benchmarks/c5-scripts/c5_analyze.py; python results/benchmarks/c5-scripts/c5_physdiff.py
```
Compression-round measurement: the report 301 method. For each repetition a fresh scratch root (copy of `compress/` and `results/compress/<enc>` with one round's entries and attempts removed), then the track's own CLI `round --round N --evaluate --no-lean --root <scratch>`: twelve round 4 (3 programs), spinnet round 5 (3), rishon round 4 (3), fuzzy_ub round 9 (3), fuzzy_link round 2 (1). No proposer was started, no file under `compress/` or `results/compress/` was written (all in `scratch/bench304/roots/`). Per-candidate time: `run_candidate --full` (spinnet: `su2plaq.spinnet.loop candidate --full`; rishon: `su2plaq.rishon.compress.run_candidate --full`; fuzzy: `scripts/m10_round.py candidate --full`) of each encoding's headline program, with the same command line in both trees.

## Verdict

**PASS. No unexplained slowdown above 10 %; physics output unchanged.** Against the pre-consolidation code, the only quantities that moved by more than 10 % are every evaluator call of an encoding whose physical span is not the whole code space (twelve, spin network, LSH) and the compression-round times that are built from those calls. The extra cost is one constant block inside `evaluate`: about $+0.28$ s per twelve-qubit verdict and $+0.03$ s per spin-network or LSH verdict, independent of the circuit. This is the span-leak computation that prompts/008 section 12 announces as "a planned change of the benchmark, not a regression". The rishon and fuzzy evaluator paths, the route-A build, the circuit builders and the encoding builds are unchanged within noise (0.97-1.03). Two places where the measured *ratio* is larger than the multiplier quoted in STATUS/section 12 (twelve $\times1.35$-$1.39$ vs "$\times1.3$"; spin network $\times1.16$-$1.24$ vs "$\times1.1$-$1.15$"; very light verdicts up to $\times2.0$) are listed in flag F1; the absolute cost stays inside the section 12 numbers.

## 1. Evaluator time per circuit, old vs HEAD (A/B on this machine)

Medians, CPU 4. "later" = warm repeat (the number the compression loop pays after the first circuit). Full per-row data for every task are in `results/tester/benchmark-304.json::summary`.

| encoding | quantity | old `ed4d18a`, s | HEAD, s | ratio | absolute change, s | explanation |
|---|---|---|---|---|---|---|
| twelve | `evaluate` identity, inner span (later) | 0.7211 [0.7168, 0.7242] | 0.9984 [0.9946, 1.003] | 1.384 | +0.277 | span leak (F1) |
| twelve | `evaluate` $U_E$ (later) | 0.7234 [0.7211, 0.7271] | 1.002 [0.9987, 1.006] | 1.385 | +0.279 | span leak |
| twelve | `evaluate` $U_B$ first / later | 2.976 / 0.8041 [0.7995, 0.8079] | 3.376 / 1.092 [1.083, 1.097] | 1.134 / 1.358 | +0.400 / +0.288 | span leak |
| twelve | `evaluate` step order 1 (later) | 0.8048 [0.8008, 0.8076] | 1.086 [1.083, 1.101] | 1.350 | +0.281 | span leak |
| twelve | `evaluate` with 3 outer bits (later) | 0.278 [0.2756, 0.2795] | 0.5626 [0.558, 0.5654] | 2.023 | +0.285 | span leak; light verdict, so the ratio is large (F1) |
| twelve | `evaluate` synthesised $U_B$ (later) | 1.155 [1.151, 1.162] | 1.446 [1.442, 1.451] | 1.252 | +0.291 | span leak |
| twelve | Paulo QPY `evaluate` (aer_mps, 3 runs) | 24.31 [24.24, 24.41] | 24.63 [24.56, 24.65] | 1.013 | +0.32 | within noise (+1.3 %, a 0.3 s change on a 24 s call) |
| spin network | `evaluate` $U_B$ first / later | 0.5033 / 0.1663 [0.1647, 0.1679] | 0.5344 / 0.1939 [0.1912, 0.1961] | 1.062 / 1.166 | +0.031 / +0.028 | span leak |
| spin network | `evaluate` $U_E$ (later) | 0.1413 [0.1392, 0.1435] | 0.1700 [0.1684, 0.1725] | 1.203 | +0.029 | span leak |
| spin network | `evaluate` step 1 / `pairs9` (later) | 0.1652 / 0.1642 | 0.1931 / 0.1926 | 1.169 / 1.173 | +0.028 / +0.028 | span leak |
| spin network | `evaluate` with outer register, Paulo 15-qubit, synthesised $U_B$ / step 1 (later) | 0.1652 / 0.165 / 0.1995 / 0.2346 | 0.1923 / 0.1917 / 0.228 / 0.2621 | 1.164 / 1.162 / 1.143 / 1.117 | +0.027 / +0.027 / +0.029 / +0.028 | span leak |
| spin network | `evaluate` 12-qubit $U_B$ (shared quantity, later) | 0.804 | 1.086 | 1.351 | +0.282 | span leak |
| LSH | `evaluate` $U_B$ first / later | 0.5039 / 0.1656 [0.1647, 0.1798] | 0.5403 / 0.1945 [0.1937, 0.1951] | 1.072 / 1.175 | +0.036 / +0.029 | span leak (LSH is not named in section 12; same code path, same size, see F1) |
| LSH | `evaluate` $U_E$ / step 1 / wrapped `flags4` (later) | 0.1406 / 0.1664 / 0.1658 | 0.1705 / 0.1968 / 0.1956 | 1.212 / 1.182 / 1.179 | +0.030 / +0.030 / +0.030 | span leak |
| LSH | `evaluate` synthesised step 1 (later) | 0.2296 | 0.2594 | 1.130 | +0.030 | span leak |
| rishon | `verify` $U_E$ / $U_B$ / step 1 (later) | 4.242 / 5.689 / 5.982 | 4.272 / 5.751 / 5.919 | 1.007 / 1.011 / 0.989 | +0.03 / +0.06 / -0.06 | unchanged (section 12: "0 rishon", full-space shortcut) |
| rishon | three-layer verification of headline `r04-F1-004` (3 verifications) | 25.11 [25.04, 95.27] | 24.93 [24.91, 25.18] | 0.993 | -0.18 | unchanged (the old maximum 95.3 s is its very first run in the fresh tree, see F5) |
| fuzzy | `verify_plaquette` first / later | 0.3711 / 0.03327 | 0.368 / 0.0333 | 0.992 / 1.001 | $\le$ 0.003 | unchanged (section 12: "0 fuzzy") |
| fuzzy | `verify_step_samples` order 1 | 16.67 [16.62, 16.70] | 16.62 [16.53, 16.68] | 0.997 | -0.05 | unchanged |
| fuzzy | `verify_link` first | 0.001518 | 0.001475 | 0.972 | -0.00004 | unchanged |

## 2. Route-A build, builders, encoding builds, shared set-up

All unchanged (ratios 0.96-1.03; only outliers are tasks of 1-60 microseconds): twelve `physical_basis()` cold 0.0720 vs 0.0709 s; route-A `h_magnetic_phys` later 0.02468 vs 0.02477 s; `target(step)` 0.0979 vs 0.0974 s; route B `h_magnetic_phys_6j` 4.26 vs 4.32 ms; twelve `build_UB` 0.47 ms both; `SpinNet()` first / later 0.1636 / 0.0506 vs 0.1636 / 0.0505 s; `LSH()` 0.1508 / 0.0442 vs 0.1511 / 0.0442 s; `RishonEncoding` basis cold 2.387 vs 2.393 s, `inner_span` 0.7606 vs 0.7633 s; rishon `build_UB` first 1.826 vs 1.829 s; fuzzy `build_UB` 0.2911 vs 0.2881 s; fuzzy `build_step` order 1 1.9 ms both. Synthesis (`synthesize`, pygridsynth) first / later: spin-network $U_B$ 0.433 / 0.00275 vs 0.432 / 0.00279 s, LSH step 1 0.4575 / 0.00475 vs 0.4565 / 0.00478 s, twelve $U_B$ 0.4785 vs 0.4800 s.

## 3. Compression: per-candidate evaluation and round wall time (no proposer round was run)

Per candidate = `run_candidate --full` of the headline program (nominal pair plus the two alternate angle pairs, all physical states):

| encoding / program | old, s | HEAD, s | ratio | peak RSS old / HEAD, MB | note |
|---|---|---|---|---|---|
| twelve `F2/005-outer-t2-peephole` (CX 111, T 912) | 12.20 [12.14, 12.28] | 13.16 [13.14, 13.18] | 1.078 | 386 / 499 (+29 %) | 3 verdicts x +0.3 s span leak = +0.96 s; memory +113 MB = section 12's "span leak up to 0.2 GB on twelve" |
| spin network `F1/002-dimer-linear-corner-walk` (CX 31) | 1.884 [1.878, 1.901] | 1.948 [1.938, 1.980] | 1.034 | 249 / 257 | 3 verdicts x +0.03 s |
| rishon `F1/004-pz-selector-walsh6` (CX 228) | 22.96 [22.94, 23.24] | 23.05 [22.93, 23.16] | 1.004 | 811 / 863 (+6 %) | unchanged |
| fuzzy_ub `F1/010-ten-qubit-short-window-exact-angles` (CX 83) | 0.7877 [0.7834, 0.8025] | 0.7817 [0.7755, 0.7841] | 0.992 | 146 / 144 | unchanged |
| fuzzy_link `F2/001-plane_bfs_frame_fusion12` (CX 12) | 0.6163 [0.6156, 0.6237] | 0.6097 [0.6066, 0.6147] | 0.989 | 123 / 123 | unchanged |

Round re-evaluation (`--no-lean`; the "round wall" is the `wall_s` field of the round file, "process" the whole CLI call). 3 repetitions each:

| encoding, round (programs) | old round wall, s | HEAD round wall, s | ratio | old / HEAD process wall, s | ratio | explanation |
|---|---|---|---|---|---|---|
| twelve, round 4 (3) | 9.194 [9.192, 9.217] | 11.947 [11.944, 11.954] | **1.299** | 9.374 / 12.13 | 1.294 | 9 verdicts (3 programs x 3 angle pairs) x +0.3 s = +2.7 s measured +2.75 s: span leak |
| spin network, round 5 (3) | 4.645 [4.626, 4.684] | 5.172 [5.159, 5.198] | **1.113** | 5.161 / 5.350 | 1.037 | 9 verdicts x +0.03-0.05 s = +0.27-0.45 s; measured +0.53 s (slightly above section 12's +0.05 s per verdict; absolute +0.5 s on a 5 s round; F1) |
| rishon, round 4 (3) | 82.96 [82.81, 83.43] | 83.02 [82.68, 83.42] | 1.001 | 83.22 / 83.29 | 1.001 | unchanged |
| fuzzy_ub, round 9 (3) | 1.485 | 1.471 | 0.990 | 1.78 / 1.766 | 0.992 | unchanged |
| fuzzy_link, round 2 (1) | 0.7016 | 0.6933 | 0.988 | 1.008 / 0.9919 | 0.984 | unchanged |

In every round the archive best key is identical in old and HEAD: twelve $(111, 912, 1663, 31)$, spin network $(31, 1062, 2173, 17)$, rishon $(228, 846, 1417, 53)$, fuzzy_ub $(83, 638, 1517, 10)$, fuzzy_link $(12, 644, 1183, 4)$, 3/3/3/3/1 valid entries. A real twelve round also pays the Lean certificate of its best (351 s in report 003); `lean/` and `src/su2plaq/lean/` have no diff between the tag and HEAD (`git diff --stat pre-consolidation-008..HEAD -- lean src/su2plaq/lean` is empty), so that time was not re-measured.

## 4. Scripts (regeneration of the tracked results), old vs HEAD

3 runs each, `--out <scratch>` (tracked results untouched):

| script | old, s | HEAD, s | ratio | peak RSS old / HEAD, MB | explanation |
|---|---|---|---|---|---|
| `scripts/m1_results.py` (twelve $U_E$, $U_B$, step; 4 eps x re-verification) | 66.26 [65.93, 66.58] | 72.76 [72.63, 72.81] | **1.098** | 1802 / 1932 (+7 %) | about 23 twelve verdicts x +0.28 s = +6.5 s measured +6.5 s: span leak; just below the threshold |
| `scripts/m3_results.py` (spin network) | 9.135 [9.127, 9.196] | 9.838 [9.828, 9.881] | 1.077 | 302 / 301 | about 24 verdicts x +0.03 s |
| `scripts/m7_results.py` (LSH) | 9.558 [9.525, 19.50] | 10.10 [10.09, 10.17] | 1.057 | 838 / 838 | span leak; the old maximum 19.5 s is its first run in the fresh tree (F5) |
| `scripts/m4_results.py` (spin-network headline, Lean certificate reused) | 6.233 [6.219, 6.235] | 6.415 [6.401, 6.459] | 1.029 | 838 / 838 | span leak (the 838 MB is the shared Lean process) |

## 5. The new absolute numbers next to the old reports

These are context, not the regression test (different machine states, see the top). A "+" above 10 % is flagged and explained.

| report | quantity | then | now (HEAD) | change |
|---|---|---|---|---|
| 301 (omnicommander, CPU 14, load 3) | spin-network `evaluate` $U_B$ first / later | 0.606 / 0.2089 s | 0.5344 / 0.1939 s | -11.8 % / -7.2 % |
| 301 | spin-network `evaluate` step 1 later | 0.2115 s | 0.1931 s | -8.7 % |
| 301 | 12-qubit $U_B$ `evaluate` first / later | 3.321 / 0.872 s | 3.376 / 1.092 s | +1.7 % / **+25.2 %** (span leak; the machine state of 301 was about 10 % slower than the clean pinned core used now, so the true code effect is the +35 % of section 1) |
| 301 | synthesised $U_B$ / step 1 `evaluate` later | 0.2083 / 0.2464 s | 0.2280 / 0.2621 s | +9.5 % / +6.4 % |
| 301 | spin-network round 5 (process) / `loop candidate` headline | 6.64 s / 2.62 s | 5.35 s / 1.95 s | -19 % / -26 % |
| 301 | `m3_results.py` / `m4_results.py` | 10.63 / 6.95 s | 9.84 / 6.42 s | -7.4 % / -7.6 % |
| 302 | LSH `evaluate` $U_B$ first / later | 0.5736 / 0.1843 s | 0.5403 / 0.1945 s | -5.8 % / +5.5 % |
| 302 | LSH `evaluate` $U_E$ first / later | 0.1698 / 0.1524 s | 0.1854 / 0.1705 s | +9.2 % / **+11.9 %** (span leak, +0.018 s on a 0.15 s call) |
| 302 | `m7_results.py` | 9.20 s | 10.10 s | +9.8 % |
| 303 | rishon `verify` $U_B$ first / later | 6.709 / 6.486 s | 5.929 / 5.751 s | -11.6 % / -11.3 % |
| 303 | rishon `verify` step 1 later; three-layer headline | 6.775 s; 28.21 s | 5.919 s; 24.93 s | -12.6 %; -11.6 % |
| 303 | 12-qubit $U_B$ `evaluate` first / later | 3.109 / 0.840 s | 3.376 / 1.092 s | +8.6 % / **+30.0 %** (span leak) |
| 303 | rishon basis cold | 2.450 s | 2.393 s | -2.3 % |
| 300 (Threadripper, shared) | fuzzy `verify_step_samples` order 1; `verify_plaquette`; `build_UB` | 23.81 s; 0.587 s; 0.539 s | 16.62 s; 0.368 s; 0.288 s | -30 %; -37 %; -47 % (different machine; the A/B above shows 0.99-1.00) |
| 100 / 003 (older states) | spin-network `evaluate` $U_B$ first / later (100); twelve `run_candidate --full` best (003, laptop) | 0.503 / 0.1673 s; 36.84 s | 0.5344 / 0.1939 s; 13.16 s | +6.2 % / +15.9 % (span leak, +0.027 s); laptop vs desktop, not comparable (A/B ratio 1.078) |
| 003 (laptop) | Paulo QPY `evaluate` | 84.07 s | 24.63 s | machine change; A/B ratio 1.013 |

## 6. Physics output unchanged (old tree vs HEAD)

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| fields of all worker verdicts (`ok`, reason, op-norm error, block error, leak amplitude, Gauss residual, engine, method, certified, `n_rot`, `t_rot`, gate counts, spectra, build counts), 37 worker jobs | identical | 576 fields compared, 0 differ, maximum absolute difference 0.0 (bit-identical) | $10^{-13}+10^{-9}$ rel. | PASS |
| `run_candidate --full` summaries of the 5 headline programs | identical counts, errors | identical (CX/T/depth/qubits, op-norm error, pruning); the only text differences are the new `span_leak ... total_error ...` line and fuzzy_link `gauss nan` instead of `0.0` (prompts/008 section 5: with the Gauss check off the residual stays NaN) | exact | PASS |
| best key of the 5 re-evaluated rounds | identical | identical (section 3) | exact | PASS |
| regenerated `m1/m3/m4/m7_results` JSON (10 files, old tree vs HEAD, provenance, seconds and file lists excluded) | identical | 5050 fields compared, 2 differ, both text: (a) `m3 UB.json` `extra.comparison.paulo15.source` = recorded path of Paulo's gates file (old-tree path vs HEAD path; same cause as in report 301); (b) `m4-compressed.json` `extra.report_table_markdown`: the commit labels of the archive entries (`@ 2fd5b3d` ... vs `@ 02c499d`, the consolidation replay re-tagged the entries) and the label of the Paulo row, `beta = 1` (old) vs `beta = 0.05` (HEAD); all numbers in that table (counts, errors) are identical, and 0.05 = $\alpha_P/2$ is the angle used in `m3_results.py`, so the HEAD label is the correct one (a label fix in `compress/report.py`) | exact | PASS |
| new fields in the regenerated results | present | `span_leak`, `total_error`, `extra.span_leak_max_state`, `extra.gauss` added; no span-leak value above $10^{-9}$ outside the synthesised-circuit entries; largest values $1.9\times10^{-4}$ and $1.6\times10^{-4}$ (synthesised order-2 step at $\varepsilon=10^{-4}$, inside the $N_{\rm rot}\varepsilon+10^{-9}$ tolerance) | tolerances unchanged | PASS |

## 7. Flags and notes for the coordinator

| # | flag | numbers | cause |
|---|---|---|---|
| F1 | Every evaluator call on twelve / spin network / LSH is slower by a constant: twelve $+0.277$ to $+0.291$ s (ratio 1.25-1.39 on 0.7-1.2 s calls; 2.02 on the 0.28 s outer-bits call), spin network and LSH $+0.027$ to $+0.036$ s (ratio 1.12-1.24 on 0.14-0.26 s calls); the compression rounds that call it follow (twelve round x1.30, spin-network round x1.11, process wall x1.04). | section 1 and 3 | Explained by prompts/008 section 12 (span leak per verdict, "a planned change"). Attribution measured, not assumed: `cProfile` of one warm twelve `evaluate`: `evaluate` own time 0.071 s (old) vs 0.316 s (HEAD), cumulative 0.885 vs 1.207 s; `_inner_span_error` 0.365 vs 0.367 s (unchanged); new `_local_basis` 0.003 s; the added block is the per-pattern QR/Gram code of `git diff pre-consolidation-008..HEAD -- src/su2plaq/evaluate/evaluator.py`. Rishon (inner view) and fuzzy take the `full_space` shortcut and show ratio 0.99-1.01, as section 12 says ("0 fuzzy/rishon"). Two places where the measured ratio is above the quoted multiplier: STATUS says twelve wall $\times1.3$ (measured $\times1.35$-$1.39$) and spin network $\times1.1$-$1.15$ (measured $\times1.16$-$1.24$); on a very light verdict (outer-bits call, 0.28 s) the ratio is 2.0. The absolute costs are inside the section 12 numbers (twelve +0.4 to +1.5 s quoted, +0.28 s measured on the identity-like circuits, +0.40 s on the cold first call; spin network +0.05 s quoted, +0.03 s measured), so I count them as explained; the ratios in STATUS are just too low for light verdicts. LSH is not listed in section 12 but uses the same evaluator path as the spin network and shows the same +0.03 s. |
| F2 | Twelve round and `run_candidate` memory +29 % (386 -> 499 MB) and `m1_results.py` +7 % (1.80 -> 1.93 GB). | section 3, 4 | span leak arrays; +113 MB is below section 12's "$\le0.2$ GB extra on twelve". |
| F3 | `m1_results.py` is at +9.8 %, 0.2 percentage points under the threshold. | 66.26 -> 72.76 s | span leak (23 verdicts x +0.28 s = +6.5 s measured +6.5 s). A fourth heavy twelve regeneration would cross 10 %; not a failure. |
| F4 | Round-wall comparison is on re-evaluations without Lean and without proposers; the Lean certificate and any proposer time are not in these numbers. | - | by the caller's instruction (no real round). |
| F5 | Cold-start outliers in the old tree only: three-layer rishon verification 95.27 s vs 25.0 s on its first run; `m7_results.py` 19.50 s vs 9.5 s on its first run. | the median of 3 is used, the HEAD runs show no outlier | guess: first execution in the freshly unpacked tree (disk caches written by the first run; Python bytecode was pre-compiled, so not that). Does not touch HEAD, but if you quote single first runs from a fresh checkout, expect such cold costs. |
| F6 | Not measured here: pytest suite wall times (the full run is `reports/tests/430`), Lean `--certify-best` times (no Lean diff), real compression rounds, `scripts/m5_results.py` / `m9_results.py` / `m10_round.py best-step` regeneration (rishon and fuzzy evaluators are unchanged by the A/B above). | - | scope of this gate benchmark. |
| F7 | Environment notes: (a) the old tree needs Lean artifacts for `m4_results.py`; my first attempt let `lake` start a network fetch of its package dependency inside the scratch tree (`scratch/bench304/old-lake-partial`, 314 MB, gitignored), the three failed runs (rc 1, 5.8-28.4 s) stay in `c5-raw/scripts.jsonl` and are excluded from the statistics; I then symlinked `scratch/bench304/old-pre008/lean/.lake` to the HEAD `lean/.lake` (identical Lean sources) and re-ran 3+3, which are the numbers above. (b) The gridsynth cache of both trees was synced before timing so neither arm pays a cold cache. | - | - |

## 8. Files touched

- Created (untracked): `results/benchmarks/c5-raw/`, `results/benchmarks/c5-scripts/`, `results/tester/benchmark-304.json`, this report; scratch (gitignored): `scratch/bench304/` (old tree, scratch roots, regenerated results, logs). `compress/cache/gridsynth` (gitignored) received the union of both trees' cached words.
- Tracked files rewritten by the benchmark: none (`git status --short` shows only the untracked items above); nothing to restore. No file under `src/`, `tests/`, `prompts/` was edited. `graphify update .` run at the start.
- `tools/check_lock.py`: LOCK OK; `~/.claude/bin/acceptance-check`: PASS (acceptance-v22).

VERDICT: PASS (all deltas above 10 % against the pre-consolidation code are the span-leak cost of prompts/008 section 12; physics bit-identical; rishon and fuzzy unchanged).

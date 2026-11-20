# Benchmark report 306 - LSH milestone 8 gate, step 3 (mode benchmark)

- Date: 2026-11-20 (runs 14:15-15:11 EST). Commit: `git rev-parse --short HEAD` = `513eb51` at the end of the session (`148d404` at the start; `git diff --stat 148d404 513eb51` touches only `docs/report-8-lsh-compression.md` and `notes/STATUS.md`, so `src/`, `tests/`, `compress/`, `scripts/` are identical to the audited tree). Acceptance lock `acceptance-v23` (`tools/check_lock.py`: `LOCK OK`; `acceptance-check`: `PASS: tests/acceptance matches acceptance-v23`, run at the end).
- Prompt in force: `prompts/402` (G2 erratum) on `prompts/401` (row 8.10, benchmark list in section 9). Gate so far: tester `reports/tests/446` PASS (full, acceptance-v23), auditor `reports/audits/308` PASS WITH NOTES.
- Compared against: `reports/benchmarks/302-lsh-m7.md` (M7 baseline, same machine, other session) and, new in this report, a same-session A/B against the **milestone-7 source tree** (`git archive milestone-7 src`, extracted to `scratch/bench-m8/m7tree`, run interleaved with HEAD).
- Raw numbers (all repeats, load average before/after every run, commands, commit): `results/benchmarks/lsh-m8/summary.json` plus `raw_*.json`, `logs/`. Scripts: `results/benchmarks/lsh-m8/scripts/` (`bench_driver_m8.py` is the driver, `w_eval.py` the per-program worker, `bench_worker_lsh.py` the 302 worker with a source-path switch, `assemble_m8.py` builds `summary.json`, `run_all_m8.sh` the phase chain).
- Machine: `omnicommander` (the desktop; Intel i7-12700KF: 8 P-cores with SMT and 4 E-cores, 20 logical CPUs; 31 GiB; no GPU; Omarchy). python 3.12, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2. `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`. Pinning: single-process tasks `taskset -c 0` (P-core 0, SMT sibling CPU 1 idle); loop/script/certify jobs `taskset -c 0-8` through `tools/run-capped`; m7 and unit suites `taskset -c 0-8` with `tools/pytest-safe -n 6`; m8 suite `taskset -c 0-7` with `-n 2`. One timed job at a time. Report 302 used CPUs 14-19, so absolute numbers carry a core-assignment shift (see Verdict).
- Load: `/proc/loadavg` at the start 0.05 / 0.29 / 1.13, at the end 0.59 / 3.09 / 3.53 (the 5- and 15-minute values contain my own suite runs). Cores 9-19 showed no job of other users in `ps` (top consumers: a qemu VM at 20 % of one core, Chrome renderers at a few percent). Per-run 1-minute load before each run is in the JSON: 0.4-1.4 for all single-process tasks (that is my own job's own load), 1.6-3.3 before the suites. The spread of every measurement below is tiny (max/min within 1-3 %), which is itself evidence the machine was quiet.
- Seeds: nothing stochastic is timed. Robust angle set: seed 20261107, 20 pairs. Transpiler seed 20261104. Parameters: $(\alpha,\beta)=(0.37,0.61)$, order 1, $\varepsilon=10^{-6}$, alternate angle pairs $(0.91,0.23)$ and $(1.70,1.00)$, engine `sparse`.
- Method: "later" = pooled timed calls after the warm-up (n shown), "first" = first call in a fresh process. Statistic = median [min, max]. Item 1-4: 5 fresh processes, each 1 warm-up + 5 timed calls (n = 25 timed) unless stated. A "cold" variant points `su2plaq.compress.synth.CACHE_DIR` (module attribute, in-process only) at an empty scratch directory (cold pygridsynth cache); the warm variant uses the repository's own cache (`compress/cache/gridsynth`, gitignored, already filled).

## Verdict

**REGRESSION (one item, explained, physics unchanged).** The verdict-level `evaluate` call is 16-21 % slower per circuit than the milestone-7 source on the same machine in the same session (A/B, section 5), above the 10 % threshold. The cause is a deliberate code change, the span-leak validity check added to `src/su2plaq/evaluate/evaluator.py` in prompts/008 section 5 (guess confirmed by profile: about +30 ms per call from an extra 433x433 eigenvalue problem and an SVD-based local basis). Against the stored report 302 the same quantity is only +4 to +14 %, because today's machine state is about 9 % faster than the 302 session (the milestone-7 tree itself measures 0.168 s today against 0.184 s in 302). Everything else is within 10 % (route-A style build 0.99-1.00, synthesis 0.99-1.00, encoding build 1.00, Lean certificate faster than in 302). All physics outputs are unchanged (section 6). No quantity of items 1-4 has an earlier value, so they are new baselines.

Whether to treat the evaluator slowdown as blocking is the coordinator's call: it buys a validity check (`total_error = op_norm_error + span_leak`), costs 0.03 s per verdict, and the headline `evaluate_program` is 1.18 s in total.

## 1. Evaluator time per circuit, full `evaluate_program` (item 1)

`evaluate_program(path, default_spec("lsh","step"), "full", cache=False)`: build in the sandbox subprocess (nominal + 2 alternate angle pairs = 3 specs), then `evaluate_circuit` (three verdicts, metrics, measured T of the synthesised rotations), 24-25 qubit register with the outer qubits as controls.

| program | key (CX, T(1e-6), depth_CT, qubits) | `evaluate_program`, warm cache, s | first call in process, s | cold pygridsynth, first call, s | build (subprocess), s | `evaluate_circuit`, s | verdict-level `evaluate` (nominal), s | RSS, MB |
|---|---|---|---|---|---|---|---|---|
| headline `compress/programs/lsh/F3/005-alpha-early-walk22.py` (r05-F3-005) | (68, 1396, 3210, 24) | **1.183** [1.173, 1.200] (n=25) | 1.941 [1.928, 1.950] | 2.096 [2.091, 2.350] (n=5; later calls 1.185) | 0.437 [0.430, 0.457] | 0.746 [0.743, 0.908] | 0.230 [0.229, 0.241] (method `physical`, 2 outer bits read) | 258 |
| round-0 wrapped seed `seed/005-wrap_sn_headline.py` (r00-seed-005, round-0 headline) | (71, 1118, 2276, 25) | **1.065** [1.059, 1.096] (n=25) | 1.807 [1.798, 1.811] | 2.232 [2.226, 2.239] | 0.431 [0.429, 0.438] | 0.632 [0.629, 0.652] | 0.197 [0.196, 0.198] (`inner_span`) | 255 |
| round-0 general `seed/000-general.py` (reference) | (94, 598, 880, 31) | 1.052 [1.043, 1.103] (n=25) | 1.810 [1.807, 1.878] | 2.073 [2.065, 2.080] | 0.433 [0.431, 0.442] | 0.617 [0.614, 0.641] | 0.198 [0.197, 0.203] (`inner_span`) | 254 |

IQR of the 25 warm headline calls: [1.180, 1.186] s. All verdicts `ok`, operator-norm error $1.4\times10^{-14}$ (headline), Gauss residual $5.7\times10^{-16}$.

M7 equivalent: `evaluate_program` did not exist for LSH at milestone 7 (the registry entry `lsh` of the shared loop arrived with prompts/008, so a milestone-7 tree cannot run it). The closest equivalent is the verdict-level `evaluate` of one circuit, 0.15-0.19 s in report 302; the three LSH programs above give 0.197-0.230 s at HEAD, and the like-for-like A/B in section 5 says +16-21 % for the same call.

## 2. `python -m su2plaq.lsh.loop seed` wall time (item 2)

Run with `--root <fresh empty scratch directory>` under `taskset -c 0-8 tools/run-capped`. The CLI takes `--root`, so everything it writes (43 files per run: archive, programs, attempts, round-000.json, stop.json, certificate) goes to the scratch root; `results/compress/lsh` and `compress/` were not touched. The gridsynth cache is the only shared, gitignored state.

| variant | runs | wall, s | peak RSS, MB | note |
|---|---|---|---|---|
| `seed`, with Lean certificate of the best seed, warm gridsynth cache | 5 | **23.24** [23.14, 23.34] | 826 (the compiled Lean checker, a child process) | round-0 best key (71, 1118, 2276, 25), 10 valid, 0 invalid, Lean 0.87 s in-run |
| `seed --no-lean`, warm | 5 | 22.55 [22.54, 22.57] | 308 | same key |
| `seed`, with Lean, cold pygridsynth cache (cache redirected in-process) | 3 | 59.63 [59.51, 59.71] | 822 | cache directory filled with 1432 words; the cold-cache cost is 36 s |

Both variants reproduce the committed round-0 key. There is no earlier `seed` timing to compare with (new baseline).

## 3. Robust headline wall time (item 3)

Robust key over the 20 angle pairs of the committed angle set (seed 20261107), `robust_metrics("lsh","step",path)`: 21 builds (20 pairs + nominal) in the sandbox subprocess plus the measured T(1e-6) and depth_CT at every pair.

| quantity | value, s | notes |
|---|---|---|
| `robust_metrics` of the headline r05-F3-005, warm cache | **1.573** [1.551, 1.602] (n=25; first call in process 2.499 [2.486, 2.520]) | key (68, 28348, 0, 63378, 24), identical to the committed `results/compress/lsh/robust.json`; skeleton equal, angle-linear |
| same, cold pygridsynth cache | first call **5.672** [5.641, 5.674] (n=5); later calls 1.562 | cold cost 4.2 s for the 20 pairs |
| `robust_metrics` of the round-0 wrapped seed r00-seed-005, warm | 1.297 [1.290, 1.322] (n=15; first 2.240) | key (71, 22480, 0, 46384, 25) = committed |
| `loop headline --refresh` (all 28 ranked entries + 1 unrankable, scratch root copy, cache deleted so everything is recomputed) | 37.53 [37.51, 37.60] (3 runs), 262 MB | headline id r05-F3-005, key (68, 28348, 0, 63378, 24) |

No earlier measurement exists (new baselines).

## 4. Certificate time (item 4)

`python -m su2plaq.lsh.loop certify-headline --root <scratch copy of the LSH loop state>` under `taskset -c 0-8 tools/run-capped`, 5 runs. The scratch root has the committed `robust.json` cache (so the headline selection is cached), no `results/lsh/certs` and an empty `lean/certs`, so every run exports a new certificate and runs the compiled checker. Wall time includes python start-up, archive load, headline selection, the sandbox rebuild of the program, export and check, and writing the theorem file.

| quantity | value |
|---|---|
| CLI wall | **1.870** [1.868, 1.881] s |
| certify (export + check) as reported by the loop | 0.890 [0.888, 0.893] s |
| of which compiled checker `su2plaq_cert_lsh check` | 0.599 [0.598, 0.600] s |
| status | `certified` in 5 of 5; checker sha256 `16b3278f...` (as in 302); `git_dirty` false |
| certificate `lsh-step-o1-dd63c8bf6fad.json` against the committed one | all fields equal except `provenance`; within `provenance` only the volatile fields `git_commit` (committed `1e765f1`, run `513eb51`) and `export_seconds` differ (`_same_up_to_volatile` returns True). The theorem file `lean/certs/lsh-best-step.lean` differs only in the comment line with the git commit and the embedded certificate sha256 (which covers the volatile provenance); the committed files were not touched |
| peak RSS | 824 MB (checker process) |

The general-step certificate of the M7 benchmark (`lsh_lean_cert`, 31 qubits, 165 KiB) is 1.694 [1.685, 1.699] s at HEAD (export 0.639, check 1.049), against 1.976 [1.878, 2.092] s in 302 (export 0.726, check 1.261): 14 % faster, status `certified` in 5 of 5. The headline certificate is cheaper because the headline circuit is a 24-qubit, 215-gate circuit.

## 5. The M7 benchmark quantities again (item 5)

Same worker and tasks as 302 (`bench_worker_m4.py`, copied with a source-path switch), 5 fresh processes per task and per tree, HEAD and milestone-7 source interleaved on CPU 0. "ratio" = HEAD median / milestone-7-source median (same session, same machine); "vs 302" = HEAD today / value stored in report 302.

Invalidated first attempt: the first run of this phase (`raw_m7tasks_INVALID_AB_head_vs_head.json`) pointed the M7 tree at a non-existent directory, so it silently compared HEAD with HEAD (all ratios 1.00). I noticed because `m7_results.py` showed 817 vs 279 MB and re-ran the phase with the correct path; the worker now records `su2plaq.__file__` per run and the new raw file shows `scratch/bench-m8/m7tree/src/...` for the control. Only the corrected data are used below.

| quantity | HEAD first / later, s | milestone-7 src first / later, s | ratio first / later | vs 302 first / later |
|---|---|---|---|---|
| `LSH()` build | 0.1533 / 0.0444 | 0.1536 / 0.0446 | 1.00 / 1.00 | 0.88 / 0.86 |
| `target("UB")`, `target("step")` later | 0.0177 / 0.0094; 0.0180 / 0.0181 | 0.0180 / 0.0094; 0.0180 / 0.0180 | 0.98-1.00 / 1.00 | 0.92-0.94 / 0.91-0.93 |
| `build_UB` (cold coupling table / later) | 0.0457 / 0.0015 | 0.0457 / 0.0015 | 1.00 / 1.01 | 0.86 / 0.99 |
| `build_step` order 1 / 2 | 0.0016 / 0.0016 | 0.0016 / 0.0016 | 0.98-1.00 / 1.01-1.02 | 0.95-0.97 / 0.98-0.99 |
| **`evaluate` $U_E$** | 0.1889 / **0.1736** | 0.1522 / 0.1437 | 1.24 / **1.21** | 1.11 / 1.14 |
| **`evaluate` $U_B$** | 0.5496 / **0.1982** | 0.5098 / 0.1679 | 1.08 / **1.18** | 0.96 / 1.08 |
| **`evaluate` step order 1** | 0.5472 / **0.1977** | 0.5128 / 0.1686 | 1.07 / **1.17** | 0.95 / 1.04 |
| **`evaluate` step order 2** | 0.5457 / **0.1986** | 0.5092 / 0.1681 | 1.07 / **1.18** | 0.95 / 1.04 |
| **`evaluate` wrapped `flags4` / `pairs9` / `general7`** | 0.547 / 0.198; 0.544 / 0.198; 0.546 / 0.199 | 0.512 / 0.168; 0.509 / 0.167; 0.513 / 0.172 | 1.06-1.07 / **1.16-1.19** | 0.95-0.99 / 1.04-1.09 |
| `synthesize` $U_E$ / $U_B$ / step 1 (later) | 0.0031 / 0.0034 / 0.0048 | 0.0031 / 0.0034 / 0.0048 | 0.99-1.00 | 0.87-0.97 |
| `synthesize` first call $U_E$ / $U_B$ / step 1 | 0.355 / 0.442 / 0.462 | 0.354 / 0.440 / 0.463 | 1.00 | 0.83-0.92 |
| **synthesised $U_E$ / $U_B$ / step 1 `evaluate`, later** | 0.2421 / 0.2339 / 0.2624 | 0.2117 / 0.2043 / 0.2330 | **1.14 / 1.15 / 1.13** | 1.04 / 0.99 / 1.01 |
| Lean certificate of the general step (`certify`, 31 qubits) | 1.694 [1.685, 1.699] | not run (the extracted tree has no compiled checker) | - | 0.86 |

Spread of every HEAD median: max/min within 1-3 % (full min/max in `summary.json`, `phases.m7tasks.rows`). RSS is identical between the trees (192-250 MB for the evaluate tasks, 327 MB for the certificate task).

Scripts, loop quantities and suites:

| quantity | runs | HEAD | like-for-like control | 302 | verdict |
|---|---|---|---|---|---|
| `scripts/m7_results.py --out <scratch>` with HEAD's script | 5 | 9.59 [9.57, 9.66] s, 825 MB | the script itself changed since M7 (+20 lines, step 8.A2: a Lean certificate of the general step; the 825 MB is the compiled Lean checker child process, not python) | 9.20 s, 281 MB | +4 % vs 302 (not like-for-like, see next row) |
| `m7_results.py` of milestone 7 on HEAD source / on milestone-7 source | 5 + 5 | 8.71 [8.71, 8.73] s, 281 MB | 7.99 [7.94, 8.04] s, 279 MB | - | **+9.0 %** (below 10 %; the evaluate share of the script is 5.4 s -> 6.2 s, +14 % by cProfile) |
| compression round: `loop round --round 5 --evaluate --no-lean --root <scratch root with round-5 entries removed>`, 3 programs (F1-004, F3-005, F5-005), warm cache | 5 | 5.69 [5.66, 5.73] s, 259 MB | reproduces the committed best key (68, 1396, 3210, 24) | no LSH baseline; spinnet round 5 was 6.64 s (report 301) | new baseline |
| same, cold pygridsynth cache | 3 | 5.94 [5.94, 5.95] s | the round needs only 10 distinct rotation angles | - | new baseline |
| `pytest tests/acceptance/m7` (29 tests), `-n 6`, CPUs 0-8 | 6 | 8.08 [6.94, 19.47] s (runs: 19.5, 7.4, 7.9, 10.7, 6.9, 8.2) | - | 12.08 [12.05, 12.22] s | not slower (302 ran on CPUs 14-19, E-cores included); the 19.5 s first run is a cold start (disk cache) |
| `pytest tests/unit` (1224 tests; 943 at M7), `-n 6`, CPUs 0-8 | 2 | 393 [371, 416] s | - | 504.9 [484, 574] s (943 tests) | not comparable (more tests, different cores); no slowdown signal |

## 6. Optional: the m8 acceptance suite and the G2 share (item 6)

`taskset -c 0-7 tools/pytest-safe -n 2 tests/acceptance/m8 -m "slow or not slow"`, 4 runs: 108.9, 109.1, 109.5, 110.1 s wall (median 109.3 s), all `33 passed`, peak RSS 6.76 GB (the Lean process tree).

- `test_M8_G2_best_and_headline_second_engine_aer`: 106.4, 106.8, 107.3 s call time (3 logged runs), i.e. 97 % of the wall time and 50.5 % of the summed call durations (210.9 s). With `-n 2` the suite cannot be faster than G2.
- Next: `test_M8_H2_headline_selection_on_seed_round` 25.9 s, `test_M8_S4_round_one_dry_run_briefs_and_stop_state` 24.7 s, `test_M8_S3_seed_round_dry_run` 23.6 s (the seed-round dry runs). All other tests are under 5 s.
- No earlier m8 timing exists (new baseline). The `-m "slow or not slow"` expression selects everything (the project's usual way to include slow tests).

## 7. Physics output unchanged

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| headline key and metrics | (68, 1396, 3210, 24), 22 rotations, $T_{\rm fixed}=24$, depth 96 | same | exact | PASS |
| robust key of the headline | (68, 28348, 0, 63378, 24) | same, in all 25 timed calls and in `loop headline --refresh` | exact | PASS |
| round-0 seed round | best key (71, 1118, 2276, 25), 10 valid | same in 13 of 13 runs | exact | PASS |
| round 5 re-evaluation | entries r05-F1-004, r05-F3-005, r05-F5-005, best (68, 1396, 3210, 24) | same in 8 of 8 runs | exact | PASS |
| operator-norm error of the headline verdict | $\le 10^{-10}$ | $1.44\times10^{-14}$, Gauss residual $5.7\times10^{-16}$ | $10^{-10}$ | PASS |
| Lean certificate of the headline | `certified`, content identical to committed up to volatile provenance | `certified` 5 of 5, only `git_commit`, `export_seconds` differ | - | PASS |
| `m7_results.py` outputs (written to scratch) | numerically as before | not diffed field by field in this report (the tester 446 full run covers it); status of the Lean block `certified` | - | not rechecked |
| `check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS ... acceptance-v23` | - | PASS |
| suites during the benchmark | all pass | m7 29 passed (6 of 6), m8 33 passed (4 of 4), unit 1224 passed (2 of 2) | - | PASS |

## Flags (more than 10 % slower than the previous value)

1. **Verdict-level `evaluate` per circuit (all LSH `evaluate` rows of section 5): +16 to +21 % later-call (+6-8 % first call, which is dominated by lazy Qiskit set-up), and +13 to +15 % for the synthesised-circuit `evaluate`**, against the milestone-7 source in the same session; $U_E$ +21 % (0.144 -> 0.174 s). Likely cause (guess supported by profile): `evaluator.py` now forms the span leak $\|S\|_2$ for every call where the physical span is not the whole code space (prompts/008 section 5): `cProfile` of 5 `evaluate(U_B)` calls shows `eigvalsh` of a 433x433 matrix (14 ms per call) and 2 SVD calls (14 ms each) that the milestone-7 code does not have; the evaluator's own time rose from 8 ms to 22 ms per call. `d["local_basis"]` is documented as cached on the encoding data, but the SVD calls reappear in every call, so the cache may not persist across calls (guess, not tested). Against report 302 the same rows are +4 to +14 % only, because the whole machine is about 9 % faster today than in the 302 session; use the A/B ratio.
2. **`m7_results.py`, HEAD script: 9.59 s and 825 MB against 9.20 s and 281 MB in 302** (+4 % time, +194 % RSS). Cause: a code change in the script itself since milestone 7 (step 8.A2 added the Lean certificate; 0.95 s and the compiled checker's 800 MB). With the milestone-7 script the difference is +9.0 % time, +0 % RSS, which is inside the threshold. Not a regression of production code beyond item 1.
3. Not flagged but worth knowing: the headline `evaluate_program` is 1.18 s warm and 2.10 s cold, the robust headline 1.57 s warm and 5.67 s cold, the seed round 23 s warm and 60 s cold, round 5 about 5.7 s. Under heavy load these scale with the evaluator, so a +17 % evaluator slowdown is roughly +8 % on a full `evaluate_program` (three verdicts of a 1.18 s call).

## Files touched by my runs

- Tracked file rewritten: `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` (provenance rewrite by the m7/m8/unit pytest runs; known). Restore with `git checkout -- results/spinnet/certs`. Nothing else tracked changed (`git status --short` at the end: that file and the new untracked `results/benchmarks/lsh-m8/`).
- Untracked, new: `results/benchmarks/lsh-m8/` (scripts, raw JSON, `summary.json`, three pytest logs, the invalidated first A/B file), `reports/benchmarks/306-lsh-milestone-8.md`. A transient `lean/Lemma_*.lean` appeared during the unit run and was gone afterwards.
- Gitignored state: `compress/cache/gridsynth` was read (warm runs) and may have been extended by a few entries; all cold runs used scratch cache directories under `scratch/bench-m8/`. `scratch/bench-m8/` (scratch roots, the milestone-7 tree, probes) is gitignored.
- `results/lsh/certs/`, `results/compress/lsh/`, `lean/certs/`, `compress/` were not written: every loop, certify and round run used a `--root` scratch copy.

## Commands (all from `/home/digimonk/Projects/su2qc-encoding`, env as above)

```
BENCH_RUN=scratch/bench-m8/run1 results/benchmarks/lsh-m8/scripts/run_all_m8.sh evalprog robust seed certify
BENCH_RUN=scratch/bench-m8/run1 results/benchmarks/lsh-m8/scripts/run_all_m8.sh m7tasks scripts suite_m7 suite_m8 suite_unit
BENCH_RUN=scratch/bench-m8/run2 results/benchmarks/lsh-m8/scripts/run_all_m8.sh m7tasks          # corrected A/B (run1's m7tasks invalidated)
BENCH_RUN=scratch/bench-m8/run2 results/benchmarks/lsh-m8/scripts/run_all_m8.sh round m7results_ab suite_m7 suite_m8
BENCH_RUN=scratch/bench-m8/run3 ... suite_m8 suite_unit ; BENCH_RUN=scratch/bench-m8/run4 ... suite_m8
python results/benchmarks/lsh-m8/scripts/assemble_m8.py results/benchmarks/lsh-m8 scratch/bench-m8/run{1,2,3,4}
git archive milestone-7 src | tar -x -C scratch/bench-m8/m7tree      # control source tree
```

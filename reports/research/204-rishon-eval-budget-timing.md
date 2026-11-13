# Research 204 — rishon track: the evaluator's wall-clock budget and the Qiskit L3 seed in the replay of round 0

- Date: 2026-11-13 · Author: planner · Git commit at writing: `77b68ce` (branch `merge-desktop-tracks`, working tree with the rishon builder's uncommitted C1 files)
- Prompt in force for track R: `prompts/204-rishon-det-term-amendment.md` on `prompts/203-rishon-m6-plan.md`. This note backs the erratum `prompts/205-rishon-s3-eval-budget-erratum.md`.
- Trigger: coordinator request. The rishon builder rehearsed step C2 (replay of rounds 0–4 under the 10 % prune cap) on a scratch copy; the seed `r00-seed-qiskit_l3` came out `eval_budget`, and the locked slow test `tests/acceptance/m6/test_rishon_m6_seeds.py::test_M6_S3_round0_recorded` allows only `ok` or `pruning_bound` for it.
- Related: `prompts/008-merged-repo-consolidation.md` §3.3, §8, §12 (the consolidation window in which C2 runs), `docs/METHODS-rishon.md` R10, R15, `reports/research/203-rishon-det-term-prune-cap.md` §3.6.
- Machine: omnicommander (Intel i7-12700KF), logical CPUs 0–1, jobs under `tools/run-capped`. Environment: conda `coding`.
- No literature was needed: no numerical method changes. This note is about a time limit and a test.

Words used. *Seed*: a circuit the loop starts from (round 0), not written by a proposer. *Windowed Qiskit L3*: the general circuit cut into windows of 32 gates, each optimised by Qiskit's level-3 transpiler. *Nominal / alternate pairs*: the three angle pairs $(\alpha,\beta)$ at which every candidate must be exact: $(0.37,0.61)$, then $(0.91,0.23)$ and $(1.70,1.00)$. *Verdict*: the evaluator's judgement of one circuit at one pair. *`eval_budget`*: the verdict "not judged within the time limit". *Wall time*: elapsed clock time. *Logical CPU / SMT sibling*: this processor shows each fast core as two logical CPUs that share the core's hardware; a job on one slows a job on the other. *Replay*: re-running stored rounds under a new evaluator hash (`prompts/204` §6.2).

## 1. The rule in the code
`src/su2plaq/rishon/compress/evaluate.py::evaluate_circuit` (a copy of the shared `src/su2plaq/compress/evaluate.py::evaluate_circuit`): the nominal verdict runs under `_time_limit(spec.eval_budget_s)` with `eval_budget_s` $=300$ s; each alternate verdict under `_time_limit(min(120.0, spec.eval_budget_s))` $=120$ s. `_time_limit` is a `SIGALRM` timer on **elapsed** time (`signal.ITIMER_REAL`). A timeout gives `valid = False`, `reason = "eval_budget"`. Documented in `prompts/203` §11 and METHODS-rishon R10 ("wall ≤ 300 s (nominal) and ≤ 120 s per alternate pair").

The code already treats this verdict as a fact about the run, not about the circuit: `evaluate_program` never caches a result with reason `eval_budget` or `build_timeout`, and `prompts/008` §12 lists "evaluation budget under machine load (reason `eval_budget`; re-run that archive alone on idle cores — a timeout is never cached)" as a known replay risk.

After step B5 of `prompts/008` (locked, acceptance-v18) `rishon/compress/evaluate.py` re-exports the shared `evaluate_circuit` (§3.3 there), so the 120 s rule will be the shared one for all five encodings.

## 2. Measurements
Each number is the wall time of one call `su2plaq.rishon.compress.evaluate._one_verdict(circuit, spec, "full", <no limit>)`: all 1296 inner codes plus the Gauss sample of 273 physical states, i.e. exactly the work the evaluator times. One process, one thread, pinned to one logical CPU. Evaluator hash `a4dbd16c…` in all runs.

| Run | Seed | Nominal | Alternate 1 | Alternate 2 | Conditions |
|---|---|---|---|---|---|
| Builder, `l3time.py` (scratchpad `l3time.log`, 2026-11-13 08:19) | `qiskit_l3` | 151.8 s | 140.0 s | 134.7 s | "one loaded core"; peak memory 1.87 GB |
| Planner, `scratch/planner/p205/time_seed_pairs.py qiskit_l3` → `l3.json` (08:39–08:55) | `qiskit_l3` | 429.0 s | 249.4 s | 226.2 s | CPU 0; 1-min load average 16–32 at the start, 8 at the end; its SMT sibling (CPU 1) busy until 08:45, then free of my jobs; peak 1.96 GB |
| Planner, same script, `general` → `general.json` | `general` (ccx ladders) | 40.6 s | 33.9 s | 37.6 s | CPU 1, sibling busy with the L3 run; load 16–32; 0.81 GB |
| Planner, same script, `general-rccx` → `rccx.json` | `general-rccx` | 58.6 s | 51.7 s | 52.5 s | CPU 1, sibling busy; load 20–22; 0.82 GB |

Process CPU time equals wall time within 1 % in every planner row, so the processes were not waiting for a CPU: the same computation simply ran slower (shared core, shared memory bandwidth and cache, clock frequency).

Physics of the L3 seed, measured without a time limit (planner run): at the three pairs `ok`, `certified`, `op_norm_error` $4.13$, $4.08$, $4.18\times10^{-12}$ (tolerance $10^{-10}$), `dropped_total` $3.79$, $3.74$, $3.84\times10^{-12}$ (cap $10^{-11}$), Gauss residual $\le1.5\times10^{-14}$ (tolerance $10^{-10}$), gate skeleton identical at the three pairs. The circuit is exact; only the clock decides its verdict.

What the numbers say:
1. **The same verdict took 152 s and 429 s on the same machine within one hour** (factor 2.8; alternates factor 1.7–1.8). Against a fixed limit this is the difference between `ok` and `eval_budget`.
2. The L3 seed is the only round-0 candidate near a limit. Alternates: 135–249 s against 120 s (ratio 1.1–2.1 above). Nominal: 152–429 s against 300 s (0.5–1.4). The ladder seeds have margins of at least 2.0 under the heaviest load measured (59 s against 300 s; 53 s against 120 s; `general` 41 s and 38 s). Rounds 1–4 take 137–160 s each for all their programs together (builder rehearsal, `round_wall_s`).
3. Likely reason the L3 seed is slow (not profiled): it is a flat circuit of 24 438 basis gates with 3 458 bare Hadamards; the ladder seeds are 4 289–4 561 instructions in which the engine treats each macro `ccx` / `ccz` as one non-branching gate (METHODS-rishon R11, correction).

Builder rehearsal of the whole replay (scratchpad `rehearsal_root/results/compress/rishon/replay-204.json`, on a scratch copy, commit `a36d829` + working tree): 19 entries; the 16 previously valid ones keep their keys (`key_equal` true for all, `lost == []`); newly valid `r00-seed-001` (general-rccx, key $(6874,17694,31954,58)$) and `r00-seed-002` (general-mcx, $(7360,18180,32428,58)$); `r00-seed-qiskit_l3`: `eval_budget`, with the nominal verdict recorded (`ok`, certified, `op_norm_error` $4.13\times10^{-12}$, `dropped_total` $3.79\times10^{-12}$), `alt_ok == []`, `skeleton_equal` true, metrics present (9 688 CX, $T$ estimate 19 046, not measured). Best unchanged: `r04-F1-004` $(228,846,1417,53)$. Wall 2 822 s (round 0: 2 220 s).

## 3. Machine facts that matter for any timed verdict here
`lscpu -e`: logical CPUs $(0,1),(2,3),\dots,(14,15)$ are pairs on the eight fast cores (4.9–5.0 GHz); CPUs 16–19 are four slower cores (3.8 GHz, no sibling). "Cores 0–1" is therefore one physical core. A timed job should have a fast core to itself (its sibling left idle) and should never run on CPUs 16–19.

## 4. Options compared

| | (a) raise the rishon alternate budget (e.g. 120 s → 300 s) | (b) erratum: S3 also accepts `eval_budget` for `qiskit_l3` | (c) replace seconds by a deterministic work count |
|---|---|---|---|
| Makes the L3 verdict reproducible? | No. Nominal measured 429 s > 300 s today; any fixed number of seconds can be crossed by load | The verdict stays load-dependent, but **nothing else depends on it** (below), and the test says so | Yes |
| Hashed files | `rishon/compress/evaluate.py` changes now; after `prompts/008` B5 that function is the shared one, so the change must move into shared code or into a new registry field of a locked plan | none | shared `evaluate/sparse_sim.py`, `evaluate/evaluator.py`, `compress/evaluate.py`; a new budget field changes the spec text and `TaskSpec.sha256()` of every encoding |
| Rule change for the loop | yes (R10) | no | yes, all five tracks; the `aer_mps` fallback engine has no such counter |
| Locked tests touched | none now; `m2c` registry tests if it becomes a registry field | one branch of `M6_S3` | `m2c`, `m6/test_rishon_m6_spec.py` (pins `eval_budget_s == 300.0`), spec tests of every track |
| Cost | builder step + still fragile | planner only | a cross-track plan change inside the 008 window, for one baseline row |

Why nothing depends on the L3 verdict: (i) it is a circuit-valued baseline without a program file, so it is never a parent (`rishon/compress/round.py::_seed_candidates`); (ii) it has 9 688 CX against 6 874 for the rccx seed, so valid or not it is not the round-0 best, and the global best is 228 CX; (iii) `test_M6_G1`, `G2`–`G4`, `G5` and `m2c::test_M2C_G1[rishon-step]` do not require it to be valid (G5: "a candidate is newly valid only if its old reason was `pruning_bound`" holds either way); (iv) the headline rule ranks valid archived programs only.

Decision: **(b)**, restricted to that one seed and to a timeout at an alternate pair. A timeout at the nominal pair is not accepted: the row would then carry neither a verdict nor gate counts (`metrics` is empty), and Report 6 needs the L3 counts. (c) is the only option that makes time-limit verdicts reproducible in general; it is left as an optional decision for Digonto (not recommended now).

## 5. Check of the amended test
`scratch/planner/p205/check_s3_erratum.py <rehearsal_root> <work dir>` calls the amended `test_M6_S3_round0_recorded` on the builder's rehearsal root and on 14 mutated copies of its `round-000.json` (15 cases, about 1 minute):

| Case | Expected | Got |
|---|---|---|
| as rehearsed (`eval_budget`, nominal exact, `alt_ok == []`) | pass | pass |
| L3 `ok` with both alternates | pass | pass |
| L3 `eval_budget` after one finished alternate | pass | pass |
| L3 `pruning_bound` with `dropped_total` $3\times10^{-11}$ (old branch) | pass | pass |
| L3 timeout at the nominal pair (no verdict, no metrics) | fail | fail |
| L3 `eval_budget` but two alternates recorded | fail | fail |
| L3 `eval_budget`, a finished alternate not ok | fail | fail |
| L3 nominal `op_norm_error` $10^{-9}$ | fail | fail |
| L3 nominal not certified | fail | fail |
| L3 nominal `dropped_total` $2\times10^{-11}$ | fail | fail |
| L3 cheaper (6 000 CX) than the best valid seed | fail | fail |
| L3 reason `error` | fail | fail |
| general-rccx `eval_budget` | fail | fail |
| general `eval_budget` | fail | fail |
| L3 `eval_budget` but `valid: true` | fail | fail |

With the amended file in the tree and `LOCK.json` not yet updated, every acceptance run aborts with `ACCEPTANCE LOCK BROKEN` (seen once, then undone). The tree was therefore put back to the locked file (`python tools/check_lock.py` → `LOCK OK`); the change is delivered as `scratch/planner/p205/s3-erratum.patch` (sha256 `e4feda64…`, `git apply --check` passes) and inline in `prompts/205` §4. sha256 of the amended test file: `f21a2042ae12f1fd53083f9bca5bd113f147ca062fb5f86861ae3d4bfec3c503`.

## 6. Files of this run
`scratch/planner/p205/time_seed_pairs.py`, `l3.json`, `general.json`, `rccx.json` (+ `.log`); `check_s3_erratum.py`; `s3-erratum.patch`; `test_rishon_m6_seeds.py.after`. Nothing under `src/`, `results/`, `compress/` or `tests/` was left changed.

# Report 021 — M1 gate, mode `full` (steps 1.9-pre and 1.9 included)

- Date: 2026-11-05
- Git: `b6d5f50` (acceptance-v5), working tree dirty = steps 1.9-pre (`src/su2plaq/evaluate/evaluator.py`, `tests/unit/test_evaluator_unit.py`) and 1.9 (`scripts/m1_results.py`, `results/twelve/*`, `tests/unit/test_m1_results_script.py`)
- Plan in force: `prompts/005-relative-prune-cap.md` (+ 002, 003, 004)
- Related: reports/tests/014–020
- Raw numbers: `results/tester_m1_gate_full.json`; scratch scripts in `scratch/tester_m1gate/` (gitignored)

## Verdict: PASS (no failures; 31 m2 tests PENDING as allowed at the M1 gate)

## Commands
```
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "evaluate"
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest --collect-only -q tests/acceptance
pytest -n auto -q tests/acceptance/m0 tests/acceptance/m1          # incl. slow, 197 s
pytest -n auto -q tests/acceptance/m2 ; pytest -n auto -q tests/unit
grep -rn TOL_PRUNE src tests
python scratch/tester_m1gate/prune_indep.py        # independent prune checks
python scratch/tester_m1gate/counts_indep.py       # independent counts + pygridsynth T
python scratch/tester_m1gate/{inner_ue,outer_gauss}.py   # independent synthesised-UE error/Gauss
PYTHONPATH=src python scripts/m1_results.py --out /home/digimonk/Projects/su2qc-encoding/scratch/tester_m1gate/twelve_abs
```

## 1. Gate
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `check_lock.py` | LOCK OK | LOCK OK | – | PASS |
| `acceptance-check` | matches acceptance-v5 | PASS | – | PASS |
| collect-only | 88 tests, clean | 88 collected | – | PASS |
| m0 + m1 acceptance incl. slow (PENDING = FAIL) | all pass | 56 passed (m0 34, m1 22), 0 failed, 0 pending, 197 s | exact | PASS |
| m1 V1, V2 (`test_evaluator_prune.py`) | pass | pass | locked | PASS |
| m2 acceptance | PENDING only | 1 passed, 31 failed, all 31 are `PENDING: NotImplementedError: default_spec is not built yet` | – | PENDING 31 (allowed) |
| unit | pass | 166 passed (59 s) | – | PASS |
| `grep -rn TOL_PRUNE src tests` | no use | one hit: `tests/unit/test_evaluator_unit.py:440` `not hasattr(ev, "TOL_PRUNE")` (the assertion that it is gone) | – | PASS |

## 2. Step 1.9-pre (relative prune cap, independent construction)
Own circuit (not the acceptance-test code): $k$ gates `u(2δ,0,0)` on `d[0]`, $\delta=\tfrac12\,\texttt{PRUNE\_REL}$, evaluated against the identity target; expected certified bound $d_{\rm tot}=25\,k\sin\delta$.

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| planner circuit $k=250$, $\delta=5\times10^{-15}$: `dropped_total` | $3.125\times10^{-11}$ | $3.1250000000000067\times10^{-11}$ | $10^{-6}$ rel. | PASS |
| default $\texttt{tol\_err}=10^{-10}$ | `pruning_bound` (cap $10^{-12}$) | `pruning_bound`, `failing_inputs = [("dropped_total", 3.125e-11), ("prune_cap", 1e-12)]` | exact | PASS |
| flip at $\texttt{tol\_err}=d_{\rm tot}/10^{-2}\times f$, $f=1.0001/0.9999$ | ok / pruning_bound | ok / pruning_bound | $\pm10^{-4}$ | PASS |
| same for $f=1.01/0.99$ and $1.2/0.8$ | ok / pruning_bound | ok / pruning_bound (both pairs) | – | PASS |
| second circuit $k=100$, $\delta=3\times10^{-15}$: total | $7.5\times10^{-12}$ | $7.49999999999998\times10^{-12}$ | $10^{-6}$ rel. | PASS |
| its flip at $f=1.0001/0.9999$ | ok / pruning_bound | ok / pruning_bound | – | PASS |
| two outer bits read (`cry` on `o[0]` ×60, on `o[1]` ×150; groups with 0/60/150/210 drops): `dropped_total` | max over groups $=25\cdot210\sin\delta=2.625\times10^{-11}$ (sum would be $5.25\times10^{-11}$) | $2.6250000000000203\times10^{-11}$, `n_blocks=3` (the 4th group has no physical outer pattern), `max_dropped_l2=1.05\times10^{-12}$ | $10^{-6}$ rel. | PASS |
| per-group bounds from `sparse_sim.run_batch` directly | $25 n\sin\delta$ | 0, $7.5\times10^{-12}$, $1.875\times10^{-11}$, $2.625\times10^{-11}$ | exact to $10^{-14}$ rel. | PASS |
| validity vs unpruned run (`PRUNE_REL=0`): true $\|M_{\rm pruned}-M_{\rm unpruned}\|_2$ per group | $\le$ group bound | 0, $3.0\times10^{-13}$, $7.5\times10^{-13}$, $1.05\times10^{-12}$ ($\le$ bounds, ratio 25) | – | PASS |
| unpruned verdict `op_norm_error` $\le$ pruned verdict `op_norm_error` | yes | $9.16\times10^{-13}\le2.625\times10^{-11}$ | – | PASS |

(`n_blocks=3` instead of 4: one combination of the two read outer bits does not occur among the 433 physical outer patterns; the maximum is the group with both bits set.)

## 3. Step 1.9 (results regeneration)
`scripts/m1_results.py --out <dir>` was re-run (≈ 6 min on 1 thread). Diff against `results/twelve/{UE,UB,step}.json`: **every number bit-identical** (including all verdict fields, t-tables, Paulo comparison, `dropped_total`, errors). Only `seconds` fields, `provenance.timestamp_utc`, and the `files.*` path strings (different `--out`) differ. The 5 `.qpy` and 5 `.qasm3` files are byte-identical (`cmp`). Provenance present: `git_commit` `b6d5f50`, `git_dirty` true, versions (python, numpy, scipy, qiskit, qiskit_aer, pygridsynth), platform, cpu_count, seeds, timestamp, `schema_version`, `params`, QPY sha256.

Independent recomputation (macro counts by hand and by `qiskit.transpile` of each macro; T per rotation by calling `pygridsynth.gridsynth_gates` directly on the angles extracted from the saved QPY; physics from `physical_vectors()`), 55 + 9 + 4 comparisons, all equal:

| quantity (JSON path) | independent value | JSON | result |
|---|---|---|---|
| UB CX: $8\cdot6+60\cdot3+50+10+3\cdot2$ (ccx, rccx, cx, cz, crx) | 294 | 294 | PASS |
| UB $T_{\rm fixed}$: $8\cdot7+60\cdot4+8+8$ | 312 | 312 | PASS |
| UB $n_{\rm rot}$ ($3\times$crx$\to 2$ rz) | 6 (angles ±1.22, ±0.61, ±0.305) | 6 | PASS |
| UE $n_{\rm rot}$, angles | 4 × $-0.2775=-3\alpha/4$ | 4 | PASS |
| UE $T_{\rm rot}$ at $\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$ | 176 / 256 / 328 / 416 | same | PASS |
| UB $T_{\rm rot}$ | 248 / 384 / 508 / 624 | same | PASS |
| UB $T_{\rm total}$ | 560 / 696 / 820 / 936 | same | PASS |
| step-1 $T_{\rm rot}$, $T_{\rm total}$ | 424/640/836/1040; 736/952/1148/1352 | same | PASS |
| step-2 $T_{\rm rot}$, $T_{\rm total}$ (n_rot 14) | 584/912/1180/1456; 896/1224/1492/1768 | same | PASS |
| UE outer row $T$ (n_rot 12) | 528 / 768 / 984 / 1248 | same | PASS |
| physics: histogram of $\dim S_o$ over 6561 patterns | {0:3408, 1:976, 2:1073, 3:392, 4:320, 5:280, 8:64, 9:32, 17:16}; 3153 supported; max 17 | same, all 9 bins | PASS |
| inner span rank | 625 | 625 | PASS |
| Paulo QPY: CX, T | 294, 1162 (= `refs/paulo` metadata) | 294, 1162 | PASS |
| Paulo verdict | ok, certified, block $2.905\times10^{-6}$ + leak $7.851\times10^{-6}$ = $1.076\times10^{-5}\le2\times10^{-5}$, Gauss $1.16\times10^{-10}$, aer_mps | same | PASS |
| our $U_B(\beta=1)$ vs Paulo's logical | CX 294 both; $T_{\rm fixed}$ 296 (Paulo logical) vs 312 (ours), $n_{\rm rot}$ 14 vs 6; $T_{\rm total}(10^{-6})$ 684 (ours) vs 1162 (Paulo compiled) | same | PASS |
| synthesised UE, own dense-ish propagation of the pygridsynth words (apply 2×2 words to the 433 physical states, project on the basis): physical block error | $9.7387\times10^{-5}$, $1.7318\times10^{-6}$, $1.6768\times10^{-9}$, $1.869\times10^{-12}$ | JSON `op_norm_error_physical` $9.7387\times10^{-5}$, $1.7318\times10^{-6}$, $1.6768\times10^{-9}$, $1.868\times10^{-12}$ | PASS (rel. ≤ 4e-4, last digit) |
| same, Gauss residual | $6.7956\times10^{-6}$, $1.1147\times10^{-7}$, $2.3693\times10^{-9}$, $1.9067\times10^{-11}$ | JSON $6.796\times10^{-6}$, $1.115\times10^{-7}$, $2.369\times10^{-9}$, $1.907\times10^{-11}$ | PASS |
| same, max per-state weight outside the code space | $1.66\times10^{-5}$, $2.73\times10^{-7}$, $5.8\times10^{-9}$, $4.7\times10^{-11}$ | JSON `leak_amplitude` $1.66\times10^{-5}$, $2.73\times10^{-7}$, $5.80\times10^{-9}$, $4.67\times10^{-11}$ | PASS |
| step-order-2 $\varepsilon=10^{-4}$ verdict (the prompts/005 target) | `ok` | `ok`, `op_norm_error` $5.774\times10^{-4}\le1.4\times10^{-3}$, `dropped_total` $3.88\times10^{-11}$, `max_dropped_l2` $2.63\times10^{-12}$, Gauss $6.6\times10^{-5}$ | PASS |
| all other exact / synthesised verdicts (UE, UB, step 1, step 2, 4 ε each, plus Paulo) | `ok`, certified | all `ok` and `certified`; `op_norm_error / tol_err` ≤ 0.48 | PASS |

### The outer-electric-row NaN (Gauss)
The `gauss_residual: NaN` values are **only** in the four *synthesised* verdicts of the outer row (`UE.json` `extra/outer_electric_row/metrics/t_table[*]/synth/verdict`). They are *not* because Gauss was switched off: `evaluate(..., gauss=True)` is the default and the script never passes `gauss=False`. Cause: the verdict is `ok=False, reason="writes_outer"` with message `gate h on (13,) is not diagonal on outer qubit(s)`. A Clifford+T word for $R_z$ on an outer qubit contains $H$, and the evaluator rejects any gate that is not diagonal on an outer qubit (the outer register is a control only), so `_early(...)` returns before any simulation (`op_norm_error=inf`, `gauss_residual=NaN`, `n_blocks=0`). The *exact-angle* outer row has a full verdict: ok, error $3.8\times10^{-15}$, Gauss $5.6\times10^{-16}$, 128 blocks. So there is no violation of the "gauss=True is mandatory" rule, but those four stored verdicts say "not ok" about a circuit that simply cannot be judged by this evaluator, and the stored JSON contains non-standard `Infinity`/`NaN`.

I computed the quantities myself for the synthesised outer-row circuits (12 words, product of single-qubit gates, 433 physical states, same projection as above; target `include_outer_electric=True`):

| $\varepsilon$ | Gauss residual | block error | max weight outside code space | budget $12\varepsilon+10^{-9}$ | within budget |
|---|---|---|---|---|---|
| $10^{-4}$ | $9.61\times10^{-6}$ | $2.76\times10^{-4}$ | $2.54\times10^{-5}$ | $1.2\times10^{-3}$ | yes |
| $10^{-6}$ | $1.58\times10^{-7}$ | $4.90\times10^{-6}$ | $4.17\times10^{-7}$ | $1.2\times10^{-5}$ | yes |
| $10^{-8}$ | $3.35\times10^{-9}$ | $4.74\times10^{-9}$ | $8.87\times10^{-9}$ | $1.21\times10^{-7}$ | yes |
| $10^{-10}$ | $2.70\times10^{-11}$ | $5.29\times10^{-12}$ | $7.13\times10^{-11}$ | $2.2\times10^{-9}$ | yes |

(The "weight outside code space" is a per-state norm, not the operator norm $\|X\|_2$, so block + leak is indicative, not the certified bound; with it, $\varepsilon=10^{-4}$ gives $3.0\times10^{-4}\le1.2\times10^{-3}$.) The $T$ totals of the outer row (528/768/984/1248) are unaffected.

## 4. Regression against reports 014–020: numbers that changed
- Changed (intended): step order 2, $\varepsilon=10^{-4}$: `pruning_bound` (report 020, `max_dropped_l2` $2.63\times10^{-12}>10^{-12}$) → `ok`. Its numbers are unchanged ($5.774\times10^{-4}$, $3.88\times10^{-11}$, $2.63\times10^{-12}$). Failing-input payload of a `pruning_bound` verdict changed from `("max_dropped_l2", v)` to `("dropped_total", v), ("prune_cap", cap)` (prompts/005).
- Unchanged (compared with report text): 015 (UE error $1.2\times10^{-13}$, $T$ 176/256/328/416, outer 528/768/984/1248); 016 (codec: unit tests green); 017/018 (UB $T$ 560/696/820/936, $\varepsilon=10^{-6}$ error $1.854\times10^{-6}\le6.0\times10^{-6}$, cx 294, $T_{\rm fixed}$ 312, depth 292); 019 (step exact $2.7\times10^{-13}$, cx 294, $T_{\rm total}(10^{-6})$ 952/1224, Paulo ok $1.0756\times10^{-5}$); 020 (all t-table rows incl. error_measured_sum 8.730e-5 etc., dropped values, Gauss). Paulo verdict took 78 s here (84 s in 019): no change in the physics result.
- No other number changed. `dropped_total` values do not change anywhere because every branching circuit has `n_blocks=1` (sum = max), as predicted in prompts/005 §2.

## Observations (not failures)
1. `scripts/m1_results.py --out` fails with `ValueError: ... is not in the subpath of <repo>` unless `--out` is an absolute path inside the repository (`qpath.relative_to(ROOT)`). The default path works; only affects re-running into a scratch directory. Guess: a plain `relative_to` without `.resolve()` / fallback. Non-blocking.
2. Outer-row synthesised verdicts are stored as failed (`writes_outer`, `inf`/`NaN`); see §3. Suggest either storing an explicit "not verifiable by this evaluator (H on outer qubit); verified separately: …" note, or leaving them out of the JSON. My numbers above can be cited. Non-blocking; no locked test covers the outer row.
3. Timing (1 thread per process, 12-core machine, contended during the m0+m1 run): m0+m1 acceptance 197 s, unit 59 s, results script ≈ 6 min.

## Failures
None.

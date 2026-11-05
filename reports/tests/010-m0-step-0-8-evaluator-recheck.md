# Tester report 010 — M0 step 0.8 evaluator, recheck after builder fixes (mode: step)

- Date: 2026-11-04
- Commit: `5c5f567` + uncommitted step-0.8 files (builder's F1/F4/F6 fixes in the working tree)
- Plans in force: `prompts/002-…`, `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md` (F2 is NOT tested here, as instructed)
- Related: reports/tests/009 (first 0.8 round), 007, 008
- Raw numbers: `results/evaluator_0_8_recheck_*.json` (seed 20261104); scripts: `tests/independent/evaluator_0_8/` (`adv1`..`adv8`, new `adv9_fuzz.py`)

## VERDICT: the code fixes PASS (F1, F6 confirmed fixed; no regression). The overall step verdict is FAIL on the lock rule: `acceptance-check` fails because three locked test files were edited after `acceptance-v2` (planner amendment, prompts/003) and not re-locked, and the amended E5 needs API that is not built yet.

## 1. Commands
```
pytest -n auto tests/unit                                    # 100 passed, 25.0 s
pytest -n auto -m "not slow" tests/acceptance/m0 / test_evaluator.py   # INTERNALERROR: ACCEPTANCE LOCK BROKEN
python tools/check_lock.py ; ~/.claude/bin/acceptance-check  # LOCK BROKEN / FAIL
git show acceptance-v2:tests/acceptance/m0/test_evaluator.py > scratch; pytest scratch   # locked E3-E5
pytest <scratch copy of working-tree test_evaluator.py>      # amended E5
python tests/independent/evaluator_0_8/adv{1..9}.py          # adversarial rerun (9 scripts in parallel)
```

## 2. Lock status (the blocking item)
`git status`: `tests/acceptance/m0/test_evaluator.py`, `m1/test_twelve_metrics.py`, `m1/test_twelve_paulo.py` are modified relative to `acceptance-v2` (not by me; the diff implements prompts/003: `tol_gauss`, `Verdict.tolerances`, `synth_tolerances`, E5 loosened to 1e-9 for aer_mps). Results:
- `pytest tests/acceptance/...` aborts at session start: `ACCEPTANCE LOCK BROKEN: changed: m0/test_evaluator.py, m1/test_twelve_metrics.py, m1/test_twelve_paulo.py`; `tools/check_lock.py` LOCK BROKEN; `acceptance-check` FAIL. So no acceptance test can be run in place and, by the rules, the verdict is FAIL until the coordinator re-locks (`acceptance-lock`, not my role).
- To still get numbers, I ran copies outside the tree: **locked (acceptance-v2) E3/E4/E5: 3 passed** (17.6 s, 6.8 s, 8.6 s). **Amended (working-tree) E5: FAILS** with `AttributeError: 'Verdict' object has no attribute 'tolerances'` at line 119 (also needs `tol_gauss=` in `evaluate` and `evaluator.synth_tolerances`); amended E3 and E4 are unchanged in content and pass. So the amended E5 is simply PENDING on the prompts/003 implementation step; it is not a regression of the F1/F6 fixes.
- `m0` other tests, collect-only and the M1-C1 status could not be rerun in place because of the lock abort (nothing outside `evaluate`/`layout_of`/`gauss` changed; earlier result: 26 pass + 6 PENDING, M1-C1 pending at `describe`).

## 3. F1 (layout) — fixed
| check | expected | got | result |
|---|---|---|---|
| layout `d,a(2),o`, `p` on `o[1]` vs $\mathrm{diag}(e^{i\theta[j_{o0}]})$ | ok | ok, err $3.4\cdot10^{-15}$ | PASS |
| old FALSE-ACCEPT probe: same circuit vs $\mathrm{diag}(e^{i\theta[j_{o1}]})$ | rejected | `error`, err $0.686$ | PASS (was ACCEPTED in 009) |
| layouts `d,o`, `d,o,a`, `o,d`, `a,d,o` | ok, identical | all ok, err $3.4\cdot10^{-15}$, read 1 | PASS |
| 28 unnamed qubits (first 12 = data) | evaluated, ancillas | `error 0.299` (correct: `p` on an ancilla qubit vs diag target) | PASS |
| `d` with 11 qubits; `o` with 15 qubits | ValueError | ValueError (messages name the sizes) | PASS |

**Register-order fuzz** (`adv9_fuzz.py`): all 24 orderings of the four registers (`d`:12, `o`:16, `a`:2, `b`:1) × 8 circuits (outer phase + $U_E$ vs correct target; outer phase vs wrong target; CZ(outer, inner) vs its diagonal target; ancilla compute/use/uncompute plus an idle `b`; dirty `b`; CX inner→outer; CX(outer→inner) vs independent oracle $\Psi^\dagger F\Psi$; $U_E$) = 192 evaluations.
| circuit | reason over 24 orders | op-norm err / leak / dirty / Gauss (reference) | spread | result |
|---|---|---|---|---|
| outer phase + $U_E$ | ok ×24 | $3\cdot10^{-15}$ / 0 / 0 / $10^{-15}$ | 0 | PASS |
| outer phase vs wrong link | error ×24 | $0.685795614910903$ | 0 (rel $10^{-9}$) | PASS |
| CZ(outer, inner) | ok ×24 | $3\cdot10^{-15}$ | 0 | PASS |
| ancilla compute/uncompute | ok ×24 | $1.21\cdot10^{-13}$ | 0 | PASS |
| dirty `b` | dirty_ancilla ×24 | err $1.000000000000061$, leak 1 | 0 | PASS |
| CX inner→outer | writes_outer ×24 | inf | n/a | PASS (my script printed "mismatch" only because it compared `inf-inf`; reason and signature are identical in 24/24) |
| CX(outer→inner) vs oracle | leak ×24 | err $4\cdot10^{-15}$ vs oracle | 0 | PASS |
| $U_E$ | ok ×24 | $1.21\cdot10^{-13}$ | 0 | PASS |
Verdict and all numbers identical for every ordering (tolerance $10^{-13}$ abs + $10^{-9}$ rel; observed difference 0).

## 4. F6 — fixed
- ancilla `ry(1e-5)` (weight $2.5\cdot10^{-11}$): reason `dirty_ancilla`, `failing_inputs` now filled (e.g. $(432, 2.5\cdot10^{-11}), (0, 2.5\cdot10^{-11})$).
- X on $q_{m'}$ (valid→invalid code), sparse and aer_mps: both `leak` (max_leak 1, dirty 0); aer_mps failing ids are strings (`inner_code_index 0`). X on an ancilla under aer_mps: `dirty_ancilla`, dirty 1. Labels now match the sparse engine.
- (F5 unchanged: `id` on an outer qubit still counts as a read.)

## 5. F4 — behaviour unchanged
`engine='aer_mps'` at the default tolerances is still `ok=True, certified=False, engine_accuracy=2e-10`; at $10^{-9}$ it is `certified=True`. `Verdict` has no `tolerances` field (amended tests expect one; prompts/003 work).

## 6. Regression of the known-verdict list
Rerun of adv1–adv8 (125 + 24 checks): everything that passed in 009 still passes with identical numbers ($U_E$ err $1.2\cdot10^{-13}$/$3.3\cdot10^{-15}$, $U_B$ 12-qubit unitary ok, perturbation scan, 4 oracles, 16-outer-bit oracle $1.9\cdot10^{-15}$ in 25 s, `specialise` worst $4.2\cdot10^{-15}$ on 236 blocks, aer_mps accounting, `gauss_residuals_coo`). The remaining FAIL lines are the same six check errors of my own as in 009 (identity 1e-13 threshold; non-identity ancilla circuit; the adv2 permutation line written without its control, correct in adv3; `UB^T`=$U_B$; two vacuous Gauss-sign controls) plus F5 (`id` on outer). Paulo's QPY run was skipped (F2 excluded).

## 7. Counts
unit 100 passed (was 94; +6 new, incl. `test_register_order_does_not_change_verdicts`); acceptance: locked E3–E5 3/3 pass (out of tree), in-tree run blocked by the lock abort; amended E5 fails on the missing prompts/003 API; independent: F1 evidence 5/5 and fuzz 192/192 identical; new failures vs report 009: 0 in code, 1 process failure (lock).

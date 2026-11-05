# Tester report 013 - M0 gate (mode full), includes step 0.10 (results store, report, provenance)

- Date: 2026-11-04. Commit: `5f094ab` (step 0.10 files uncommitted: `src/su2plaq/metrics/provenance.py`, `src/su2plaq/results/{store,report}.py`, `tests/unit/test_results_unit.py`).
- Prompt in force: `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md` on top of `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (step 0.10 row, section 3 M0 gate). Mode: full.
- Related: `reports/tests/001`-`012`. Raw numbers: `results/tester_013_m0_gate.json`; scripts: `results/tester_013_scripts_{prov_check,render_check,compare}.py`. Machine: 12 CPUs, 62 GB, pytest-xdist 6 workers.

## Commands
```
pytest -n auto tests/acceptance/m0 --durations=0 --junitxml=...        # full m0 incl. slow tests
pytest -n auto tests/acceptance/m1 tests/acceptance/m2 -rf --tb=line   # classification
pytest -n auto tests/unit ; pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
graphify update . ; graphify query "results store report provenance render" ; graphify affected provenance
python results/tester_013_scripts_prov_check.py <root>   # scratch clone: commit / dirty flag
python -I results/tester_013_scripts_render_check.py     # render, round trip, inf
# regression: every earlier tester script (scratchpad + tests/independent/*) re-run with outputs redirected, compared with stored logs/JSON
```
`graphify affected provenance`: `save_result`, `test_M0_R1_results_json_and_report`, the 4 new unit tests, `results/report.py`; all run.

## 1. Gate table
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `tests/acceptance/m0` (33 tests incl. slow C6, E3-E5, R1; no skips) | 33 pass | 33 passed, 0 failed, 0 skipped, 0 pending | exact | PASS |
| M0-R1 `test_M0_R1_results_json_and_report` | pass | pass (0.03 s) | exact | PASS |
| m1 + m2 (51 collected) | only PENDING + 3 known R1 | 1 passed (`test_macro_costs_match_lowering`), 46 PENDING (NotImplementedError), 3 known M1-R1 AssertionErrors, **1 non-pending failure: M1-O1** (see section 3) | - | PASS with 1 flag |
| unit suite | all pass | 131 passed (127 earlier + 4 new), 37.6 s | - | PASS |
| `pytest --collect-only -q tests/acceptance` | 84, clean | 84 collected, no errors | - | PASS |
| `python tools/check_lock.py` | LOCK OK | LOCK OK | - | PASS |
| `~/.claude/bin/acceptance-check` | PASS | PASS, matches acceptance-v3; `git diff -- tests/acceptance` empty | - | PASS |

Totals: acceptance 84 = 33 (m0) + 51 (m1/m2). Passed 34, failed 50 = 46 PENDING + 3 M1-R1 + 1 M1-O1. Unit 131/131.

### Timing of the full m0 run (6 xdist workers)
Wall time 28.3 s (pytest says 27.69 s), well inside the "< 3 min" expectation of prompts/002 section 3. Per file (sum of case times, parallel so the sum exceeds wall):

| file | tests | summed s |
|---|---|---|
| test_evaluator.py | 3 | 43.43 (E3 18.87, E5 17.65, E4 6.90) |
| test_physical.py | 7 | 4.24 (C6 slow jmax=1 count 2.96) |
| test_operators.py | 6 | 4.12 |
| test_metrics.py | 5 | 3.79 |
| test_spinnet.py | 3 | 1.13 |
| test_algebra.py | 4 | 1.07 |
| test_sparse_sim.py | 2 | 0.30 |
| test_results.py | 1 | 0.03 |
| test_geometry.py | 2 | 0.01 |

m1 + m2 collection+run: 8.0 s. Unit suite: 37.6 s.

### m1/m2 classification by message (51 tests)
| message | count | class |
|---|---|---|
| PENDING NotImplementedError `default_spec is not built yet` | 23 | PENDING (M2 + M1) |
| `build_UB is not built yet` | 7 | PENDING |
| `gridsynth_T is not built yet` | 4 | PENDING |
| `build_UE is not built yet` (M1-E1 x2, M1-T1[UE]) | 3 | PENDING |
| `build_step is not built yet` (M1-S1 x2, M1-T1[step]) | 3 | PENDING |
| `Archive.load is not built yet` | 2 | PENDING |
| `TwelveQubit.describe is not built yet` (M1-C1) | 1 | PENDING |
| `paulo_logical is not built yet` (M1-P2) | 1 | PENDING |
| `paulo_circuit is not built yet` (M1-P1) | 1 | PENDING |
| `code_hash is not built yet` | 1 | PENDING |
| `AssertionError: missing .../results/twelve/{UB,UE,step}.json` (M1-R1) | 3 | the 3 known results-file failures |
| `assert (3153 == 6561)` at `test_twelve_outer.py:24` (M1-O1) | 1 | **not a NotImplementedError**, see section 3 |
| passed: `m2::test_macro_costs_match_lowering` | 1 | PASS |

## 2. Step 0.10 independent checks
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `provenance()["git_commit"]` vs `git rev-parse --short HEAD`, real repo | equal | `5f094ab` = `5f094ab` | exact | PASS |
| same in a scratch clone after 2 commits (hashes `17ffa6a`, `a1e08f6`) | follows HEAD | equal each time | exact | PASS |
| `git_dirty`, clone with step-0.10 files modified vs HEAD | True | True | - | PASS |
| `git_dirty`, clean clone | False | False | - | PASS |
| `git_dirty`, tracked file edited / reverted / staged-only edit | True / False / True | True / False / True | - | PASS |
| `git_dirty`, new untracked file | by design `False` (`status --untracked-files=no`) | False | - | PASS, see note 1 |
| outside a git repository | `"unknown"`, `None` | `unknown`, `None` | - | PASS |
| real repo (step 0.10 uncommitted) | True | True | - | PASS |
| `versions` vs `pip list`: python 3.12.14, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, qiskit_aer 0.17.2, pygridsynth 1.2.0 | equal | identical | exact | PASS |
| `seeds` passed through; `cpu_count` 12; `timestamp_utc` ISO Z (UTC clock, so 2026-11-05T03:19Z at local 2026-11-04 20:19) | yes | yes | - | PASS |
| `render` idempotent: 3 calls (also with `str` paths) | identical | identical; render does not modify the file (byte-compare) | exact | PASS |
| `render` numbers come from JSON only: all 20 numeric table cells matched against numbers in the JSON | 0 foreign | 0 foreign | rel 1e-5 | PASS |
| perturbation: `cx` 294 -> 777, `depth` 391 -> 4242, `op_norm_error` -> 9.87e-7, `ok` -> false, `beta` 0.61 -> 0.5, `t_table[0].t_total` -> 31415, `t_est` -> 1234.5678 | new value shown, exactly 1 table line changes (t_est: old 1133.06 gone) | all 7 as expected | exact | PASS |
| dirty marker `*` after commit hash only when `git_dirty` is true | yes | yes | - | PASS |
| file order of `render([a, b])` respected | yes | yes | - | PASS |
| `load_result` rejects wrong `schema_version` and a missing key; `save_result` raises `TypeError` for an unserialisable object | raises | raises | - | PASS |
| Verdict round trip (`Verdict` object and `verdict_to_dict` give the same JSON); phase $0.6-0.8i \to [0.6,-0.8]$; `failing_inputs`, `tolerances` kept; save of the loaded doc is identical modulo timestamp | equal | equal | exact | PASS |
| Verdict with `inf` (op_norm_error, max_leak, gauss_residual) and `nan` (dirty_ancilla) | round trip | $\infty$ and NaN restored | - | PASS |

### Non-strict JSON (Infinity / NaN) - is it acceptable?
Yes for the project as it stands, with a caveat. `save_result` writes the Python tokens `Infinity`, `-Infinity`, `NaN`. Python `json` and `jq` (1.7) read them; strict parsers do not: Python with `parse_constant` raising, and Node's `JSON.parse` both rejected `results/.../inf.json` (`"op_norm_error": Infinity`). This is not hypothetical: the evaluator itself returns `inf, inf, inf` and a NaN Gauss residual for every rejection path (evaluator.py lines 228-229), so any stored failed-verdict record will contain them. All consumers in this project (tests, `render`, compression archive) are Python, so it is acceptable; if any non-Python reader (JS viewer, strict schema validator) is planned, encode as strings or `null`. (Caveat is a recommendation, not a failure; the plan's schema does not forbid it and `store.py` documents it.)

Notes:
1. `git_dirty` ignores untracked files. A brand-new, not yet `git add`ed source file used by a run is therefore not flagged. Consistent with the docstring; I report it only because a new module in `src/` would be invisible to the flag until staged.
2. `provenance` and `store` use `subprocess git` with a 30 s timeout and fall back to `"unknown"`; failures are not silently swallowed into numbers (the field says `unknown`/`None`).

## 3. Flag: M1-O1 is a real assertion failure, not NotImplementedError
`tests/acceptance/m1/test_twelve_outer.py:24`: `assert len(dims) == 6561` fails with `3153`. Cause (guess, verified in source): `su2plaq.exact.physical.s_o_dims` (step 0.4, `physical.py:276`) returns only outer keys that have support (3153 entries), while prompts/002 step 1.8 and the locked test demand the full 3^8 = 6561-entry table with zeros. Report 004 noted "3153 entries, zeros allowed" but this was never reconciled with M1-O1. It is a step 1.8 deliverable (the plan row says "6561-entry table"), so it belongs to PENDING work, not to the M0 gate (no m0 test touches it). To fix in 1.8: add zero entries (`range(3^8)`), and update `tests/unit/test_physical_unit.py:59` (`all(1 <= v <= 625 ...)` must become `0 <= v`). The rest of O1 (nonzero = 3153, `dims[0] == 2`, max 17, 625 codes occurring, rank equality) is already satisfied by the data in report 004 but is not executed beyond line 24.

## 4. Regression against reports 001-012
Every earlier independent check was re-run at this commit (outputs redirected, tracked `results/` untouched) and compared with the stored logs/JSON (tolerance: absolute 1e-13 or relative 1e-6; timing keys ignored).

| report | what was re-run | result |
|---|---|---|
| 001 scaffold, 002 geometry | `tools/check_lock.py`, acceptance-check; independent geometry (34 checks) | 34/34, lock OK; identical |
| 003 algebra | `verify_step03.py` JSON (Haar-quadrature U, 570 6j vs sympy, V_P) | identical (only commit label and a timing differ); 6j max err 5.55e-17, 570 admissible |
| 004 physical | `tests/independent/check_physical_0_4.py` JSON | 0 differences (433/2/256/95/17362, 3153, rank 625, Gauss, Gram) |
| 005 operators | `tests/independent/check_operators_0_5.py` | 0 differences except the W build timing (0.295 vs 0.300 s); slopes 1.7/1.93/1.98, fitted 1.8758; order-1/2 local-error slopes 1.908 / 2.921; $U_B(0.25)U_B(0.36)-U_B(0.61)=1.5\cdot10^{-15}$ |
| 006 route B | `indep_routeb.py`, `corner.py` (out1/out2 JSON) | 0 differences |
| 007/008 sparse sim | `chk1e` (vs Aer), `chk6` (A/B), `chk7` (64 896 forced-pruning cases), `chk9`, `chk5r/chk5br` (timing), `chk3/4/8/10/11/12` | results JSON identical except `rss_MB` (148.8 vs 151.0 MB; 869 vs 844 MB); 64 896 cases, 0 bound violations, worst err-bound $6.5\cdot10^{-16}$; MPS vs sparse $2.05\cdot10^{-10}$; heavy timing run 25.7 s (stored 26 s class, peak 5.12e6 entries) |
| 009-011 evaluator | `adv1`-`adv8`, `adv9_fuzz` (24 orders), `adv10`, `adv11` (26 tol checks), `adv12_paulo_p1` | verdict lines identical to the final logs (adv1 36 PASS/3 expected-FAIL, adv2 19/1, adv3 24/3, adv4 21/2, adv5 2/0, adv6 12/1, adv7 1/0, adv8 1/0, fuzz 18/1 as before); differences only in the Qiskit UUID text and file paths. Paulo QPY under amended M1-P1: ok, certified, err $2.905\cdot10^{-6}$, leak $4.19\cdot10^{-12}$, dirty $1.12\cdot10^{-13}$, Gauss $1.160\cdot10^{-10}$, acc $2\cdot10^{-10}$ (run time 83.7 s vs 107.7 s before; timing only) |
| 012 metrics | `t1`-`t4` JSON (30 random circuits, 24 angles x 4 eps, synthesize, Paulo ct_compile) | 0 differences: T per rotation 42.58/62.83/82.58/101.92, Paulo cx 294, T 1162, depth 2549 |

Numbers that changed: none that are physics or verdict relevant. Changed items: timings (wall seconds, e.g. Paulo 107.7 -> 83.7 s), resident memory, commit label, Qiskit UUIDs, absolute paths in warnings. The adv-script "FAIL" lines are the intentional negative controls recorded in reports 009-011 (unchanged).

Side effect to disclose: while redirecting outputs, `verify_step03.py` overwrote the tracked `results/tester_m0_step03_algebra.json`; I restored it with `git checkout -- results/tester_m0_step03_algebra.json` (the content differed only in commit label and a timing). `git status` now shows exactly the four step-0.10 files plus my new `results/tester_013_*` files.

## 5. Failures
None in the gate. One flag (M1-O1, section 3) and two recommendations (non-strict JSON, untracked files in the dirty flag).

## Known issues carried (unchanged, from STATUS)
Ross-Selinger band lower edge at eps 1e-10; `t_table['t_qiskit']` uses the lowered circuit; M1-T1 needs the sparse engine for UE/UB; aer_mps floor 2e-10. Not re-examined here.

VERDICT: PASS (M0 gate: 33/33 acceptance m0 incl. slow, 131/131 unit, lock + acceptance-check OK, 84 collected, step 0.10 verified independently, no regression; m1/m2: 46 PENDING + 3 known M1-R1 + 1 flagged M1-O1 length mismatch to fix in step 1.8).

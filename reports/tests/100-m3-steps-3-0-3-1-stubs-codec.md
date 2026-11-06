# Test report 100 — M3 steps 3.0 (stubs) + 3.1 (spin-network codec)

- Date: 2026-11-06 · Commit under test: `bd37c15` (HEAD) + uncommitted files `src/su2plaq/encodings/spinnet.py`, `src/su2plaq/spinnet/{__init__,walk,paulo,trotter_v2,lean_export}.py`, `src/su2plaq/circuits/spinnet.py`, `tests/unit/test_spinnet_codec_unit.py`
- Branch `m3-spin-network` (clone `~/Projects/su2qc-spinnet`), prompt in force `prompts/100-spinnet-m3-plan.md`, mode **step**, tester Claude Sonnet 5.5
- Related reports: `reports/research/100-spinnet-m3-encoding-gauge-general-circuit.md` (planner prototype); previous M1 codec/gauge reports `reports/tests/016`, `reports/tests/006` (route B); no earlier report on this track
- Raw numbers: `results/spinnet/tester/m3_step_3_0_3_1.json`; independent script `results/spinnet/tester/m3_step_3_0_3_1_verify.py` (deterministic; the only random draw is `default_rng(7)` for a test gauge)

## Commands
```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 0-9 pytest --collect-only -q tests/acceptance
taskset -c 0-9 pytest -n 10 -q tests/acceptance/m3 -rf --tb=line
taskset -c 0-9 pytest -q tests/acceptance/m3/test_spinnet_codec.py -v
taskset -c 0-9 pytest -n 10 -q tests/unit
taskset -c 0-9 pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
python tools/check_lock.py && ~/.claude/bin/acceptance-check
graphify update . ; graphify affected SpinNet                    # affected = only tests/unit/test_spinnet_codec_unit.py (new code)
taskset -c 0-9 python results/spinnet/tester/m3_step_3_0_3_1_verify.py results/spinnet/tester/m3_step_3_0_3_1.json
git status --short
```

## 1. Suites

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `pytest --collect-only -q tests/acceptance` | 126, clean | 126 collected, no errors | exact | PASS |
| `m3/test_spinnet_codec.py::test_M3_C1_codec_and_vectors` | pass | pass | — | PASS |
| `m3/test_spinnet_codec.py::test_M3_K1_route_b_target_with_gauge` | pass | pass | — | PASS |
| other 22 m3 tests | PENDING / missing results only | 16 `PENDING: NotImplementedError` (build_UE x3, build_UB x7, build_step x3, paulo_circuit x1, trotter_v2_circuit x2), 2 `PENDING: lean/Su2Plaq/SpinNet/{Counts,Circuit}.lean missing`, 1 `PENDING: Su2PlaqCert checker not delivered`, 3 `missing results/spinnet/{UE,UB,step}.json` | no other reason | PASS (PENDING, not failures) |
| `pytest -n 10 tests/unit` | all pass | 236 passed, 1 failed | — | see note |
| m0 + m1 `-m "not slow"` | green | 54 passed | — | PASS |
| `tools/check_lock.py` / `acceptance-check` | PASS | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v7` | — | PASS |

m3 totals: 2 passed, 22 not passed = 19 PENDING (NotImplementedError / missing Lean files / missing checker) + 3 missing results files (R1, PENDING by construction until step 3.7). No m3 failure of any other kind.

Unit-suite failure note (not counted against this step): the single failure is `tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers`, `AssertionError: 'c1' not in ...  yes | bd37c15 |` — the rendered table contains the git short hash `bd37c15`, which contains the substring `c1`. This is exactly the known laptop-owned flake; the only cause. The 14 new unit tests of `test_spinnet_codec_unit.py` all pass.

## 2. Independent physics (script `results/spinnet/tester/m3_step_3_0_3_1_verify.py`, own Gauss operator built from `LinkSpace().generators()` with its diagonal convention $L^z=-m_L$, $R^z=+m_R$ asserted)

### 2a. Fallback judged (builder deviation): per-end $G^z=\pm\tfrac12$
Set of codes: 47 inner data codes $\times$ 256 outer patterns = 12 032; 433 physical; 11 599 inadmissible.

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| Gram of `decode_state` over all 12 032 codes, $\max|G-\mathbb 1|$ | 0 | $7.3\cdot10^{-15}$ (physical block = route-A Gram rounding) | 1e-12 | PASS |
| Gram, inadmissible-vs-inadmissible off-diagonal | 0 | 0.0 (exact) | 1e-12 | PASS |
| overlap of any inadmissible code with any physical state | 0 | 0.0 (exact) | 1e-12 | PASS |
| Gauss residual, all 11 599 inadmissible: min (own implementation) | $\ge 0.5$ | 0.5 (exactly), max 2.0 | $\ge 0.5-10^{-10}$ | PASS |
| same with library `gauss_residuals_coo` | equal to own | max difference 0.0 | 1e-12 | PASS |
| Gauss residual, 433 physical decoded states (own) | 0 | $5.4\cdot10^{-16}$ | 1e-10 | PASS |
| decoded physical code $k$ vs $\mathrm{gauge}[k]\cdot$(route-A state $k$), max coefficient deviation | 0 | 0.0 | 1e-12 | PASS |
| reproduction of the discarded prototype fallback ($m=\pm\tfrac12$ on every end, `m` replaces the out/in-dependent sign) | overlaps with physical states | 60 codes with overlap $>10^{-12}$, max overlap 0.3536 | — | confirms the defect (builder quotes 76 codes; my re-implementation of the naive rule gives 60; max 0.354 agrees; count difference is a guess about the exact prototype rule, immaterial) |

The deviation is correct: the fallback is an isometry on the whole code space with Gram $=\mathbb 1$ and minimum Gauss residual exactly 1/2. It does not alter the 433 physical codes: they are looked up in `_index` first and never reach `_fallback` (deviation 0.0 against $\mathrm{gauge}\cdot$route A). Note the "unchanged on physical codes" statement is structural (separate branch) rather than a numerical coincidence.

### 2b. Codec, K, targets
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| $K$ (47 inner codes) dark rows | 31 | 31 | exact | PASS |
| bright pairs | 8, partner $=$ code $\oplus$ 0b1111, no other non-zero entries | 8, XOR 15 for all, 0 rows with other pattern | exact | PASS |
| pair couplings | $\{-2,-\tfrac12,1\times6\}$ | $-2.0000000000000018,\ -0.5,\ 1.0000000000000004\times6$ | 1e-12 | PASS |
| $K$ real symmetric | 0 | 0, 0 | 1e-12 | PASS |
| gauge from `gauge_align`: real $\pm1$, minus signs, residual $|H_A-DH_BD|$ | $\pm1$; 64; $\le10^{-10}$ | $\pm1$, 64, $2.7\cdot10^{-15}$ | 1e-10 | PASS |
| $\|U_B^{B}(\beta)-\exp(-i\beta H_B)\|$, $\beta=0.61/1.0$ | 0 | $2.2\cdot10^{-16}$ / $3.3\cdot10^{-16}$ | 1e-12 | PASS |
| route-B $U_B$ vs route-A $U_B$ after `gauge_align` (residual), $\beta=0.61$ / $1.0$ | $\le10^{-12}$ | $1.4\cdot10^{-15}$ / $2.7\cdot10^{-15}$ | 1e-12 | PASS |
| $\|U_B^{B}-D U_B^{A}D\|$ with `enc.gauge`, $\beta=0.61/1.0$ | $\le10^{-12}$ | $1.4\cdot10^{-15}$ / $2.7\cdot10^{-15}$ | 1e-12 | PASS |
| $U_B^\dagger U_B-\mathbb 1$ | 0 | $4.4\cdot10^{-16}$ / $5.6\cdot10^{-16}$ | 1e-12 | PASS |
| `inner_target('UB')` vs $\exp(-i\beta K)$ | 0 | $2.2\cdot10^{-16}$ / $3.3\cdot10^{-16}$ | 1e-12 | PASS |
| every outer-pattern block of the 433x433 `target('UB')` equals the 47x47 `inner_target` restricted (mapping via data code); cross-outer blocks zero | 0 | $2.7\cdot10^{-17}$ / $2.6\cdot10^{-17}$; cross 0.0 | 1e-12 | PASS |
| `target('step')` orders 1, 2 vs `inner_target('step')` blocks | 0 | $5.6\cdot10^{-17}$ both | 1e-12 | PASS |
| step route B vs route A after `gauge_align`, order 1 / 2 ($\alpha=0.37,\beta=0.61$) | $\le10^{-12}$ | $1.5\cdot10^{-15}$ / $1.5\cdot10^{-15}$ | 1e-12 | PASS |
| `target('UE')` (also with outer electric) vs route A, `inner_target('UE')` blocks | 0 | 0.0, 0.0, 0.0 | 1e-12 | PASS |
| `regauge(V, D)` vs $D_{433}VD_{433}^\dagger$ with random $D=\pm1$ | 0 | 0.0 | 1e-14 | PASS |
| `align_inner_block(e^{0.3i} D V D, V)` residual | $\le10^{-12}$ | $2.3\cdot10^{-16}$ | 1e-12 | PASS |
| `evaluate(identity, enc, UE(0))` | ok | ok=True, op-norm error $4.4\cdot10^{-16}$, Gauss $5.4\cdot10^{-16}$ | 1e-10 | PASS |

## 3. Static checks
| check | result |
|---|---|
| `git status --short` | only 4 untracked track-S paths (the 6 files listed + the unit test); no tracked/laptop-owned file modified (`git diff --stat` empty) — PASS |
| silent exception catching | `grep -nE "except|try:|pass$"` over the new source files: none — PASS |
| hard-coded expected numbers | no tabulated expected results used to produce outputs. Literals present: structural assertions `len(set(...)) != 47` (an invariant check of the codec, raises) and the fixed `describe()` prose "11 599" / "$\ge 1/2$" (documentation text; not computed) — minor, not blocking |
| §2 names of step 3.0 | all functions/classes present and raising `NotImplementedError` via `_stub.todo`, but these module-level constants named in §2 do **not** exist: `walk.GENERAL7`, `paulo.GATES_FILE`, `paulo.SHA256`, `paulo.QUBIT_MAP`, `trotter_v2.SOURCE`, `trotter_v2.SKELETONS` (the module docstring says they are "added there"). Locked tests see these as `PENDING: ... has no attribute` through `api()`, so nothing fails; the stub list of step 3.0 ("stubs for every name of §2") is incomplete in that respect — NIT, to be added in the steps that fill them (3.2/3.4/3.6) |

## Verdict
**PASS** (step 3.0 + 3.1). Passed 2 of 2 required acceptance ids (C1, K1) and all regression (m0+m1 54/54, lock OK); unit 236/237 with the single known `c1`-in-hash flake (hash `bd37c15`); 22 m3 tests PENDING as expected (19 NotImplementedError/missing Lean/checker, 3 missing results); new failures vs. last report: none. Builder's fallback deviation verified as correct: Gram $=\mathbb 1$ to $7\cdot10^{-15}$ on all 12 032 codes, Gauss residual min exactly 0.5 on all 11 599 inadmissible codes (two independent implementations agree), physical codes unchanged (deviation 0).

Open nits (non-blocking): six constants of §2 not stubbed (above); "11 599" literal in `describe()` text.

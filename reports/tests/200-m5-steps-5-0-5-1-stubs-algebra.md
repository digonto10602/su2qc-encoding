# Test report 200 — M5 steps 5.0 (stubs) + 5.1 (`rishon/algebra.py`)

Date: 2026-11-06 · Commit: `9f2e1e5` (uncommitted working tree: the 5.0/5.1 files only) · Branch `m5-rishon` (clone `~/Projects/su2qc-rishon`)
Prompt in force: `prompts/200-rishon-m5-plan.md` (acceptance-v7) · Mode: step · Related reports: none yet on this track (laptop 001–028 are the M0–M2 baseline).
Env: `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 10-19`, `pytest -n 10`.

## Commands
```
pytest --collect-only -q tests/acceptance
pytest -n 10 -q tests/acceptance/m5 [--junitxml=...]          # classification of the 32 non-pass outcomes
pytest -n 10 -q tests/unit
pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
python tools/check_lock.py && ~/.claude/bin/acceptance-check
python results/rishon/tester-200-algebra-independent.py        # own construction, not the code under test
graphify update . ; graphify affected "RishonLink"             # no dependents yet (new symbol)
git status --short
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `pytest --collect-only tests/acceptance` | clean, 136 | 136 collected, 0.22 s, no errors | exact | PASS |
| `m5::test_rishon_algebra.py::test_M5_D1_link_algebra` | pass | pass | 1e-13 | PASS |
| `m5::test_rishon_algebra.py::test_M5_D1_string_free_and_sector` | pass | pass | 1e-13 | PASS |
| other m5 tests | all `PENDING:` | 32/32 fail with `PENDING:` (25 `NotImplementedError ... is not built yet`; 3 Lean files missing; 4 `results/rishon/*.json` missing); 0 import/syntax/other errors | — | PASS (32 pending) |
| unit suite | green | 259 passed (216 baseline + 43 new: 5 algebra-unit funcs, stub tests), 32.6 s | — | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed, 87.6 s | — | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | — | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v7` | — | PASS |
| file ownership (`git status --short`) | only the listed new paths | 5 untracked entries (`circuits/rishon.py`, `encodings/rishon.py`, `rishon/`, 2 unit tests); no tracked file modified, `git diff --stat` empty | — | PASS |
| no hard-coded expected numbers / silent excepts | none | `grep except|try:|1296|38432|4352|2192|431` in new src: only a docstring mention of 1296; sector derived from `diag(N)==2`, Casimirs computed; code constants `CODE_A/B/Q` are the spec's labels; bad inputs raise `ValueError` (4 paths exercised) | — | PASS |

### Independent physics checks (own bit-manipulation JW, `c_k|n> = (-1)^{popcount(n & (2^k-1))}|n xor 2^k>`, no shared code)
| check | expected | got (max abs deviation) | tol | verdict |
|---|---|---|---|---|
| CAR $\{c_k,c_l^\dagger\}=\delta_{kl}$, $\{c_k,c_l\}=0$, 4 modes | 0 | 0 | 1e-13 | PASS |
| $[L_a,U_{ij}]=-(T_aU)_{ij}$ (BCW 4.1 / METHODS R1) | 0 | 0 | 1e-13 | PASS |
| $[R_a,U_{ij}]=+(UT_a)_{ij}$ | 0 | 0 | 1e-13 | PASS |
| $[U,U]=0$, $[N,U]=0$, $[N_R-N_L,U]=2U$ | 0 | 0 | 1e-13 | PASS |
| su(2)$_L\oplus$su(2)$_R$: $[X_a,X_b]=i\epsilon_{abc}X_c$, $[L,R]=0$ | 0 | 0 | 1e-13 | PASS |
| production vs independent ($c$, $c^\dagger$, $L_a$, $R_a$, $U_{ij}$) | 0 | 0 | 1e-13 | PASS |
| rishon-number-2 sector | dim 6, codes $\{3,5,6,9,10,12\}$ | same | exact | PASS |
| Casimir on sector | $(0,\tfrac34,\tfrac34,\tfrac34,\tfrac34,0)$; eigenvalues $\{0^2,(3/4)^4\}$ = 2 singlets + quartet | same | 1e-12 | PASS |
| $\det U=U_{00}U_{11}-U_{01}U_{10}=2c_{L1}c^\dagger_{R1}c_{L2}c^\dagger_{R2}$; on sector $=2|B\rangle\langle A|$ | 0 | 0 | 1e-13 | PASS |
| `end_generator` L/R vs 2-mode JW, and embedded (`kron(1,g)`, `kron(g,1)`) vs `L_a`,`R_a` | 0 | 0 | 1e-13 | PASS |
| string-freeness of all link bilinears $c_kc_l^\dagger$, $c_k^\dagger c_l$ (every link; global JW) vs 4-qubit local op embedded, 8 modes (2 links) | 0 | 0 | 1e-13 | PASS |
| same, 12 modes (3 links) | 0 | 0 | 1e-13 | PASS |
| `global_bilinear` vs own global JW, 8 modes | 0 | 0 | 1e-13 | PASS |
| `embed_link_op` ordering (link 0 least significant) | 0 | 0 (links 0,1 of 2) | 1e-13 | PASS |

Sensitivity controls (the checks can fail): wrong sign $[L,U]=+TU$ gives residual 1.0; an interleaved (non-contiguous) bilinear $c_2c_6^\dagger$ on 8 modes does not commute with $X_4$ (residual 2.0), i.e. strings are real when modes are not contiguous. Entries are $\{0,\pm1,\pm\tfrac12,\pm\tfrac i2\}$, so zeros are exact. Conventions (occupied = bit 1, $\sigma^-=|0\rangle\langle1|$, $A$=code 3 = both rishons at L end, $B$=12, $U$ maps $A\to Q\to B$) agree with `docs/METHODS-rishon.md` R1/R2.

Raw numbers: `results/rishon/tester-200-algebra-independent.json` (script alongside; deterministic, no seed).

## Pending (not failures, step mode): 32 m5 tests
circuits (9: E1 x2, B1 magnetic x4, B1 physical, S1 x2), codec (1), lean (3), metrics (3), observables (4), operators (4), physical (3), results (4), verify (1) — all `PENDING:`; steps 5.2-5.10, 5.L1-5.L3.

## Non-blocking notes
* `tests/unit/test_rishon_stubs_unit.py` PENDING list omits `corner_kernel, gauss_inner, heights, inner_target, closed_block, observables, verify, physical_cross_check, build_UE, build_step`, `RishonEncoding` methods other than `inner_codes`: they exist as stubs (acceptance `PENDING:` messages show several raise `NotImplementedError`), but the unit skeleton does not assert it. Minor coverage gap.
* `next-num` suggested 029 (laptop numbering); this report uses 200 as instructed.

VERDICT: PASS. 0 failures; 2 target acceptance tests pass; 32 pending; unit 259/259; m0+m1 54/54.

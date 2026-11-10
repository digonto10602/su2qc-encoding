# Test report 201 — M5 step 5.2: rishon physical basis, counts, Gauss, inner span

Date: 2026-11-06 · commit `c373e3b` (working tree: step 5.2 uncommitted) · branch `m5-rishon` · prompt in force `prompts/200-rishon-m5-plan.md` (acceptance-v7) · mode: step · related: `reports/tests/200-m5-steps-5-0-5-1-stubs-algebra.md`

**VERDICT: PASS.**

## Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 10-19`)
```
pytest -n 10 -q tests/acceptance/m5                      # junit parsed, results/rishon/tester-201-m5-outcomes.json
pytest -n 10 -q tests/unit
pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python results/rishon/tester-201-independent-counts.py   # routes H and K (no su2plaq import)
python results/rishon/tester-201-states-check.py         # audit of rishon_basis() with own operators
python results/rishon/tester-201-corner-tables.py        # 324 corner/type cases
```

## 1. Suite results
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| `test_rishon_physical.py` (3 C1 tests) | pass | 3 passed (`counts_two_routes`, `states_gauss_orthonormal`, `inner_span_full`) | – | PASS |
| `test_rishon_algebra.py` (2 D1 tests) | pass | 2 passed | – | PASS |
| other m5 tests | PENDING only | 29 failed, **all** `PENDING:`; 0 genuine failures | – | PASS (pending) |
| collection | clean, 136 | 136 collected | – | PASS |
| unit | green | 282 passed (29 s) | – | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed (94 s) | – | PASS |
| `check_lock.py` | OK | `LOCK OK` | – | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v7` | – | PASS |

Pending m5 tests (29), by cause: `build_UB` not built 6 (metrics, B1 magnetic block); `build_UE` 3; `build_step` 3; `h_magnetic_inner` 3; `plaquette_W_inner` 1; `observables.observables` 3; `closed_spectra` 1; `verify.verify` 1; `RishonEncoding.inner_codes` 1 (codec, step 5.4); Lean files missing 3 (`Counts.lean`, `JW.lean`, `HB.lean`); results files missing 4 (`UE/UB/step/observables.json`, step 5.10). Exact per-cause counts in `results/rishon/tester-201-m5-outcomes.json`. (Cause counts sum to 29 including the 4 missing results files and 3 Lean files.) None of the 29 is a failure of step 5.2.

## 2. Independent counts (nothing from `su2plaq` used; geometry derived from the link coordinates of METHODS §1)
Route H (Haar integral): $N=\int_{SU(2)^4}\!dg\,\oint_{U(1)^4}\!\prod_{\rm inner\ \ell=(x\to y)}\!\big(z_x^2+z_y^2+z_xz_y\chi(g_x)\chi(g_y)\big)\prod_{\rm outer\ c}\big(1+z_c^2+z_c\chi(g_c)\big)$; link characters of the 6 link states, outer far end a spectator (4 states per outer link, METHODS-rishon R2), uniform quadrature (16 SU(2) angles per corner with Weyl weight $2\sin^2\theta/N$, 9 U(1) phases; exact for trigonometric polynomials; coefficients integer to $5.5\times10^{-12}$, none negative). Closed: outer factor $(1+z^2)$ (singlets only). U(1) sector = coefficient of $z^Q$; U(2) sector $z^{(4,4,4,4)}$.

Route K (brute force): own Jordan–Wigner $c_k=(\prod_{m<k}Z_m)\sigma^-_k$ on an 8-qubit corner (4 ends $\times$ 2 modes), $G^a_e=\sum_{ij}\tfrac12\sigma^a_{ij}c^\dagger_{e,i}c_{e,j}$ (end generator checked equal to the same 4×4 on qubits $2e,2e+1$, $<10^{-13}$), kernel of $\sum_a(\sum_eG^a_e)^2$ per end-occupation tuple $n\in\{0,1,2\}^4$ ($\sum_a$ Casimir commutes with occupations: leak 0.0; gap of nonzero eigenvalues $>0.2$), summed over the $3^{12}$ link-occupation assignments with the link constraint $n_L+n_R=2$.

| quantity | expected (plan) | production `count_by_fusion` | production built basis | route H | route K | own count from built keys |
|---|---|---|---|---|---|---|
| dim | 38 432 | 38 432 | 38 432 | 38 432 | 38 432 | 38 432 |
| closed | 4352 | 4352 | 4352 | 4352 | 4352 | 4352 |
| U(1) sectors | 431 | 431 | 431 | 431 | 431 | 431 |
| U(2) sector | 2192 | 2192 | 2192 | 2192 | 2192 | 2192 |
| type patterns | 35 073 | 35 073 | 35 073 | – | 35 073 | 35 073 |

All PASS (exact). Hence the 38 432 built states, which I show below are orthonormal and annihilated by Gauss, **span the entire gauge-invariant space** (dimension 38 432 by two independent routes): completeness is established, not assumed.

## 3. Audit of the built basis (own operators; `results/rishon/tester-201-states-check.json`)
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| every key has 6 valid link codes (2 rishons/link) | all | all (508 688 COO entries, 352 016 distinct keys, max key $2.25\times10^{14}<2^{48}$) | – | PASS |
| outer far ends: A/B fixed full/empty, Q far colour 1 (`01`) | all keys | all keys | – | PASS |
| corner occupation constant within each state | yes | yes | – | PASS |
| Gauss residual, **all 38 432 states**, own $G^a_c=\sum c^\dagger\sigma^a c/2$ | $\le10^{-10}$ | $2.04\times10^{-16}$ | 1e-10 | PASS |
| negative control: flip sign of one amplitude of the 1296-component state | $\gg10^{-10}$ | 0.111 | – | PASS (detector sensitive) |
| unit norm, all states | $\le10^{-12}$ | $4.0\times10^{-15}$ | 1e-12 | PASS |
| **full** Gram $38432^2$ minus identity, max entry | $\le10^{-12}$ | $8.0\times10^{-15}$ | 1e-12 | PASS |
| labels unique; label types = types read off the keys | yes | yes (38 432 distinct) | – | PASS |
| $J$ labels vs $\|(G_{\rm e0}+G_{\rm e1})\psi\|^2$ per corner (1500 seeded states, 6000 corners) | $J(J+1)$ | max dev $7.1\times10^{-15}$ | 1e-10 | PASS |
| inner codes = own $6^4$ list | equal | equal | – | PASS |
| inner span: Gram of 1296 $\times$ 249 872 (state, outer-pattern) columns, rank | 1296 | 1296 at $10^{-9}$ and $10^{-6}$; $\lambda_{\min}=0.01235$ (=1/81), $\lambda_{\max}=625$ — no near-null direction | – | PASS |
| outer patterns occurring | $\le4^8$ | 32 256 | – | PASS |
| build time / memory | 2.3 s / 0.33 GB | 2.37 s / 0.42 GB peak (this audit incl. my Gram) | ≤60 s | PASS |

## 4. Independence of the two production routes (item 3)
Production fusion route (`count_by_fusion`) uses spin fusion $\sum_c n_c$ with $n_c=\#\{$singlets of $\bigotimes j_e\}$ (`_n_singlets`), no matrices. The built basis uses `eigh` nullspaces of the Casimir on the occupation-restricted 2-qubit end spaces; the live type patterns come from the kernel dimension, the label $J$ from diagonalising the pair Casimir inside the kernel. They share only the type enumeration and the end-code table. Direct comparison over all 324 (corner, type-tuple) cases: kernel dimension vs fusion table mismatches **0**; kernel dimension vs my 8-qubit brute-force kernel **0**. A wrong kernel (e.g. wrong end generator or colour assignment) would break this equality, so the routes are not secretly the same computation. The J-label diagonalisation is independently validated by the 6000-corner Casimir check (§3). No count is hard-coded: `physical.py` contains no 38432/4352/2192/431/35073 literal (the only "1296" is in a docstring); counts come from `count_by_fusion()`/`counts(basis)`.

## 5. Hygiene
* `git status --short`: only `src/su2plaq/rishon/{operators,physical}.py`, `tests/unit/test_rishon_stubs_unit.py` (modified) and `tests/unit/test_rishon_physical_unit.py` (new) — all track-R-owned; no laptop-owned file touched. `operators.inner_codes()` is the only operator built (derived from `RishonLink().sector`, equals my own list).
* `grep except` in `physical.py` and the new unit file: none; errors are explicit `ValueError`s (invalid link/role, non-half-integer pair spin, inner component outside code space, oversize sample).
* Unit tests 282 (was 259 at report 200; +23 new for 5.2 incl. the updated stub tests).
* Tests I added: none under `tests/`; scripts only under `results/rishon/tester-201-*`.

## 6. Observations (non-blocking)
1. `u1_charges` reads only the first key of each state; I verified occupations are constant over all keys of every state, so this is sound.
2. Closed-reference ordering and the sample (seed 20261104, 256 distinct, disjoint from the 17 closed states) are exercised by the locked test, which passes.
3. Spectator treatment of outer far ends matches METHODS-rishon R2 / METHODS §3 for KS (far end fixed, not gauge-covariant): all 508 688 COO keys obey it, and the Haar count with 4 states per outer link reproduces 38 432, i.e. the same convention.

Raw data: `results/rishon/tester-201-{independent-counts,states-check,corner-tables}.{py,json}`, `tester-201-m5-outcomes.json` (commit `c373e3b`, seed 201 for the J-label sample; basis sample seed 20261104 as in the plan).

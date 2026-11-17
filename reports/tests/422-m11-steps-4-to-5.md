# Report 422: tester, milestone M11 steps 11.4 and 11.5 (`crosscheck/limits.py`, `isolated_plaquette_basis` moved)

- Date: 2026-11-17. Mode: step. Commit under test: `ea6db4e` plus the uncommitted builder files (`src/su2plaq/crosscheck/limits.py`, `scripts/m9_results.py`, `tests/unit/test_crosscheck_limits_unit.py`).
- Plan in force: `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` §5.3 and §7 rows 11.4, 11.5; conventions `docs/METHODS.md` §13.3, §13.4.
- Related: reports/tests/421 (steps 11.0 to 11.3, same hashes), reports/research/006 (prototype numbers).
- Raw numbers: `results/tester/422-m11-s4-5.json`. Independent scripts (scratch): `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/{indep2.py,devs.py}`.
- Resources: `taskset -c 0-8`, `-n 3`, all inside `tools/pytest-safe` or `tools/run-capped`. The other builder's `compress/{robust,report,replay}.py` diffs were ignored.

## Commands

```
taskset -c 0-8 tools/pytest-safe -n 3 -m "not slow" tests/acceptance/m11 -q -rA --durations=8
taskset -c 0-8 tools/run-capped python -m pytest -n 3 -q -rA --durations=5 \
   tests/acceptance/m11/test_cross_models.py::test_M11_E3_rishon_433_lowest_levels_reach_the_ks_spectrum \
   tests/acceptance/m11/test_cross_models.py::test_M11_E3_rishon_levels_at_the_project_couplings      # slow ones (+ [1.0])
taskset -c 0-8 tools/run-capped python indep2.py a|b ; python devs.py
taskset -c 0-8 tools/pytest-safe -n 3 tests/unit/test_crosscheck_{ks,embed,limits}_unit.py tests/unit/test_m9_results_script_unit.py -q
python hashes.py ; sha256sum of results/fuzzy + results/compress/fuzzy_{ub,link} (84 files) before and after
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Verdict: PASS

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| collect-only | 407, clean | 407 collected | exact | PASS |
| m11 not-slow | E2, E3[1.0], F1, F2 newly green; 11.0 to 11.3 set still green; only R1, T1, T2 pending | 21 passed, 3 failed; the 3 are R1, T1, T2, each `PENDING: results/crosscheck/{spectra,gate-table}.json missing`; E2, E3[1.0], F1, F2 pass; K1, K2, K3, E1, E1_det, F3 still pass; H1 passed (reported, not judged) | exact | PASS |
| slow tests via `tools/run-capped` (E3[0.5], E3[2.0], E3_levels, plus E3[1.0]) | pass | 4 passed, wall 35 s (3 workers); call times 26.8 s ([0.5]), 26.9 s ([2.0]), 26.9 s ([1.0]), 8.0 s (E3_levels) | exact | PASS |
| unit tests (ks, embed, limits, m9 results script) | pass | 40 passed in 56 s (slowest: `test_isolated_plaquette_levels` 53 s, `test_isolated_plaquette_basis_is_the_gauss_kernel` 30 s, rishon levels 25 s) | exact | PASS |
| six hashes vs report 420 | equal | all six equal (provenance `99663fa6…`, lsh `88e0d76b…`, spinnet `10f5727f…`, fuzzy `b4bd20fe…`, rishon `5f5decfa…`, spinnet loop `f1314a01…`) | exact | PASS |
| `acceptance-check`, `check_lock.py` | pass | "PASS: tests/acceptance matches acceptance-v22", "LOCK OK" | exact | PASS |
| `results/fuzzy/*.json` byte-identical | identical | sha256 of 84 files (results/fuzzy, results/compress/fuzzy_ub, fuzzy_link) identical before and after; `git status` shows no `results/` change | exact | PASS |

### Deviations that E2, E3, F1, F2 test, against their locked tolerances

(module functions called by me with the acceptance tests' own formulas; planner prototype values from the comments of the tests / research 006)

| test | quantity | got | locked tolerance | prototype | result |
|---|---|---|---|---|---|
| E2 | Hermiticity of `rishon_closed_block` | 0 | 1e-12 | | PASS |
| E2 | closed-block spectrum vs R13 formula (4 coupling sets, relative) | 1.2e-15 | 1e-12 | | PASS |
| E2 | coefficient, $L=256$, relative deviation, $g^2=0.5/1/2$ | 1.73e-3, 1.35e-3, 1.48e-3 | 1e-2 | 0.17 % max | PASS (margin 5.8) |
| E2 | $\lvert\text{slope}+1\rvert$ ($L$ 128 to 256) | 2.43e-3, 1.94e-3, 2.13e-3 | 1e-2 | 2.4e-3 | PASS |
| E2 | next band offset $\lvert(e_2-e_1)-(4L-e_k)\rvert$ | 0.0554, 0.0172, 0.0058 | 0.2 | 0.055 | PASS |
| E3 | $\lvert\text{slope}+1\rvert$ ($L$ 64 to 128), $g^2=0.5/1/2$ | 2.7e-3, 1.0e-3, 4.3e-3 | 2e-2 | measured -0.9973, -1.0010, -1.0043 | PASS |
| E3 | coefficient $128\,\text{dev}$ vs $\tfrac{13}{4g^4}w_{\rm upper}$, relative | 1.69e-3, 0.76e-3, 2.96e-3 | 1e-2 | 0.0017, 0.0008, 0.0030 | PASS |
| E3 | gap to next band minus $4L$ ($L=64$, 128) | -9.52, -9.53 (0.5); -7.25, -7.26 (1); -9.59, -9.60 (2) | in $[-12,0]$ | -7.3 to -9.6 | PASS |
| E3 levels | level count, lowest level vs closed form, multiplicity | 38 432; deviation 0.0; 256 | exact; 1e-10; 256 | | PASS |
| F1 | dimensions (2, 4, 3) for all 16 patterns, Hermitian, $H_{00}$ | all dims right; Hermitian dev 0; $\lvert H_{00}\rvert$ 0 | 1e-12; 1e-10 | | PASS |
| F1 | KS levels reproduced in the two aligned patterns | 1.8e-15 | 1e-10 | 1.8e-15 | PASS |
| F1 | smallest distance of KS levels to the other 14 sectors | 0.6076 | $\ge0.5$ | 0.608 | PASS |
| F2 | $K_1$ only: ground splitting (0.5/1/2) | 1.8e-15, 8.9e-16, 5.1e-15 | 1e-10 | 7e-15 | PASS |
| F2 | $K_1$ only: third minus ground | 7.810, 3.600, 0.8446 | $\ge0.5$ | 7.81, 3.60, 0.845 | PASS |
| F2 | gap slope, $K_2$ only; $r=1$ | 7.00044; 7.02865 | $7\pm0.02$; $7\pm0.06$ | 7.0004; 7.029 | PASS |
| F2 | gap ratio for doubled $b$ | 16.0029 | $16\pm0.32$ | 16.002 | PASS |
| F2 | strong coupling $(E_1-E_0)/32-1$ at $g^2=16$ | -2.71e-6 | 1e-4 | 2.7e-6 | PASS |

### Independent checks (my own code, run after the builder's)

**11.4 rishon blocks.** `rishon_block_sizes()`: 305 blocks, largest 4352, total 38 432 states. This agrees with the locked production routine `rishon.physical.det_sector_structure()` (`blocks["full_det"]` = 305, `max_block["full_det"]` = 4352, dim 38 432; leaving weight $1.6\times10^{-25}$, so no weight is lost when images outside the physical codes are dropped). Operators are real, $H_E$, $H_D$ exactly symmetric, $H_B$ symmetric to $8.9\times10^{-16}$. Peak memory: 403 MB after building the operators, 607 MB after all four-$L$ by three-$g^2$ level computations (limit 1 GB), PASS.

**Rishon to KS limit.** $H=c_EH_E+c_BH_B-L H_D$, $c_E=g^2/2-8L/3$, $c_B=1/g^2$, 433 lowest levels plus $24L$ against my own KS levels ($\tfrac{g^2}2\mathrm{diag}(h_E)+H_B/g^2$ from the spinnet encoding's attributes; the module's `ks_levels` agree with mine to $2.7\times10^{-14}$). Maximum deviation over the 433 levels, $L\in\{32,64,128,256\}$:

| $g^2$ | dev at $L=32$ | 64 | 128 | 256 | $L\cdot$dev at 256 | slope (4 pts / last 3) | $a$ from fit dev $=a/L+b/L^2$ | plan $\tfrac{13}{4g^4}w_{\rm upper}$ | rel. diff fit vs plan |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 0.22035 | 0.11065 | 0.055427 | 0.027738 | 7.1009 | -0.9967 / -0.9980 | 7.1104 | 7.1067 | 5.3e-4 |
| 1.0 | 0.068801 | 0.034356 | 0.017166 | 0.008580 | 2.1964 | -1.0011 / -1.0008 | 2.19589 | 2.19558 | 1.4e-4 |
| 2.0 | 0.023534 | 0.011698 | 0.0058318 | 0.0029116 | 0.74537 | -1.0049 / -1.0032 | 0.74426 | 0.74427 | 1.8e-5 |

So the deviation falls like $1/L$ (slopes within $0.005$ of $-1$) and $L\cdot$dev converges to the predicted coefficient: this is the plan's $\tfrac{13}{4}g^{-4}w_{\rm upper}$ with $w_{\rm upper}=0.5467,\,0.6756,\,0.9160$ the weight of the loop state on the upper level of the KS block (research 006: 0.17 %, 0.08 %, 0.30 % at $L=128$; mine at $L=256$: 0.08 %, 0.04 %, 0.15 %). Gap of level 434 above level 433: $4L-7.26$ to $4L-9.60$, as in the plan. (Note: the plan text writes $13/(4g^4)$, and since $g^4=(g^2)^2$ this is the same as the tests' `(13/4)/g2**2`.) The KS closed block's two levels also occur in the 433-level inner-only spectrum to $\le3.6\times10^{-15}$.

**11.5 isolated plaquette.** 50 states (equals `gauss.isolated_plaquette_count()` = 50, an independent character count), complex128, orthonormality $2.0\times10^{-15}$, gap above the kernel 1.500, kernel eigenvalue max $7.5\times10^{-15}$. Gauss residual by my own tensordot of $\mathcal T^L_A$/$\mathcal T^R_A$ on `gauss.CORNER_ENDS` (all 4 corners, 3 generators, inner ends only): $1.69\times10^{-14}$ against the limit $10^{-12}$ (same as the m9 script's `gauss_residual_dense`: $1.69\times10^{-14}$). The checker is not blind: a random vector has residual ratio 0.71. Basis moved, not changed: against the function in `HEAD:scripts/m9_results.py` the 50 x 65 536 array differs by exactly 0.0, singular values of the 50 x 50 overlap differ from unitary by $4\times10^{-15}$, eigenvalues by 0.0. The m9 splitting row (`splitting_block()` from the modified script) equals `results/fuzzy/splitting.json`: Trotter order-1 vs order-2 error $1.4773130032355548$ in both (difference 0.0), basis Gauss residual and gap identical, all cluster-product rows equal.

**Flavour sectors, own route.** I rebuilt the 65 536 x 65 536 sparse $\sum\mathcal K_1$ and the sparse plaquette (the 256 x 256 row matrix embedded with index map $n=\sum_l(4i_l+j_l)16^l$, Hermitian to 0), built the flavour vacuum and the Krylov subspace of the two generators with my own sparse matvecs, for all 16 sign patterns at $g^2=0.5,1,2$ (48 blocks). My eigenvalues vs `fuzzy_flavour_block`: max difference $7.1\times10^{-15}$. The KS $2\times2$ block $[[0,-2/g^2],[-2/g^2,\tfrac32g^2]]$ appears exactly (difference $\le 10^{-15}$) in exactly 2 of the 16 sectors, $(F_b,F_r,F_t,F_l)=(+,+,-,-)$ and $(-,-,+,+)$, at all three $g^2$; dimensions: 2 sectors of dimension 2, 2 of dimension 4, 12 of dimension 3. In the other 14 the KS levels are at least 0.608 away (4.17 at most).

**Stale-cache analysis.** All three caches are zero-argument or keyed by the arguments they depend on: `_rishon_phys_ops()` and `_fuzzy_isolated_blocks()` have no parameters (the couplings are applied afterwards, outside the cache: `rishon_levels` builds a new `H` per call, `fuzzy_isolated_levels` a new matrix per call), `_flavour_blocks(signs)` is keyed by the sign tuple (`maxsize=None`, 16 entries) and `fuzzy_flavour_block` coerces `signs` to a tuple of ints first. Tested: calls with other coupling sets in between return bit-identical results for the first arguments (rishon, isolated, flavour: all True), different arguments give different results, and mutating a returned flavour block does not change the next call. Remaining risk (not a defect for this step): the private cached sparse matrices and arrays are shared objects, so a future caller that mutates them in place would corrupt later calls; the public functions never do.

### Code review

| item | finding | result |
|---|---|---|
| hard-coded expected numbers | none: only definitions (det amplitude 2, $H_E=\tfrac34\times$ quartet links, 12 links, 65 536, the zero thresholds 1e-9/1e-12/1e-14, Krylov cut 1e-9) | PASS |
| silent exception handling | no `try`/`except`; a non-real physical operator raises `RuntimeError`, bad `signs` raises `ValueError` | PASS |
| dtype | float64 for the real rishon operators, complex128 for the fuzzy ones | PASS |
| caching | see stale-cache analysis | PASS |
| m9 script | imports the function (`from su2plaq.crosscheck.limits import isolated_plaquette_basis`), same object, results unchanged | PASS |
| hashed files / acceptance | `git diff --stat`: only `scripts/m9_results.py`, `crosscheck/limits.py`, one new unit test (plus the other builder's `compress/*` files); no hashed file, no `tests/acceptance` | PASS |

## Observations (not failures)

- O1: `rishon_levels` drops matrix entries below $10^{-12}$ and images that fall outside the union of physical codes without counting them. The locked routine `det_sector_structure` counts the second kind and gives $1.6\times10^{-25}$, and the levels reproduce the closed form to $10^{-16}$, so the effect is negligible; counting them would make the claim self-contained.
- O2: while I ran, a resource accident in my own scratch script (a 65 536 x 65 536 product I wrote by mistake) was killed by the slice cap with no effect on the session; it was my script, not the module. Peak memory of the module is the 607 MB above.
- O3: `HEAD` moved from `a9009ac` to `ea6db4e` between reports 421 and 422; hashes unchanged.

## Counts

passed: 21 acceptance (not slow) + 4 slow + 40 unit; failed: 0; pending: 3 (R1, T1, T2: need steps 11.6 to 11.8). H1 passed, not judged. New failures versus report 421: none. Newly green: E2, E3[0.5, 1.0, 2.0], E3_levels, F1, F2.

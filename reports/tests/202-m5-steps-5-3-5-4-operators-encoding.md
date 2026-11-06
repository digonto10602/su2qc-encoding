# Test report 202 — M5 steps 5.3 + 5.4: rishon inner operators and RishonEncoding

Date: 2026-11-06 · commit `98ae337` (working tree: steps 5.3+5.4 uncommitted: `src/su2plaq/rishon/operators.py`, `rishon/observables.py`, `encodings/rishon.py`, `tests/unit/test_rishon_{operators,encoding,stubs}_unit.py`) · branch `m5-rishon` · prompt in force `prompts/200-rishon-m5-plan.md` (+ `prompts/201` codec-test fix) · lock **acceptance-v8** (commit 4512003) · mode: step · related: `reports/tests/200-…`, `reports/tests/201-…`

**VERDICT: PASS for step 5.3 and for step 5.4.** No failures. 24 other m5 tests are PENDING (steps not yet built).

Note on the codec test: when this run started the lock was acceptance-v7 and `test_M5_C1_encoding_codec_and_vectors` failed at line 35 (`va | outer | (1 << 0)`). I confirmed independently that this was a defect of the test and not of the code: link `b` of `va` is type A = `0b0011`, so `(va|outer|1) == (va|outer)` (checked in Python: `True`; `(va|outer|4) == (va|outer)` is `False`). A patched copy outside `tests/` with `(1 << 2)` in both places passed (1 passed, 8 s). Digonto then approved the fix; the planner re-locked it as acceptance-v8 (`(1 << 2)` at both places) and the unmodified locked test now **passes**. Reported below as a normal 5.4 check.

## Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 10-19`)
```
pytest -n 10 -q tests/acceptance/m5 --junitxml=results/rishon/tester-202-m5.xml   # parsed by tester-202-parse-junit.py
pytest -n 10 -q tests/unit                                                         # 280 (new files: 24)
pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python results/rishon/tester-202-independent-operators.py   # -> results/rishon/tester-202-operators.json (101 s)
python results/rishon/tester-202-independent-encoding.py    # -> results/rishon/tester-202-encoding.json (21 s)
```
No stochastic step except 40 random states / 1500-state sample (seed 20261106, in the JSON).

## 1. Suite results
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| `test_rishon_operators.py` (X1: structure; bright pairs + closed block; target properties × 2 angle sets) | 4 pass | 4 passed | – | PASS |
| `test_rishon_algebra.py` D1 ×2 | pass | 2 passed | – | PASS |
| `test_rishon_physical.py` C1 physical ×3 | pass | 3 passed | – | PASS |
| `test_rishon_codec.py::test_M5_C1_encoding_codec_and_vectors` (v8) | pass | passed | – | PASS (step 5.4) |
| other m5 tests | PENDING only | 24 failed, **all** `PENDING:`, 0 genuine failures | – | PASS (pending) |
| collection | clean, 136 | 136 collected | – | PASS |
| unit (all) | green | 280 passed (37 s); new operators+encoding files 24 passed | – | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed (63 s) | – | PASS |
| `check_lock.py` | OK | `LOCK OK` | – | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v8` | – | PASS |

m5 total 34 = 10 passed + 24 pending. Pending by cause: `build_UB` 6, `build_UE` 3, `build_step` 3 (steps 5.5-5.7); `observables.observables` 3, `closed_spectra` 1 (step 5.8/5.5); `verify.verify` 1 (5.6/5.7); Lean files missing 3 (`Counts.lean`, `JW.lean`, `HB.lean`; 5.L1-5.L3); results files missing 4 (`UE/UB/step/observables.json`; step 5.10). Unit count 280 vs 282 in report 201: the builder replaced the 11+10 "stub raises NotImplementedError" unit cases of the now-built functions (`test_rishon_stubs_unit.py`) by 24 real tests.

## 2. Independent operator checks (step 5.3)
Reference (no `su2plaq.rishon` code): sparse Jordan–Wigner on **all 16 inner modes** with the *global* string $c_k=\big(\prod_{m<k}Z_m\big)\sigma^-_k$ (so link-locality is tested rather than assumed; CAR violation $0.0$), $U_{ij}=c_{L,i}c^\dagger_{R,j}$, $U_P=U_bU_rU_t^\dagger U_l^\dagger$, $W=\sum_{abcd}U^b_{ab}U^r_{bc}(U^t_{dc})^\dagger(U^l_{ad})^\dagger$ on the $2^{16}$ space, restricted to my own 1296 codes (nibble weight 2); $H_B=-(W+W^\dagger)$; Gauss generators from the link coordinates of METHODS §1 (`L` on links starting at the site, `R` on links ending there). Data: `results/rishon/tester-202-operators.json`.

| check | expected | got | tol | verdict |
|---|---|---|---|---|
| own codes = production `inner_codes` | equal | equal | exact | PASS |
| $\max|W_{\rm prod}-W_{\rm own}|$ | 0 | **0.0** (256 non-zeros, all integer) | 1e-12 | PASS |
| $W$ leakage outside the 1296 codes (own, 16-mode) | 0 | 0.0 | 1e-12 | PASS |
| $W$ real; $H_B^{\rm in}$ hermitian; $H_B^{\rm prod}=-(W+W^\dagger)_{\rm own}$ | 0 | 0.0 / 0.0 / 0.0 | 1e-12 | PASS |
| $\max\|[W,G^a_c{}^{\rm in}]\|$ (own $G$, 12 generators), and production $W$ vs own $G$ | 0 | 0.0 / 0.0 | 1e-12 | PASS |
| production `gauss_inner` vs own | 0 | 0.0 | 1e-12 | PASS |
| $W^3$ (heights raise by 1) | 0 | 0.0 | 1e-12 | PASS |
| $H_E$ per link: $\mathbf L^2=\mathbf R^2$, values | $\{0,\tfrac34\}$ ($j(j+1)$), $\tfrac34$ on Q | $\{0.0,0.75\}$; $L^2$–$R^2$ diff 0.0; $|H_E-\tfrac34\#Q|=0$ | 1e-12 | PASS |
| production `h_electric_inner` vs own Casimir sum | 0 | 0.0 | 1e-12 | PASS |
| spectrum of $H_B^{\rm in}$ | $\pm4\sqrt2$(1), $\pm2$(48), $\pm1$(32), 0(1134) | exactly these multiplicities (±5.6568542: 1, ±2: 48, ±1: 32, 0: 1134) | 1e-7 rounding | PASS |
| bright pairs: 81; $\kappa$ multiset (own, from graph components of $H_B$) | $\{1{:}32,\,2{:}48,\,4\sqrt2{:}1\}$ | own and production both $\{1.0{:}32,\,2.0{:}48,\,5.656854249{:}1\}$ | 1e-9 | PASS |
| $\|H_B+\sum_p\kappa_p(|u\rangle\langle v|+{\rm h.c.})\|$; orthonormality of 162 vectors | 0 | $6.7\times10^{-16}$; $4.4\times10^{-16}$ | 1e-10 | PASS |
| amplitudes of $u,v$ | $\subset\{1,\tfrac1{\sqrt2},\tfrac12,\tfrac14\}$ | $\{0.25,0.5,0.7071,1.0\}$ | 1e-9 | PASS |
| documented sign convention ($u$'s first max-modulus entry $>0$) | true | true | – | PASS |
| `inner_target('UB')` vs `expm(-iβH_B)` (own $H_B$), (0.37, 0.61) | 0 | $4.4\times10^{-16}$ | 1e-10 | PASS |
| same, (1.70, 1.00) | 0 | $8.3\times10^{-16}$ | 1e-10 | PASS |
| `UE` vs $\mathrm{diag}(e^{-i\alpha H_E})$ (both angle pairs) | 0 | 0.0 | 1e-12 | PASS |
| step order 1 $=U_BU_E$ / order 2 $=U_E(\alpha/2)U_BU_E(\alpha/2)$ vs own expm, both pairs | 0 | $\le8.2\times10^{-16}$ | 1e-12 | PASS |
| unitarity of $U_B$; $[U_B,G]$ | 0 | $\le1.3\times10^{-15}$; $\le2.2\times10^{-16}$ | 1e-10 | PASS |
| closed block: $\langle{\rm loop}|W|{\rm vac}_A\rangle=\langle{\rm vac}_B|W|{\rm loop}\rangle$, $\|W{\rm vac}_A\|$, nnz | 4, 4, 4 / 16 | 4.0, 4.0, 4.0 / 16; loop codes all type Q and = production `closed_codes`; $W^\dagger{\rm vac}_A=0$, $W{\rm vac}_B=0$ | 1e-12 | PASS |
| `closed_block(g2)` vs own block vs METHODS-rishon formula $\tfrac{g^2}2\mathrm{diag}(0,3,0)-\tfrac4{g^2}\mathrm{adj}$, $g^2\in\{0.5,1,2\}$ | 0 | 0.0 for both | 1e-12 | PASS |
| eigenvalues of the block vs $0,\ \tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+32g^{-4}}$ | 0 | $\le2.5\times10^{-15}$ (g²=0.5: −10.9449, 0, 11.6949; 1: −4.9564, 0, 6.4564; 2: −1.7016, 0, 4.7016) | 1e-10 | PASS |
| 3-dim span invariant under the *full* inner $H(g^2)$ | residual 0 | 0.0; the three eigenvalues also lie in the spectrum of the full 1296 matrix | 1e-9 | PASS |

**What the closed-sector formula refers to:** the 3×3 block in $\{|{\rm vac}_A\rangle,|{\rm loop}\rangle,|{\rm vac}_B\rangle\}$ (per outer singlet choice, from the *rishon* theory, coupling $4$ not $2$). The eigenvalue $0$ is the antisymmetric combination $|{\rm vac}_A\rangle-|{\rm vac}_B\rangle$; the formula $\tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+32/g^4}$ is the roots of $\lambda^2-\tfrac{3g^2}2\lambda-2(4/g^2)^2=0$ (the factor 2 from two couplings, hence 32 rather than the KS value 4). Correct.

### Dark-code reconciliation (990 vs 1134)
Both numbers are right and refer to different things; nothing is inconsistent. Components of the graph $\{|H_B|_{ij}>0\}$ (own): sizes $1\times990,\ 2\times32,\ 4\times16,\ 5\times32,\ 18\times1$ (total $990+64+64+160+18=1296$). 
* **990** = isolated codes (rows/columns of $H_B$ identically zero; production `dark_codes()` equals my isolated set exactly). The plan's text "990 dark" and test assertion `len(dark)==990` use this definition.
* **1134** = total multiplicity of eigenvalue 0 $=1296-2\times81$ $=990+144$, where 144 are the zero modes *inside* the non-isolated components ($16\times2+32\times3+16$). STATUS's "1134 dark" is the spectral multiplicity, not the dark-code count. 81 bright pairs use 162 of the 306 non-isolated dimensions.
The "16 loop codes" are part of the single 18-code component ($\kappa=4\sqrt2$: 16 loop + vac$_A$ + vac$_B$).

### KS reference `ks_closed_block`
`ks_closed_block(g2)` returns `[[0,-2/g2],[-2/g2,3*g2/2]]`, a closed formula in $g^2$ quoted from METHODS §4 (Paulo Eq. 37), not a number table and not derived from any run. I judged it by comparing with the laptop's exact KS Hamiltonian: block of `hamiltonian_phys(physical_basis(), g2)` on the two states with all outer $j=0$ (labels all-zero and $j_{\rm inner}=\tfrac12$): maximum difference of entries $8.9\times10^{-16}$ ($g^2=0.5$), $4.4\times10^{-16}$ (1), $2.2\times10^{-16}$ (2); eigenvalues also equal $\tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+4g^{-4}}$ to $1.7\times10^{-16}$. The formula is therefore a **correct, documented reference formula** (planner-specified "independent of exact.operators"), not a hard-coded wrong/unchecked answer; no tuning to a test. Mild remark (not a defect): it cannot detect a change of the KS convention by itself, which is what test O1 (pending) compares against `hamiltonian_phys`.

## 3. Independent encoding checks (step 5.4)
Data: `results/rishon/tester-202-encoding.json`; reference: own 16-mode $W$ (above), own 2-mode JW end generators $\sum_{ij}T^a_{ij}c^\dagger_ic_j$ applied with bit operations to the production COO states (all 38 432), geometry from METHODS §1 coordinates.

| check | expected | got | tol | verdict |
|---|---|---|---|---|
| decode valid set over all 65 536 inner bit patterns (outer = near-empty code of the closed vacuum, `0xc3cc3c33`) | = my 1296 codes | 0 mismatches | exact | PASS |
| decoded types of the 4 inner links = nibble classification A/B/Q | all | 0 mismatches | exact | PASS |
| `inner_codes()` sorted, unique, int64, equal own | true | true | exact | PASS |
| valid nibbles per outer link | 4 (A, B, Q-colour 1, Q-colour 2) | 4 on each of the 8 | exact | PASS |
| codes $\ge2^{48}$ or negative | invalid | `None` | – | PASS |
| `decode` is injective on the 1296 codes? | – | **No, by design:** it returns the 12 link types (3 values per link) so there are 81 distinct decodes; the colour label (4 Q patterns) lives in the code itself. The code↔state map is the identity on the 1296 sorted codes; `decode_state` is the identity on valid codes and raises `ValueError` otherwise (also tested in the acceptance test) | – | informational |
| `physical_vectors('all')` count | 38 432 | 38 432 | exact | PASS |
| norms | 1 | max $|{\|\psi\|-1}|=1.8\times10^{-15}$ | 1e-12 | PASS |
| every key of every state decodes as valid | all | all (checked on all ~5·10⁵ keys, test only samples 200 states) | exact | PASS |
| Gauss residual, own end generators, all 38 432 states × 4 corners × 3 colours | ≤ 1e-10 | **$2.3\times10^{-16}$** | 1e-10 | PASS |
| Gram matrix of all 38 432 states minus identity | 0 | $8.0\times10^{-15}$ | 1e-10 | PASS |
| `closed` = 17 states, equal to `closed_indices(basis)`, all share one outer code | true | true; $\|B B^\dagger-1\|=6.7\times10^{-16}$ | 1e-10 | PASS |
| `target(kind, states=closed)` shape and unitarity ($U_B$, $U_E$, step 1, step 2 at (0.37, 0.61) and (1.70, 1.00)) | 17×17, $\|V^\dagger V-1\|\le10^{-10}$ | 17×17; $\le2.4\times10^{-15}$ | 1e-10 | PASS |
| same targets vs $B^*V_{\rm own}B^T$ with *my* $V_{\rm own}$ from expm of my $H_B$, closed states built from the keys | 0 | $\le1.1\times10^{-15}$ (all 8) | 1e-10 | PASS |
| closed subspace invariant under $V_{\rm in}$ (outer spectator) | residual 0 | $2.6\times10^{-16}$ | 1e-10 | PASS |
| `target(step, states=<40 random states>)` vs own outer-pattern-resolved assembly (seed 20261106) | 0 | $4.4\times10^{-16}$ | 1e-10 | PASS |
| `target(..., states=None)` | `ValueError` | `ValueError` (acceptance test) | – | PASS |
| `inner_view`: 1296 single-code states, `is_basis_encoding`, `layout_of` | as locked test | true | – | PASS |
| `RISHON_NOMINAL` | (0.37, 0.61) | (0.37, 0.61) | exact | PASS |

## 4. Repository hygiene
* `git status --short`: modified `src/su2plaq/encodings/rishon.py`, `src/su2plaq/rishon/{operators,observables}.py`, `tests/unit/test_rishon_stubs_unit.py`; new `tests/unit/test_rishon_{operators,encoding}_unit.py` and my `results/rishon/tester-202-*`. Nothing under `tests/acceptance/`, `docs/`, `notes/`, `prompts/`, `src/su2plaq/encodings/base.py` or other laptop-owned files; `check_lock` and `acceptance-check` PASS. `RISHON_NOMINAL` lives in the rishon module as planned (base `NOMINAL_ANGLES` untouched).
* The only edit to a shared-looking unit file (`test_rishon_stubs_unit.py`) deletes stub-raises cases for functions that are now implemented; their coverage is replaced by the new unit files (not a weakening).
* Hard-coded numbers in source: none standing for results. Constants: $\tfrac34$ per Q link in `h_electric_inner` (the definition $j(j+1)$ at $j=\tfrac12$, verified against my own Casimir $\mathbf L^2$ of the JW operators: values $\{0,0.75\}$), `_TOL=1e-12` structural tolerances, height tables (checked indirectly by $W^3=0$ and by the locked test against `_ref`). `ks_closed_block` discussed in §2. "990" appears only in docstrings; `dark_codes()` is computed from the graph.
* Exceptions: grep over the three source files finds no `try/except`; failures raise `ValueError` (sector non-preserving, non-real $W$, bad bright component, invalid code, bad order/kind). No silent catching.
* `affected` for `plaquette_W_inner` in graphify: no dependents recorded yet; the call sites (`encodings/rishon.py::target`, `inner_target`) are exercised by the tests above.

## Failures
None. (Cause-of-failure guess not needed.)

## Files
`results/rishon/tester-202-operators.json` · `tester-202-encoding.json` · `tester-202-m5-outcomes.json` · scripts `tester-202-independent-operators.py`, `tester-202-independent-encoding.py`, `tester-202-parse-junit.py`, logs `tester-202-*.log`, raw `tester-202-m5.xml`. Scratch copy of the patched v7 codec test (superseded by v8): scratchpad `patched/test_codec_patched.py`.

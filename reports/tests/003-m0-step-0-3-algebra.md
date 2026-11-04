# Tester report 003: M0 step 0.3 (link algebra, 6j / F-symbol, Paulo adapter)

- Date: 2026-11-04. Commit: `76fee39` (HEAD; the step-0.3 files are uncommitted in the working tree: `src/su2plaq/su2/algebra.py`, `wigner.py`, `tests/unit/test_su2.py`, `tests/unit/test_geometry_unit.py` (renamed), `tests/unit/test_import.py`).
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`, step 0.3. Conventions: `docs/METHODS.md` §3, §3.1, §5. Mode: **step**.
- Related: `reports/tests/001-m0-step-0-1-scaffold.md`, `reports/tests/002-m0-step-0-2-geometry.md`.
- Raw numbers: `results/tester_m0_step03_algebra.json` (script: tester scratch `verify_step03.py`, seed 12345 for the random 6j sample, quadrature 12 x 24 x 40 nodes).

## Commands
```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "f_symbol" / "paulo_adapter"
pytest -n auto tests/unit                       # 54 passed
pytest -n auto tests/acceptance/m0/test_algebra.py -v    # 4 passed
pytest -n auto -m "not slow" tests/acceptance -q          # 6 passed, 78 failed (75 PENDING + 3 known M1-R1 AssertionError)
pytest tests/acceptance -p no:xdist -q --tb=line          # full incl. slow: identical 6 passed / 78 failed
python tools/check_lock.py ; ~/.claude/bin/acceptance-check   # LOCK OK ; PASS (acceptance-v2)
pytest --collect-only -q tests/acceptance                 # 84 collected, clean
python -W ignore verify_step03.py                         # independent physics checks (below)
```
`graphify affected` lists, for `f_symbol` and `paulo_adapter`, only `tests/unit/test_su2.py` and the acceptance tests A2/A3, all run above.

## Test results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| unit tests (`tests/unit`) | all pass | 54 passed | - | PASS |
| `test_M0_A1_link_algebra[0.5]`, `[1.0]` | pass | pass, pass | 1e-12 | PASS |
| `test_M0_A2_six_j_vs_sympy` | pass | pass | 1e-13 | PASS |
| `test_M0_A3_paulo_adapter` | pass | pass | 1e-14 | PASS |
| `test_M0_G1_diagram`, `G2_point_split` (regression) | pass | pass, pass | - | PASS |
| other acceptance tests | PENDING (`NotImplementedError ... not built yet`) | 75 PENDING | - | PENDING (not failures in step mode) |
| `test_M1_R1_results_files[UE|UB|step]` | known AssertionError (results files missing) | same 3 | - | known, unchanged |
| lock (`check_lock.py`, `acceptance-check`) | pass | LOCK OK / PASS | - | PASS |
| vendored code vs skqd `su2.py` @ eda63c1a | identical | only differs by one type annotation on `SIGMA` | - | PASS |

New failures versus report 002: none. (Counts: 6 passed = A1x2, A2, A3, G1, G2; 78 = 75 PENDING + 3 known; total 84.)

## Independent physics checks (own script, not the builder's tests)
Reference for $U$: Haar-measure quadrature of $\langle j'm_L'm_R'|U_{ij}|jm_Lm_R\rangle=\int dU\,\overline{\sqrt{2j'+1}D^{j'}_{m_L'm_R'}}\,D^{1/2}_{ij}\,\sqrt{2j+1}D^{j}_{m_Lm_R}$ with explicit Euler-angle Wigner matrices $D^j=e^{-i\alpha J_z}e^{-i\beta J_y}e^{-i\gamma J_z}$ (exact quadrature; orthonormality of the nodes checked to 1e-13). Generators $L_a=-J_a^{\mathsf T}\otimes 1$, $R_a=1\otimes J_a$ rebuilt independently with `kron`.

| check | expected | got (max abs deviation) | tolerance | verdict |
|---|---|---|---|---|
| (1) $U_{ij}$ from `LinkSpace.U()` vs Haar quadrature, $j_{\max}=\tfrac12,1,\tfrac32$ | 0 | 4.4e-16, 8.6e-16, 8.9e-16 | 1e-12 | PASS |
| (1) closed form $\langle0|U_{ij}|\tfrac12 m_Lm_R\rangle=\tfrac1{\sqrt2}s(m_L)s(m_R)\delta_{i,-m_L}\delta_{j,-m_R}$ | 0 | 2.2e-16 | 1e-12 | PASS |
| (1) closed form $\langle\tfrac12 m_Lm_R|U_{ij}|0\rangle=\tfrac1{\sqrt2}\delta_{i,m_L}\delta_{j,m_R}$ | 0 | 1.1e-16 | 1e-12 | PASS |
| (1) $[L_a,U_{ij}]=-(T_aU)_{ij}$, $[R_a,U_{ij}]=+(UT_a)_{ij}$ (own $L,R$), $j_{\max}=\tfrac12,1,\tfrac32$ | 0 | 0, 1.1e-16, 1.9e-16 | 1e-12 | PASS |
| (1) Casimirs $\sum L^2=\sum R^2=j(j+1)$ | 0 | 0, 4.4e-16, 4.4e-16 | 1e-12 | PASS |
| (1) `generators()` equals own `kron` $L,R$; su(2) algebra, $[L,R]=0$, Hermiticity | 0 | 0 / 0 / 2.2e-16 | 1e-12 | PASS |
| (1) $U_{ij}^\dagger=s(i)s(j)U_{\bar i\bar j}$; $\det U=1$ and $\sum_kU_{ki}^\dagger U_{kj}=\delta_{ij}$ on low-spin subspace ($j_{\max}=1,\tfrac32$); $[U_{ij},U_{kl}]=0$ | 0 | $\le$ 8.9e-16 | 1e-12 | PASS |
| (2) `six_j` vs sympy `wigner_6j`, all admissible arguments $\le2$ (570 admissible tuples, $9^6$ scanned) | 0 | 5.6e-17 | 1e-13 | PASS |
| (2) inadmissible tuples return exactly 0 | 0 nonzero | 0 nonzero | exact | PASS |
| (2) 300 random admissible tuples, arguments up to 4 | 0 | 5.6e-17 | 1e-13 | PASS |
| (2) orthogonality $\sum_x(2x+1)(2f+1)\{a\,b\,x;c\,d\,f\}\{a\,b\,x;c\,d\,f'\}=\delta_{ff'}$ (855 cases) | 0 | 4.4e-16 | 1e-13 | PASS |
| (2) tetrahedral symmetries (column/row-pair swaps), Racah sum rule | 0 | 5.6e-17, 4.4e-16 | 1e-13 | PASS |
| (3) `f_symbol` matrix (over $j_{12}\times j_{23}$) orthogonal, 112 matrices, spins $\le\tfrac32$ | $FF^{\mathsf T}=1$ | 4.4e-16 | 1e-13 | PASS |
| (3) `f_symbol` vs METHODS §5 formula $(-1)^{j_1+j_2+j_3+J}\sqrt{(2j_{12}+1)(2j_{23}+1)}\{\cdot\}$ using sympy 6j | 0 | 2.2e-16 | 1e-13 | PASS |
| (3) `f_symbol` vs direct overlap $\langle(j_1j_2)j_{12},j_3;J|j_1,(j_2j_3)j_{23};J\rangle$ from sympy CG sums (270 elements; fixes the overall sign) | 0 | 3.3e-16 | 1e-13 | PASS |
| (4) Paulo states $|mm'\rangle_P=\sqrt2\,\overline{D^{1/2}_{mm'}}$, $|0\rangle_P=1$ orthonormal (Haar) | 0 | 4.4e-16 | 1e-13 | PASS |
| (4) `paulo_U()` vs first-principles Haar matrix elements in Paulo's basis | 0 | 2.2e-16 | 1e-14 | PASS |
| (4) `paulo_U()` vs Eq. 28 rules (PDF p. 5) element by element, incl. dagger rules | 0 | 0 | 1e-14 | PASS |
| (4) `paulo_adapter()` vs METHODS §3.1 formula (independent build); $V_P=V_P^{\mathsf T}=V_P^{-1}$; entries in $\{0,\pm1\}$ | exact | 0 / 0 / True | exact | PASS |
| (4) $V_PU^{\rm CG}_{ij}V_P^{\mathsf T}=\tilde U_{ij}$ for all four $(i,j)$ | 0 | 2.2e-16 | 1e-14 | PASS |
| (4) same, with $U^{\rm CG}$ from Haar quadrature (independent of `LinkSpace`) | 0 | 1.1e-16 | 1e-14 | PASS |
| (4) $V_P|{\rm CG}_c\rangle$ as wavefunctions equals $|k\rangle_P$ | 0 | 3.1e-16 | 1e-13 | PASS |
| (4) 625-dim plaquette $W$: $V_P^{\otimes4}W^{\rm CG}V_P^{\otimes4\,\mathsf T}$ vs $W$ built from $\tilde U$ | 0 | 3.1e-16 | 1e-13 | PASS |
| (4) Paulo Eq. 29: $\|\tilde W|0000\rangle\|$ = 1, 16 equal components of magnitude 1/4, no overlap with $|0000\rangle$ | 1, 16, 0.25, 0 | 0.9999999999999996, 16, 0.25, 0 | 1e-12 | PASS |

## Verdict: PASS
No failing checks. All deviations are at the level of one or two float64 roundings ($\le 9\times10^{-16}$), far below the tolerances.

## Notes (not failures)
- `test_geometry.py -> test_geometry_unit.py` rename: no collision with `tests/acceptance/m0/test_geometry.py` remains; both run (unit 54 passed, acceptance G1/G2 pass).
- `f_symbol` argument order is `(j1, j2, j12, j3, J, j23)`; the plaquette call pattern $F^{J_c\,j_p\,j_n}_{1/2\,j'_n\,j'_p}$ of METHODS §5 must be mapped to that order in step 0.x (spin network); not testable at this step.
- `U` is only correct as a product of operators within the truncation (e.g. $\det U=1$ holds only on states with $j\le j_{\max}-1$); this is inherent to the truncation, not a bug.

# Test report 005 — M0 step 0.5, exact operators $W$, $H_E$, $H_B$, targets

- Date: 2026-11-04
- Commit: 3c8cb88 (step files uncommitted: `src/su2plaq/exact/operators.py`, `tests/unit/test_operators_unit.py`)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`, §2.4 operators, §3 row 0.5; method `docs/METHODS.md` §2, §4
- Mode: step
- Related: `reports/tests/004-m0-step-0-4-physical-states.md`
- Raw numbers: `results/tester_m0_step05_operators.json` (no RNG; script is deterministic); independent script `tests/independent/check_operators_0_5.py` (not collected by pytest, added by the tester; ~5 s)

## Commands

```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify query "plaquette_W h_magnetic_phys target" ; graphify affected "h_magnetic_phys"
pytest -n auto tests/unit -q
pytest -n auto tests/acceptance/m0/test_operators.py -q
pytest -n auto -m "not slow" tests/acceptance/m0 -q ; pytest -n 0 -m "not slow" tests/acceptance/m0 -q --tb=line     # classify the failures
pytest -n 0 tests/acceptance/m1 tests/acceptance/m2 -q --tb=line
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
python tests/independent/check_operators_0_5.py
```

`graphify affected h_magnetic_phys` lists `hamiltonian_phys`, `target` and the 3 tests in `tests/unit/test_operators_unit.py`; all ran and pass. (`plaquette_W`, `target` have no unique graph node; their callers are the same functions and the acceptance tests.)

## Verdict: PASS

## Test results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests (`tests/unit`) | all pass | 66 passed, 6.6 s | - | PASS |
| M0-X2 plaquette leak, $W$ shape, $\lVert W e_0\rVert=1$ | pass | pass | leak $\le10^{-10}$ | PASS |
| M0-X3 hermitian, $H_E$ spectrum | pass | pass | $10^{-12}$ | PASS |
| M0-X7 closed block, $g^2=0.5,1,2$ | pass | 3 passed | $10^{-12}$ | PASS |
| M0-X8 target properties | pass | pass | $10^{-12}$ | PASS |
| earlier m0 tests (A1 x2, A2, A3, G1, G2, C1-C5, X1; C6 slow excluded here, run in 004) | pass | 18 passed in the non-slow m0 run (incl. the 6 operator tests) | - | PASS |
| `tools/check_lock.py`, `acceptance-check`, collect-only | OK, 84 tests | LOCK OK; PASS (matches acceptance-v2); 84 collected | - | PASS |
| m0 remaining failures | PENDING only | 14 failed, all `PENDING: NotImplementedError` (list below) | - | PENDING (not failure) |
| m1+m2 | PENDING + known R1 | 51 failed = 48 PENDING + 3 "missing results/twelve/{UE,UB,step}.json" | - | PENDING / known M1-R1 |

### The 14 remaining m0 failures, by message (all PENDING)

| count | test ids | message |
|---|---|---|
| 3 | E3, E4, E5 (`test_evaluator.py`) | `TwelveQubit is not built yet` |
| 1 | M1 (`test_metrics.py`) | `logical_metrics is not built yet` |
| 3 | M2 band $\varepsilon=10^{-4},10^{-6},10^{-8}$ | `pygridsynth_word is not built yet` |
| 1 | M3 | `ct_compile is not built yet` |
| 1 | R1 (`test_results.py`) | `save_result is not built yet` |
| 2 | E1, E2 (`test_sparse_sim.py`) | `run_batch is not built yet` |
| 3 | X4, X5, X6 (`test_spinnet.py`) | `h_magnetic_phys_6j is not built yet` (route-B operator, belongs to the next step) |

m1+m2: 17 `TwelveQubit`, 23 `default_spec`, 4 `gridsynth_T`, 2 `Archive.load`, 1 `code_hash`, 1 `logical_metrics` (all not-built) + 3 M1-R1 (`results/twelve/{UE,UB,step}.json` missing: will exist once the 12-qubit run is saved). No genuine failure.

## Independent physics (own script; builder's objects used only as input vectors or as the thing compared)

Own pieces: hand-built $5\times5$ link matrices (CG convention from $D^{1/2}_{ij}D^{1/2}_{kl}$ singlet part $\tfrac12\epsilon_{ik}\epsilon_{jl}$; Paulo Eq. 28 rewritten), own contraction $W=\sum_{abcd}U_b[a,b]\,U_r[b,c]\,(U_t^\dagger)[c,d]\,(U_l^\dagger)[d,a]$ with $(U^\dagger)[c,d]=(U[d,c])^\dagger$ (loop $U_P=U_bU_rU_t^\dagger U_l^\dagger$, link 0 least significant), own sparse $\Psi$ and own $A=\Psi^\dagger(W\otimes1)\Psi$, own Gauss generators, own `expm`.

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| (1) $\max\lvert W_{\rm builder}-W_{\rm own}\rvert$, cg | 0 | $3.1\times10^{-16}$ | $10^{-12}$ | PASS |
| (1) same, paulo | 0 | $0$ | $10^{-12}$ | PASS |
| $\max\lvert$`LinkSpace.U` $-$ own hand-built $U\rvert$ | 0 | $2.2\times10^{-16}$ | $10^{-12}$ | PASS |
| (1) Eq. 37: $W\lvert0000\rangle$ norm; #nonzero; $\lvert$amp$\rvert$ | 1; 16; $1/4$ | 1.000000000000001 (cg), 1.000000000000000 (paulo); 16; 0.250000/0.250000 (min/max); all inner links $j=\tfrac12$ | $10^{-12}$ | PASS |
| (2a) $\max\lvert[W,G^a_c|_{\rm inner}]\rvert$, 4 corners x 3 colours, 625-space | 0 | $0$ (exact) | $10^{-12}$ | PASS |
| (2a) negative control: $W$ with open index $a$ (not a trace), $\sigma_x$ at corner (0,0) | $\gg10^{-10}$ | $0.125$ | - | PASS (test can fail) |
| (2b) leak $\max_k\lVert W\psi_k-\Psi\Psi^\dagger W\psi_k\rVert$ (own) | $\le10^{-10}$ | $1.2\times10^{-15}$ | $10^{-10}$ | PASS |
| (2b) leak $\max_k\lvert\lVert W\psi_k\rVert^2-\sum_{k'}\lvert A_{k'k}\rvert^2\rvert$ (own); builder's `h_magnetic_phys` leak | $\le10^{-10}$ | $1.3\times10^{-15}$; **$1.1\times10^{-15}$** | $10^{-10}$ | PASS |
| (2b) $\max\lvert H_B^{\rm builder}-H_B^{\rm own}\rvert$ | 0 | $2.7\times10^{-15}$ | $10^{-12}$ | PASS |
| **$\lVert H_B-H_B^\dagger\rVert_{\max}$** (433x433) | 0 | **0 (exactly)**; $\max\lvert{\rm Im}H_B\rvert=0$ (real symmetric) | $10^{-12}$ | PASS |
| (2c) Gauss residual of $(W\otimes1)\psi_k$, all 12 links, 4 corners x 3 colours, 87 states (every 5th) | 0 | $3.3\times10^{-16}$ | $10^{-10}$ | PASS |
| (3) $\langle16\vert W\vert0\rangle$, $\langle16\vert W^\dagger\vert0\rangle$ | 1, 1 | $1.000000000000$, $1.000000000000$ (so $H_B$ off-diagonal $=-2$) | $10^{-12}$ | PASS |
| (3) $W\psi_0$ has support on the physical states | one state | only index 352 ($=\lvert16\rangle$), $\lvert A\rvert=1$ | - | PASS |
| (3) closed block at $g^2=0.5,1,2$ vs $\begin{psmallmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{psmallmatrix}$ | equal (sign: same, $-$) | $[[0,-4],[-4,0.75]]$, $[[0,-2],[-2,1.5]]$, $[[0,-1],[-1,3]]$; dev $8.9\times10^{-16}$, $4.4\times10^{-16}$, $2.2\times10^{-16}$ | $10^{-12}$ | PASS |
| (3) coupling of the 2 closed states to the other 431 | 0 | $0$ (exact) | exact | PASS |
| (5) targets UE, UB, step1, step2, step1+outer, step2+outer vs own `expm` products | 0 | $0$, $1.6\times10^{-15}$ (UB, S1, S2, S1o, S2o) | $10^{-12}$ | PASS |
| (5) **unitarity** $\max\lvert U^\dagger U-1\rvert$: UE, UB, S1, S2, S1o, S2o | $\le10^{-12}$ | $2.5\times10^{-17}$, $2.2\times10^{-16}$, $4.4\times10^{-16}$, $2.4\times10^{-16}$, $4.4\times10^{-16}$, $4.4\times10^{-16}$; $\lvert\det\rvert$ UB, S2 $=1+1\times10^{-15}$, $1+1.8\times10^{-14}$ | $10^{-12}$ | PASS |
| (5) group property $U_B(0.25)U_B(0.36)-U_B(0.61)$ | 0 | $1.5\times10^{-15}$ | $10^{-12}$ | PASS |

### (3) Where the numbers come from

- $3g^2/2$: $H_E^{\rm inner}$ on the all-$\tfrac12$ state is $4\times j(j+1)=4\times\tfrac34=3$ (measured 3.0), times $g^2/2$ gives $\tfrac{g^2}{2}\cdot4\cdot\tfrac34=\tfrac{3g^2}{2}$. Confirmed. $H_E^{\rm inner}|0000\rangle=0$.
- $-2/g^2$: $H_B=-(W+W^\dagger)$; measured $\langle16|W|0000\rangle=+1$ and $\langle16|W^\dagger|0000\rangle=+1$ (each term of ${\rm Tr}\,U_P+{\rm h.c.}$ maps $|0000\rangle$ to the same unit-norm state, which is the normalised 16-term superposition of Eq. 37, 16 components of $1/4$, $16\times\tfrac1{16}=1$). The sum is $2$, so the off-diagonal is $-2$, times $1/g^2$. The sign comes out $-$ in this convention (not just up to sign).

### (4) Spectrum of $H_B^{\rm phys}$ (433 states, trace $-2.8\times10^{-14}$)

| eigenvalue | multiplicity |
|---|---|
| $-2$ | 16 |
| $-1$ | 96 |
| $-\tfrac12$ | 16 |
| $0$ | 177 |
| $+\tfrac12$ | 16 |
| $+1$ | 96 |
| $+2$ | 16 |

Sum of multiplicities 433. Exactly symmetric under $\lambda\to-\lambda$ (traceless, consistent with a bipartite $j=0\leftrightarrow\tfrac12$ structure of $W$ on the inner links). Paulo-convention basis: identical spectrum and multiplicities, max eigenvalue difference $1.8\times10^{-15}$, leak $1.2\times10^{-15}$, hermiticity 0.

### (5) Order-1 vs order-2 target

$\lVert[H_B,H_E^{\rm inner}]\rVert_2=6.000000$. Leading prediction $\lVert U_2-U_1\rVert\approx\tfrac12\alpha\beta\lVert[H_B,H_E]\rVert$ (from $e^Xe^Y=e^{X+Y+\frac12[X,Y]}$).

| scale $s$ | $(\alpha,\beta)$ | $\lVert U_2-U_1\rVert_2$ | $\tfrac12\alpha\beta\lVert[H_B,H_E]\rVert$ | ratio |
|---|---|---|---|---|
| 1 | (0.3700, 0.6100) | $5.1454\times10^{-1}$ | $6.771\times10^{-1}$ | 0.760 |
| 1/2 | (0.1850, 0.3050) | $1.5846\times10^{-1}$ | $1.6928\times10^{-1}$ | 0.936 |
| 1/4 | (0.0925, 0.1525) | $4.1632\times10^{-2}$ | $4.2319\times10^{-2}$ | 0.984 |
| 1/8 | (0.0462, 0.0762) | $1.0537\times10^{-2}$ | $1.0580\times10^{-2}$ | 0.996 |

Successive slopes $\log_2[\,\mathrm{err}(s)/\mathrm{err}(s/2)\,]=1.699,\ 1.928,\ 1.982$ (approach 2 from below as the next-order terms die); fitted log-log slope over the four points $=1.876$. Ratio $\to1$ confirms the coefficient, not only the exponent. Extra check: local error against the exact $e^{-i(\alpha H_E+\beta H_B)}$: order 1 slope $1.908$ (expect 2), order 2 slope $2.921$ (expect 3), values order 1 $5.5\times10^{-1},1.6\times10^{-1},4.2\times10^{-2},1.05\times10^{-2}$; order 2 $2.4\times10^{-1},3.4\times10^{-2},4.4\times10^{-3},5.5\times10^{-4}$.

## Notes (no failures)

- `h_magnetic_phys_6j` is still a stub: X4-X6 stay PENDING until the route-B step.
- Bug-class checks that were NOT possible to break: the commutator with the inner part of $G_c$ is exactly 0 (not just $<10^{-12}$) because truncation to $j\le\tfrac12$ commutes with the generators; the negative control (open index) gives $0.125$, so the test has teeth.
- `include_outer_electric` is applied to both $U_E$ factors in the order-2 formula, as the acceptance test X8 requires; verified separately here ($1.6\times10^{-15}$).
- Step files are still uncommitted; this report is for the working tree on top of 3c8cb88.

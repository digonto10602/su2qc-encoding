# Plan 301 — M9 amendment: two approved fixes to the locked acceptance tests (acceptance-v8 -> v9)

Date: 2026-11-06. Planner (Claude Fable 5.1). Amends `prompts/300-fuzzy-m9-plan.md` (§4 M9-O1, M9-K1); nothing else in plan 300
changes. Trigger: coordinator finding during step 9.6/9.7 (`notes/STATUS.md` Decisions 2026-11-06) that two locked assertions
were wrong or infeasible; Digonto approved exactly these two changes in chat on 2026-11-06.

## 1. Diagnosis

### 1.1 `tests/acceptance/m9/test_fuzzy_observables.py::test_M9_O1_definitions_and_identities`
The locked line asserted `abs(ob.one_step_plaquette(alpha, beta, 0.0, order=2)) <= 1e-10`. This is a planner error: the
docstring (and plan 300 §4 M9-O1, METHODS-fuzzy F7) state the identity for the **first-order** step
$U = U_B U_K U_E$, where $U_E, U_K$ are phases on the vacuum and $U_B$ commutes with the plaquette, so
$\langle\Omega|U^\dagger \mathrm{Re\,Tr}\,U_P\, U|\Omega\rangle = \langle\Omega|\mathrm{Re\,Tr}\,U_P|\Omega\rangle = 0$.
For the symmetric order-2 step $U_E(\alpha/2)U_K(\kappa_2/2)U_B U_K(\kappa_2/2)U_E(\alpha/2)$ the outer kinetic half-layers act
on $U_B|\Omega\rangle$, which is not a kinetic eigenstate, and the value is $O(\alpha\beta)$, not zero. Measured with the
production `one_step_plaquette` (this session, verified before writing the test):

| $(\alpha,\beta)$ | order 2, $r=0$ | order 2, $r=1$ | order 1, $r=0$ | order 1, $r=1$ |
|---|---|---|---|---|
| (0.37, 0.61) nominal | 0.03477 | -0.36155 | -1.1e-16 | -1.2e-16 |
| (0.05, 0.05) | 0.014738 | 0.071528 | -1.4e-16 | -1.2e-16 |
| (0.025, 0.025) | 0.0037335 | 0.018530 | -1.5e-16 | -1.5e-16 |
| (0.0125, 0.0125) | 0.00093647 | 0.0046737 | -1.6e-16 | -1.6e-16 |

Ratios under halving both angles: $r=0$: 3.95, 3.99; $r=1$: 3.86, 3.97 — consistent with $O(\alpha\beta)$ (leading ratio 4,
corrections $O(\alpha,\beta)$). The same docstring contained two further false statements that were never asserted but are now
fixed and asserted: the closed-sector dimensions are **12** ($r=1$) and **9** ($r=0$) (not "the same for both r"), and the
vacuum energy is $\langle\Omega|H|\Omega\rangle = H[0,0] = -4 r g^2$ (not $-2 r g^2$): four inner links each contribute
$-g^2 r$ from the $\kappa_2\mathcal K_2$ term. Verified numerically: $H_1[0,0] = -4.4056595 = -4 g^2$ at $g^2 = 1.1014149$,
$H_0[0,0] = 0$, $E_0(r{=}1) = -5.839 < -4g^2$, $E_0(r{=}0) = -5.645 < 0$.

### 1.2 `tests/acceptance/m9/test_fuzzy_circuits.py::test_M9_K1_electric_link_and_layout`
The locked line `full = _unitary(big)` built `Operator(build_UE(alpha)).data`, a dense $65536\times65536$ complex128 matrix
(69 GB), and `op_norm_after_phase(full, kron^4)` needed a second such matrix plus an SVD: infeasible on this host. The check
itself (build_UE acts the one-link block on each of the four inner links) is still wanted.

## 2. Changes (exactly two tests; nothing else in `tests/acceptance/` touched)

### 2.1 O1 (`test_M9_O1_definitions_and_identities`)
* `one_step_plaquette(alpha, beta, r, order=1)` asserted $\le 10^{-10}$ at **both** $r=1$ and $r=0$ (was: $r=1$ order 1 and
  $r=0$ order 2). Tolerance unchanged, $10^{-10}$: the quantity is a 256-dim dense contraction, float64 error $\sim10^{-15}$.
* **Added** order-2 check for $r\in\{1,0\}$: $|v(0.37,0.61)| > 10^{-3}$, $|v(0.05,0.05)| > 10^{-4}$, $|v(0.025,0.025)| > 10^{-5}$,
  and $3 \le v(0.05,0.05)/v(0.025,0.025) \le 5$. Justification: measured values above are 10-35x above the "nonzero"
  thresholds; the ratio band [3, 5] brackets the leading-order 4 with a $\pm25\%$ margin against the measured 3.86-3.99 while
  still rejecting $O(\alpha)$ or $O(\beta)$ scaling (ratio 2) and $O(\alpha^2\beta)$-type scaling (ratio 8).
* Dimension assertion tightened from "$\ge 2$, $\le 50$" to `d1 == 12 and d0 == 9` (values verified above; the plan already
  fixed the closed-sector construction as the Krylov space from $\Omega$, so the dimension is a property of the method).
* Added `abs(H1[0,0] + 4 g2) <= 1e-10`, `abs(H0[0,0]) <= 1e-10`, ground state strictly below $-4g^2$ ($r=1$) and $\le 0$ ($r=0$).
* Docstring rewritten to state only what is asserted.

### 2.2 K1 (`test_M9_K1_electric_link_and_layout`)
Replaced the dense `Operator(big)` comparison with: 8 seeded random (`np.random.default_rng(SEED)`, `SEED = 20261104`)
normalised 16-qubit states $\psi_k$; `Statevector(psi).evolve(build_UE(alpha))` vs. $(U_{16}^{\otimes 4})\psi$ applied link by
link with `np.tensordot` on the `(16,16,16,16)` reshape (never forming the $65536^2$ matrix; axis 0 = qubits 12-15, little-endian
as `Operator`); a single global phase $e^{i\phi} = \langle\mathrm{ref}_0|\mathrm{out}_0\rangle/|\cdot|$ fixed from the first
state and reused for all eight; per-state 2-norm error $\le 10^{-10}$ (tolerance unchanged). Prototype
`scratch/planner/k1_seeded_proto.py`: worst error $8\times10^{-16}$ ($\alpha=0.37$), $1\times10^{-15}$ ($\alpha=0.91$), 0.4 s per
angle; the tensordot route equals an explicit `np.kron` on a 2-link toy to $2\times10^{-15}$. Why this is still a strong check:
the random states are generic in the full $2^{16}$ space, so a mismatch $U_{\rm big} - e^{i\phi}U_{16}^{\otimes4} \ne 0$ is
detected with probability 1 (a nonzero operator annihilates a Gaussian random vector with probability 0); with 8 states the
residual $\|\Delta\psi_k\|$ averages $\|\Delta\|_F/\sqrt{65536}$, so an op-norm defect $\ge 10^{-10}$ concentrated on one
direction gives a per-state residual $\ge 10^{-10}\cdot|\langle u|\psi_k\rangle| \sim 4\times10^{-13}$ — below $10^{-10}$ only if
the defect is in a single direction, which for a product of four identical exact one-link blocks (each certified to $10^{-10}$
as a 16x16 unitary in the same test) cannot happen: any layout error (wrong qubit, missing link) is $O(1)$.
Everything else in the test (16x16 block, phases, `verify_link` Verdict, 48-qubit layout, `logical_metrics`) is unchanged.

## 3. Test cost notes (for the tester / coordinator; nothing added to the tests)
* `test_fuzzy_circuits.py::test_M9_S1_step_orders[*]` and `test_M9_S1_outer_row_and_gauss_on_outputs` form `np.kron` of four
  16x16 blocks as a dense $65536\times65536$ complex matrix (69 GB each; 68-135 GB peak per test). Run with **`pytest -n 1`**
  (or exclude S1 from parallel runs with `-k "not S1"`). Noted in the file header.
* `test_fuzzy_codec_gauss.py` C1 takes **~18 min** (the test's own reference Gauss residual on the $4^{12}$ vacuum).
* Both must be written into `prompts/302` (M10 plan) run instructions as well.

## 4. Lock
`tools/lock.py` refuses to re-lock m9; the coordinator updates `tests/acceptance/LOCK.json` by hand (acceptance-v9) with the
new sha256 of the two files. The planner did not edit `LOCK.json`.

## 5. Done-check
```
pytest -n 4 tests/acceptance/m9/test_fuzzy_observables.py -q        # O1 identities pass; shared_table_file fails only until results/fuzzy exists
pytest -n 2 tests/acceptance/m9/test_fuzzy_circuits.py -q -k electric   # 2 passed, ~1 min
```

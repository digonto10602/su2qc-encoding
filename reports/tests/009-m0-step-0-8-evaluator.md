# Tester report 009 — M0 step 0.8, evaluator (mode: step)

- Date: 2026-11-04
- Commit: `5c5f567` + uncommitted step-0.8 files (`git status`: METHODS.md, twelve.py, aer_check.py, evaluator.py, sparse_sim.py, physical.py modified; `tests/unit/test_evaluator_unit.py` new)
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md`, step 0.8 (§2.7, §3 row 0.8); `docs/METHODS.md` §6
- Related: reports/tests/007, 008 (sparse simulator, aer check)
- Raw numbers: `results/evaluator_0_8_adversarial.json` (125 adversarial checks, seed 20261104, angles $(\alpha,\beta)=(0.37,0.61)$); scripts: `tests/independent/evaluator_0_8/` (run with `python adv*.py` from that folder)

## VERDICT: PASS for the step's done-check, with 1 serious finding (F1, a possible false ACCEPT) and 1 forward-looking blocker for step 1.6 (F2). Details below.

## 1. Commands run

```
source .../conda.sh && conda activate coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "evaluate"
pytest -n auto tests/unit                                   # 94 passed, 19.4 s
pytest -q tests/acceptance/m0/test_evaluator.py --durations=5   # 3 passed, 33.7 s
pytest -n auto -m "not slow" tests/acceptance/m0 -q -rA     # 26 passed, 6 PENDING (NotImplementedError), 0 real failures
pytest --collect-only -q tests/acceptance                   # 84 collected, clean
python tools/check_lock.py ; ~/.claude/bin/acceptance-check # LOCK OK ; PASS (matches acceptance-v2)
pytest -q tests/acceptance/m1/test_twelve_codec.py          # see §3
python tests/independent/evaluator_0_8/adv{1..8}.py, adv_paulo.py   # adversarial, §4
```

## 2. Step checks

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests | all pass | 94 passed (19.4 s, `-n auto`) | — | PASS |
| `m0::test_M0_E3_sensitivity` | pass | pass, 17.8 s (serial) | — | PASS |
| `m0::test_M0_E4_outer_control_blocks` | pass | pass, 6.9 s | — | PASS |
| `m0::test_M0_E5_gauss_of_outputs` | pass | pass, 8.4 s | — | PASS |
| all earlier m0 (G1,G2,A1–A3,C1–C5,X1–X8,E1,E2) | pass | 26 passed in total (incl. E3–E5) | — | PASS |
| remaining m0 tests | PENDING only | 6 PENDING: M0-M1, M0-M2 (3 params), M0-M3 (`ct_compile`/`logical_metrics`/`pygridsynth_word` not built), M0-R1 (`save_result` not built) = steps 0.9–0.10 | — | PENDING (not failures) |
| acceptance lock | pass | `LOCK OK`; `acceptance-check` PASS; 84 tests collected | — | PASS |
| `m1::test_M1_C1_codec_and_vectors` | informational | FAILS only at its last line, `describe()` (`NotImplementedError`, PENDING, planned for M1 step 1.1). Everything before it (codec bijection, 625 sorted inner codes, registers, outer code, 433 vectors norm/orthogonality, Gauss via `decode`) passes: I ran the test body with the last two lines removed in a scratch copy | 1e-12 / 1e-10 | status: PENDING at `describe` (the rest is green) |

`graphify affected "evaluate"` lists the three E-tests plus M1 tests (E1, B1–B4, S1, T1, P1) that call `evaluate`; the M1 ones are not yet buildable (circuit modules missing), so they are covered only through my own circuits (§4).

## 3. Independent adversarial checks (own scripts)

Numbers: 125 checks recorded; 114 PASS; 11 recorded as FAIL, of which 6 are errors in my own check or vacuous controls (listed at the end of §4), 4 are F1 evidence (layout probes) and 1 is F5 (`id` on an outer qubit counted as read). Classification below. The final summary of each requested item:

### (1) Circuits with a known verdict (12-qubit register `d`, outer `o`, ancillas `a`)

| circuit | expected | got | result |
|---|---|---|---|
| identity vs $\mathbb 1$ | ok | ok, err $1.2\cdot10^{-13}$ (inner_span), $3.4\cdot10^{-15}$ (physical) | PASS (my first 1e-13 threshold was too tight: the span fast path has a floor $1.2\cdot10^{-13}$ from the SVD) |
| exact $U_E(\alpha=0.37)$ = 4 `p(-3α/4)` on qubits 2,5,8,11 vs target `UE` | ok | ok, `op_norm_error` $=1.2\cdot10^{-13}$ (inner_span), $3.3\cdot10^{-15}$ (physical), Gauss $5.3\cdot10^{-16}$ | PASS; sign convention $U_E=e^{-i\alpha H_E}$ confirmed |
| same with `p(+3α/4)` | fail | error, op-norm $1.281$; accepted against $U_E^\dagger$ | PASS |
| global phase only (0.9 rad) | ok, phase $e^{0.9i}$ | ok, phase $=0.62161+0.78333i$ (error $<10^{-12}$) | PASS |
| `Z` on data qubit 4 | fail | error, op-norm $2.0$ (span) / $1.0$ (physical) | PASS |
| `X` on an ancilla left dirty | dirty_ancilla | `dirty_ancilla`, weight $1$ | PASS |
| ancilla computed and uncomputed (cx, ccx, undone) | ok | ok | PASS |
| compute-use-uncompute: phase on ancilla $=j_b\oplus j_r$ vs matching diagonal target | ok | ok, err $1.2\cdot10^{-13}$; vs $\mathbb 1$ fails (err $0.160$) | PASS |
| one cx forgotten in uncomputation | dirty_ancilla | `dirty_ancilla`, weight $1$ | PASS |
| ancilla `ry(ε)`: weight $\sin^2(\varepsilon/2)$ | fail iff weight $>10^{-12}$ | ε=1e-5 (2.5e-11) → dirty_ancilla; ε=1e-7 (2.5e-15) → ok | PASS (policy is a weight threshold: amplitude $\le10^{-6}$ passes) |
| CX inner→outer; X, H, RX, RY, SX, unitary-X on outer; SWAP(outer,inner); CCX/CY/CRY with outer target; CX outer→outer; CSWAP that swaps an outer qubit; custom gate hiding such a CX | `writes_outer` | all 14 `writes_outer` | PASS |
| CZ(outer $q_j$ of link 0, inner), CX(outer→inner), CCX(outer,outer→inner), CRY(outer ctrl), CP(outer,outer), RZZ(outer,inner) and RZZ(inner,outer), P(outer) | classified as read, not `writes_outer` | all read (read count 1 or 2), method `physical` | PASS |
| CZ(outer0.$q_j$, inner $q_j$ of link b) vs $\mathrm{diag}(-1\ \text{if}\ j_b=j_{o0}=\tfrac12)$ | ok | ok, err $3.4\cdot10^{-15}$; vs $\mathbb 1$: error $2.0$ | PASS |
| phase on invalid codes only ($q_j=0,q_{m'}=1$); permutation of invalid codes (001↔011) | ok (don't-care) | ok, err $1.2\cdot10^{-13}$, both methods | PASS |
| valid→invalid code (X on $q_{m'}$; X on $q_m,q_{m'}$) | leak | `leak`, weight $1$ | PASS |
| exact $U_E$ vs target with the row of state 217 sign-flipped | fail; names 217 | `error`, failing_inputs $=[(217, 2.0)]$ only | PASS |
| multi-controlled Z on data $=0$ (ancilla chain) vs oracle $A=\Psi^\dagger D\Psi$ from `physical_vectors` | err $\le10^{-12}$ | $1.0\cdot10^{-14}$; vs $\mathbb 1$: error 2.0, failing ids all among the 16 states with weight on code 0 | PASS |
| outer phase `p(θ)` on outer link $k$ ($k=0,5$) vs $\mathrm{diag}(e^{i\theta[j_{o_k}=1/2]})$ | ok | ok, err $3.4\cdot10^{-15}$ | PASS |
| same vs $\mathbb 1$: analytic $\mathrm{err}=\max_k|e^{i\theta s_k}-e^{i\varphi}|$, $\varphi=\arg\sum_ke^{i\theta s_k}$ ($n_1=246$ of 433 states) | $0.397042028824$, $\varphi=0.399697$ | $0.397042028824$, phase angle $0.399697$ | PASS (4) |

### (2) `specialise` vs dense `Operator`
60 random 7-qubit circuits (2 read outer qubits; gates incl. h, rx, u, cx, ccx, swap, 2-qubit unitaries, cz/cp/ccz/crz/cry/ch/cswap/ccx with outer controls, t, sdg, s, z, block-diagonal "controlled" unitaries, random global phase): 236 (circuit, outer-pattern) blocks. Worst block difference $4.2\cdot10^{-15}$ (tol $10^{-12}$); `classify_outer_gates` read-set equals the set of outer qubits used in 60/60; the specialised circuit never touches a read qubit; `cx` onto outer raises `OuterWriteError`. PASS.
Also, 4 independent oracles (phase+permutation circuits that read 1, 2, 2 and 3 outer bits; computed directly from `physical_vectors` without the evaluator): $\|A_{\rm eval}-A_{\rm oracle}\|_2\le4.4\cdot10^{-15}$; 16 outer bits read (3153 blocks): $1.9\cdot10^{-15}$, 25 s wall. PASS.

### (3) `inner_span` vs `physical`
Nontrivial branching circuit: the exact $U_B(\beta=0.61)$ embedded as a single 12-qubit `UnitaryGate` (unitarity of the 4096×4096 embedding $2.2\cdot10^{-16}$; embedding uses `inner_target` and Paulo's local ordering) against the *independent* physical target `target(basis,'UB')`: ok in both methods (err $1.2\cdot10^{-13}$ span, $3.4\cdot10^{-15}$ physical, Gauss $6.2\cdot10^{-16}$). This also confirms that `inner_target('UB')` and the CG-basis physical target agree on all 433 states. $U_B U_E$ (step, order 1) ok in both ($1.2\cdot10^{-13}$ / $3.3\cdot10^{-15}$); against the Strang target (order 2) fails ($0.51$); $U_EU_B$ against the $U_BU_E$ target fails ($0.99$); wrong targets $U_B(-\beta)$, $\overline{U_B}$ fail ($1.878$), $U_B(0.5)$ fails ($0.220$).
Agreement on 9 circuits (identity, UE, UB, UB·UE, UB vs wrong β, UE wrong sign, Z, diagonal p/cp network ok and vs $\mathbb 1$): identical verdicts 9/9 and identical op-norm errors to $\le10^{-12}$ whenever exact; for failing circuits the errors are equal in 4 cases (UB vs wrong β $0.2196$, UE wrong sign $1.281$, diagonal network vs $\mathbb 1$ $0.924$, and exact ones) and differ in 1 (Z on data: span $2.0$ vs physical $1.0$; the span path measures $\sup$ over unnormalised inner components, the physical path over normalised physical states — not a bug, but the two numbers are not interchangeable for failing circuits). PASS.

### (4) One global phase
Analytic comparison above (outer-bit phase, 433×433 single $\varphi$): matches to $10^{-12}$ in err and phase angle. A circuit with `p(θ)` on an outer qubit plus `global_phase=-θ/2` is accepted against $\mathrm{diag}(e^{i\theta(s-1/2)})$. Perturbed $U_E$ ($\delta$ added to all four `p` angles): evaluator = analytic $\max_k|e^{-i\delta n_k}-e^{i\varphi}|$ to $10^{-6}$ relative for $\delta\in\{10^{-3},10^{-6},10^{-9},3\cdot10^{-10},10^{-10},3\cdot10^{-11}\}$; verdict flips between $10^{-10}$ (err $2.5\cdot10^{-10}$, rejected) and $3\cdot10^{-11}$ (err $7.5\cdot10^{-11}$, accepted), i.e. exactly at the tolerance $10^{-10}$. PASS.

### (5) Gauss residual of outputs
`decode_state(physical_vectors)` reproduces the CG-basis amplitudes `basis.amps` exactly (max diff $0$, all 433 states, both keys and amplitudes). Gauss of the exact embedded UB/UE outputs: $\le6.2\cdot10^{-16}$. `gauss_residuals_coo` equals `gauss_residual` on 40 random states (20 exact up to phase, 20 with random 30-key noise; max diff $0$). Caveat, measured: the $V_P$ sign product $\sigma=\prod_l\sigma(p_l)$ is constant on the support of every physical state (188 of 433 states have $\sigma=-1$), so the Gauss residual of any in-span output is blind to the $V_P$ signs; my "decode without signs" control gave $5.4\cdot10^{-16}$ (vacuous) and the sign-conjugated circuit $D\,U_B\,D$ is identical to $U_B$ ($D$ commutes). The sign matters only for out-of-span outputs. I could not construct a circuit that discriminates the two decodings; the equality with `basis.amps` is the real check. PASS (with this caveat).

### (6) aer_mps accounting
`engine='aer_mps'`, default tolerances ($10^{-10},10^{-12}$): `engine=aer_mps`, `engine_accuracy=2e-10`, `certified=False`, still `ok=True` on the exact $U_E$. With `tol_err=tol_leak=1e-8`: `certified=True`. Sparse: accuracy 0, certified True. aer_mps rejects Z-on-data, X-on-ancilla and the wrong-sign $U_E$; accepts correct outer-read circuit (2 blocks); `auto` with a tiny cap falls back to aer_mps; `sparse` with tiny cap returns `unsimulable`; sparse and aer_mps op-norm error on $U_E(\delta=10^{-3})$ agree to $4.9\cdot10^{-17}$. Paulo's compiled QPY (34 qubits, 294 CX, 1162 T) through `engine='auto'` (→ aer_mps, 73.7 s): op-norm error $2.905\cdot10^{-6}$ vs $U_B(\beta=1)$ (planner: $2.9\cdot10^{-6}$), leak $4.2\cdot10^{-12}$, `certified=True` at tol $2\cdot10^{-5}/10^{-9}$, inverse target rejected (err $1.819$). BUT verdict `ok=False, reason='gauss'` (Gauss residual $1.16\cdot10^{-10}>10^{-10}$) — see F2. PASS for the accounting.

## 4. Findings (ordered by severity)

**F1 — SERIOUS (possible false ACCEPT).** `layout_of` takes the outer qubits from the register named `o` wherever it sits, but the evaluator maps outer qubit $q$ to physical outer bit $q-12$ (`evaluator.py` lines 336–337 and 348–349 `(q - n_data)`), assuming `o` = qubits 12..27. For a circuit `d(12), a(2), o(16)` a `p(θ)` on `o[1]` (intended outer link 0 $q_j$) acts on outer bit 3 (link 1 $q_j$): measured, the circuit is ACCEPTED against $\mathrm{diag}(e^{i\theta[j_{o1}]})$ (err $3.4\cdot10^{-15}$) and rejected against the correct $\mathrm{diag}(e^{i\theta[j_{o0}]})$ (err $0.686$). With `o` before `d` (or `a,d,o`) data and outer index lists overlap / are shifted and no error is raised (verdict `error 0.397`/`0.686` for a circuit that is correct). Layout `d,o,a` (data, outer, ancillas — the order the plan's builders use) is fine (ok, $3.4\cdot10^{-15}$). A guess for the cause: the outer-bit index should be the position of $q$ in `layout.outer`, and `layout_of` should raise unless `o` is exactly qubits 12..27 (or a mapping is used). Free-form proposer circuits could hit this.

**F2 — blocker for M1-P1 (forward-looking).** `TOL_GAUSS=1e-10` is hard-coded and not tied to `tol_err`. Paulo's circuit has op-norm error $2.9\cdot10^{-6}$ and leak $4\cdot10^{-12}$ and passes `error`/`leak`, but `gauss=1.16\cdot10^{-10}$ flips the verdict to `gauss`: `test_M1_P1_paulo_qpy_verifies` asserts `v.ok` with `tol_err=2e-5` and would fail on this. aer_mps noise ($\sim2\cdot10^{-10}$) alone is at this level, so the Gauss threshold cannot be $10^{-10}$ for aer_mps. Needs a planner decision (scale with tolerance / engine accuracy), not a tolerance change by me. Guess: gauss check not given the synthesised-circuit/aer budget.

**F3 — design note.** With `gauss=False` and the `physical` method (some outer bit read), an out-of-span amplitude is only seen at second order: `crx(1e-5)` on $q_m$ of link b (amplitude $5\cdot10^{-6}$ out of the physical span) gives op-norm err $1.25\cdot10^{-11}$, `span_leak` $2.5\cdot10^{-11}$, reason `ok` (accepted). With `gauss=True` (default) the same circuit is rejected (`gauss`, residual $5\cdot10^{-6}$), and with no outer read `inner_span` rejects it (err $5\cdot10^{-6}$). Consequence: the compression loop and acceptance tests must keep `gauss=True`; METHODS already says span leak is caught by Gauss, `max_span_leak` is not part of `reason`.

**F4 — consumer hazard.** An aer_mps verdict at tolerances tighter than $2\cdot10^{-10}$ is `ok=True, certified=False`; anyone who reads only `.ok` is told "ok". Fine as documented, but every consumer (loop, report) must test `certified`.

**F5 — conservative false rejects (per spec: a gate touching an outer qubit must be diagonal on it after lowering).** Operator-level diagonal circuits are rejected as `writes_outer` when the lowering writes the outer qubit in an intermediate gate: `ControlledGate(UnitaryGate(2x2))` with an outer control (`u` on the control), `mcp`/multi-controlled `rx` with two outer qubits (`cx` between the two outer qubits). Also `id` on an outer qubit counts as a read (method `physical` instead of `inner_span`). Controlled `ry/rx/rz/h/s/sx/y/u/swap`, `rzz`, `ccz` are fine (all lower to outer-diagonal gates). Not a correctness risk; may surprise proposers.

**F6 — cosmetic.** `failing_inputs` is empty when the failure is a small dirty ancilla (ry 1e-5: err $1.3\cdot10^{-11}$); under aer_mps a valid→invalid-code leak is reported as `dirty_ancilla` (leak and dirty are the same derived number). `outer_bits_read` counts `id`.

My own check bugs (not evaluator bugs): tight 1e-13 threshold on identity; an "identity" ancilla circuit that actually contained `p(0.3)` on a data-dependent ancilla (evaluator correctly rejected); `UB^T` expected to fail but $U_B$ is complex-symmetric ($\|U_B-U_B^T\|=2.2\cdot10^{-16}$); invalid-code permutation first written without the `d2` control (corrected in `adv3.py`, passes); sign-sensitivity controls for the Gauss decode are vacuous (see (5)).

## 5. Timing

E3 17.8 s, E4 6.9 s, E5 8.4 s (serial, one process each). Evaluator per circuit: 12-qubit $U_E$/$U_B$ unitary: 2.0–2.4 s `inner_span`, 0.9–1.3 s `physical`; 625 inputs × 3153 outer blocks (all 16 outer qubits read): 24–25 s; aer_mps $U_E$ 3–9 s; Paulo's 34-qubit circuit 66–74 s via aer_mps.

## 6. Counts

passed 26 (m0) + 94 (unit) ; failed 0 ; pending 6 (m0 M1/M2/M3/R1) ; new failures vs report 008: 0 ; M1-C1 pending at `describe()`.

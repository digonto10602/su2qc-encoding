# Test report 203 — M5 steps 5.5 + 5.6: rishon verifier, observables, `build_UE`

Date: 2026-11-06 · commit `6da30dd` (working tree: uncommitted `src/su2plaq/circuits/rishon.py`, `rishon/observables.py`, `rishon/verify.py`, `tests/unit/test_rishon_stubs_unit.py`, new `tests/unit/test_rishon_{verify,observables}_unit.py`) · branch `m5-rishon` · prompt in force `prompts/200-rishon-m5-plan.md` (+ `prompts/201` codec-test fix) · lock acceptance-v8 · mode: step · related: `reports/tests/200`, `201`, `202`

**VERDICT: PASS** for steps 5.5 and 5.6. 0 failures, 0 new failures. 3 notes (none blocking), listed in section 6.

## 0. Plain-English summary
* Asked: check the new verifier (`verify`), the shared observables, and the electric-step circuit `build_UE` (with its outer electric row).
* Done: ran the locked acceptance tests, the unit tests and the lock checks; then wrote my own checks that do not use the builder's physical-state code: 36 adversarial circuits against the verifier, 72 randomly built physical 48-qubit states (my own construction), independent circuit matrices from Qiskit, and the observables recomputed from scratch.
* Meaning: the verifier rejected every wrong circuit I could build (including every way of hiding an outer-qubit read), accepted only circuits that are really correct up to the stated tolerance, and for the circuits I tried the error measured on full physical states equals the error the verifier reports on the 1296 inner codes (to 3 digits or better). `build_UE` has the right phase $e^{-3i\alpha/4}$ on quartets and 1 on singlets; counts are 8 CX / 4 rotations (depth 3), outer row +16 CX / +8 rotations.
* Caveats: see section 6 (the outer-row circuit cannot be passed through `verify` by design; the `ValueError` catch is harmless but redundant; one wording point in METHODS R6).

## 1. Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, all under `taskset -c 10-19`, `pytest -n 10`)
```
pytest -n 10 -q tests/acceptance/m5 -rA                          # 34 tests
pytest -n 10 -q tests/unit                                        # 283
pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
graphify update .  ;  graphify affected verify|build_UE            # returned no extra nodes (graph has no call edges for these); coverage judged by hand: E1, B1(verify), O1, T1[UE]
PYTHONPATH=src python results/rishon/tester-203-adversarial.py             # -> tester-203-adversarial.json   (36 cases)
PYTHONPATH=src python results/rishon/tester-203-fullstate-soundness.py     # -> tester-203-fullstate-soundness.json (seed 20261106)
PYTHONPATH=src python results/rishon/tester-203-gauss-detector.py          # -> tester-203-gauss-detector.json (sample seed 20261104)
PYTHONPATH=src python results/rishon/tester-203-ue-check.py                # -> tester-203-ue-check.json
PYTHONPATH=src python results/rishon/tester-203-outer-row-fullstate.py     # -> tester-203-outer-row-fullstate.json
PYTHONPATH=src python results/rishon/tester-203-observables-independent.py # -> tester-203-observables-independent.json
```
Peak memory of every script $\le 0.65$ GB. No `src/`, `tests/acceptance/`, tolerance or marker was touched.

## 2. Suite results
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| `test_rishon_verify.py::test_M5_B1_verifier_sensitivity` | pass | passed | – | PASS |
| `test_rishon_observables.py::test_M5_O1_closed_spectra` | pass | passed | – | PASS |
| `test_rishon_observables.py::test_M5_O1_observables_after_steps[3 angle pairs]` | pass | 3 passed | – | PASS |
| `test_rishon_circuits.py::test_M5_E1_electric_step[0.37, 0.91]` | pass | 2 passed | – | PASS |
| D1 ×2, C1 ×4 (codec + physical ×3), X1 ×4 (still green), T1[UE] (synthesised UE re-verifies, bonus) | pass | 11 passed | – | PASS |
| m5 total | 34 | **18 passed, 16 pending** (all `PENDING:`/Lean-missing, 0 genuine failures) | – | PASS |
| collection | clean, 136 | 136 collected | – | PASS |
| unit (all) | green | 283 passed (54 s) | – | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed (86 s) | – | PASS |
| `check_lock.py` / `acceptance-check` | OK / PASS | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v8` | – | PASS |

Pending by cause (16, read from the messages): `build_UB` not built — B1 magnetic ×4, B1 physical+Gauss ×1, T1[UB] ×1 (6); `build_step` not built — S1 ×2, T1[step] ×1 (3); results files missing (step 5.10) — R1 ×4; Lean files missing (`Counts.lean`, `JW.lean`, `HB.lean`; steps 5.L1–5.L3) — L1, L2, L3 (3). All belong to later steps; none belongs to 5.5/5.6.

## 3. Soundness of `verify` (item 2)

### 3(a) The R6 argument: inner-code certification covers all 38 432 physical states
**Argument as I re-derived it.** `verify` first rejects any circuit in which any gate touches an outer qubit (`classify_outer_gates` → `outer_read_unsupported`, or `writes_outer` for non-diagonal use). A circuit that passes therefore contains only gates on data and ancilla qubits, i.e. $U=U_{\rm in}\otimes 1_{\rm outer}$ exactly (the gate list comes from `_translate`, which expands custom gates from their definitions and only trusts exact Qiskit classes, so the check is on what the circuit really does). For a physical state $\Psi=\sum_o|o\rangle\otimes\psi^o$ with $\psi^o$ in the code space (checked by `_pairs`: ValueError if not),
$$\|(U-e^{i\varphi}V\otimes1)\Psi\|^2=\sum_o\|(M-e^{i\varphi}V)\psi^o\|^2+\sum_o\|X\psi^o\|^2\le\big(\|M-e^{i\varphi}V\|^2+\|X\|^2\big)\sum_o\|\psi^o\|^2,$$
with $M$ the code-space block, $X$ the part leaving the code space or dirtying ancillas; outputs for different $o$ are orthogonal because the outer bits are untouched. The inner view evaluates $M,X$ on all 1296 codes (outer 0, ancillas 0), so `op_norm_error` $=\|M-e^{i\varphi}V\|+\|X\|+$dropped bounds every physical state; sufficient. Necessity holds because the inner span is the full 1296 (rank 1296, report 201). The argument is correct. One wording point: R6 calls the bound $\|\cdot\|\le\|M-e^{i\varphi}V\|_2^2$ with "the same for the leak" and then adds the three terms — the sum is a valid (slightly loose, triangle) bound; see note N3.

**Numerical test with my own construction** (`tester-203-fullstate-soundness.py`, seed 20261106). No `su2plaq.rishon.physical` code: per type pattern (random $A/B/Q$ on all 12 links) and per corner, the Gauss kernel is the null space of $\sum_a(\sum_eG^a_e)^2$ built from own global-string Jordan–Wigner end generators (tester-201 module), random complex kernel combination, tensor product over corners, far ends of outer links as in R2. 72 states, from 907 tried patterns; own Gauss residual (40 states) $4.7\times10^{-16}$; norms $1\pm4.4\times10^{-16}$; the sample contains inner types AAAA and QQQQ. Mutated 48+7-qubit circuits are run on the **full 48-bit keys** of every state with the sparse simulator and compared with $e^{i\varphi}(V_{\rm in}\otimes1)\Psi$ ($\varphi$ = `verify`'s phase):

| mutant of $U_E(0.37)$ | `verify` reason | `verify` op_norm_error | max full-state error (72 states) | verdict |
|---|---|---|---|---|
| none | ok | $1.1\times10^{-16}$ | $2.3\times10^{-16}$ | PASS |
| phase $10^{-3}$ only on inner code AAAA (ancilla AND chain, restored) | error | $9.9923\times10^{-4}$ | $9.9923\times10^{-4}$ | PASS |
| phase $10^{-6}$ only on AAAA | error | $9.9923\times10^{-7}$ | $9.9923\times10^{-7}$ | PASS |
| `ccz(0,1,4)` on valid codes | error | 2.0 | 2.0 | PASS |
| `p(1e-4)` on one data qubit | error | $5.0\times10^{-5}$ | $5.0\times10^{-5}$ | PASS |
| `ccz(0,1,2)` (acts only on invalid patterns, don't-care) | ok | $1.1\times10^{-16}$ | $2.3\times10^{-16}$ | PASS |

The verifier error equals the worst full-state error to $\le 10^{-12}$ relative in every row (both directions: nothing accepted that is wrong on a physical state; nothing wrong on a physical state missed).

### 3(b) Adversarial circuits (`tester-203-adversarial.py`, 36 cases, 0 mismatches)
Base: $U_E(0.37)$ on `d` (16) + `o` (32) + ancillas, kind `UE`, $\alpha=0.37$. Control (unmodified circuit): ok, error $1.1\times10^{-16}$.

| attack | result | verdict |
|---|---|---|
| outer read hidden in a custom gate named `cx` (`to_gate` of a `cp`, controlled by an outer qubit) | `outer_read_unsupported` | rejected |
| `Gate` subclass reusing the name `cz` with a different definition, outer control | `outer_read_unsupported` | rejected |
| `UnitaryGate` controlled phase on (outer, data); nested custom gate inside a custom gate | `outer_read_unsupported` ×2 | rejected |
| gate named `cx` with a matrix but no definition | `disallowed_gate` (ValueError path) | rejected |
| gate named `cx` whose definition is a `swap` on data | `error` 2.0 | rejected |
| gate named `cp` whose definition is off by $3\times10^{-9}$ | `error` 0.083 | rejected |
| outer-controlled `cp(1e-3)`, `cx`, `ccx`, `crz`, `cry`, `rzz`, lone `rz` on outer | `outer_read_unsupported` ×7 | rejected |
| 3-control `mcx` with an outer control | `disallowed_gate` | rejected |
| open-control `cx` on outer, `swap` of outer qubits, `x`·`x` on outer | `writes_outer` ×3 | rejected |
| `rx(1e-13)` on an outer qubit (below the $10^{-12}$ commutation test) | `outer_read_unsupported` | rejected |
| ancilla dirtied only on code AAAA (8-qubit AND chain, last ancilla not uncomputed) | `dirty_ancilla`, error 2.0 | rejected |
| phase $\epsilon$ only on code AAAA (ancillas restored), $\epsilon=3,\,10^{-3},\,10^{-6},\,5\times10^{-10},\,2\times10^{-10}$ | `error`, errors $1.99,\,9.99\times10^{-4},\,9.99\times10^{-7},\,5.0\times10^{-10},\,2.0\times10^{-10}$ | all rejected (outside the 273-state Gauss sample or not: the inner block sees all 1296 codes) |
| phase $5\times10^{-11}$ only on AAAA | ok, error $5.0\times10^{-11}\le10^{-10}$ | accepted, correctly (within tolerance) |
| `ccz(0,1,4)` on valid codes | `error` 2.0 | rejected |
| `ccz(0,1,2)` on invalid patterns only | ok | accepted by design (don't-care) |
| bad layout (15+33 qubits), unnamed 16-qubit register | `bad_layout`; `error` 0.72 | rejected |
| `reset`, `measure` | `disallowed_gate` ×2 | rejected |
| wrong sign of $\alpha$ | `error` 1.35 | rejected |
| global phase 0.3; `rz` instead of `p` (equal up to a global phase) | ok ×2 | accepted, correctly |

**The `ValueError` catch.** In `verify`, `classify_outer_gates` is wrapped in `except ValueError: read = set()`, and `evaluate` is then called. I checked every way it can fire (bad layout, outer write, custom gate without definition, 3-control `mcx`, reset/measure — cases above): in each, `evaluate` repeats exactly the same translation and layout steps (`evaluator.py` lines 355–370) and returns an early verdict with `ok=False` (`bad_layout`, `writes_outer`, `disallowed_gate`) and infinite error; `verify` then skips the Gauss part (`np.isfinite(op_norm_error)` is False) and keeps that reason. So no failure mode can become an accept: the catch is not silent (the information is reported by the second call) and a ValueError cannot yield ok. Verdict on the rule "no silent exception catching": acceptable, see N2.

### 3(c) Gauss: what is certified and what is sampled (`tester-203-gauss-detector.py`)
* **Certified (all 38 432 states):** the inner-block bound of 3(a). It implies $\|G^a_c U\Psi\|\le 2\cdot$`op_norm_error` for every physical $\Psi$ (since $G(V\otimes1)\Psi=0$ and $\|G^a_c\|\le2$), so the Gauss residual cannot be large for any state whenever the inner verdict is ok.
* **Sampled:** the explicit Gauss residual is computed for 17 closed reference states + 256 seeded physical states $=273$ (distinct; 17 + 256, verified), seed **20261104** (recorded in `RishonVerdict.extra["seed"]`, with `gauss_sample`), `sample_indices` excludes the closed states; outer-quartet counts in the sample $\{0{:}46,\,2{:}124,\,4{:}87,\,6{:}16\}$ (odd counts cannot occur). It is a cross-check, and the "first-order detector": with $\mathrm{err}\in(\mathrm{tol}_G/2,\ \mathrm{tol}_G]$ it can reject a circuit the inner block accepts.
* **Detector actually fires:** circuit `swap(0,1)` (flips the colour of the L end of link $b$: maps codes to codes, breaks SU(2)) with its own code block as the target: inner block ok (`block_error` 0.0), `verify` returns `reason='gauss'`, residual $1.0000$, 273 states; with `gauss_sample=1` residual $1.0000$ on 18 states; with `gauss=False` the same circuit is accepted (`ok`, NaN residual). So with an explicit `target=` argument the Gauss sample is the only guard against a non-gauge-invariant target; with the built-in kind targets it is redundant.
* One doc detail: R6 item 3 says amplitudes below $10^{-14}$ *relative* are dropped; the code drops $<10^{-14}$ *absolute* (`_AMP_DROP`). Harmless for unit-norm states; N3.

## 4. `build_UE` physics (item 3; `tester-203-ue-check.py`, `tester-203-outer-row-fullstate.py`)
Independent of the sparse simulator: Qiskit `Operator` per link (4 qubits) and `Statevector` on the 16-qubit circuit.
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| per-link $16\times16$ operator is diagonal | exact | max off-diagonal $<10^{-15}$ (all 4 links) | $10^{-15}$ | PASS |
| singlet codes $A$=3, $B$=12 phase, $\alpha=0.37$ and $0.91$ | 1 | $|d-1|=0.0$ | $10^{-15}$ | PASS |
| quartet codes 5, 6, 9, 10 phase, both $\alpha$ | $e^{-3i\alpha/4}$ | max deviation $0.0$ | $10^{-15}$ | PASS |
| `Statevector` of the 16-qubit circuit on 40 random valid codes vs $e^{-i\alpha\,\frac34\#Q}$ | exact | max dev $1.1\times10^{-16}$ ($\alpha=0.37$), $1.2\times10^{-16}$ ($0.91$) | $10^{-12}$ | PASS |
| invalid link codes (don't-care) | unconstrained | codes 1, 2, 13, 14 get $e^{-3i\alpha/4}$, the others 1 (reported) | – | info |
| inner counts: Qiskit `count_ops` / `logical_metrics` | `{cx: 8, p: 4}` / cx 8, n_rot 4, $T_{\rm fixed}$ 0 | `{'cx': 8, 'p': 4}`; cx 8, n_rot 4, depth 3 | exact | PASS |
| 48-qubit `with_outer` (no row) | same as inner, 48 qubits | `{cx: 8, p: 4}`, 48 qubits | exact | PASS |
| outer row `include_outer_electric` | `{cx: 24, p: 12}`, depth 3; separate row $+16$ CX, $+8$ rot | `{'cx': 24, 'p': 12}`, depth 3; difference cx 16, n_rot 8 | exact | PASS |
| outer row on 8 outer links: valid codes diagonal with phases 1 / $e^{-3i\alpha/4}$ | – | all 8 links: True | $10^{-15}$ | PASS |
| outer Q physical codes (near $L$ or $R$ end, far colour 1) are quartet codes | – | True | – | PASS |
| outer row on my 72 full physical states (64 have outer quartet links; $\alpha=0.37,0.91$): output $=e^{-i\alpha\frac34\#Q_{12}}\Psi$, every basis state returned to itself | exact | max dev $1.6\times10^{-16}$, $1.1\times10^{-16}$ | $10^{-12}$ | PASS |
| same circuit without row, on those states: $e^{-i\alpha\frac34\#Q_{\rm in}}\Psi$ | exact | max dev $6.2\times10^{-17}$, $5.6\times10^{-17}$ | $10^{-12}$ | PASS |

Metrics (reported separately, as required): inner $U_E$: 8 CX, 4 rotations, depth 3, $T_{\rm fixed}=0$; outer row: +16 CX, +8 rotations; total with row 24 CX, 12 rotations. `verify` of the 48-qubit inner circuit: ok, error $1.1\times10^{-16}$, Gauss $1.8\times10^{-16}$, 273 states, certified, 4.8 s for `verify` (+2.4 s basis build), peak 0.57 GB (builder: 7.4 s total, 0.54 GB) — consistent.

## 5. Observables (item 4; `tester-203-observables-independent.py`)
Definitions in `observables.py` match METHODS-rishon R5 exactly: $E_{\rm link}(n)=\frac14\langle H_E^{\rm inner}\rangle$ (rishon: $\frac14\sum p\,H_E$ on the 1296-dim state; KS: laptop 433-dim state), $P(n)=-\frac12\langle H_B\rangle=\langle\mathrm{Re\,Tr}\,U_P\rangle$, echo $=|\langle\Omega|U_1^n|\Omega\rangle|^2$ with $U_1=U_B(\beta)U_E(\alpha)$ (electric first), vacuum rishon vac$_A$, KS closed vacuum; closed forms $\theta_{\rm KS}=2\beta$, $\theta_R=4\sqrt2\beta$; $P(1)=0$ and independence of $\alpha$ at $n=1$.

Independent recomputation: own sparse 16-mode global-string JW, $W=\mathrm{Tr}(U_bU_rU_t^\dagger U_l^\dagger)$, own 1296 codes, $H_B=-(W+W^\dagger)$, $H_E=\frac34\#Q$, `expm_multiply`; KS from the closed $2\times2$ blocks $H_B=\begin{pmatrix}0&-2\\-2&0\end{pmatrix}$, $H_E=\mathrm{diag}(0,3)$ (METHODS §4).
| check | expected | got | tol | verdict |
|---|---|---|---|---|
| $W$ leakage outside the codes; $\langle{\rm vac}_A|H_B|{\rm vac}_A\rangle$; $\|H_B|{\rm vac}_A\rangle\|$ | 0; 0; 4 | 0.0; $-0.0$; 4.0 | $10^{-12}$ | PASS |
| production vs own, all of $E_{\rm link},P,$ echo, $n=1,2$, rishon and KS, 3 angle pairs $(0.37,0.61),(0.91,0.23),(1.7,1.0)$ (36 numbers) | equal | max diff $3.2\times10^{-15}$ | $10^{-10}$ | PASS |
| spot values, rishon $(0.37,0.61)$: $E_{\rm link}(1)$, echo$(1)$, $P(2)$, echo$(2)$ | – | 0.034699, 0.000561, 0.734122, 0.872508 (production = own to 6 digits) | – | PASS |
| spot values, KS $(0.91,0.23)$: $E_{\rm link}(1)$, echo$(1)$, $P(2)$ | – | 0.147817, 0.80291, 0.318296 | – | PASS |
| spot values, rishon $(1.7,1.0)$: $E_{\rm link}(1)$, $P(2)$ | – | 0.128851, 1.2436 | – | PASS |
| closed forms (own formula) vs `closed_forms` and vs own evolution at $n=1$ | equal | 0.0; $2.2\times10^{-16}$ | $10^{-12}$ | PASS |
| closed spectra at $g^2=0.5,1,2$: production vs own $3\times3$/$2\times2$ diagonalisation vs formulas $\tfrac34g^2\pm\sqrt{\frac9{16}g^4+32/g^4}$ (rishon, plus 0) and $\pm\sqrt{\cdot+4/g^4}$ (KS) | equal | max dev $1.8\times10^{-15}$; multiplicities $[1,15,1]$ rishon, $[1,1]$ KS | $10^{-10}$ | PASS |
| `observables_table()` JSON-serialisable, keys | `angles, rishon, ks, closed_forms, closed_spectra, definitions` | yes | – | PASS |

(My Krylov loop state differs from $|\ell\rangle$ by a sign; the eigenvalues, which I compare, are gauge-independent.)

## 6. Notes (non-blocking)
* **N1 (guess: by design).** The outer-row circuit (`include_outer_electric=True`) cannot be passed through `verify`: its CX gates write outer qubits (restored afterwards), so the evaluator says `writes_outer`. I verified the row by Qiskit `Operator` and on 72 full physical states instead (section 4). If a later step wants a verified "step + outer row" circuit, it needs a separate check; the plan says the row is only reported separately, so fine for now.
* **N2 (guess: cosmetic).** The `except ValueError: read = set()` in `verify` is redundant with `evaluate`, which repeats the same calls and returns the non-ok verdicts. Safe as written (all failure modes tested); an explicit `except OuterWriteError` / comment would document it. Not a rule violation.
* **N3 (doc).** METHODS-rishon R6: (i) the inequality writes $\le\|M-e^{i\varphi}V\|_2^2$ for the squared norm and then "same for the leak" — the implemented bound is the sum of block error, leak and dropped (a valid triangle bound, looser than the quadrature sum); (ii) "below $10^{-14}$ relative" vs code "absolute". Coordinator/planner to adjust the wording when convenient.
* Single global phase $\varphi$ is fitted over all 1296 codes (as the laptop evaluator does for the physical space); a circuit differing from the target by different phases on different sectors is rejected (error $\approx$ phase difference), as the AAAA-only cases show.

## 7. Item 5: hygiene
`git status --short`: modified only `src/su2plaq/circuits/rishon.py`, `src/su2plaq/rishon/{observables,verify}.py`, `tests/unit/test_rishon_stubs_unit.py`; new `tests/unit/test_rishon_{verify,observables}_unit.py` (all track-R files). No laptop-owned file (`evaluate/`, `exact/`, `encodings/base.py`, docs/METHODS.md, `tests/acceptance/`, `LOCK.json`) modified. No expected numbers hard-coded in the three source files (grep for 38432, 4352, long decimals: only the dimension 1296 in docstrings; observables quote formulas, not numbers). Exception handling: two `except` clauses in `verify.py` (the ValueError discussed above; `SimCapExceeded` → verdict reason `unsimulable_gauss` when the inner block is ok, never silent). My new scripts and JSON are under `results/rishon/tester-203-*` (untracked; the coordinator commits).

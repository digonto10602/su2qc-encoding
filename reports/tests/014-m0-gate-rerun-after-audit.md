# Tester report 014 - M0 gate rerun after audit 001 (mode full): step 0.11 "leak judged as amplitude" + audit fixes N2, N3, N4, N7, N8, N9

- Date: 2026-11-04. Commit: `35bd2a6` (= acceptance-v4) **plus uncommitted** changes in `src/su2plaq/{compress/spec,evaluate/{aer_check,evaluator,sparse_sim},exact/physical,metrics/{cliffordt,logical},results/{report,store}}.py` and `tests/unit/test_{evaluator,physical,results}_unit.py`.
- Prompt in force: `prompts/004-leak-amplitude-combined-error-bound.md` (on top of 003, 002). Related: `reports/tests/001`-`013`, `reports/audits/001-m0-foundation-audit.md`, `reports/research/003-leak-amplitude-bound.md`.
- Machine: 12 CPUs, 62 GB, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, pytest-xdist 6 workers. Seeds: no stochastic test in the gate; the only random scan (`scan.py`) used `default_rng(20261104)`.
- Raw numbers: `results/tests/014-leak-checks.json` (a, b, c-set 1, d-set 1), `014-leak-checks2.json`, `014-leak-checks3.json` (c, d, circuits that discriminate $\|X\|_2$ from the largest column norm), `014-paulo-p1.json`, `014-ry-ancilla.json`, `014-audit-spot.json`. Scripts are in the session scratchpad (`chk_leak.py`, `chk_leak2.py`, `chk_leak3.py`, `chk_paulo.py`, `chk_audit.py`, `chk_n9.py`, `chk_ry.py`, `scan*.py`, `cmp_logs.py`); every script took `commit` = `35bd2a6` as argument.

## Commands
```
graphify update . ; graphify affected evaluate     # affected: M0-E3/E4/E5/E6, M1-B1/B2/B3/B4/E1/S1/T1/P1 (all run or PENDING), tests/independent/evaluator_0_8/*
pytest -n auto tests/acceptance                    # full: 86 tests
pytest -n 6 tests/acceptance/m0 -q                 # 34 tests
pytest -n 6 tests/unit -q ; pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python chk_leak.py 35bd2a6 results/tests/014-leak-checks.json      # (a)(b)(c)(d) set 1
python chk_leak2.py / chk_leak3.py                                 # (c)(d) sets 2 and 3
python chk_paulo.py 35bd2a6 results/tests/014-paulo-p1.json         # (e), Paulo QPY loaded with qiskit.qpy (paulo_circuit() is still a stub)
python chk_audit.py results/tests/014-audit-spot.json ; python chk_n9.py <plain|noise> <seed> out.npz
adv1..adv7, adv9_fuzz (tests/independent/evaluator_0_8, outputs redirected to scratch) + cmp_logs.py    # regression vs the final logs of reports 009-011
```

## 1. Gate table
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `tests/acceptance/m0` (34 tests incl. slow C6 and new E6) | 34 pass | 34 passed, 0 failed, 0 skipped (33.1 s) | exact | PASS |
| E3, E5, E6, R1 (named ids) | pass | pass (E3 18.7 s, E5 19.5 s, E6 11.7 s, R1 0.03 s) | - | PASS |
| `tests/acceptance` full | m0 all pass; rest PENDING / known | 35 passed, 51 failed (33 s) = **47 PENDING** (`NotImplementedError`) + **3 known M1-R1** (`missing results/twelve/{UE,UB,step}.json`) + **1 known M1-O1** (`assert 3153 == 6561`, `test_twelve_outer.py:24`); 1 m2 pass (`macro_costs_match_lowering`) | - | PASS (no new failure) |
| PENDING by message | - | `default_spec` 24, `build_UB` 7, `gridsynth_T` 4, `build_UE` 3, `build_step` 3, `Archive.load` 2, `TwelveQubit.describe` 1, `paulo_logical` 1, `paulo_circuit` 1, `code_hash` 1 | - | all class PENDING |
| unit suite | all pass | 140 passed (131 before + 9 new), 48.7 s | - | PASS |
| `pytest --collect-only -q tests/acceptance` | 86, clean | 86 collected, 0 errors | - | PASS |
| `python tools/check_lock.py` | LOCK OK | LOCK OK | - | PASS |
| `~/.claude/bin/acceptance-check` | PASS (v4) | `PASS: tests/acceptance matches acceptance-v4` | - | PASS |

## 2. Independent checks of the new rule (own scripts)
Notation: $X$ = out-of-code part of the output on the physical inputs; `leak_amplitude` $=\|X\|_2=\sqrt{\lambda_{\max}(X^\dagger X)}$; `block_error` $=\|A-e^{i\varphi}V\|_2$.

### (a) $\mathrm{cry}(\theta)$ data $q_j\to$ ancilla, target $\mathbb 1$ (sparse engine, default tolerances $10^{-10}$)
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| leak_amplitude $=\sin(\theta/2)$, 4 link $j$-qubits (2, 5, 8, 11) $\times$ $\theta\in\{1.9\cdot10^{-6},10^{-8},10^{-10},10^{-3},0.3,\pi\}$ = 24 cases | exact | worst relative deviation $2.6\cdot10^{-16}$ | $10^{-3}$ (test) | PASS |
| $\theta=1.9\cdot10^{-6}$ (auditor's case, amplitude $9.5\cdot10^{-7}$) | rejected | `ok=False`, reason `dirty_ancilla`, amp $9.500000\cdot10^{-7}$, 10 failing inputs, old `max_leak` $9.0\cdot10^{-13}$ | - | PASS |
| $\theta=10^{-8}$ (amp $5\cdot10^{-9}$) | rejected | `ok=False`, `dirty_ancilla`, 10 failing inputs | - | PASS |
| $\theta=10^{-10}$ (amp $5\cdot10^{-11}$) | accepted | `ok=True`, op-norm $5.01\cdot10^{-11}$ ($=$ block $1.2\cdot10^{-13}$ + amp) | - | PASS |
| $\theta=1.9\cdot10^{-6}$ under `synth_tolerances(1,1e-6)` $=\{1.001\cdot10^{-6},1.001\cdot10^{-6}\}$ | accepted | `ok=True`, `tolerances == tol`, op-norm $9.500005\cdot10^{-7}$ | - | PASS |
| invalid-data-code variant `x; cry(θ,q_j,q_m'); x`, 5 $(q_j,q_{m'})$ pairs $\times$ $\theta\in\{1.9\cdot10^{-6},10^{-8},10^{-10}\}$ | $\theta\ge10^{-8}$: reason `leak`, `dirty_ancilla`$=0$, non-empty failing; $10^{-10}$ accepted | exactly that in all 15 cases (`dirty_ancilla` $=0.0$, 10 failing inputs, amp $=\sin(\theta/2)$ to $10^{-16}$) | - | PASS |

### (b) $\texttt{op\_norm\_error}=\texttt{block\_error}+\texttt{dropped\_total}+\texttt{leak\_amplitude}$
13 verdicts: `writes_outer`, `disallowed_gate` (mcx 3 controls), 3 x `bad_layout` (d11, o15, 5 qubits), `error` (Z on $q_j$), X on ancilla, `cry(0.3)`, identity (gauss on/off), `rz` on ancilla, outer read (cz), `inner_span` + `cry(1e-3)`. All five early exits report `inf` for all three terms and the sum identity (inf $=$ inf). Largest $|{\rm op}-{\rm sum}|$ over the eight finite verdicts: $0.0$ (tolerance $10^{-15}$). Invariant $\texttt{max\_leak}\le\texttt{leak\_amplitude}^2+10^{-30}$ held on every one. `evaluate(..., tol_leak=...)` raises `TypeError`. PASS.

### (c) $\|X\|_2$ (not the largest column norm) is what is reported
Own construction (no evaluator code): for each circuit, Qiskit `Statevector` evolution of the 625 valid inner codes; the out-of-code part $X_{\rm in}$ (outputs with any ancilla set or an invalid 12-bit data code); $G=X_{\rm in}^\dagger X_{\rm in}$; $X^\dagger X=\sum_oP_o^\dagger GP_o$ with the 3153 outer-pattern blocks $P_o$ taken from `enc.physical_vectors()` (33 425 entries); `eigvalsh`.

First, a finding about the test material: for 7 + 7 circuits of the "obvious" type ($Z$-basis controlled leaks, $H$-conjugated leaks, parity leaks, multi-controlled, leaks into invalid codes) and ~270 further circuits scanned with the evaluator (random rotations, all qubit pairs of 2-control `ccry`, all 66 CX parities, 4-bit patterns on link pairs, outer-controlled `cry` on all 16 outer qubits), $\|X\|_2$ equals the largest column norm $\max_k\|X\psi_k\|$ to $10^{-5}$ or better. Reason (my reading, a guess): the physical basis has definite link spins and the Gauss-law singlets are SU(2)-scalars, so $\Psi^\dagger G\Psi$ is diagonal for single-qubit-type leaks; $X^\dagger X$ in `xx_struct.py` has max off-diagonal $8.9\cdot10^{-19}$. Circuits that merge input codes $c$ and $c\oplus\mathbb 1_S$ into one leaked state with $S$ = all four $j$-qubits (or all 12 bits) break the diagonality; these are the discriminating cases:

| circuit (ancilla leak) | own $\|X\|_2$ | own max col | evaluator `leak_amplitude` | ratio ev/own | $\|X\|_2/\max$col | verdict |
|---|---|---|---|---|---|---|
| merge $S=\{2,5,8,11\}$, $\theta=0.3$ | 1.12201579e-1 | 1.05817767e-1 | 1.12201579e-1 | 1.000000000000 | 1.0603 | PASS |
| merge $S=\{2,5,8,11\}$, $\theta=0.1$ | 3.74889340e-2 | 3.53461333e-2 | 3.74889340e-2 | 1.000000000000 | 1.0606 | PASS |
| merge $S=\{2,5,8,11\}$, $\theta=0.8$ | 2.94388093e-1 | 2.78174701e-1 | 2.94388093e-1 | 1.000000000000 | 1.0583 | PASS |
| merge all 12 bits, $\theta=0.3$ | 1.12201579e-1 | 1.05817767e-1 | 1.12201579e-1 | 1.000000000000 | 1.0603 | PASS |
| merge $S=\{2,5,8,11\}$ with $R_z(0.7)$ on the pivot, $\theta=0.3$ | 1.12201579e-1 | 1.05817767e-1 | 1.12201579e-1 | 1.000000000000 | 1.0603 | PASS |
| merge $j$-bits ($\theta=0.2$, anc 0) + merge 12 bits ($\theta=0.15$, anc 1) | 9.35632595e-2 | 8.82446377e-2 | 9.35632595e-2 | 1.000000000000 | 1.0603 | PASS |

The evaluator's `max_leak` equals $(\max{\rm col})^2$ in each ($\sqrt{\texttt{max\_leak}}$ $=1.05817767\cdot10^{-1}$ etc.), so the two quantities are distinguishable and the evaluator reports the operator norm. In the non-discriminating sets (14 more circuits, `014-leak-checks.json`/`...2.json`) the evaluator also agrees with the own construction to a relative $10^{-9}$ (assertion) and in practice to $10^{-12}$. PASS. Caveat: no circuit I could build makes the gap larger than 6 % on this physical basis; the coherent-sum code path is exercised but not stressed.

### (d) aer_mps direct weights vs sparse (same circuits, `tol_err=1`, `gauss=False`)
Maximum support size of an outer block: **17** (builder is right, prompts/004 text "16" is off by one). Distribution over the 3153 outer patterns: size 1: 656, 2: 1120, 4: 504, 5: 576, 8: 216, **17: 81**. The bound $\sqrt{\max_oW_o}$ is a Cauchy-Schwarz upper bound for any support size, so validity does not depend on 16 vs 17; the worst-case pessimism is $\sqrt{17}=4.123$, not 4.

| circuit | sparse $\|X\|_2$ | aer_mps bound | ratio | in $[1,\sqrt{17}]$ |
|---|---|---|---|---|
| 3 x cry onto one ancilla | 1.048072e-1 | 4.192287e-1 | 4.0000 | yes |
| ccry + cry, 2 anc | 1.017972e-1 | 4.071888e-1 | 4.0000 | yes |
| rx on $m'$ of links 0,1 (invalid codes) | 4.997437e-2 | 8.541848e-2 | 1.7092 | yes |
| x-cry-x on 3 links (invalid codes) | 4.553210e-2 | 7.581367e-2 | 1.6651 | yes |
| rx on $j$ + cry | 4.083522e-2 | 1.633399e-1 | 4.0000 | yes |
| cry among $j$-qubits | 5.640978e-2 | 2.256391e-1 | 4.0000 | yes |
| ancilla chain | 6.016265e-2 | 2.406506e-1 | 4.0000 | yes |
| H-cry-H on $m'$, $m$, $j$ (3 circuits) | 7.0637e-2, 7.0637e-2, 7.0626e-2 | 2.9107e-1, 2.9107e-1, 2.9119e-1 | 4.1207, 4.1207, 4.1230 | yes |
| H-cry-H $d_0+d_4$; H-ccry-H $d_3,d_6$; H-cry-H $d_1,d_7,d_{10}$ (2 anc); H-ccry-H $d_0,d_3,d_6$ | 8.816e-2, 8.628e-2, 7.370e-2, 8.131e-2 | 3.171e-1, 3.081e-1, 2.926e-1, 2.897e-1 | 3.597, 3.571, 3.970, 3.563 | yes |
| merge circuits of (c), 6 of them | 3.75e-2 ... 2.94e-1 | - | 3.8874 ... 3.8937 | yes |
| cry($10^{-3}$) and cry($1.9\cdot10^{-6}$) $j\to$ anc (tolerance $10^{-9}$, aer certified) | 5.0e-4, 9.5e-7 | 2.0e-3, 3.8e-6 | 4.0000, 4.0000 | yes |
| **uncontrolled** $R_y(\theta)$ on ancilla (leak on every input) $\theta=10^{-3},0.1,1$ | $\sin(\theta/2)$ exactly | $\sqrt{17}\sin(\theta/2)$ | **4.12311 $=\sqrt{17}$** | yes (extremal) |

Range over 30 circuits: ratio $\in[1.665,\,4.12311]$, never below 1, never above $\sqrt{17}$ ($+10^{-6}$ slack in the assertion). Block errors of the two engines agree to all printed digits (e.g. $5.507\cdot10^{-3}$ vs $5.507\cdot10^{-3}$). **Cosmetic note:** for a gross leak (X on ancilla) aer_mps reports `leak_amplitude`$=\sqrt{17}=4.12$ and `max_leak`$=17$ (a "weight" larger than 1, adv6 log: err 5.123 vs sparse 2.000); still a valid upper bound, verdicts are rejected as they should be.

### (e) Paulo's QPY (`refs/paulo/SU2_plaquette_jmax_half_CT.qpy`, 34 qubits, 294 CX, 1162 T) through `evaluate` with $\{$tol_err $2\cdot10^{-5}$, tol_gauss $2\cdot10^{-5}\}$, target $U_B(\beta=1)$, `engine="auto"`
Loaded with `qiskit.qpy` because `circuits.twelve.paulo_circuit` is still a stub (M1-P1 itself is PENDING).

| quantity | planner prediction | got | tolerance (M1-P1) | verdict |
|---|---|---|---|---|
| `ok`, `reason` | ok | True, `ok` | - | PASS |
| `block_error` | $2.905\cdot10^{-6}$ | $2.9048\cdot10^{-6}$ (physical $2.9048\cdot10^{-6}$) | $\le1.6\cdot10^{-5}$ | PASS |
| `leak_amplitude` | $7.85\cdot10^{-6}$ | $7.8511\cdot10^{-6}$ | $\le2\cdot10^{-5}$ | PASS |
| `op_norm_error` (combined) | $1.08\cdot10^{-5}$ | $1.0756\cdot10^{-5}$ (= block + leak to $10^{-21}$); margin vs $2\cdot10^{-5}$: 1.86 | $\le2\cdot10^{-5}$ | PASS |
| `max_leak` | $6.2\cdot10^{-11}$ | $6.164\cdot10^{-11}\le\texttt{leak\_amplitude}^2=6.164\cdot10^{-11}$ | $\le$ amp$^2$ | PASS |
| `dirty_ancilla` | $\approx10^{-19}$ | $8.77\cdot10^{-20}\le\texttt{max\_leak}$ | - | PASS |
| `gauss_residual` | $1.16\cdot10^{-10}$ | $1.160\cdot10^{-10}$ | $\le2\cdot10^{-5}$ | PASS |
| `engine`, `certified`, `engine_accuracy` | aer_mps, True, $2\cdot10^{-10}$ | `aer_mps`, True, $2\cdot10^{-10}$ | $\le10^{-9}$ | PASS |
| `tolerances` | $=$ tol | $\{2\cdot10^{-5},2\cdot10^{-5}\}$ | exact | PASS |
| method, blocks, outer bits read | - | `inner_span`, 1, 0 | - | info |
| inverse target $U_B^\dagger$ | rejected | `ok=False`, `error`, op-norm 1.8186 | $>0.1$ | PASS |
| time | 67 s (prototype), 108 s (before) | **84.1 s** (inverse run 102 s) | - | info |

The sum-vs-RSS stop condition of prompts/004 §7 is not triggered: both terms are below the budget and the sum is below $2\cdot10^{-5}$.

## 3. Audit-fix spot checks
| fix | check | expected | got | verdict |
|---|---|---|---|---|
| **N2** | identity circuit vs outer-electric-phase target ($U_E$ with `include_outer_electric=True`, $\alpha=0.7$), methods `inner_span`/`physical`/`auto` | `block_error` $=\max$(inner-span error, physical error), never below the physical error | block $=1.935823$ $=$ inner $=$ physical (all three methods); inner-only $U_E$ target: $1.221864$ in all; identity: block $1.2068\cdot10^{-13}$ $=\max(1.2068\cdot10^{-13},3.4\cdot10^{-15})$ | PASS |
| **N4** | allowed multi-controlled gates with idle qubits (`mcp`, `c3sx`, `mcrx`, `mcry`, `mcrz`) 8 qubits: sparse sim vs `Operator` | exact | $\max|U_{\rm sparse}-U_{\rm Qiskit}|=1.67\cdot10^{-15}$ | PASS |
| N4 | same circuit through `metrics.logical.lower` (up to global phase) | exact | $6.8\cdot10^{-15}$ | PASS |
| N4 | `MCXGate(4)` with idle qubits: `lower`, `_translate`, and wrapped in a custom gate inside `evaluate` | rejected (T-count policy) | both `ValueError`; `evaluate` -> `disallowed_gate`; plus `ccx`/`cswap` with idle qubits exact ($0.0$) | PASS |
| N4 | root cause present and fixed: default `transpile` of `MCXGate(4)` vs `qubits_initially_zero=False` | hazard $\sim1$, fix $\sim10^{-16}$ | $0.99999999999999$ vs $6.7\cdot10^{-16}$ | PASS |
| **N7** | layout errors: `d` with 11 qubits, `o` with 15, 5-qubit circuit | reason `bad_layout`, non-empty `failing_inputs`, tolerances present | all three: `bad_layout`, message kept, `inf` for all numbers | PASS |
| N7 | `measure`, `mcx` 3 controls | still `disallowed_gate` | yes | PASS |
| **N8** | `verdict_to_dict` keeps `extra`; docstring of `evaluator.py` updated; new keys `block_error`, `leak_amplitude`; report column "leak amp" | present | present (unit test `test_verdict_extra_is_persisted`, M0-R1 passes, diff inspected) | PASS |
| **N9** | corner-singlet basis identical for BLAS thread count 1 vs 8 | identical | md5 of all 433 real amplitude vectors identical; keys identical; $\max|\Delta a|=0$ | PASS |
| N9 | basis rebuilt with symmetric noise $10^{-13}$ injected into every `eigh` input (3 seeds) | identical labels, same signs | supports identical in all 433 states, $\max|\Delta a|=5.8\cdot10^{-14}$, $6.9\cdot10^{-14}$, $8.0\cdot10^{-14}$ (no sign flip) | PASS |
| **N3** | direct (non-subtracted) aer weights | see (d) | identical-noise check: in adv6 `leak` for the exact outer-read circuit went from $2.2\cdot10^{-16}$ to $0.0$ | PASS |

## 4. Regression against reports 001-013
Re-ran adv1-adv7 and adv9_fuzz (tests/independent/evaluator_0_8, outputs to scratch) and compared line by line with the final logs of reports 009-011 (`cmp_logs.py`): 38/38/27/23/2/13/1/19 checks matched by name. Everything else of 001-013 is covered by the 140 unit tests, the 34 m0 tests and the locked lock files; reports 003-006, 012 and the physics numbers were not re-run individually this time (the unit suite and the acceptance tests exercise them; no source file of those steps changed apart from N9 in `physical.py`, verified above).

**Numbers that changed, all explained by prompts/004 or the audit fixes:**

| check (log) | old | new | cause |
|---|---|---|---|
| `op_norm_error` of every leaking circuit: X on ancilla 1.000 | 1.000 | 2.000 | op-norm now includes leak amplitude (1 + 1) |
| CX(outer$\to$inner) / CCX(outer,outer$\to$inner) | 1.000 / 1.000 | 1.866 / 1.866 | block 1.0 + leak amplitude 0.866 ($=\sqrt{0.75}$) |
| CRY(outer ctrl $\to$ inner) | 0.0199 | 0.192 | block + leak amplitude 0.172 |
| `forgot to uncompute`, `RC3X`, adv2 X on $q_{m'}$ | 1.0, 1.0, 2.0 | 2.0, 1.5, 3.0 | same |
| `ancilla ry(1e-5)` / `ry(1e-7)` | 1.26e-11 / 1.2e-13 (**ry(1e-7) accepted**) | 5.0e-6 / 5.0e-8 (**ry(1e-7) now rejected**) | the intended tightening (amplitude $5\cdot10^{-8}>10^{-10}$) |
| adv2 `oracle A` x3 with outer reads and data flips (CX, CCX, mixed): `err` | $4\cdot10^{-15}$, $4\cdot10^{-15}$, $6\cdot10^{-16}$ | 1.0, 0.866, 0.968 | the script asserts `op_norm_error<1e-12`; its oracle $\Psi^\dagger D\Psi$ is the block, and `block_error` still equals it: re-run with `block_error` in the assertion (`adv2b`) -> all PASS, block $<10^{-12}$. These circuits leak by construction (reason `leak`, weight 1 / 0.75 / 0.94) |
| adv3 `11 qubits` and adv9 `bad layout dsize`, `osize` (expected `ValueError`) | `ValueError` raised | verdict `bad_layout`, no exception | N7 (a verdict instead of an exception; the scripts assert the old behaviour). Flag for the coordinator: any caller that relied on `ValueError` from `evaluate` for a wrong register size must now check `reason == "bad_layout"` |
| adv4 / adv3 "identity vs outer-dependent diag target" span error | 0.299 | 0.397 | N2 (now $\max$ with physical) |
| adv6 aer_mps `leak` of exact circuits | $2.2\cdot10^{-16}$ | 0.0 | direct weights instead of $1-\sum|M|^2$ (N3) |
| adv6 `aer_mps rejects: X ancilla` | err 1.000, leak 1.0 | err 5.123, leak 17.0 | Cauchy-Schwarz bound $\sqrt{17}$ on a gross leak (see (d)); still rejected |
| adv2 `exact UE vs target with one row sign-flipped`, failing_inputs | 1 entry (217) | 10 entries (217 plus noise-level $3\cdot10^{-15}$ states) | for reason `error` the list is no longer filtered by `> tol_err` (it uses `> 0`); harmless but the list can contain states with noise-level error. Not a failure |

Not changed: all remaining checks of adv1-adv7/adv9 (PASS/FAIL status and numbers identical apart from timings and Qiskit UUIDs); the intentional negative controls (adv1 3, adv2 1, adv3 3, adv4 2, adv6 1, adv9 1) are the same as in 013. Paulo's QPY: $2.905\cdot10^{-6}$ block error (before: total $2.905\cdot10^{-6}$), Gauss $1.160\cdot10^{-10}$ unchanged; leak $4.19\cdot10^{-12}$ (weight, subtraction) $\to$ amplitude bound $7.85\cdot10^{-6}$.

## 5. Failures
None. Flags (not failures):
1. prompts/004 says "support $\le16$ inputs" and "$\le4\times$ pessimistic"; the physical basis has 81 outer blocks with 17 inputs and the measured worst ratio is $\sqrt{17}=4.123$ (uncontrolled ancilla rotation). The bound is valid; only the text is off.
2. aer_mps `leak_amplitude`/`max_leak` can exceed 1 (4.12 / 17) for gross leaks.
3. `evaluate` no longer raises `ValueError` for a wrong register size (N7 intended); `failing_inputs` for reason `error` uses `> 0`.
4. $\|X\|_2$ and the largest column norm coincide on all but the "merge" circuits (SU(2) structure of the physical basis); the maximum gap I could construct is 6 %.
5. Known and unchanged: M1-O1 (3153 vs 6561), M1-R1 files, 47 PENDING (M1/M2 builders and `paulo_circuit`).

VERDICT: PASS (m0 34/34, unit 140/140, acceptance-v4 lock + check OK, 86 collected; m1/m2: 47 PENDING + 3 known R1 + 1 known O1; independent checks (a)-(e) and N2/N4/N7/N8/N9 all pass; Paulo QPY combined $1.0756\cdot10^{-5}\le2\cdot10^{-5}$).

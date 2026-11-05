# Tester report 017 — M1 step 1.3 `build_UB` (+ simulator translation-path change)

- Date: 2026-11-04. Git commit: 99846e4 + uncommitted `src/su2plaq/circuits/twelve.py`, `src/su2plaq/evaluate/sparse_sim.py`, `tests/unit/test_sparse_sim_unit.py`, `tests/unit/test_twelve_circuits_unit.py`.
- Prompt in force: `prompts/004` (over `prompts/002` §4 row 1.3, `prompts/003`); `docs/METHODS.md` §2, §3.1. Mode: step. Related: reports/tests/008 (simulator), 015, 016.
- **VERDICT: FAIL** — all locked step tests are green (B1 x3, B2, B3, B4, P2), but the changed simulator has a new silent-wrong-result regression (cache collision, section 3, SERIOUS). U_B physics is correct.
- Raw numbers: `results/m1_step_1_3_{sim_regression,ub_physics,ub_counts_synth,sparse_peak,sparse_growth,synth_program_order}.json`; scripts `tests/independent/magnetic_1_3/*.py` (all need `PYTHONPATH=src`).

## Commands
```
pytest -n auto tests/unit                      # 151 passed, 57.6 s (was 143)
pytest -n auto tests/acceptance/m0             # 34 passed (incl. slow), 33.7 s
pytest -n auto tests/acceptance/m1 -rA         # 11 passed, 9 not green (below), 70.6 s
python tools/check_lock.py                     # LOCK OK;  ~/.claude/bin/acceptance-check -> PASS matches acceptance-v4
pytest --collect-only -q tests/acceptance      # 86 collected, clean
graphify update . ; graphify affected run_batch   # _simulate, evaluate, E1/E2, M1-B1, M1-E1, M1-P2, unit tests -> all run
python tests/independent/magnetic_1_3/check_sim_regression.py results/m1_step_1_3_sim_regression.json
python tests/independent/magnetic_1_3/check_ub_physics.py results/m1_step_1_3_ub_physics.json
python tests/independent/magnetic_1_3/check_ub_counts_synth.py results/m1_step_1_3_ub_counts_synth.json
python tests/independent/magnetic_1_3/check_sparse_{peak,growth,trace}.py, check_synth_program_order.py
```

## 1. Locked tests
| check | expected | got | result |
|---|---|---|---|
| M0 acceptance incl. slow (E1/E2 on the changed simulator) | 34 pass | 34 passed | PASS |
| unit | all | 151 passed | PASS |
| M1-B1 beta = 0.4 / 1.0 / 2.0 | pass | pass x3 | PASS |
| M1-B2, B3, B4 | pass | pass x3 | PASS |
| M1-P2 (paulo_logical) | pass | pass | PASS |
| M1-C1, M1-E1 [0.37, 0.91], M1-T1[UE] (regression) | pass | pass | PASS |
| acceptance-check / check_lock | OK | PASS (v4) / LOCK OK | PASS |

Not green in `tests/acceptance/m1` (9; none is a step-1.3 test): PENDING (NotImplementedError): S1[1], S1[2], T1[step] (`build_step`), P1 (`paulo_circuit`, step 1.6). Failing now, later step: O1 (3153 != 6561 entries, known, step 1.8), R1[UE|UB|step] (results files, step 1.9), **T1[UB]** (see section 5: `v.engine == "sparse"` fails, engine is `aer_mps`).

## 2. Simulator regression (translation path changed)
36 seeded random circuits (default_rng 3000..3035; 5 to 11 qubits; 30 to 80 gates; 24 contain foreign gates: ry rx y sxdg cy ch crz crx cry cswap rzz rxx iswap u3 rccx rc3x c3sx mcp(3 ctrl) cu cu3 ecr dcx csx controlled-RZ(3 ctrl), custom `to_gate` macros incl. nested; all contain 2-qubit `unitary` incl. a non-adjacent one, random global phase, barriers), 24 inputs each, vs Aer statevector and dense `Operator`:

| check | expected | got | tol | result |
|---|---|---|---|---|
| max abs error vs `Operator` | 0 | 2.2e-15 | 1e-12 | PASS |
| max abs error vs Aer statevector | 0 | 2.4e-15 | 1e-12 | PASS |
| program order vs DAG-schedule order (`_run` on the same op list) | identical | 5.7e-16 | 1e-12 | PASS |
| column norm deviation | 0 | 1.0e-14 | 1e-12 | PASS |
| special cases: ctrl_state variants (crz/cry with ctrl_state, `cx(ctrl_state=0)`, `ch`), same gate on different qubits, near-equal params (3e-1 vs 3e-1+1e-9), global phase + foreign gates, bound `Parameter`, barrier-only | 0 | <= 9.7e-16 | 1e-12 | PASS |
| forced pruning, certified bound, 80 circuits x 6 thresholds (1e-1..1e-14) x all columns = 64 896 cases (circuits now include `crx`, `rccx`, custom gates) | err <= `dropped_l2` | 0 violations; worst err - bound = +8.7e-16; max err/bound = 1.0000 | 1e-13 | PASS |
| mcx >= 3 controls rejected (`mcx` 3/4/5, C3X, C4X, MCXGate(3), recursion, v-chain, gray, `XGate().control(3)`, ctrl_state, with `unitary`, wrapped 1, 2, 3 levels deep, wrapped C4X, `to_instruction`, named wrapper) | ValueError | ValueError in all 19 | - | PASS |
| measure, reset, delay, `if_test`, `for_loop` rejected up front | ValueError | ValueError x5 | - | PASS |
| exact multi-controlled gates still accepted and exact (ccx, mcx2, mcp4, rccx, rc3x, c3sx, ccx on ancilla, wrapped rccx) | 0 | <= 1.4e-15 | 1e-12 | PASS |
| cap: 11-qubit H^10 H^10 circuit, 1 input, cap 200: program order | SimCapExceeded | SimCapExceeded | - | PASS |
| cap: same, DAG order | ok | ok (1 stored) | - | PASS |
| cap: `run_batch(cap=200)` falls back to DAG, result = dense | equal | equal, err 0 | - | PASS |
| cap: genuinely wide circuit (14 H-rz) cap 1000, both orders | SimCapExceeded | SimCapExceeded | - | PASS |
| **two different custom gates with the same name and no free parameters** | exact | **err 1.0** (2-qubit example), 0.737 (parametrised `to_gate` macros of one name) | 1e-12 | **FAIL** |

## 3. FAIL: `_DECOMP_CACHE` key collision (new in this change; HEAD handles the same circuits exactly, err 6e-17)
`_decompose_local` caches by `(op.name, tuple(float(params)), op.num_qubits)`. A circuit-derived `Gate` carries its angles inside its definition, not in `params`, so two different macros with the same name (`QuantumCircuit.to_gate()` takes the circuit's name) get the first one's decomposition. Silent wrong simulation, hence silent false accept/reject. Realistic repro, no exotic input (the builder names every circuit `"UB"`):
```
a = QuantumCircuit(2, name="m"); a.cx(0,1); b = QuantumCircuit(2, name="m"); b.cz(0,1)
q = QuantumCircuit(2); q.h(0); q.append(a.to_gate(),[0,1]); q.append(b.to_gate(),[0,1])
run_batch(q, arange(4))  vs Operator(q):  max error 0.7071
```
and `qc.append(build_UB(0.3).to_gate(), ...); qc.append(build_UB(0.31).to_gate(), ...)` evaluates as $U_B(0.60)$ (error vs target 0.60 = 1.3e-9, "ok") and is rejected for 0.61 (error 2.0e-2): the simulator applied $U_B(0.3)$ twice. Not reached by the current builders (`grep to_gate src` empty) and `build_UB(...).compose(...)` is correct (3.6e-13), but proposer programs in M2 can easily hit it. Guess for the fix (not mine to apply): cache only gates whose class is a Qiskit standard-library gate (name in `get_standard_gate_name_mapping()`), or key on the gate's definition (`id(op)` / a hash of `Operator(op)`), never on name alone.

## 4. U_B physics (independent assembly: 433 physical vectors, 28-bit codes, propagated through `build_UB(beta, with_outer=True)` with `run_batch`, projected on the physical basis; Gram of my vectors 7.3e-15)
$\epsilon_{\rm blk}=\min_\phi\|M-e^{i\phi}T\|_2$ on the 433x433 block, leak $=\|{\rm Out}-VM\|_2$ (everything outside the physical span, incl. ancillas $\neq 0$).

| beta | $\epsilon_{\rm blk}$ | leak | unitarity $\|M^\dagger M-1\|_\infty$ | `evaluate` (physical, Gauss on) | inner 625 block err / leak | Gauss | outer bits read |
|---|---|---|---|---|---|---|---|
| 0.4 | 1.7e-14 | 5.9e-15 | 3.4e-14 | ok, op-norm 1.4e-13, max_leak 0 | 1.2e-14 / 0 | 6.0e-16 | 0 |
| 0.61 | 1.7e-14 | 5.9e-15 | 3.4e-14 | ok, 1.4e-13 | 1.3e-14 / 0 | 7.6e-16 | 0 |
| 1.0 | 1.7e-14 | 5.9e-15 | 3.4e-14 | ok, 1.4e-13 | 1.3e-14 / 0 | 9.6e-16 | 0 |
| 2.0 | 1.7e-14 | 6.9e-15 | 3.3e-14 | ok, 1.3e-13 | 1.3e-14 / 0 | 7.3e-16 | 0 |

All $\le 10^{-10}$ (tol), $\ge 3$ orders margin. Engine `sparse`, pruning bound `dropped` 6e-15, 7 to 9 s per beta.

Wrong targets must fail (operator-norm distance of the circuit block to the wrong target, and `evaluate` verdict):

| wrong target | beta = 0.4 | 0.61 | 1.0 | 2.0 | `evaluate.ok` |
|---|---|---|---|---|---|
| $\beta\to-\beta$ (= dagger = complex conjugate, $T$ is symmetric) | 1.435 | 1.878 | 1.819 | 1.819 | False x4 |
| $1.01\,\beta$ | 8.0e-3 | 1.22e-2 | 2.0e-2 | 4.0e-2 | False x4 |
| $1.0001\,\beta$ | 8.0e-5 | 1.22e-4 | 2.0e-4 | 4.0e-4 | False x4 |
| identity | 0.78 | 1.15 | 1.68 | 1.82 | False x4 |

(errors $\approx |\Delta\beta|\,\|H_B\|=2|\Delta\beta|$, as expected.)

| check | expected | got | tol | result |
|---|---|---|---|---|
| composition: `build_UB(0.3)` then `build_UB(0.31)` vs target(0.61), 433 states | 0 | 3.0e-14 (leak 8e-15) | 1e-10 | PASS |
| `build_UB(0.3)` twice vs target(0.61) | fail | 2.0e-2 | - | PASS (fails as it must) |
| `build_UB(0.3)` twice vs target(0.6) | 0 | 3.1e-14 | 1e-10 | PASS |
| `paulo_logical(1.0)` (native `mcrx`) vs `inner_target` at beta = 1, 625 codes | 0 | 1.2e-14, leak 0 | 1e-10 | PASS |
| `paulo_logical(1)` block vs `build_UB(1)` block | 0 | 9.3e-16 | 1e-10 | PASS |
| `evaluate(paulo_logical(1), target UB 1.0)` | ok | ok, op-norm 2.4e-13, Gauss 7.6e-16 | 1e-10 | PASS |
| `paulo_logical(1)` counts: cx / n_rot / t_fixed / qubits / ancilla | 294 / 14 / 296 / 34 / 22 | 294 / 14 / 296 / 34 / 22 (depth 391) | exact | PASS |
| `ct_compile(paulo_logical(1), 1e-6, level 3, seed 12345)` vs Paulo's metadata | cx 294, T 1162, depth 2549 | cx 294, T 1162, depth 2549, gate counts identical (h 1155, t 1027, s 504, cx 294, tdg 135, sdg 92) | 5 % | PASS (exact equality) |

## 5. `build_UB(0.61)`: counts and T(eps)
| quantity | got |
|---|---|
| cx / n_rot / t_fixed / depth (level-0) / qubits / ancilla | 294 / 6 / 312 / 292 / 34 / 22 (with outer: 50 qubits, same cx, T, depth) |
| native gates | rccx 60, cx 50, x 50, h 16, cz 10, ccx 8, sdg 8, tdg 8, t 8, s 8, z 4, crx 3 |
| level-0 lowering | cx 294, h 178, t 160, tdg 152, x 50, s 8, sdg 8, z 4, rz 6 |
| rotations | 3 native `crx` (angles $-2\alpha_P=-2.44$, $-\alpha_P=-1.22$, $-\alpha_P/2=-0.61$ with $\alpha_P=2\beta=1.22$) = 6 `rz` of $|\theta|\in\{1.22, 0.61, 0.305\}$, **all on the single data qubit `d[11]`** (controls `h[0]`, `h[0]`, `g[1]`, ancillas) |
| outer register `o[0..15]` | touched by 0 gates |
| skeleton independent of beta | yes (same gate names for beta = 0.4 and 0.61) |
| ancillas returned to $|0\rangle$ | dirty weight 0 (all four betas) |

$T(\varepsilon)$ for `build_UB(0.61)`, $T_{\rm fixed}=312$, $N_{\rm rot}=6$ (`t_table`, pygridsynth 1.2.0; Qiskit column = Qiskit level-3 Clifford+T pass manager on the lowered circuit):

| $\varepsilon$ | $T_{\rm rot}$ pygridsynth | $T_{\rm total}$ | estimate $T_{\rm fixed}+3N\log_2(1/\varepsilon)$ | $T$ Qiskit | rel. diff Qiskit vs total | per-angle T ($|\theta|$ = 1.22, 1.22, 0.61, 0.61, 0.305, 0.305) |
|---|---|---|---|---|---|---|
| 1e-4 | 248 | 560 | 551.2 | 536 | 4.3 % | 42 42 44 44 38 38 |
| 1e-6 | 384 | 696 | 670.8 | 670 | 3.7 % | 62 62 64 64 66 66 |
| 1e-8 | 508 | 820 | 790.4 | 780 | 4.9 % | 84 84 86 86 84 84 |
| 1e-10 | 624 | 936 | 910.0 | 912 | 2.6 % | 104 x 6 |

CX after Qiskit level 3: 294 (no growth); Qiskit depth 864 / 1202 / 1485 / 1805. (Each of the 6 per-angle T values lies in the M0-measured band.)

### Feasibility of M1-T1[UB] on the sparse engine (the question asked)
`synthesize(build_UB(0.61), eps)` then `evaluate(..., **synth_tolerances(6, eps))`, inner-span method, 625 inputs:

| eps | engine | ok / certified | op-norm error (block + leak) | tolerance $6\varepsilon+10^{-9}$ | block / leak amp | Gauss (tol = same) | wall | T in circuit |
|---|---|---|---|---|---|---|---|---|
| 1e-4 | `sparse` forced | **unsimulable** (cap 5e6; also 2e7 and 6e7 on `run_batch`) | - | - | - | - | 2 s (fail) | 560 |
| 1e-4 | `auto` -> `aer_mps` | ok, certified (acc 2e-10) | 3.09e-4 | 6.0e-4 | 1.52e-4 / 1.57e-4 | 1.4e-10 | 51.6 s | 560 |
| 1e-6 | `sparse` forced | unsimulable (same caps) | - | - | - | - | 1.9 s (fail) | 696 |
| 1e-6 | `auto` -> `aer_mps` | ok, certified | 3.40e-6 | 6.001e-6 | 1.31e-6 / 2.09e-6 | 1.3e-10 | 53.6 s | 696 |

Consequence: **`test_M1_T1_t_table_and_synth_verify[UB]` fails today** at its last-but-one assertion (`v.engine == "sparse"`, got `aer_mps`; everything before it, i.e. the whole T(eps) table with Ross-Selinger bands, 10 % Qiskit agreement, CX growth, synthesise() n_rot/gates/error sum, and `v.ok`, passes). Peak RSS of my script 20.6 GB (aer_mps; informational).

Diagnosis (`check_sparse_peak.py`, `check_sparse_trace.py`; 5 inputs, cap 3e8): exact `build_UB(0.61)` peaks at 15 stored amplitudes per input in both orders, but `synthesize()` output peaks at $2^{21}=2\,097\,152$ per input in both orders (program order 17 s, DAG 15 s). The blow-up starts at gate 100 to 123, i.e. in the *compute* stage (relative-phase-Toffoli Hadamards on 21 ancillas), long before any rotation word (stored sizes during the rotation stage are 16 to 64). Cause (guess, but strongly supported): `synthesize()` starts from `metrics.logical.lower()`, a Qiskit level-0 transpile, which re-emits the circuit layer by layer and hoists all the Hadamards of the rccx/ccx expansions together, so the sparse engine sees 21 open branches; the new in-place program-order translation in `run_batch` cannot help because the order is already baked into the circuit. Not the number of rotation qubits (only `d[11]`).
Confirmed by a diagnostic that touches no source: lowering `build_UB(0.61)` **gate by gate in program order** to {cx, h, s, sdg, t, tdg, rz, x, z} and substituting the pygridsynth words (`check_synth_program_order.py`):

| eps | engine | ok / certified | op-norm error | tolerance | block / leak amp | Gauss | wall | T count |
|---|---|---|---|---|---|---|---|---|
| 1e-4 | `sparse` | ok / certified | 1.92e-4 | 6.0e-4 | 1.52e-4 / 4.05e-5 | 1.6e-15 | 7.9 s | 248 + 312 = 560 |
| 1e-6 | `sparse` | ok / certified | 1.85e-6 | 6.001e-6 | 1.31e-6 / 5.39e-7 | 1.9e-15 | 3.5 s | 384 + 312 = 696 |

So the feasibility answer is yes on the sparse engine, provided `lower()`/`synthesize()` keep program order (suggested fix: lower gate by gate, like `sparse_sim._decompose_local`, instead of one whole-circuit `transpile`). The T counts are the same as in `t_table`.

## 6. Failures (guessed causes)
1. **Simulator cache collision** (section 3), SERIOUS, new in this change. Guess: cache key `(name, params, n)` misses the gate's definition; key on definition/matrix or cache standard gates only.
2. **M1-T1[UB]** (fails at `engine == "sparse"`, not a step-1.3 test; will reappear at the T1 step): `synthesize()` uses a level-0 `transpile` that reorders gates layer by layer, giving a $2^{21}$-amplitude peak per input; guess: lower in program order. Physics of the synthesised circuit is fine (aer_mps and sparse-program-order agree it is within tolerance).

Everything else in the request: PASS (B1 all beta, B2, B3, B4, P2; U_B physics at 4 betas; wrong targets fail; composition; `paulo_logical`/Paulo metadata reproduced exactly; counts; rotation qubit and outer register as claimed).

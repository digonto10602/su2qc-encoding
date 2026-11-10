# Test report 102 — M3 steps 3.3–3.5 (`build_UE` + outer electric row, `build_UB`, `build_step` orders 1/2)

- Date: 2026-11-06 · Commit `1c4c73e` (HEAD) + uncommitted `src/su2plaq/circuits/spinnet.py`, `src/su2plaq/encodings/spinnet.py` (import_map now uses `paulo.QUBIT_MAP`/`QUBIT_MAP_OPEN`), `src/su2plaq/spinnet/paulo.py` (`N_FILE_QUBITS` removed), `tests/unit/test_spinnet_circuits_unit.py` (new)
- Branch `m3-spin-network`, prompt in force `prompts/100-spinnet-m3-plan.md` (§3 rows 3.3, 3.4, 3.5), mode **step**, tester Claude Sonnet 5.5
- Related: `reports/tests/100` (steps 3.0+3.1), `reports/tests/101` (step 3.2)
- Raw data and scripts (track-owned): `results/spinnet/tester/m3_steps_3_3_3_5.json` (+ `.log`), `m3_steps_3_3_3_5_verify.py`, `m3_steps_3_3_3_5_depth_probe.{py,json}`. Deterministic; the only random numbers are `np.random.default_rng(12345)` choosing 20 states for the 23-qubit cross-check. Peak RSS of the final run ≈ 1.75 GB under `systemd-run --user --scope -p MemoryMax=12G -p MemorySwapMax=0`.
- Process note: two earlier runs of my verify script were killed by the kernel OOM killer. Cause (my script, not the production code): the first version of the Gauss helper formed a dense `(rows × 433)` product `G @ W` (≈17 GB). Fixed in the script by the 433×433 Gram matrix $Q=G^\dagger G$; the 23-qubit cross-check was reduced to one state at a time (128 MB). The 433-column, 60-input 23-qubit runs seen before the second crash (UB and step 1, max entry deviation 0.0, dirty $\le1.4\times10^{-29}$) are not in the log any more (overwritten); the persisted 20-input runs below replace them.

## Commands
```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected build_UE|build_UB|build_step|import_map|QUBIT_MAP
taskset -c 0-9 pytest --collect-only -q tests/acceptance
taskset -c 0-9 pytest -n 10 -q tests/acceptance/m3 -rA --tb=line
taskset -c 0-9 pytest -n 10 -q tests/unit
taskset -c 0-9 pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0 taskset -c 0-9 python -u results/spinnet/tester/m3_steps_3_3_3_5_verify.py results/spinnet/tester/m3_steps_3_3_3_5.json
systemd-run --user --scope -q -p MemoryMax=12G -p MemorySwapMax=0 taskset -c 0-9 python results/spinnet/tester/m3_steps_3_3_3_5_depth_probe.py
git status --short
```
graphify: `affected` found no unique graph node for `build_UE/UB/step` (names collide with the tests); the only affected node listed was `test_qubit_maps_agree_with_encoding_import_map` (runs, green). All callers (acceptance E1/B1/B2/B3/S1/T1, unit tests) were executed.

## 1. Suites

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `pytest --collect-only -q tests/acceptance` | 126 clean | 126 collected | exact | PASS |
| `m3/test_spinnet_circuits.py`: E1[0.37], E1[0.91], B1[0.4/0.61/1.0/2.0], B2, B3, S1[1], S1[2] | 10 pass | 10 passed | — | PASS |
| C1, K1, P1 (regression) | pass | 3 passed | — | PASS |
| `m3/test_spinnet_metrics.py::T1[UE/UB/step]` (step 3.6 ids, already green) | pending allowed | 3 passed (synthesised re-verification included) | — | PASS (bonus) |
| m3 remaining failures | only later steps | 8 failed, all PENDING: L1, L2 (Counts.lean, Circuit.lean missing), L3 (Su2PlaqCert checker not delivered), V1[pairs9], V1[flags4] (`trotter_v2_circuit` NotImplementedError), R1[UE/UB/step] (missing `results/spinnet/*.json`) | no other reason | PASS (pending: steps 3.6/3.7/3.L*) |
| total m3 | — | 16 passed / 8 pending-failed / 0 real failures | | |
| `pytest -n 10 tests/unit` | all pass | 257 passed (+6 vs report 101: `test_spinnet_circuits_unit.py`) | — | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed | — | PASS |
| `tools/check_lock.py` / `acceptance-check` | OK | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v7` | — | PASS |

## 2. Independent physics check (Aer statevector, own targets)

Method. For each circuit: Aer statevector (not the library sparse engine) on the 47 inner codes of the circuit without the outer register (8 data + ancillas), then the 433×433 matrix $W$ is assembled using the fact that the outer register is a spectator. That assumption is verified structurally (below) and by direct 23-qubit Aer runs. $U_E$ with the outer register (16 qubits) was run on all 433 inputs. Targets: route-B (`enc.target`-equivalent built from `enc.h_magnetic()` and my own diagonal $H_E$ from the route-A labels), route A (`exact.operators.target`, then `gauge_align` – independent of `enc.gauge`). Error $=\lVert W-e^{i\varphi}V\rVert_2$ with $\varphi$ from $\arg\operatorname{tr}V^\dagger W$ (no phase fit gives the same digits). Leak = max over inputs of the amplitude on non-physical data codes (ancilla 0); dirty = max ancilla$\neq0$ probability; Gauss = $\max_k\lVert G\,W e_k\rVert$ with my own corner-Gauss operators from `LinkSpace` generators on the route-A decoded vectors (floor $1.1\times10^{-15}$ = the decoded basis itself).

**Structural (outer bits never written).** For UB, step 1, step 2 the with-outer circuit equals the no-outer circuit with ancilla indices shifted by 8 gate for gate (names, qubits, angles to $10^{-15}$): True ×3. Qubits touched in $\{8..15\}$: none. Registers `d[8], o[8], a[7]`, 23 qubits, global phase 0.0.

### 2a. $U_E$ (step 3.3)

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| my $H_E$ (sum of $j(j+1)$ over 4 inner links, from labels) vs `enc.h_electric()`; outer: all 12 links | equal | $0.0$, $0.0$; also $=\tfrac34\cdot\mathrm{popcount}(c\,\&\,0xF)$: $0.0$ | 1e-12 | PASS |
| single $j=\tfrac12$ link (code `0b0001`) amplitude after $U_E(\alpha)$ | $e^{-3i\alpha/4}$ | $\alpha=0.37$: $0.96174-0.27395i$ (exact match, dev $0.0$); $\alpha=0.91$: $0.77600-0.63073i$ (dev $0.0$) | 1e-12 | PASS (sign correct) |
| $U_E(0.37)$, $U_E(0.91)$, 433 states, no outer: error vs route B / route A | $\le10^{-10}$ | $1.6\times10^{-16}$ / $1.6\times10^{-16}$; $1.2\times10^{-16}$ / $1.2\times10^{-16}$; unitarity $2.2\times10^{-16}$; Gauss $1.1\times10^{-15}$; leak, dirty $0$ | 1e-10 | PASS |
| with_outer (16q), all 433 inputs, inner-only target | $\le10^{-10}$ | $1.6\times10^{-16}$ ($\alpha=0.37$), $1.1\times10^{-16}$ (0.91); same circuit vs the outer-electric target: $1.18$, $2.00$ (rejected, as it must) | 1e-10 / >1e-3 | PASS |
| with_outer + `include_outer_electric`, all 433 (16q): 12 `p` gates, error vs route B / route A outer-electric target | $\le10^{-10}$ | $4.0\times10^{-16}$ / $4.0\times10^{-16}$ ($\alpha=0.37$); $6.2\times10^{-16}$ ($0.91$); vs inner-only target $1.18$, $2.00$ (rejected); extra phase equals $e^{-3i\alpha n_{\rm out}/4}$ to $4.4\times10^{-16}$ | 1e-10 | PASS |
| `build_UE(include_outer_electric=True)` without `with_outer` | `ValueError` | `ValueError` (acceptance E1 + unit test) | — | PASS |

### 2b. $U_B$ (step 3.4), 433 states

| $\beta$ | err vs route B | err vs route A, ungauged | err vs route B$(-\beta)$ (must be rejected) | leak | dirty | Gauss | unitarity |
|---|---|---|---|---|---|---|---|
| 0.4 | $3.8\times10^{-15}$ | 0.779 | 1.435 | $4.3\times10^{-16}$ | $5.2\times10^{-31}$ | $1.1\times10^{-15}$ | $7.5\times10^{-15}$ |
| 0.61 | $3.8\times10^{-15}$ | 1.146 | 1.878 | $4.4\times10^{-16}$ | $4.8\times10^{-31}$ | $1.1\times10^{-15}$ | $7.4\times10^{-15}$ |
| 1.0 | $4.0\times10^{-15}$ | 1.683 | 1.819 | $1.1\times10^{-15}$ | $6.3\times10^{-31}$ | $1.1\times10^{-15}$ | $6.8\times10^{-15}$ |
| 2.0 | $5.5\times10^{-15}$ | 1.819 | 1.819 | $2.1\times10^{-15}$ | $7.0\times10^{-31}$ | $1.1\times10^{-15}$ | $6.6\times10^{-15}$ |

All within tolerance (error, leak $\le10^{-10}$, dirty $\le10^{-20}$). Route-A column "ungauged" is large only because route A and route B differ by the sign gauge; after my own `gauge_align` the residual is $3.8\times10^{-15}$ (UB 0.61) and the recovered diagonal $D$ equals `enc.gauge` (up to a global sign) in all four cases checked. Consistent with K1: wrong sign of $\beta$ is rejected by $1.4$–$1.9$ against the route-B target (it is a gauge change, not physics).

### 2c. Trotter steps (step 3.5), 433 states, 15-qubit Aer on 47 inner codes

$U_1=U_BU_E$ (electric layer first in the circuit), $U_2=U_E(\alpha/2)U_BU_E(\alpha/2)$. "wrong order" = the other order's target; "$U_E U_B$" = reversed product for order 1; "−β" = target at $-\beta$.

| circuit, $(\alpha,\beta)$ | err vs route B | err vs route A, gauge-aligned residual | leak | dirty | Gauss | wrong order | $U_EU_B$ (order 1) | −β |
|---|---|---|---|---|---|---|---|---|
| order 1, (0.37, 0.61) | $3.7\times10^{-15}$ | $3.8\times10^{-15}$ | $4.3\times10^{-16}$ | $5.1\times10^{-31}$ | $1.1\times10^{-15}$ | 0.515 | 0.990 | 1.878 |
| order 1, (0.91, 0.23) | $3.7\times10^{-15}$ | — | $3.4\times10^{-16}$ | $7.2\times10^{-31}$ | $1.1\times10^{-15}$ | 0.560 | 0.869 | 0.888 |
| order 1, (1.70, 1.00) | $4.2\times10^{-15}$ | — | $1.3\times10^{-15}$ | $4.9\times10^{-31}$ | $1.1\times10^{-15}$ | 1.74 | 1.61 | 1.819 |
| order 2, (0.37, 0.61) | $4.0\times10^{-15}$ | $3.9\times10^{-15}$ | $5.4\times10^{-16}$ | $4.6\times10^{-31}$ | $1.1\times10^{-15}$ | 0.515 | — | 1.878 |
| order 2, (0.91, 0.23) | $3.3\times10^{-15}$ | — | $3.6\times10^{-16}$ | $7.0\times10^{-31}$ | $1.1\times10^{-15}$ | 0.560 | — | 0.888 |
| order 2, (1.70, 1.00) | $4.1\times10^{-15}$ | $4.4\times10^{-15}$ | $1.3\times10^{-15}$ | $4.9\times10^{-31}$ | $1.1\times10^{-15}$ | 1.74 | — | 1.819 |

All PASS (accept $\le10^{-10}$; wrong order and −β rejected by $0.5$–$1.9 \gg10^{-3}$). The order-1 circuit has the electric `p` layer **before** the first `rz` (unit test + my structure check), i.e. the matrix product $U_BU_E$ as required.

### 2d. 23-qubit cross-check with the outer register present (one state at a time, 128 MB each, 20 seeded random physical states per circuit)

| circuit (with_outer) | inputs | max entry deviation vs 15-qubit inner-run matrix | dirty ancilla (sum) | leak | verdict |
|---|---|---|---|---|---|
| $U_B(0.61)$ | 20 | $0.0$ | $4.6\times10^{-30}$ | $4.4\times10^{-16}$ | PASS |
| step 1 (0.37, 0.61) | 20 | $0.0$ | $5.1\times10^{-30}$ | $3.5\times10^{-16}$ | PASS |
| step 2 (0.37, 0.61) | 20 | $0.0$ | $5.7\times10^{-30}$ | $5.4\times10^{-16}$ | PASS |

The library evaluator on all 433 states with the outer register (B2/B3/S1 acceptance) passed in addition (`outer_bits_read` 0, one block).

### 2e. Second-order Trotter claim

Operator-norm error of one step against $e^{-i(\alpha H_E+\beta H_B)}$ (433×433, route-B $H_B$), with $(\alpha,\beta)=s\,(0.37,0.61)$:

| $s$ | $\lVert U_1-\mathrm{exact}\rVert$ | $\lVert U_2-\mathrm{exact}\rVert$ | ratio $U_2/U_1$ |
|---|---|---|---|
| 1 | 0.5532 | 0.2370 | 0.43 |
| 0.5 | 0.1610 | 0.03381 | 0.21 |
| 0.25 | 0.04179 | 0.004365 | 0.10 |
| 0.125 | 0.010547 | 0.0005501 | 0.052 |
| 0.0625 | 0.002643 | 0.00006890 | 0.026 |

Log-log slopes (fit over $s\le0.5$): order 1 $=1.977$ (expected 2, local error $O(s^2)$), order 2 $=2.980$ (expected 3, local error $O(s^3)$). Circuit vs its own formula target remains $\le4\times10^{-15}$ at every $s$. PASS.

## 3. Counts, angles, skeleton

Own `qiskit.transpile(..., basis_gates=[cx,h,s,sdg,t,tdg,x,z,rz], optimization_level=0)` of the whole circuit vs `logical_metrics` (gate-by-gate lowering). CX, rotations, fixed T (= t+tdg+rz at odd $\pi/4$) agree exactly everywhere; depth also agrees.

| circuit | raw `count_ops` | CX | rot | $T_{\rm fixed}$ | qubits / anc | depth (own = library) | builder's claim | verdict |
|---|---|---|---|---|---|---|---|---|
| $U_E$ | `p`:4 | 0 | 4 | 0 | 8 / 0 | 1 | 0 CX / 4 rot / depth 1 | PASS |
| $U_E$+outer electric (16q) | `p`:12 | 0 | 12 | 0 | 16 / 0 | 1 | 12 rot | PASS |
| $U_B$ | x16, rccx14, cx12, rz4, h2 | 54 | 4 | 56 | 15 / 7 | 67 | 54/4/56/7/67 | PASS |
| step 1 | + p4 | 54 | 8 | 56 | 15 / 7 | 67 | 54 CX / 8 rot / 67 | PASS |
| step 2 | + p8 | 54 | 12 | 56 | 15 / 7 | 67 | 54 / 12 / 67 | PASS |
| $U_B$, step 2 with_outer | same | 54 | 4, 12 | 56 | 23 / 7 | 67 | outer adds no gates | PASS |

**Depth 67 for steps is real, not a metric quirk.** Probe (`m3_steps_3_3_3_5_depth_probe.json`): a layer of `p` on the head or tail of UB leaves the depth at 67 for qubits 0–3, data 0–7, corners 4–7, but gives 68 for all 15 qubits or the 7 ancillas. The critical path runs through the ancilla/flag chain (ASAP final times: ancilla 9 = 67, data 0–3 = 60–62), so the data-qubit `p` layers sit in slack. The metric is sensitive; no quirk.

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| $U_B$ rz angles / $\beta$ at $\beta\in\{0.4,0.61,1,2,0.23,-0.4\}$ | $(-\tfrac72,-1,3,\tfrac32)$ | match, max dev from the metadata fractions $\le7.1\times10^{-15}$ | 1e-9 | PASS |
| metadata `angle_fractions` | `["-7/2","-1","3","3/2"]` | identical at all six $\beta$ | exact | PASS |
| `p` angle / $\alpha$ in $U_E$ (α = 0.37, 0.91, 1.7) | $-3/4$ | $-0.75$ (to $10^{-16}$); in step 2 each half layer $-3/8$ | 1e-12 | PASS |
| gate skeleton (names + qubits) at (0.37,0.61), (0.91,0.23), (1.70,1.00), (0.01,0.02), (3.0,−0.4) | identical | identical for UB, step 1, step 2 | exact | PASS |

## 4. Code review items

- `git status --short`: modified `circuits/spinnet.py`, `encodings/spinnet.py`, `spinnet/paulo.py`; new `tests/unit/test_spinnet_circuits_unit.py`. No laptop-owned file, no `tests/acceptance/`, no `docs`/`prompts` touched. PASS.
- No hard-coded expected numbers: the only constant is `J_HALF_PHASE = 3/4` (= $j(j+1)$ at $j=\tfrac12$, the physical electric eigenvalue, also cross-checked against the labels, $0.0$ deviation); the `rz` angles come from `solve_angles` at every call; the unit tests compare with `0.75*alpha` and derived quantities only. PASS.
- No `try/except`, no bare `pass` in the new code (grep on the three source files and the unit test). PASS.
- Single definition of the Paulo qubit map is preserved (`import_map` reads `paulo.QUBIT_MAP`); the unit test `test_frame_and_target_single_definition` asserts it and the P1 acceptance test stays green. PASS.
- Observation (not a failure): `build_step` never includes the outer electric phases (documented in its docstring); the outer row exists only as `build_UE(..., include_outer_electric=True)`, as in the plan.

## Verdict

**PASS.** 16 m3 acceptance tests pass (E1×2, B1×4, B2, B3, S1×2, C1, K1, P1, T1×3); the 8 m3 failures are exactly L1–L3, V1×2, R1×3 and are PENDING for steps 3.6/3.7/3.L*; unit 257/257; m0+m1 54/54; lock and `acceptance-check` PASS. Independent Aer check: every circuit matches the route-B target on all 433 states to $\le5.5\times10^{-15}$, leak $\le2.1\times10^{-15}$, dirty ancilla $\le7\times10^{-31}$, Gauss at the $1.1\times10^{-15}$ floor, outer bits never written; wrong order and −β rejected by $\ge0.5$ and $\ge0.89$; Trotter slopes 1.98 and 2.98; counts match Qiskit exactly.

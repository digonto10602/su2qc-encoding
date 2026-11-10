# Test report 101 — M3 step 3.2 (Paulo 15-qubit file + phase-walk solver)

- Date: 2026-11-06 · Commit `3441ab1` (HEAD) + uncommitted `src/su2plaq/circuits/spinnet.py`, `src/su2plaq/spinnet/{paulo,walk}.py`, `tests/unit/test_spinnet_{paulo,walk}_unit.py`
- Branch `m3-spin-network`, prompt in force `prompts/100-spinnet-m3-plan.md` (§3 row 3.2), mode **step**, tester Claude Sonnet 5.5
- Related: `reports/tests/100` (steps 3.0+3.1)
- Raw numbers: `results/spinnet/tester/m3_step_3_2.json`, `m3_step_3_2_mirror.json`; scripts `results/spinnet/tester/m3_step_3_2_verify.py`, `m3_step_3_2_mirror.py` (deterministic, no random numbers). The verify script uses its own regex parse of the gate file and its own 15-qubit circuit (not `paulo.py`, not the sparse simulator): `qiskit.quantum_info.Statevector` on the 47 inner codes, 5-input Aer cross-check, `scipy.linalg.expm` of `enc.K_codes`.

## Commands
```
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected build_walk ; graphify affected load_circuit
taskset -c 0-9 pytest --collect-only -q tests/acceptance
taskset -c 0-9 pytest -n 10 -q tests/acceptance/m3 -rf --tb=line
taskset -c 0-9 pytest -q tests/acceptance/m3/test_spinnet_external.py::test_M3_P1_paulo15_open_states tests/acceptance/m3/test_spinnet_codec.py -v
taskset -c 0-9 pytest -n 10 -q tests/unit
taskset -c 0-9 pytest -n 10 -q -m "not slow" tests/acceptance/m0 tests/acceptance/m1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
taskset -c 0-9 python results/spinnet/tester/m3_step_3_2_verify.py results/spinnet/tester/m3_step_3_2.json
taskset -c 0-9 python results/spinnet/tester/m3_step_3_2_mirror.py results/spinnet/tester/m3_step_3_2_mirror.json
git status --short
```
graphify: `affected build_walk` = the two walk unit tests; `affected load_circuit` = `paulo_circuit` and the paulo unit test (both run). `paulo_circuit` has no unique graph node (name collision with the test), covered via `load_circuit`.

## 1. Suites

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `pytest --collect-only -q tests/acceptance` | 126, clean | 126 collected | exact | PASS |
| `m3/test_spinnet_external.py::test_M3_P1_paulo15_open_states` | pass | pass | — | PASS |
| `m3/test_spinnet_codec.py::test_M3_C1…`, `…K1…` | pass | 2 passed | — | PASS |
| `tests/acceptance/m3` total | 3 pass, rest PENDING | 3 passed, 21 PENDING: 15 `NotImplementedError` (build_UE x3, build_UB x7, build_step x3, trotter_v2_circuit x2), 3 Lean (Counts.lean, Circuit.lean missing; checker not delivered), 3 `missing results/spinnet/{UE,UB,step}.json` | no other reason | PASS (pending are later steps 3.3–3.7, 3.L*) |
| `pytest -n 10 tests/unit` | all pass | 251 passed (laptop flake `test_results_unit` did not trigger at `3441ab1`) | — | PASS |
| m0+m1 `-m "not slow"` | green | 54 passed | — | PASS |
| `tools/check_lock.py`, `acceptance-check` | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v7` | — | PASS |

## 2. Paulo's file, independent numbers (open 433 states; $\beta=\alpha_P/2=0.05$)

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| sha256 of the file | pinned `e4b8687f…a504` | identical (own `hashlib`) | exact | PASS |
| own parse: gate counts | 68 CX, 34 H, 12 X, 32 T, 32 Tdg, 4 p; 182 lines; 15 qubits touched ({0-3, 12-22}) | identical | exact | PASS |
| `paulo_circuit()` gate-by-gate vs own parse (name, mapped qubits, angle) | 0 mismatches | 0 of 182; ops `{cx 68, h 34, t 32, tdg 32, x 12, p 4}`; the 4 `p` stay `p` (not renamed `rz`) | exact | PASS |
| lowered (level-0) counts | 68 CX, 64 T, 4 rot, 7 anc | cx 68, h 34, t 32, tdg 32, x 12, rz 4; `logical_metrics`: cx 68, t_fixed 64, n_rot 4, ancilla 7, qubits 15, depth 90; rz angles [0.025, 0.05, 0.1, −0.2] = $\alpha_P(\tfrac14,\tfrac12,1,-2)$ | exact | PASS |
| `with_outer=True`: 23 qubits, outer 8–15 untouched, global phase | none touched, 0 | none touched, 0.0 | exact | PASS |
| unitarity of the 47×47 block (own sim) | $\mathbb 1$ | $1.1\times10^{-14}$ | 1e-10 | PASS |
| leak (amplitude outside the 47 inner codes, ancilla bits $\neq 0$) | 0 | $8.2\times10^{-16}$; dirty-ancilla probability $6.6\times10^{-31}$ | 1e-10 / 1e-20 | PASS |
| Aer statevector vs `Statevector` (5 inputs) | agree | max dev $7.4\times10^{-15}$ | 1e-10 | PASS |
| raw route-B target $e^{-i\beta K}$, $\beta=+0.05$ (47×47, up to global phase) | rejected, $\approx 0.2$ | $0.19967$ (= $2\sin(2\beta)$, $k_{\max}=2$) | > 0.1 | PASS |
| gauge: pair ratio $M_{ba}/(\varphi V_{ba})$ on the 8 bright pairs (31 dark, 16 bright) | $-1$ on each | all 8 equal $-1$ (within $4\times10^{-15}$), imaginary parts $\le 3.5\times10^{-15}$; global phase from dark codes $1 \pm 5\times10^{-15}$ | — | PASS (8 minus signs, one per pair) |
| gauged 47×47: $\lVert M-D\,e^{-i\beta K}D\rVert_2$ | 0 | $5.8\times10^{-15}$ (entrywise max $5.6\times10^{-16}$) | 1e-10 | PASS |
| 433-level, own matrix $W$ from $M$ + code map: output weight on non-physical codes | 0 | 0.0 (every output code is a physical code, so Gauss is preserved exactly) | 1e-10 | PASS |
| 433-level $\lVert W - \mathrm{regauge}(V_B)\rVert$ | ≈ 0 | $5.6\times10^{-15}$ | 1e-10 | PASS |
| 433-level vs raw `enc.target("UB",None,0.05)` | rejected | $0.19967$ | > 0.1 | PASS |
| evaluator, gauge-fixed (23-qubit circuit, 433 inputs, `physical`, `gauss=True`) | ok | ok, err $9.7\times10^{-15}$, leak 0, Gauss $5.4\times10^{-16}$, dirty 0, outer_bits_read 0, engine sparse | 1e-10 | PASS |
| evaluator, raw target | not ok | `reason="error"`, err $0.19967$ | > 0.1 | PASS |

Finding (consistent with the plan, not a failure): the 8 minus signs are equivalent to flipping the sign of $\beta$. With my own bit-for-bit mapping, $M = e^{+i\beta K}$ with no gauge at all (error $5.78\times10^{-15}$ for $-\beta$; identical to the gauged value), i.e. $D K D=-K$ for $D$ with one $-1$ per bright pair. This matches "exp(+i α_P Re Tr U_P)" in the file and "sign of β is a gauge at $j_{\max}=\tfrac12$".

## 3. `build_walk(GENERAL7, β)`

Independent check: own 15-qubit `Statevector` run on the 47 inner codes against `scipy.linalg.expm(-1j*beta*enc.K_codes)`, plus the library evaluator against `enc.target("UB",None,β)` (433 states, ancilla cleanliness, and with the outer register under `method="physical", gauss=True`).

| β | 47×47 error vs expm | leak (own) | evaluator err (no outer) | evaluator err (outer, 433) | Gauss | outer_bits_read | rz angles / β |
|---|---|---|---|---|---|---|---|
| 0.4 | $8.8\times10^{-16}$ | $2.7\times10^{-16}$ | $1.05\times10^{-14}$ | $1.01\times10^{-14}$ | $5.4\times10^{-16}$ | 0 | (−3.5, −1, 3, 1.5) |
| 0.61 | $1.6\times10^{-15}$ | $1.6\times10^{-16}$ | $1.02\times10^{-14}$ | $9.8\times10^{-15}$ | $5.4\times10^{-16}$ | 0 | same |
| 1.0 | $2.1\times10^{-15}$ | $1.0\times10^{-15}$ | $1.42\times10^{-14}$ | $1.42\times10^{-14}$ | $5.4\times10^{-16}$ | 0 | same |
| 2.0 | $4.3\times10^{-15}$ | $2.0\times10^{-15}$ | $2.05\times10^{-14}$ | $2.05\times10^{-14}$ | $5.4\times10^{-16}$ | 0 | same |

All `ok`, evaluator leak 0, dirty ancilla 0 (tolerance 1e-10 / 1e-20): PASS at all four β.

| check | expected | got | verdict |
|---|---|---|---|
| angles linear in β | θ/β constant | rz/β constant to $2\times10^{-15}$ across β ∈ {0.4, 0.61, 1, 2}; solve residual $4\times10^{-15}$ | PASS |
| `angle_fractions` (order of the 4 rz in the skeleton) | $(-\tfrac72,-1,3,\tfrac32)$ | `[-7/2, -1, 3, 3/2]` | PASS |
| distinct non-zero $K$ entries | — (record) | {0.5, 1, 2}; 31 dark codes | recorded |
| counts at β = 0.61 (record, not asserted) | ≈ 54 CX, 4 rot, 56 T_fixed, 7 anc | circuit ops {x 16, rccx 14, cx 12, rz 4, h 2}; lowered: **cx 54, n_rot 4, t_fixed 56** (h 30, t 28, tdg 28, x 16), ancilla 7, qubits 15, depth 67 | recorded |
| `mirror` with rc3x / rc3x_dg / rccx (not used by GENERAL7; needed for 3.6) | compute·mirror = 𝟙 | $1.6\times10^{-15}$; RC3X classical action matches Toffoli semantics on all 16 inputs; plain `RC3X` is not self-inverse ($\lVert g^2-\mathbb 1\rVert=2$) so the inverse swap is required | PASS |

## 4. Code review items

- `git status --short`: only the five listed source/test files are modified/new (plus my `results/spinnet/tester/*`); no laptop-owned file touched. PASS.
- No `try`/`except` anywhere in `paulo.py`, `walk.py`, `circuits/spinnet.py`; failures raise `ValueError` (sha mismatch, unparsable line, unknown gate, file touching q4–11 gives `KeyError`, K not a matching, non-rational angles, residual > 1e-9). PASS.
- Hard-coded numbers: the SHA256 is a provenance constant, also checked against `refs/paulo/SOURCE.md` by a unit test and rechecked by me with `sha256sum`; acceptable. `FILE_ALPHA_P = 0.1` is a typed constant (not derived from the file) but is cross-checked by the file's own angles ($\alpha_P(\tfrac14,\tfrac12,1,-2)$) in both the unit and acceptance tests; acceptable as provenance. The rotation angles come from the file (Paulo) or are solved from $K$ (walk), never typed. GENERAL7 is a structural skeleton, not an expected number. PASS.
- Minor, non-blocking: (a) `QUBIT_MAP`/`QUBIT_MAP_OPEN` are duplicated in `encodings/spinnet.import_map` and `paulo.py` (guarded by `test_qubit_maps_agree_with_encoding_import_map`); `FRAME`/`TARGET` are duplicated in `walk.py` and `circuits/spinnet.py`; (b) `N_FILE_QUBITS = 23` is unused; (c) the walk unit test checks `ops["rccx"] == 14` and `set(ops) <= {...}`, a structural check, fine.

## Verdict

**PASS.** 0 failures, 3 acceptance tests passed (P1, C1, K1), 21 later-step m3 tests PENDING (no new failures versus report 100), unit 251/251, m0+m1 54/54, lock OK.

# Tester report 007 — M0 step 0.7, sparse simulator

- Date: 2026-11-04
- Commit: 06ea6bc (step files `src/su2plaq/evaluate/sparse_sim.py`, `tests/unit/test_sparse_sim_unit.py` uncommitted)
- Prompt in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (§2.7, §3 row 0.7), `docs/METHODS.md` evaluator section
- Mode: step
- Previous report: `reports/tests/006-m0-step-0-6-route-b-spin-network.md`
- Verdict: **FAIL** (one check, pruning accounting; everything else PASS). Details in section 3.

## 1. Commands

```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
graphify update . ; graphify affected "run_batch" ; graphify affected "encoded_block"
pytest -n auto tests/unit
pytest -n auto -m "not slow" tests/acceptance/m0
pytest tests/acceptance/m0/test_sparse_sim.py
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
# own scripts (copies in scratch/, gitignored): chk1e.py (1), chk2.py (2), chk3.py (3), chk4.py (4), chk5.py / chk5b.py (5)
```

graphify `affected` for `run_batch`/`encoded_block`: M0-E1, M0-E2, M1-E1, M1-B1, M1-P2 (M1 tests are pending, later steps). Everything reachable now (E1, E2) was run.

## 2. Standard checks

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| unit tests `tests/unit` | all pass | 77 passed (8 s) | – | PASS |
| M0-E1 `test_M0_E1_vs_aer` | pass | pass | 1e-12 | PASS |
| M0-E2 `test_M0_E2_vs_dense_operator` | pass | pass | 1e-12 | PASS |
| earlier M0 acceptance (A1-A3, G1-G2, C1-C5, X1-X8) | pass | 23 passed (incl. E1, E2) | – | PASS |
| PENDING (NotImplementedError only) | – | 9: E3, E4, E5 (TwelveQubit/evaluator), M1, M2 x3, M3 (metrics/gridsynth/ct_compile), R1 (save_result); all raise `NotImplementedError`, none are real failures | – | PENDING |
| `tools/check_lock.py`, `acceptance-check` | OK | LOCK OK; "tests/acceptance matches acceptance-v2" | – | PASS |
| `--collect-only` | 84 tests, clean | 84 collected | – | PASS |

Note: the plan table for row 0.7 also lists `evaluate/aer_check.py`; it is still a stub (`aer_statevector_block`, `aer_mps_block` call `todo`). The coordinator's brief did not name it, so it is recorded but not counted as a failure here.

## 3. Independent checks

### (1) vs Aer and dense Operator on random circuits: PASS
36 seeded circuits (seeds 1000..1035), 5 to 14 qubits, 31 to 89 gates, nonzero random global phase, 1358 basis inputs in total (≤ 40 per circuit, batched), gate set h, sx, u, rz, p, cp, ccx, ccz, swap, cx, cz, t, tdg, s, sdg, x, z, a random 2-qubit `unitary` on qubits (0, n-1) in every circuit plus a random-orientation one; 12 circuits additionally use gates outside SIM_BASIS (ry, rx, y, sxdg, cy, ch, crz, cswap, rzz, iswap, u3) to exercise the transpile / per-instruction `unitary` path. Reference: Aer statevector (inputs sub-sampled to every 6th for n ≥ 13) and `Operator` (n ≤ 10, 20 circuits). Raw: `results/m0_step07_check1.json`.

| check | expected | got | tol | result |
|---|---|---|---|---|
| max amplitude error vs Aer | ≤ 1e-12 | 3.2e-15 | 1e-12 | PASS |
| max amplitude error vs `Operator` | ≤ 1e-12 | 2.9e-15 | 1e-12 | PASS |
| max deviation of column norm from 1 | ≤ 1e-12 | 3.8e-15 | 1e-12 | PASS |

Side finding (not a failure of the contract, see section 5): `mcx` with ≥ 3 controls on a circuit that has an idle qubit returns a wrong operator (error 0.5 to 1.0) because Qiskit's transpile uses idle qubits as clean ancillas.

### (2) Pruning (|a| ≤ 1e-14 dropped after every branching gate, no accounting): FAIL
Method: run with `PRUNE = 1e-14` and with `PRUNE = 0` (exact, large cap) and compare in $\ell^2$; compare with the closed formula for product states. Raw: `results/m0_step07_check2_pruning.json`, `results/m0_step07_check2_product_bound.json`.

**What is dropped, theory.** A column's state is a vector $\psi$ with $K$ stored entries. A branching gate creates at most $2^k K$ entries; each dropped entry has $|a|\le\delta=10^{-14}$. The dropped $\ell^2$ norm is $\le\sqrt{2^kK}\,\delta$ per gate, and since later gates are unitary the errors add at most linearly over gates: $\|\psi_{\rm sim}-\psi_{\rm exact}\|\le\sum_g\sqrt{D_g}\,\delta$, $D_g$ = number of dropped entries. With the evaluator's cap $K\le5\cdot10^6$ the per-gate worst case is $\sqrt{10^7}\cdot10^{-14}=3\cdot10^{-11}$, i.e. 3 gates are enough to reach $10^{-10}$ (the evaluator's op-norm tolerance).

**Measured, product states of rotations** ($n$ qubits each passed through $h$-$rz(\theta)$-$h$, drop rule identical to the simulator; the closed form matches the simulator to 1e-13 relative at every point):

| n | θ (rad) | stored (pruned / exact) | dropped $\ell^2$ norm, measured | closed form |
|---|---|---|---|---|
| 12 | 3e-3 | 794 / 4096 | 2.14e-13 | 2.14e-13 |
| 16 | 3e-3 | 2517 / 65536 | 5.02e-13 | 5.02e-13 |
| 20 | 1e-8 | 21 / 1048576 | 3.4e-16 | 3.4e-16 |
| 20 | 1e-4 | 1351 / 1048576 | 4.4e-16 | 4.4e-16 |
| 20 | 3e-3 | 6196 / 1048576 | 9.5e-13 | 9.5e-13 |
| 20 | 0.2 | 988116 / 1048576 | 1.87e-12 | 1.87e-12 |

Worst case over $\theta$ for the product state, restricted to cap-compliant retained support ($\le5\cdot10^6$ entries, closed form validated above):

| n | max dropped $\ell^2$ (one column) | at θ (rad) | retained entries |
|---|---|---|---|
| 12 | 2.8e-13 | 0.0091 | 1586 |
| 16 | 1.1e-12 | 0.035 | 26333 |
| 20 | 3.9e-12 | 0.079 | 431910 |
| 24 | 1.3e-11 | 0.105 | 4.5e6 |
| 28 | 2.3e-11 | 0.055 | 4.8e6 |
| 34 | 2.3e-11 | 0.020 | 1.7e6 |

So ordinary small-angle layers (0.02 to 0.1 rad on 20 to 34 qubits) already lose $10^{-12}$ to $2\cdot10^{-11}$ per column in a single layer, and the loss is silent and accumulates over layers. Tiny rotations of $10^{-8}$ rad on many qubits lose only 3e-16 (they are mostly kept; the dropped tail is the $f\ge2$ products below 1e-14).

**Constructed scenario that biases the op-norm verdict.** $m=20$ qubits in $|+\rangle$ ($K=2^{20}$ entries of amplitude $2^{-10}$), then $N$ gates $u(\theta,0,0)=R_y(\theta)$ with $\theta=2\cdot10^{-11}$ rad on a 21st qubit in $|0\rangle$ (an empty target, so the new entries do not merge with existing ones): branch amplitude $2^{-10}\sin(\theta/2)=9.8\cdot10^{-15}\le10^{-14}$, dropped for every one of the $2^{20}$ entries.

| N gates | stored (pruned / exact) | $\|\psi_{\rm sim}-\psi_{\rm exact}\|_2$ | $\sin(N\theta/2)$ (analytic) |
|---|---|---|---|
| 10 | 1048576 / 2097152 | **1.0e-10** | 1.0e-10 |
| 20 | 1048576 / 2097152 | **2.0e-10** | 2.0e-10 |
| 40 | 1048576 / 2097152 | **4.0e-10** | 4.0e-10 |

The simulator reports the 21st qubit as exactly $|0\rangle$ for any $N$, while the true rotation grows linearly; the error enters the code block $M$ directly (if the qubit is a code qubit) and exceeds / equals the $10^{-10}$ op-norm tolerance for $N\ge10$. Smaller supports (m = 10, 12, 16) did not trigger the drop at the same angles, as predicted ($|a|\sin(\theta/2)>10^{-14}$).

**Leak check ($10^{-12}$, defined on weights).** Dropped weight per gate $\le D_g\delta^2\le10^7\cdot10^{-28}=10^{-21}$, and in the scenario above $(2\cdot10^{-10})^2=4\cdot10^{-20}$. This cannot bias the $10^{-12}$ leak check. The op-norm check is the exposed one.

**Verdict for check (2): FAIL.** The silent drop can bias a $10^{-10}$ op-norm verdict (demonstrated: $1\cdot10^{-10}$ with 10 gates; and $\sim2\cdot10^{-11}$ per column per layer in generic small-angle product circuits). Whether such circuits occur in the compression loop is unknown, but the evaluator cannot tell, because nothing is recorded. Guess of the cause: `_coalesce` filters `|a| > PRUNE` with an absolute threshold and returns no dropped-norm bookkeeping. Proposed remedy (for the coordinator / builder to decide): add `dropped_l1` and `dropped_l2` fields to `Batch` (accumulated in `_coalesce`) and let the evaluator add `dropped_l1` to its error budget (or reject when it exceeds, say, 1e-12); alternatively prune only when $|a|\le10^{-14}$ AND the total accumulated dropped $\ell^1$ stays below a stated budget. Not a physics-method error, an accounting gap.

### (3) Cap, qubit limit, measure/reset: PASS
| check | expected | got | result |
|---|---|---|---|
| 30-qubit all-$h$, 1 input, cap 5e6 | `SimCapExceeded`, bounded time | raised after 1.47 s (gate #22, 2^23 entries) | PASS |
| 30-qubit all-$h$, 625 inputs | raised | raised after 0.89 s | PASS |
| 40-qubit all-$h$, 1 input | raised | raised after 1.44 s | PASS |
| 34 qubits, cap 1000, 4 inputs | raised | raised after 0.00 s | PASS |
| cap equal to exact count (1024 entries, cap 1024) / cap 1023 | no raise / raise | no raise (amp 0.03125) / raise | PASS |
| number of inputs > cap | raise | raised | PASS |
| 62 qubits (incl. key $2^{61}$, 2 input columns) | works | works, keys/cols correct | PASS |
| 63, 64 qubits | `ValueError` | `ValueError("at most 62 qubits")` | PASS |
| `measure`, `measure_all`, `reset`, `reset`+`unitary` (per-instruction path), `if_test` | rejected | `ValueError` each | PASS |

Peak memory note: the cap is tested after coalescing, so a single branching gate can transiently hold up to $2^k\times$ cap entries (measured: heavy run below, stored 2.56e6, transient 5.12e6, RSS 810 MB). Bounded by about $4\cdot\text{cap}\cdot(8+4+16)$ bytes $\approx0.6$ GB at the default cap. OK. Minor: `delay` is rejected like an unsupported gate (harmless in practice).

### (4) `encoded_block`: PASS
Hand example: 3 qubits (data = bits 0,1; ancilla = bit 2), codes $\{00,11\}$, mask `0b011`, circuit $h(0)\,\mathrm{cx}(0,1)$, inputs $\{000,100\}$. Expected $M[:,0]=(2^{-1/2},2^{-1/2})$, leak 0; input 100: all weight has the ancilla set, $M[:,1]=0$, leak 1. Got $M[:,0]=(0.707107,0.707107)$, leak $=(0,1)$. Reordering `codes` reorders the rows of $M$ (checked). Direct-sum test with a hand-built non-normalised batch (amplitudes 0.5 in a code, $0.5i$ on a non-code, 0.2 on a key with an ancilla bit): leak $=0.25+0.04=0.29$ (expected, direct sum of out-of-code weights); $1-\sum$ would give 0.75. A code with a bit outside the mask is never matched (counted as leak). Empty batch gives zeros. Ancilla-$h$ example: leak 0.5 per column and $\sum|M|^2=0.5$. Minor precondition: duplicate entries in `codes` put the amplitude into the first row only (no loss from either $M$ or leak).

### (5) Timing, almost-classical 34-qubit circuit, 625 inputs: PASS (with the structure caveat)
Circuit generator `scratch/chk5.py` (seed 20261104, inputs: 625 random 12-bit data patterns, ancillas 0): ~3000 permutation/phase gates (x, cx, ccx, rz, p) plus 14 Pauli-rotation blocks, each with 3 $h$ pairs, a CX ladder, an $rz$ and uncompute, all in compute-uncompute form; 4109 gates, 84 $h$ (42 pairs). A first structure with random permutations moving the data qubits (never uncomputed) hit `SimCapExceeded` after 5 s, as expected for entangled garbage; that is a property of the circuit, not of the simulator, and is exactly the case `aer_mps` fallback is for.

| circuit | gates | h | wall (s) | peak transient entries | final entries | max column-norm deviation | max RSS (MB) |
|---|---|---|---|---|---|---|---|
| 14 blocks x 3 h, rotations on data qubits 0-7 | 4109 | 84 | 2.99 | 3.2e5 | 1.6e5 | 1.4e-14 | 145 |
| 14 blocks x 3 h, rotations on data qubits 0-4 | 4109 | 84 | 0.47 | 4.0e4 | 2.0e4 | 1.4e-14 | 145 |
| 40 blocks x 1 h pair, rotations on data qubits 0-7 | 3825 | 80 | 2.11 | 3.2e5 | 1.6e5 | 1.4e-14 | 148 |
| HEAVY: 14 blocks x 3 h, rotations on all 12 data qubits (support $2^{12}$ per input) | 4131 | 84 | 22.8 | 5.12e6 | 2.56e6 | 1.5e-14 | 810 |

The plan's expectation "3000-gate 34-qubit circuit ≈ 1 to 5 s" holds for supports up to ~$2\cdot10^5$ entries; at the cap scale (2.6e6 stored entries) it is 23 s. Raw: `results/m0_step07_check5_timing.json`, `results/m0_step07_check5b_timing.json`.

## 4. Summary table

| check | expected | got | tol | result |
|---|---|---|---|---|
| unit 77 | pass | 77 pass | – | PASS |
| M0-E1, M0-E2 | pass | pass | 1e-12 | PASS |
| earlier M0 acceptance | pass | pass (23 incl. E1/E2) | – | PASS |
| lock / acceptance-check | pass | pass | – | PASS |
| (1) 36 random circuits vs Aer / Operator | ≤ 1e-12 | 3.2e-15 / 2.9e-15 | 1e-12 | PASS |
| (2) drop accounting | bias < budget | 1e-10 (N=10) to 4e-10 (N=40) constructed; 2e-11 per column generic | 1e-10 | **FAIL** |
| (3) cap / limit / measure-reset | as specified | as specified | – | PASS |
| (4) `encoded_block` semantics, direct leak | as specified | as specified | 1e-14 | PASS |
| (5) timing | 1 to 5 s plan estimate | 0.5 to 3.0 s (light), 22.8 s (cap-scale) | – | PASS |

Counts: passed 7 groups of checks plus unit 77 and acceptance 23; failed 1 (pruning accounting); pending 9 (all `NotImplementedError`); new failures vs report 006: 1.

## 5. Other observations (not counted as failures)
1. `mcx` with ≥ 3 controls (and `c4x`) through the transpile path returns a wrong operator whenever the circuit has an idle qubit (error 0.5 for 3 controls, 1.0 for 4; the transpiled circuit itself differs from `Operator` by the same amount, so it is Qiskit's use of idle qubits as clean ancillas, not a simulator bug). `mcp`, `c3sx`, `rccx`, `rc3x`, `cu`, `cswap`, `iswap` etc. are exact. The plan excludes native `mcx` from the gate set and the evaluator is meant to return `disallowed_gate`; `run_batch` itself silently accepts it. Guess: should be rejected in `_translate` (or decomposed with no ancilla use).
2. `aer_check.py` still a stub, listed in the plan row 0.7.
3. Cause guess for all of (2) is the absolute-threshold filter in `_coalesce`; the closed-form match (1e-13 relative) shows the drop behaves exactly as coded, there is no extra bug.

## 6. Files
- Raw numbers: `results/m0_step07_check1.json`, `results/m0_step07_check2_pruning.json`, `results/m0_step07_check2_product_bound.json`, `results/m0_step07_check5_timing.json`, `results/m0_step07_check5b_timing.json` (commit 06ea6bc + uncommitted step files, seeds 1000..1035 / 20261104 / 1 as stated).
- Scripts (gitignored): `scratch/chk1e.py`, `chk2.py`, `chk3.py`, `chk4.py`, `chk5.py`, `chk5b.py`.
- No source or acceptance files were modified; no tests added.

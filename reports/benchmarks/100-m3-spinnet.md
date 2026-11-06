# Benchmark report 100 - M3 spin-network encoding (mode benchmark, milestone gate M3, track S)

- Date: 2026-11-06. Commit: `9c0aee6` (branch `m3-spin-network`; tree clean apart from this benchmark's two new scripts and `results/benchmarks/spinnet-m3.json`).
- Prompt in force: `prompts/100-spinnet-m3-plan.md` (+ `prompts/101` erratum), plan row 3.8. Auditor: `reports/audits/100` (PASS WITH NOTES; N1/N2/N4 fixed in `d82a472`).
- Related: `reports/benchmarks/001-m0-baseline.md`, `reports/benchmarks/002-m1-twelve-qubit.md` (laptop), `reports/tests/106` (gate, mode full), `reports/audits/100`; desktop baseline `~/su2qc-sync/setup-log.md` section 1.8.
- Raw numbers (all repeats, provenance): `results/benchmarks/spinnet-m3.json`. Scripts: `results/benchmarks/scripts/bench_worker_m3.py` (one task per fresh process) and `bench_driver_m3.py` (driver).
- Machine: desktop, Intel i7-12700KF (20 logical CPUs), 31 GB, no GPU used. Python 3.12.16, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, qiskit-aer 0.17.2. `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `PYTHONHASHSEED=20261104`, every job under `taskset -c 0-9`. Peak RSS of every non-pytest job < 660 MB; pytest peak is the largest single process (see section 4), always < 10 GB.
- **Concurrency caveat:** the other track (rishon, `~/Projects/su2qc-rishon`, cores 10-19) was running its own jobs during these timings and a memory-guard / watchdog service also runs. I did not control it. Load average (1/5/15 min) read before each suite run: 1.1-4.9 / 1.4-3.7 / 1.8-2.9 on 20 CPUs, so my 10 cores were not oversubscribed, but shared caches / memory bandwidth / turbo state may differ from the 2026-11-05 baseline. Spread of the repeats (below) is small, so the numbers are reproducible within this session.
- Seeds: no stochastic call is timed (`ct_compile` seed 12345 is not used here; `m3_results.py` uses its own fixed seeds `20261104` / `12345`).
- Parameters: $\alpha=0.37$, $\beta=0.61$, $j_{\max}=1/2$ (433 physical states, 47 inner codes), spin-network register 8 data qubits ($+8$ outer, $+7$ ancilla for the $U_B$ skeleton). Synthesis $\varepsilon=10^{-6}$ per rotation, tolerances `synth_tolerances(n_rot, eps)`, engine `sparse`.
- Method: one task per fresh process; "first" = first call in the fresh process (cold: Qiskit lazy imports, caches), "later" = remaining calls (warm); median [min, max]; peak RSS = `ru_maxrss` of the process.

```
cd ~/Projects/su2qc-spinnet; source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=20261104
python results/benchmarks/scripts/bench_driver_m3.py <scratch>   # tasks x 3-5 processes, m3_results.py x 3, pytest unit x 3, pytest m0+m1+m3 x 3
# like-for-like with the desktop baseline (setup-log 1.8): old unit files only, and m0+m1 only, 3 runs each (wrapper in scratch)
taskset -c 0-9 python -m pytest -n 10 -q <16 unit files that exist at a2ec571, minus test_spinnet_unit.py>
taskset -c 0-9 python -m pytest -n 10 -q tests/acceptance/m0 tests/acceptance/m1
```

## 1. Encoding build (`SpinNet()`: decode tables, physical vectors, gauge)

5 fresh processes, 4 constructions each.

| quantity | cold (first call), s | warm (later calls), s | peak RSS, MB |
|---|---|---|---|
| `import su2plaq.encodings.spinnet` (qiskit-free side) | 0.1063 [0.1058, 0.1075] | - | - |
| `SpinNet()` | **0.1615 [0.161, 0.1624]** | **0.0501 [0.0472, 0.0509]** | 192 [192, 192] (whole process) |
| `enc.target("UB", None, 0.61)` (433 x 433) | 0.0179 [0.0178, 0.0184] | 0.00937 [0.00896, 0.00969] | - |
| `enc.inner_target("UB", None, 0.61)` | 1.38e-4 | 3.2e-5 | - |
| for comparison, `import su2plaq.evaluate.evaluator` | 0.0783 [0.0778, 0.0793] | - | - |

Whole-process outputs: 433 physical states, 47 inner codes, gauge residual $2.66\times10^{-15}$. (Cold = decode tables / physical basis built once; the 0.16 s is dominated by the physical basis, as `physical_basis()` was 0.30 s in report 001.)

## 2. `evaluate` per circuit (spin network, 23 qubits for the outer-register run, 15 otherwise)

Each row: 3 fresh processes, 4 `evaluate` calls per process (1 first + 3 later). `evaluate(..., engine="auto")` picked the sparse engine everywhere; `certified` True, 0 outer bits read, leak amplitude 0 (exact-angle circuits).

| circuit | method | first, s | later, s | peak RSS, MB | op-norm err | Gauss |
|---|---|---|---|---|---|---|
| `build_UB(0.61, with_outer=True)` (rccx 14, cx 12, x 16, rz 4, h 2; 23 qubits) | physical | **0.4996 [0.4966, 0.5092]** | **0.1665 [0.1655, 0.1683]** | 231.6 [231.6, 231.9] | $1.03\times10^{-14}$ | $5.4\times10^{-16}$ |
| `build_UB(0.61)` (15 qubits) | auto = inner_span | 0.5028 [0.4995, 0.5035] | 0.1673 [0.1664, 0.1692] | 233.1 [232.7, 233.1] | $1.08\times10^{-14}$ | $5.4\times10^{-16}$ |
| `build_UE(0.37)` | auto | 0.1500 [0.1499, 0.1552] | 0.1445 [0.1442, 0.1457] | 190.8 | $4.4\times10^{-16}$ | $5.3\times10^{-16}$ |
| `build_step(0.37, 0.61, 1)` | auto | 0.5011 [0.5010, 0.5012] | 0.1678 [0.1662, 0.1685] | 232.5 | $1.15\times10^{-14}$ | $5.5\times10^{-16}$ |
| `build_step(0.37, 0.61, 2)` | auto | 0.5020 [0.4977, 0.5077] | 0.1673 [0.1664, 0.1682] | 232.9 | $1.14\times10^{-14}$ | $5.5\times10^{-16}$ |
| Paulo's 15-qubit file, outer present, gauge-fixed target (`gauss=True`) | physical | 0.1689 [0.1685, 0.1692] | 0.1661 [0.1655, 0.1674] | 190.8 | $9.73\times10^{-15}$ | $5.4\times10^{-16}$ |
| spinnet_v2 `pairs9` | auto | 0.5021 [0.5017, 0.5047] | 0.1656 [0.1655, 0.1663] | 232.8 | $7.9\times10^{-15}$ | $5.4\times10^{-16}$ |
| spinnet_v2 `flags4` | auto | 0.5039 [0.4985, 0.5071] | 0.1657 [0.1638, 0.1685] | 232.9 | $9.2\times10^{-15}$ | $5.4\times10^{-16}$ |

Build times (warm): `build_UB(0.61, with_outer=True)` 1.24 ms (first call in the task, which includes the cached coupling table: 49 ms); `build_step` order 1/2: 1.29 ms / 1.32 ms (first 49 ms). Paulo file load 0.80 ms; gauge alignment (`encoded_block` + `align_inner_block`, 47 codes) 2.9 ms.

Observations: all circuits cost the same warm (0.166 s) - the evaluator's per-call set-up on the 433-state space dominates, not the circuit (as in 002). The 0.33 s "first" excess is lazy Qiskit set-up in the fresh process (it does not appear for `U_E` and Paulo, where the first call is short).

## 3. Synthesised verification, $\varepsilon=10^{-6}$ (sparse engine)

3 fresh processes: `synthesize` 3 calls, `evaluate(synth, engine="sparse", tol=synth_tolerances)` 3 calls.

| circuit | `synthesize` first / later, s | `evaluate` first / later, s | peak RSS, MB | $n_{\rm rot}$ / $t_{\rm rot}$ / gates | op-norm err vs bound $n_{\rm rot}\varepsilon+10^{-9}$ | Gauss |
|---|---|---|---|---|---|---|
| $U_B$ | 0.4237 [0.4229, 0.4296] / 0.0028 | 0.2111 / **0.2006 [0.1993, 0.2018]** | 233.5 | 4 / 254 / 808 | $1.30\times10^{-6}$ ($\le 4.0\times10^{-6}$) | $5.5\times10^{-16}$ |
| step order 1 | 0.4458 [0.4421, 0.4469] / 0.0042 | 0.2531 / **0.2349 [0.2339, 0.2374]** | 235.1 | 8 / 510 / 1476 | $2.38\times10^{-6}$ ($\le 8.0\times10^{-6}$) | $5.1\times10^{-7}$ |

Both certified, engine `sparse`, 0 outer bits read.

## 4. Scripts and suites

| quantity | runs (s) | median [min, max], s | peak RSS (largest process), MB | notes |
|---|---|---|---|---|
| `scripts/m3_results.py --out <scratch>` | 8.90, 8.93, 8.91 | **8.91 [8.90, 8.93]** | 291 | reproduces committed `results/spinnet/{UE,UB,step}.json` (section 6); tester 106 measured 11.24 s (other machine load) |
| `pytest -n 10 tests/unit` (295 passed) | 25.73, 25.88, 25.53 | **25.73 [25.53, 25.88]** | 6658 | RSS from `test_lean_project_unit.py` (Lean/`lake` process, 6.66 GB alone; laptop-owned test that exists at the branch point). Other unit files <= 0.7 GB |
| `pytest -n 10 tests/acceptance/m0 m1 m3` incl. slow: 79 passed, 1 failed (= `test_M3_L3_native_certificate_general_step`, pending laptop checker, as in 106) | 66.95, 67.88, 68.98 | **67.88 [66.95, 68.98]** | 6652 | RSS added by the m3 tests (m0+m1 alone: 1.95 GB); presumably the Lean-calling m3 tests, not isolated per test (guess) |
| `pytest -n 10 tests/acceptance/m0 m1` (56 passed), like-for-like | 64.80, 64.98, 63.48 | 64.80 [63.48, 64.98] | 1950 | baseline run |
| `pytest -n 10` on the 16 baseline unit files minus `test_spinnet_unit.py` (218 passed), like-for-like | 24.42, 22.47, 23.32 | 23.32 [22.47, 24.42] | 6819 | baseline run |

The Lean-process peak (6.6-6.8 GB) is below the 10 GB cap and the 12 GB memory-guard limit but is 3x the whole rest of the suite; it is unchanged by track S (the same unit test existed at `a2ec571`; I did not run a per-test RSS for the m3 acceptance tests).

## 5. Comparison with the laptop M1 benchmark (002) and the desktop baseline

### 5a. Same quantity, different machines and different encodings

The 12-qubit UB was re-run here on cores 0-9 with the identical call as in 002 (`evaluate(build_UB(0.61), TwelveQubit(), target("UB", None, 0.61))`, 3 processes x 4 calls):

| quantity | laptop (002; i7-8750H, `-n auto`) | desktop, this run | desktop speed-up | desktop peak RSS, MB |
|---|---|---|---|---|
| 12-qubit `evaluate(build_UB(0.61))`, first / later, s | 8.16 [8.05, 8.22] / 2.31 [2.28, 2.34] | **3.072 [3.069, 3.074] / 0.797 [0.795, 0.801]** | 2.66x / 2.90x | 653 (laptop 655) |
| spin-network `evaluate(build_UB(0.61))`, first / later, s | - | **0.503 / 0.167** | - | 233 |
| spin-network $U_B$ with outer register, `physical`, first / later, s | - | 0.500 / 0.167 | - | 232 |
| 12-qubit synth $U_B$ ($\varepsilon=10^{-6}$; 6 rot, 1838 gates), evaluate later, s | 3.56 [3.53, 3.60] | not re-run | - | - |
| spin-network synth $U_B$ ($\varepsilon=10^{-6}$; 4 rot, 808 gates), evaluate later, s | - | 0.2006 | - | 233 |

Same-machine ratio, 12-qubit / spin-network $U_B$ `evaluate`: 3.072 / 0.503 = **6.1x** (first call), 0.797 / 0.167 = **4.8x** (later), and 3.5x lower peak RSS (653 / 233 MB). Cross-machine (laptop 12-qubit vs desktop spin-network): 16x / 13.8x; mixing machines, so only the same-machine figure is a clean comparison. The speed-up is expected from the encoding: 8 data qubits and 47 inner codes (vs 12 qubits, 625 inner codes) make the evaluator's inner-span set-up smaller; it is a property of the encoding, not a code regression.

### 5b. Versus the desktop baseline (`~/su2qc-sync/setup-log.md` 1.8; only test-suite times exist there)

The baseline has no per-call timings; the only shared quantities are the two suites. Like-for-like reruns:

| quantity | desktop baseline (2026-11-05, `a2ec571`) | now (`9c0aee6`) | change | flag (>10 %) |
|---|---|---|---|---|
| m0 + m1 acceptance incl. slow, 56 tests, wall, s | 62.8 (spinnet clone, concurrent with the rishon unit run) | 64.80 [63.48, 64.98] | +3.2 % | no |
| unit, baseline files only (218 vs 216 tests), wall, s | 30.9 (concurrent with the rishon unit run) | 23.32 [22.47, 24.42] | -24.5 % (not like-for-like: the baseline was run while the other track was busy, +2 tests) | no |
| unit, all files (295 tests), wall, s | - (216 tests: 30.9) | 25.73 [25.53, 25.88] | 79 more tests, still faster than the baseline | no |
| m0 + m1 + m3 acceptance incl. slow (80 tests), wall, s | - | 67.88 [66.95, 68.98] | m3 adds about 3 s on top of m0 + m1 | - |

No shared quantity is more than 10 % slower than a baseline. The M0/M1 per-call quantities (route-A build, `physical_basis`, 12-qubit `evaluate`) are not touched by track S (`git diff --name-status a2ec571 HEAD` shows only additions plus `lean/Su2Plaq.lean`, `notes/STATUS.md`, `tests/acceptance/LOCK.json`, per reports/tests/106); the 12-qubit $U_B$ `evaluate` above is the one that I re-measured and it matches the laptop ratio plausibly (2.7-2.9x for a 12th-gen vs 8th-gen core).

## 6. Physics output unchanged

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| $U_B(0.61)$ logical counts (`logical_metrics`) | 54 CX / 4 rot / 56 $T_{\rm fixed}$ / 7 anc / depth 67 | 54 / 4 / 56 / 7 / 67 (also with outer register: 54 / 4 / 56, 23 qubits) | exact | PASS |
| step order 1 / order 2 counts | 54 CX, 8 / 12 rot | 54, 8 / 12 | exact | PASS |
| $U_E$ counts | 0 CX / 4 rot / depth 1 | 0 / 4 / 1 | exact | PASS |
| $U_B$ op-norm error (exact angle), committed `UB.json` | $1.08\times10^{-14}$ | $1.0846\times10^{-14}$ (fresh run $1.0846\times10^{-14}$, with outer / physical $1.03\times10^{-14}$) | $10^{-10}$ | PASS |
| $T$ at $\varepsilon=10^{-6}$ (pygridsynth) | $t_{\rm fixed}=56$, $t_{\rm rot}=254$, total 310 | 56, 254, 310 | exact | PASS |
| synthesised $U_B$ at $10^{-6}$ | err $\le 4.0\times10^{-6}$ | $1.30\times10^{-6}$ | $n_{\rm rot}\varepsilon+10^{-9}$ | PASS |
| `m3_results.py` rerun vs committed `results/spinnet/{UE,UB,step}.json` | identical numbers | all numeric fields identical (programmatic dict comparison excluding seconds / provenance / paths) for $U_E$, $U_B$, step | exact | PASS |
| Paulo 15-qubit file, gauge-fixed | error $9.7\times10^{-15}$, leak 0 | $9.73\times10^{-15}$, leak 0 | $10^{-10}$ | PASS |
| m0 + m1 + m3 acceptance | 79 pass + L3 pending | 79 passed, 1 failed (L3 pending: Su2PlaqCert checker not delivered), all 3 runs | - | PASS (as in 106) |

## Verdict

**No regression; physics unchanged.** Flags: none above the 10 % threshold. Notes for the record (not flags): (i) timings were taken while the other track ran on cores 10-19; (ii) the 6.6-6.8 GB suite peak RSS is the Lean process of `test_lean_project_unit.py` / the m3 Lean tests, within the 10 GB cap; (iii) no earlier spin-network benchmark exists, so these numbers are the new baseline for track S (`results/benchmarks/spinnet-m3.json`).

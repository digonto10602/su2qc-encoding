# Tester report 104 — M3 step 3.7: `scripts/m3_results.py` and `results/spinnet/{UE,UB,step}.json`

- Date: 2026-11-06
- Git commit under test: `ae2349b` (results regenerated on clean `0d75ba0`, recorded in the JSON provenance as `git_commit 0d75ba0`, `git_dirty False`)
- Prompt in force: `prompts/100-spinnet-m3-plan.md` (§3 row 3.7)
- Related reports: `reports/tests/100`, `101`, `102`, `103`
- Mode: step. Track S, branch `m3-spin-network`. Lean files (`lean/`, `lean_export.py`, L1–L3) ignored as instructed.

## Verdict: PASS

All checks pass. There are no new failures. L1/L2/L3 are PENDING (Lean builder, out of scope).

## Commands run (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, `taskset -c 0-9`)
```
pytest -n 10 tests/acceptance/m3                        -> 21 passed, 3 failed (= the 3 Lean ids, all "PENDING: ... missing / not delivered")
pytest -n 10 tests/acceptance/m3/test_spinnet_results.py -v -> R1[UE], R1[UB], R1[step] PASSED
pytest --collect-only -q tests/acceptance               -> 126 tests collected, clean
pytest -n 10 tests/unit                                 -> 279 passed (26.6 s)
pytest -n 10 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -> 54 passed (91.8 s)
python tools/check_lock.py                              -> LOCK OK
~/.claude/bin/acceptance-check                          -> PASS: tests/acceptance matches acceptance-v7
PYTHONPATH=src taskset -c 0-9 /usr/bin/time -v python scripts/m3_results.py --out <scratchpad>/rerun   (reproducibility, does not touch the tree)
python results/spinnet/tester/m3_step_3_7_repro.py <scratchpad>/rerun        (diff of rerun vs committed)
PYTHONPATH=src taskset -c 0-9 python results/spinnet/tester/m3_step_3_7_verify.py   (independent recomputation, 133 checks)
```
The flaky laptop unit test (short hash containing "c1") did not trigger at `ae2349b`: 279/279.

## 1. Test suites
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `test_M3_R1_results_files[UE]`, `[UB]`, `[step]` | pass | 3 passed | - | PASS |
| other non-Lean m3 ids (21 total pass incl. R1) | pass | 21 passed | - | PASS |
| collection | 126 clean | 126 | - | PASS |
| unit | green | 279/279 | - | PASS |
| m0+m1 `-m "not slow"` | green | 54/54 | - | PASS |
| check_lock, acceptance-check | pass | LOCK OK, matches acceptance-v7 | - | PASS |
| PENDING (not failures, step mode) | - | `test_M3_L1`, `L2` (files missing), `L3` (checker not delivered) | - | PENDING 3 |

## 2. Reproducibility
`m3_results.py` supports `--out`, so the repo tree was not modified. A rerun at `ae2349b` wrote to a scratchpad directory (wall 11.7 s with the shell wrapper, peak RSS 296 MB, `time -v` max RSS 295 924 kB; committed run recorded 8.6 s / 292 MB).
`results/spinnet/tester/m3_step_3_7_repro.py` compares all three JSONs field by field (excluding only `seconds`, `wall_seconds`, `peak_rss_mb`, `timestamp_utc`, `provenance_captured_at`, `command`, `host`) and compares every `.qasm3`/`.qpy` byte for byte.

| check | expected | got | result |
|---|---|---|---|
| JSON fields differing (floats compared exactly, bitwise) | only `git_commit` (0d75ba0 vs HEAD ae2349b) and the output-directory strings in `files.*` | exactly those: 3 `git_commit` + 20 `files` path strings = 23, nothing numeric | PASS |
| 9 `.qasm3` files | identical bytes | 9/9 identical | PASS |
| 9 `.qpy` files | identical bytes | 9/9 identical (also identical gate lists) | PASS |
| `sha256` fields in JSON | equal | equal (no diff reported) | PASS |

So every number in the committed results is reproduced bit-for-bit. Raw output: `results/spinnet/tester/m3_step_3_7_repro.log`.

## 3. Independent recomputation (133 checks, 133 PASS; script `results/spinnet/tester/m3_step_3_7_verify.py`, raw `m3_step_3_7.json`/`.log`)
Method: my own Aer statevector runs on the **committed `.qpy` circuits** (47 inner-code runs → $433\times433$ matrix; outer register is a spectator, shown in report 102), my own numpy targets ($e^{-i\beta H_B}$ with `enc.h_magnetic`, $U_E$ from route-A labels $\sum j(j+1)$), my own lowering (`transpile` opt 0) + `count_ops`, my own `pygridsynth.gridsynth_gates` calls (no project cache), my own `generate_preset_clifford_t_pass_manager` call (seed 12345, level 3).

Verdict errors, $\|W-e^{i\phi}V\|_2$ (JSON value vs mine; both far below the 1e-10 tolerance; the JSON number is from the sparse engine on the physical method, mine from Aer, so they need not be equal):

| circuit | JSON | mine (Aer) | tolerance | result |
|---|---|---|---|---|
| UE ($\alpha=0.37$) | 4.4e-16 | 1.6e-16 | 5e-14 | PASS |
| UB ($\beta=0.61$) | 1.02e-14 | 3.8e-15 | 5e-14 | PASS |
| step order 1 | 1.16e-14 | 3.7e-15 | 5e-14 | PASS |
| step order 2 | 1.16e-14 | 4.0e-15 | 5e-14 | PASS |
| UB at $\beta=0.05$ | 8.6e-15 | 3.1e-15 | 5e-14 | PASS |
| pairs9 / flags4 | 8.2e-15 / 8.1e-15 | 1.7e-15 / 3.3e-15 | 5e-14 | PASS |
| Paulo 15q vs $DVD$ (recorded 8 minus codes) | 9.7e-15 | 3.4e-15 | 5e-14 | PASS |
| Paulo 15q vs ungauged target | 0.199667 | 0.1996668 ($=2\sin 0.1$ exactly) | 1e-9 | PASS (rejected as designed) |

Leak, dirty ancilla and $\|W^\dagger W-1\|$ all $<10^{-12}$ for every circuit.

Logical counts from the `.qpy` files (my lowering vs JSON; exact equality):

| circuit | CX | rot | T_fixed | depth | qubits | ancilla | result |
|---|---|---|---|---|---|---|---|
| UE | 0 | 4 | 0 | 1 | 8 | 0 | PASS |
| UB (0.61 and 0.05) | 54 | 4 | 56 | 67 | 15 | 7 | PASS |
| step order 1 | 54 | 8 | 56 | 67 | 15 | 7 | PASS |
| step order 2 | 54 | 12 | 56 | 67 | 15 | 7 | PASS |
| UE outer electric row | 0 | 12 | 0 | 1 | 16 | 0 | PASS |
| paulo15 | 68 | 4 | 64 | 90 | 15 | 7 | PASS |
| pairs9 | 34 | 9 | 24 | 38 | 11 | 3 | PASS |
| flags4 | 44 | 4 | 48 | 60 | 11 | 3 | PASS |

$T$ totals, $T_{\rm total}=T_{\rm fixed}+\sum_{\rm rot}T_{\rm gridsynth}(\epsilon)$, my own pygridsynth calls, exact equality:

| quantity | $\epsilon$ | expected (JSON / brief) | got | result |
|---|---|---|---|---|
| UB | 1e-4 / 1e-6 / 1e-8 / 1e-10 | 230 / 310 / 396 / 468 | same | PASS |
| UE | 1e-4 / 1e-6 / 1e-8 / 1e-10 | 176 / 256 / 328 / 416 | same | PASS |
| step order 1 | same grid | 406 / 566 / 724 / 884 | same | PASS |
| step order 2 | same grid | 566 / 838 / 1068 / 1300 | same | PASS |
| outer electric row (12 rot) | same grid | 528 / **768** / 984 / 1248 | same | PASS |
| paulo15 ($\beta=0.05$) | 1e-6 | 316 | 316 | PASS |
| pairs9 | 1e-6 | 576 | 576 | PASS |
| flags4 | 1e-6 | 298 | 298 | PASS |
| ours $\beta=0.61$ / $\beta=0.05$ | 1e-6 | 310 / 304 | 310 / 304 | PASS |
| outer row synthesised rows marked `evaluable: False` (`writes_outer`) | all 4 | True | True | PASS |

Qiskit Clifford+T (seed 12345, level 3, $\epsilon=10^{-6}$), (T, CX, depth): paulo15 (316, 68, 733), ours 0.61 (308, 54, 682), ours 0.05 (293, 54, 657), pairs9 (570, 34, 1413), flags4 (290, 44, 741). All identical to the JSON. PASS.

Physics block: 433 physical states; 47 inner codes; 16 bright / 31 dark; 8 pairs with couplings $\{-2,-\tfrac12,+1\times6\}$ (extracted from $V=e^{-i\beta K}$ at $\beta=0.3$, independent of the stored table); $H_B$ spectrum multiplicities $16/96/16/177/16/96/16$ (eigenvalues $-2,-1,-\tfrac12,0,\tfrac12,1,2$ in that order of sorted keys); 64 gauge minus signs; 128 outer patterns, dims $\{2{:}41,3{:}52,4{:}8,5{:}22,9{:}4,17{:}1\}$ (range 2–17); the JSON histogram equals mine. All PASS.

One initial FAIL in my own script (`UE_outer_row` ancilla = 8): my script counted the 8 outer-register qubits as ancillas; the JSON value 0 is correct (16 qubits = 8 inner + 8 outer). Script fixed, rerun: 133/133 PASS. Not a code defect.

## 4. Traceability
JSON provenance holds commit `0d75ba0`, `git_dirty False`, library versions (qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.2, scipy 1.18.0), platform, host, seeds `{transpiler_logical: 20261104, clifford_t_pass_manager: 12345, trial_subset: 0}`, `quick False`, wall time, peak RSS, and the file sha256. Satisfied. Minor notes (not blocking):
1. `provenance.command` is `python scripts/m3_results.py` (without `PYTHONPATH=src taskset -c 0-9`); the full rerun command is in the task brief and this report.
2. `comparison.paulo15.source` is an absolute path (`/home/digonto/Projects/su2qc-spinnet/refs/paulo/spin_network_plaquette3.gates.txt`), not repository-relative; it also contains a username. The `sha256` field alongside identifies the file.
3. `git_dirty` only considers tracked changes (`--untracked-files=no`): a concurrent Lean edit to a tracked file would flip it to True on a rerun in this tree. At the time of my rerun it was False.

## Failures
None.

Files: `results/spinnet/tester/m3_step_3_7_verify.py`, `m3_step_3_7.json`, `m3_step_3_7.log`, `m3_step_3_7_repro.py`, `m3_step_3_7_repro.log` (untracked, for the coordinator to commit).

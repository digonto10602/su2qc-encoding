# Tester report 027 — M2 step 2.3: compress evaluator, run_candidate, metrics, synth cache, `states=`

- Date: 2026-11-05
- Commit: f5ff810 (working tree with the uncommitted step-2.3 changes; HEAD does not contain them)
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (+ addenda 003–006), acceptance-v6
- Mode: step
- Related: reports/tests/026 (step 2.2 builder), 024 (spec/oracle), 021–023 (M1 evaluator)
- Raw numbers: `results/tester_m2_step2_3_evaluate.json`; scripts: `tests/independent/evaluate_2_3/` (they hard-code the tester scratchpad path; not collected by pytest).

## VERDICT: FAIL (physics and acceptance targets all green; FAIL because three explicitly requested adversarial requirements are not met: file I/O is not blocked (N1), a program edited during evaluation is recorded under the old SHA (N2), corrupt synth-cache entries are silently trusted (N4))

Counts: m2 acceptance 13 passed / 33 not passed (32 PENDING `NotImplementedError`, 1 Lean-track missing file) / 0 genuine failures; m0+m1 56/56 incl. slow; unit 226 passed (Lean unit file excluded); collect 102 clean; check_lock OK; acceptance-check PASS (acceptance-v6).

## Commands run
```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
pytest -n auto tests/acceptance/m2 -q -rp --tb=line
pytest -n 6 tests/acceptance/m0 tests/acceptance/m1 -q                      # incl. slow, 331 s
pytest -n 6 tests/unit --ignore=tests/unit/test_lean_project_unit.py -q     # 73 s
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
graphify update . ; graphify affected "evaluate"
python tests/independent/evaluate_2_3/{cases,extra,run_cases,states_test,synth_cache,toctou,dos2,unverified3,evil}.py
python -m su2plaq.compress.run_candidate <step_program.py> --encoding twelve --kind step --trial|--full
```

## 1. Required test ids

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| `test_evaluator_rejects_partial` | PASS | PASS | PASS |
| `test_t_eps_in_ross_selinger_band[1e-4, 1e-6, 1e-8]` | PASS x3 | PASS x3 | PASS |
| `test_t_eps_deterministic` | PASS | PASS | PASS |
| `test_cache_keyed_by_code_hash` | PASS | PASS | PASS |
| other m2 ids already green: oracle, builder_gateset, macro_costs, mcx_chain, + Lean: project_present, generic_theorems, counts_kernel_checked | PASS | PASS (13 total) | PASS |

Other m2 non-passes, classified by message (not failures of this step):
- 17 x `PENDING: general_circuit is not built yet` (accepts_general_circuit, accepts_global_phase, rejects_wrong_gate, rejects_dirty_ancilla, rejects_small_ancilla_leak, rejects_angle_error, rejects_control_change, metrics_match_qiskit_count_ops, t_estimate_formula, round_dry_run, run_candidate_cli_trial_and_full, report_table, archive_best, entry_has_provenance, skeleton_angle_independent, polish, + 1 Lean) — wait for step 2.5.
- 4 x `Archive.load is not built yet` (step 2.4), 3 x `import_seed`, 2 x `general_program_path`, 1 x `qiskit_l3`.
- Lean track: `lean.certify.*` / `lean.structure.*` not built (5), and `test_lean_theorem_file_general`: `AssertionError` at test_lean_formal.py:196, `lean/certs/twelve-general-step.lean` does not exist yet (Lean builder's file, ignore).
- Independent check of the "metrics" test content on the real step circuit (not the locked test): level-0 Qiskit `count_ops` CX 294 = metrics 294; T+Tdg 312 = t_fixed; N_rot 10 = independent count 10; depth 292 = 292; qubits 50 = `qc.num_qubits`; measured $T_\varepsilon(10^{-6})=952$ = `t_table` total 952; estimate mode $312+3\cdot10\cdot\log_2 10^6 = 909.947$ = metrics value.

## 2. Regression

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| m0 + m1 acceptance incl. slow (evaluator.py changed) | 56 pass | 56 passed (331 s) | PASS |
| unit (Lean file excluded) | all pass | 226 passed | PASS |
| `pytest --collect-only tests/acceptance` | clean | 102 collected | PASS |
| `tools/check_lock.py` / `acceptance-check` | OK | LOCK OK / matches acceptance-v6 | PASS |

## 3. Adversarial proposer programs (kind `UE`, 28 qubits; each run in `trial` and `full`; run via `evaluate_program`)

| attack | expected reason | got (trial / full) | PASS/FAIL |
|---|---|---|---|
| good UE program (control) | valid | valid / valid; err 2.4e-15 / 1.2e-13 | PASS |
| wrong on 16 physical states, all outside the trial subset (mcz on a 5-qubit pattern) | full: error | **trial VALID** (misses, by design) / full `error`, op-norm 1.0, Gauss 1.0 | PASS (trial is advisory) |
| dirty ancilla (cx data -> ancilla, no uncompute) | dirty_ancilla | dirty_ancilla / dirty_ancilla (leak 1.0) | PASS |
| leak $10^{-9}$ amplitude (ancilla $R_x(2\cdot10^{-9})$) | reject (tol $10^{-10}$) | dirty_ancilla / dirty_ancilla; leak 1.0000e-9 | PASS |
| leak $10^{-11}$ (below tolerance) | valid | valid / valid; err 1.0e-11 | PASS |
| angle-specialised skeleton (`rz` instead of `p` at alpha>0.5) | skeleton | valid (nominal) / `skeleton` | PASS |
| hard-coded nominal angle 0.37 | alt_angles | valid / `alt_angles:error` | PASS |
| disguised: `Gate("h")` with rz definition; unitary named x; `ry` pair; `sx sxdg`; native mcx x2; custom gate named cx hiding T gates; custom identity gate named h/z; id gate; measure+clbit; unitary identity named x | not valid | `error`/`disallowed_gate` (class identity, names ignored); `disguised_unitary_named_x` -> leak (X acts) | PASS |
| mutated-name standard gates (`HGate().to_mutable()` named z; CZ named cx; CX named cz) | judged by class | H,H named z valid (identity); CZ named cx + CZ valid (identity); CX named cz + CZ -> `error` (class based) | PASS |
| writes outer qubit | writes_outer | writes_outer / writes_outer | PASS |
| qubits: direct `QuantumCircuit` with 228 q; `alloc(100)`; `_n_anc=500`+`peak_qubits=0`; 40 allocs + `peak_qubits=1` | max_qubits | max_qubits (228 / 128 / 528 / 68 > cap 60), `qc.num_qubits` used | PASS |
| `_ops.append(("ry",...))` / `("mcx",...)` / qubit 300; `__class__` swap; `BASIS` monkey-patch in worker | rejected | leak / build_error / build_error; contract (type is not Builder); leak (parent tables unpatched) | PASS |
| `b.circuit = lambda: qc` override (circuit returned by proposer) | parent re-checks | re-checked in parent (rows above) | PASS |
| forbidden imports os, subprocess, sys, socket, importlib, pickle, pathlib, io, shutil, ctypes, builtins, scipy, qiskit_aer, `su2plaq.evaluate`, `su2plaq.compress.evaluate`, `from su2plaq import circuits`; `open`, `exec`, `eval`, `compile`, `__import__` | contract | contract (message names the import) for all | PASS |
| infinite loop in `build` (BUILD_TIMEOUT_S patched to 8 s) | build_timeout | build_timeout (8 s) | PASS |
| 26 Hadamard ancillas + cp (support blow-up), budget 30 s | bounded time | trial `unsimulable` 8.4 s; full aer_mps -> `dirty_ancilla` 23.4 s | PASS |
| 120 000-gate circuit (trial, budget 20 s) | bounded | valid in 6.7 s | PASS |
| parent executes proposer code? (audit hook on `import`/`open` in the parent; a `Gate` subclass whose `__init__` counts constructions) | no | no proposer import events; `sys.modules` has no `su2plaq_program_*`; Evil gate constructed once (worker), parent loaded it as a generic gate -> `disallowed_gate` | PASS |
| **static scan stops file I/O** | file I/O rejected | **BYPASSED**: `np.save(...)`, `Builder.__init__.__globals__["__builtins__"]["open"]`, `BB.pathlib.Path(...).write_text` and `import numpy.lib.npyio` all pass the scan; the programs ran in the worker and were VALID; 3 marker files were written | FAIL (see note N1) |
| change of the program file during evaluation | recorded sha = evaluated source | **sha recorded = SHA of the old content (A) while the worker built and evaluated the new content (B)** | FAIL (see note N2) |

## 4. `states=` subset (independent dense reference)

Circuit: $U_E(0.37)$ plus random diagonal perturbations (5 `p` and 4 `cp` gates, seed 20261105), target = oracle $V$; reference $A=\Psi^\dagger D\Psi$ computed in numpy from the 433 encoded vectors, block error $\|A_S-e^{i\varphi_S}V_S\|_2$ with $\varphi_S=\arg \mathrm{tr}(V_S^\dagger A_S)$.

| subset | $n$ | reference | evaluator `block_error` | $|\Delta|$ |
|---|---|---|---|---|
| full (method physical) | 433 | 0.0123812 | 0.0123812 | 2.1e-17 |
| `states=arange(433)` | 433 | same | same | 2.1e-17 |
| first 5 | 5 | 1.7816e-3 | 1.7816e-3 | 1.3e-16 |
| random 64 (seed 0) | 64 | 1.2249e-2 | 1.2249e-2 | 2.4e-16 |
| random 10 (seed 7) | 10 | 8.0037e-3 | 8.0037e-3 | 1.5e-16 |
| single {200}, {432} | 1 | 4.50e-6, 8.38e-6 | same | 3.4e-16, 5.1e-16 |
| duplicates/unsorted [300,5,5,99] | 3 (unique) | 9.4648e-3 | same | 3.8e-16 |

Max deviation 5.1e-16 (tolerance: 1e-12 stated by me; PASS). Rejections: `[]`, `[-1]`, `[433]`, `method="inner_span"`+`states` raise `ValueError`; `[0.5]` is silently truncated to index 0 (note N3, harmless). `--full` always passes `states=None` (code path `mode=="trial"` only), and the 16-state cheat above is caught in full (op-norm 1.0): a subset cannot make a wrong circuit valid in `--full`. PASS.

## 5. `unverified` mapping (step circuit, `support_cap=2000`, forces aer_mps)

| spec tolerance | engine | ok | certified | err | result | expected | PASS/FAIL |
|---|---|---|---|---|---|---|---|
| default $10^{-10}$ | aer_mps | False | False | 6.78e-10 | invalid `leak` (aer_mps bound exceeds tolerance) | invalid | PASS |
| $8\cdot10^{-10}$ (between 6.8e-10 and 1e-9) | aer_mps | True | False | 6.78e-10 | invalid `unverified` | `unverified` | PASS |
| $10^{-9}$ | aer_mps | True | True | 6.78e-10 | valid | valid (certified) | PASS |
| `support_cap=1500` on UE (no cap hit) | sparse | True | True | 1.2e-13 | valid | valid | PASS |

Note: with the default spec an aer_mps-only exact-angle candidate is rejected as `leak` (bound 6.8e-10 > 1e-10), not `unverified`; `unverified` appears only for tolerances in $[6.8\cdot10^{-10},10^{-9})$. Both are non-valid, as required.

## 6. Synth cache (`compress/synth.py`)

| check | expected | got | PASS/FAIL |
|---|---|---|---|
| file name = sha256("version\|repr(θ)\|repr(ε)") | yes | yes (pygridsynth 1.2.0) | PASS |
| next-after θ and ε·(1+1e-7) are new entries | +2 files | 3 files total | PASS |
| other pygridsynth version -> new entry | +1 file | 4 files | PASS |
| corrupt entry detected or recomputed | recomputed / error | **trusted**: garbage `HTHT...` returns T=14 instead of 64; empty file returns `''`; text `not a word ###` returned; a valid word of another angle returned (word error vs θ = 0.398) | FAIL (N4) |

## 7. Timing, realistic size (`build_step(0.37,0.61)` wrapped as program: 237 gates, 50 qubits, 10 rotations, CX 294, T_fixed 312; angles fitted as $c_\alpha\alpha+c_\beta\beta$ and checked at the third pair to 1e-12)

| command | wall (end-to-end) | budget | result |
|---|---|---|---|
| `run_candidate --trial` x 11 | 4.9–5.8 s typical (internal 5.3–5.4 s); one outlier 8.3 s under load average 4.7 | < 10 s | valid; op-norm 1.6e-13 (pruning 1.5e-13), Gauss 3.9e-15, engine sparse, T_eps 909.95 (estimate) |
| `run_candidate --full` x 4 | 17.7–20.5 s | none stated | valid; err 2.69e-13 / 2.69e-13 / 2.67e-13 at 3 angle pairs, skeleton equal, T_eps 952, depth_CT 1421 |

PASS (trial margin ~2x typical, thin under load).

## Notes / defects (labels are my best guess)

- **N1 (security, moderate)**: the AST scan is a name filter, not a sandbox: file writes through numpy, through `Builder.__init__.__globals__["__builtins__"]`, or through modules imported by the allowed `builder` module (`BB.pathlib`) succeed in the worker. `evaluate.py` calls it a "safety net (not a sandbox)", so this matches the stated design, but the instruction "file I/O rejected" holds only for the literal `open`. Guess at cause: allowlist is on top-level module names only. Suggest: run the worker with `RLIMIT`/a read-only filesystem namespace, or state the limit in `proposer.md`.
- **N2 (correctness of provenance, low-moderate)**: `evaluate_program` hashes bytes read at time $t_0$ but the worker re-reads the path later; an edit in between yields a result recorded under the wrong SHA (reproduced by swapping the file inside `_build_in_subprocess`). Guess: TOCTOU. Suggest: write the bytes to a temp file in the build tempdir and run the worker on that copy.
- **N3 (trivial)**: `states=[0.5]` is accepted (cast to 0).
- **N4 (integrity, low-moderate)**: `gridsynth_word` reads the cache without validation, so a truncated/overwritten file silently changes the T-count (and the cost key). Guess: no integrity check by design. Suggest: store a checksum or re-verify `word_error(word, θ) ≤ ε` and the alphabet on read, or recompute on mismatch.
- **N5**: the task text promises the synthesised circuit is "re-verified separately with $N_{\rm rot}\varepsilon$+slack tolerances"; `evaluate_circuit` does not do this in step 2.3 (only exact-angle verification plus measured T). Confirm that this is planned for a later step (2.5/2.6) or drop the sentence.
- Trial mode is advisory: a program that is wrong on states outside the 64-state subset passes `--trial` (seeded subset, the seed is readable from `spec.trial_seed`). The loop must use `--full` for validity.
- Lean-track failures ignored as instructed.

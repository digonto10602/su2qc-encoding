# Tester report 026 — M2 step 2.2 (compress Builder, N3 spec fix)

- Date: 2026-11-05 · Commit: `cdc6551` + uncommitted working tree (builder.py, spec.py, regenerated specs/twelve-step.md, test_compress_builder_unit.py)
- Plan in force: `prompts/002` §5 row 2.2 (+ addenda 003–006); acceptance-v6 · Mode: step
- Related: reports/tests/024 (step 2.1), 025 (Lean skeleton, parallel track — ignored here)
- Raw numbers: `results/tester_m2_step22_builder.json` (189 adversarial checks, seed 20261105 for the random-circuit check); script `scratch/tester_adv_builder_m2_step22.py`

## VERDICT: PASS

## Commands
```
pytest -n auto tests/acceptance/m2/test_compress_machinery.py -q -rf       # 4 passed, 28 failed (all PENDING, see below)
pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q    # 54 passed, 168 s
pytest -n auto tests/unit -q ; pytest tests/unit/test_compress_builder_unit.py -q
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python -W ignore scratch/tester_adv_builder_m2_step22.py                   # adversarial, 189 checks
graphify update . ; graphify query/affected "Builder"                      # affected: only builder unit tests + sparse_sim forged-class test
```

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `test_builder_gateset` | pass | pass | — | PASS |
| `test_macro_costs_match_lowering` | pass | pass | exact ints | PASS |
| `test_builder_mcx_chain` | pass | pass | 1e-12 | PASS |
| `test_oracle_matches_exact_step` (2.1, regression) | pass | pass | — | PASS |
| other m2 `test_compress_machinery` (28) | PENDING (`NotImplementedError`) | 28/28 are `NotImplementedError: <fn> is not built yet` (general_circuit 14+, gridsynth_T 4, Archive.load 3, import_seed 3, evaluate_circuit 1, code_hash 1, qiskit_l3 1); no other exception type | — | PENDING (expected) |
| m0 + m1 non-slow | green | 54 passed | — | PASS |
| unit (all) | green | 215 passed, 1 failed (Lean, see below); builder unit file 12/12 | — | PASS (Builder), Lean separately |
| `pytest --collect-only tests/acceptance` | clean | 102 collected | — | PASS |
| `check_lock.py`, `acceptance-check` | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v6` | — | PASS |

### Adversarial (own script, 189 checks, 0 failures)

| group | what was tried | result |
|---|---|---|
| disallowed native gates via `append_qiskit` | MCX(3,4), MCXGrayCode, MCXRecursive, MCXVChain, C3X, C4X, RC3X, MCPhase, sx, sxdg, y, u/u1/u2/u3, rx, ry, id, cy, cs, csdg, cu, cu1, cry, rzz, rxx, iswap, cswap, ecr, dcx, r, XXPlusYY, Diagonal, Permutation, QFT, LinearFunction, And/Or, UnitaryGate (identity and X), Pauli, `x.control(3)`, `rz.control(2)`, `h.control(2)`, `s.control(1)`, controlled gates with `ctrl_state` (cx, ccx, cz, ch, crz, cp, crx), controlled swap | all `BuilderError`, nothing appended |
| disguised custom gates | `to_gate()` named `cx`/`h`/`ccx` (hiding mcx3)/`rz` (hiding sx); subclass of CXGate; custom Gate named `x` defined via sx; class-name+module spoof of CXGate; SXGate renamed `x`; RXGate renamed `rz`; CXGate renamed `ccx`; XGate with a param; RZGate with nan / inf / Parameter | all rejected; atomic (no partial append) |
| mutated-but-genuine class | HGate with emptied `.definition` | accepted and re-emitted as a plain `h` (definition ignored — correct) |
| non-gate ops | measure, reset, delay, `if_test`, mixed (sx then x), out-of-range qubit after valid gate | rejected; all-or-nothing rollback verified |
| barrier spoof (`Instruction` named Barrier with module `qiskit.*`) | silently dropped (contributes no gate; harmless) | note only |
| qubit maps | duplicate, negative, unallocated ancilla, float, bool, short list | all `BuilderError`; numpy ints accepted |
| ancilla lifecycle | gate/cx/mcx on freed ancilla, double free, free of data qubit, unallocated 40, negative, bool, float, str, repeated qubits, nan/complex/str/bool angle, alloc(0/−1/1.5), unknown register | all `BuilderError`, no state change |
| aliasing | ancilla indices always ≥ 28 and distinct; freed indices reused lowest first ([29,31,33] after freeing 29,31) | PASS |
| peak tricks | 50 alloc3/free cycles → peak 31 = circuit width 31; alloc2/free/alloc5 → 33; allocated-but-unused ancillas still counted (32); writing `b.peak_qubits = 0` does not change circuit width (32) | PASS |
| every gate method on every ordered qubit tuple (19 gates, 3 qubits) vs the Qiskit gate | max element diff ≤ 1e-14 | PASS |
| `append_qiskit` round trip of all 19 allowed gates + qubit_map offset | op list and qubits identical | PASS |
| macro costs of Builder output via `logical_metrics` vs METHODS §7 | ccx (6,7,0) rccx (3,4,0) ccz (6,7,0) swap (3,0,0) ch (1,2,0) crz (2,0,2) crx (2,0,2) cp (2,0,3) cz (1,0,0); t/tdg/rz(π/4) = 1 T; rz(0.3), p(0.3) = 1 rotation | all equal; `MACRO_COST == METHODS` dict |
| 200 random Builder circuits (seed 20261105, ≤ 25 gates, 2 ancillas) | `logical_metrics` (cx, T_fixed, n_rot) = sum of table costs | 0 mismatches |

### `mcx` chain vs dense `Operator` ($U$ restricted to ancillas $=|0\rangle$ vs `MCXGate(k)`)

| k | qubits | max abs error | ancilla leak (amplitude out of $|0\rangle_{\rm anc}$) | CX (got / $6+6(k-2)$) | T (got / $7+8(k-2)$) | peak |
|---|---|---|---|---|---|---|
| 0 | 1 | 0 | 0 | 0 / 0 | 0 / 0 | 1 |
| 1 | 2 | 0 | 0 | 1 / 1 | 0 / 0 | 2 |
| 2 | 3 | 0 | 0 | 6 / 6 | 7 / 7 | 3 |
| 3 | 5 | 3.3e-16 | 0 | 12 / 12 | 15 / 15 | 5 |
| 4 | 7 | 3.6e-15 | 0 | 18 / 18 | 23 / 23 | 7 |
| 5 | 9 | 5.6e-15 | 0 | 24 / 24 | 31 / 31 | 9 |
| 6 | 11 | 6.7e-15 | 0 | 30 / 30 | 39 / 39 | 11 |

Lowered gates contain only cx,h,t,tdg,s,sdg,x,z (no rotations). Also exact (< 1e-12) with permuted controls on a 6-qubit register, and with reused freed ancillas while another ancilla stays live; no state change when mcx is called with an invalid qubit.

### Program-header parser
Accepts: SUMMARY + 0..3 DISCOVERY, `PARENT = None` or string, prose lines, `# DISCOVERY` comments not counted. Rejects (all `BuilderError`, never another exception type): missing SUMMARY, no docstring, SUMMARY not first, 4 DISCOVERY, FAMILY non-literal (name / call / f-string), FAMILY missing/empty/int, PARENT missing / non-literal / int, no `build`, `build` with 0 or 2 args, `build` as lambda, nested-only `build`, FAMILY inside `if`, syntax error. `program_sha256` equals hashlib sha256 and changes on a 1-byte change.
Info (not a violation): `def build(spec=None)` and `def build(spec, *, k=1)` are accepted; `build(*args)` and `async def build` are rejected.

### Spec text (N3)
`TaskSpec.render()` equals the committed `compress/specs/twelve-step.md` byte for byte (4671 chars). The new sentences state: synthesis at $\varepsilon=10^{-6}$ re-verified with both tolerances $N_{\rm rot}\varepsilon+10^{-9}$ (triangle inequality) and the pruning bound `dropped_total` $\le 0.01\times$ the error tolerance, rejected as `pruning_bound`. Numbers come from code: `synth_tolerances(0, eps)["tol_err"] = 1e-9`, `PRUNE_FRACTION = 1e-2` (evaluator.py:38), `eps = 1e-6`; check `synth_tolerances(14, 1e-6) = 1.4001e-5`. PASS.

## Non-blocking notes
1. Lean track (ignored per brief, reported only): `tests/unit/test_lean_project_unit.py` has 2 failures at the end of my run — `test_step_2L3_theorems_exist_with_standard_axioms` (`print_axioms` returns `<unknown>` for `Su2Plaq.kron_disjoint_comm`) in the full run, and both it and the known-flaky `test_print_axioms_real_and_unknown` when rerun alone. Guess: Lean build not yet in a consistent state while the Lean builder works. `tests/acceptance/m2/test_lean_*.py`: 13 failed / 1 passed — some `NotImplementedError` (PENDING) but also real-content failures (`unknown theorems`, `native_decide` found in a file, missing `lean/certs/twelve-general-step.lean`), i.e. Lean 2.L steps in progress.
2. Builder-API strictness: `rz(np.float32 / np.int64, ...)` raises `BuilderError` (only `int`/`float` incl. `np.float64`); `free(np.int64(..))` raises a plain `TypeError` rather than `BuilderError` (harmless, still an error). Guess: `isinstance(qubits, int)` test.
3. `Builder.peak_qubits`, `_ops`, `_in_use` are ordinary attributes; a program that writes them can misreport `peak_qubits`. The emitted circuit width is independent of `peak_qubits` (verified), so the evaluator (step 2.3) must use `qc.num_qubits`, not `b.peak_qubits`, and must re-check gate names itself (the Builder guard is cooperative, not a sandbox).
4. `mcx` assumes clean ancillas; if a program frees a dirty ancilla and `mcx` reuses it, only the evaluator's dirty-ancilla check (step 2.3) will catch it.
5. Benchmark 002 watch items (Paulo QPY RSS, `logical_metrics` +6 ms) not touched by this step.

## Failures
None attributable to step 2.2.

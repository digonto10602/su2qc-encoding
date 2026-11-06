# Report 036 — M2: Lean checker hardening (N1–N4 of report 031) and step 2.L5 general-step certificate (tester, mode `step`)

- Date: 2026-11-05/06
- Git: tested on `a1449ea` + uncommitted hardening/2.L5 working tree (HEAD at report time `a4c28a6`); locked tests `acceptance-v7`.
- Plan in force: `prompts/006` (§4, §5, §6 rows 2.L4/2.L5, §9). Related: reports/tests/031 (first 2.L4 test), 028.
- Raw numbers: `results/tester_m2_lean_hardening_2l5.json`; scripts `tests/independent/lean_2l4/r2/` (not collected by pytest).
- Machine: 12 cores, load average 5–14 throughout (compression builder and other agents running) — all timings are upper bounds.

## VERDICT: PASS (with notes N5, N6, N7; N1–N4 resolved)

## 1. Commands
```
cd lean && lake build ; lake env lean certs/twelve-general-step.lean
pytest tests/acceptance/m2/test_lean_formal.py -rA --durations=12
pytest -n 4 tests/unit/test_lean_cert_unit.py tests/unit/test_lean_project_unit.py ; pytest -n 6 tests/unit
pytest -n 6 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 ; pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python tests/independent/lean_2l4/r2/{gen_k2,lower_test,reexport,mk_thm,mkcerts2,hunt_r2,hunt2_r2,hunt_ub_r2,ambig2,fake_states}.py ; bash run_thm.sh ; lake env lean --run KTest2.lean kdata.json
```

## 2. Required checks
| check | expected | got | result |
|---|---|---|---|
| `lake build` | green | green (9089 jobs) | PASS |
| `test_lean_certificate_general_circuit` | pass | pass, 50.7 s | PASS |
| `test_lean_theorem_file_general` | pass | pass, 113 s | PASS |
| `test_lean_certificate_small_accept_reject_na` | pass | pass, 23 s | PASS |
| `test_lean_checker_semantics_match_sparse_sim` | pass | pass, 1.5 s | PASS |
| `test_lean_project_present_and_builds_checker`, `..._generic_theorems_standard_axioms` | pass | pass | PASS |
| other 4 ids of `test_lean_formal.py` (`polish_rules`, `program_lemma`, `round_records`, `archive_best`) | later steps 2.L7/2.L8 | fail with step-2.L7/8 content (empty `LEAN_RULES`, `lean=None`) | PENDING |
| Lean unit files | pass | 24 / 24 (123 s) | PASS |
| all unit tests | pass | 352 / 352 (178 s) | PASS |
| m0 + m1 non-slow | green | 54 / 54 (319 s) | PASS |
| collect / `check_lock` / `acceptance-check` | clean | 102 tests; LOCK OK; matches acceptance-v7 | PASS |

## 3. Independent checks
### 3.1 Arithmetic (new K fast paths `mulReal`, `mulQ`, `conj`, parallel checker)
1200 K pairs (8 modes: dense, rational, real-only, no-$\sqrt3$ x general, $\sqrt3$-only, sparse) and 120 Laurent pairs vs sympy: Lean `K.mul`, `K.mulGen`, `add`, `neg`, `sub`, `==`, `Lp.add/mul/scale/mulMono` all agree, 0 bad; `conj(xy)=conj(x)conj(y)`, `conj(x)x` real, `conj∘conj = id` hold in Lean on all 1200. (Python KNum vs sympy again exact.)

### 3.2 N4 — exact lowering of crx / crz / rx
`_translate_export` + `checker_eval` vs Qiskit `Operator`, no phase freedom, 12 random gates (angles rational multiples of $\alpha$ or $\beta$) + a mixed circuit: max $|\mathrm{exact}-\mathrm{Qiskit}|=2.3\times10^{-16}$ (tolerance 1e-12); no `u`/`unitary` left in the op list. PASS.

### 3.3 Theorem file `lean/certs/twelve-general-step.lean`
| check | result |
|---|---|
| `lake env lean` on it | elaborates, 125 s wall (user 990 s, parallel), load ≈ 4–9 |
| `#print axioms gen_step_ok` | `[propext, Classical.choice, Quot.sound, gen_step_ok._native.native_decide.ax_1_1]` — exactly the three standard axioms plus its own native axiom; no `sorryAx` |
| embedded JSON | decoded string literal has sha256 `cdfb4023…0f83061` = the hash in the header; circuit_id `step-o1-46d991552e2e`, 732 gates, 50 qubits, 433 states, base (4,4), $c=1$ |
| theorem is about the right certificate | fresh `export_certificate(general_circuit(default_spec("twelve","step")))` equals the embedded JSON in every key except `provenance` (27 s export); the seed program `compress/programs/twelve/seed/000-general.py` yields a gate list identical (name, qubits, params) to `general_circuit` (237 gates) |
| `check_certificate(embedded)` | certified, 49 s (28 s of it the exporter comparison `_exporter_mismatch`, which returns None) |
| theorem-name limit | `write_theorem_file`: 11 and 13 characters accepted; 14 characters, `bad name`, `x.y` raise `ValueError` |

### 3.4 Doctored embedded certificate via the theorem route (`native_decide` must fail to elaborate)
13 theorem files built with `write_theorem_file` from mutated copies of the embedded certificate:
| mutation | elaboration |
|---|---|
| gate angle changed, extra Z, swapped h/t, wrong phase exponent, dirty ancilla (x on qubit 45), 432 states (state+block dropped), duplicate state index, altered state coefficient, state term deleted, target exponent changed, state term moved, state 0 sign flipped (in a size-2 block) | all 12: **error** "native_decide evaluated that the proposition … is false"; `gen_step_ok` depends on `sorryAx` |
| sign flip of state 50 (size-1 block, diagonal $V$) | elaborates (true statement for the flipped gauge; see N5) |
So 12 of 13 doctored certificates fail to elaborate; the 13th is a genuine symmetry of the claim.

### 3.5 False-accept hunt on the hardened checker (bare checker `su2plaq_cert check` and Python `check_certificate`)
- UE certificate, 85 mutations (`hunt_r2.py`); UB certificate (233 circuit gates -> 728 JSON gates), 42 mutations (`hunt_ub_r2.py`); plus 10 ancilla / partial-coverage cases (`hunt2_r2.py`): **0 unexpected results** (all wrong circuits REJECT; correct UE, UB, step order 1 and 2 certificates and the controls — commuting swap, xx / cx cx / z on a clean ancilla, n_qubits 44 — ACCEPT).
- Python route: 80 `rejected`, 4 `certified` (all controls), 1 exception (N6).
- N1 resolved: 432/434 states, duplicate index (11, 432), empty state, one-term state, altered coefficient, zero-coefficient duplicate code -> REJECT with specific reasons; "wrong circuit + certificate restricted to 164 states" now REJECT ("certificate has 164 states, the physical subspace has 433").
- N2 resolved: row/column index outside the block, empty block -> REJECT (no panic).
- Sign flip of a UE state (diagonal $V$): bare Lean ACCEPT (symmetry of the statement), Python `rejected` ("state 7 differs from the exact physical basis"). Sign flip in a 2-block (UB/step) -> Lean REJECT.
- Timings of correct certificates (export + check; report 031 values in brackets): UE 22.0 s (check alone 1.5 s) [24.2], UB 52.6 s (check 40.7 s) [406], step order 1 45.5 s (41.4 s) [648], step order 2 60.6 s (51.0 s) [339] — 6–14× faster, at load 8–14. UB and step certificates now come directly from `build_UB/build_step` (no manual crx lowering); the step order 1 certificate id equals the general circuit's (`46d991552e2e`).

### 3.6 N3 — tie-break (`certify_circuit_kind`, order 1)
| $(\alpha,\beta)$ | UE | UB | step |
|---|---|---|---|
| (0.5, 0.25) $\alpha=2\beta$ | certified (was rejected in 031) | certified | **rejected** |
| (0.25, 0.5) | certified | certified | rejected |
| (0.5, 0.5) | certified | certified | rejected |
| (0.3, 0.9) | certified | certified | rejected |
| (0.9, 0.3) | certified | certified | certified |
| (0.37, 0.61) nominal | certified | certified | certified |
The step circuit at ties is rejected (assignment of an angle to $\alpha$ or $\beta$ is ambiguous and the smaller-denominator rule picks wrongly for some gates) — a conservative false reject, never an accept, as required. The UE/UB false rejects of 031 are gone.

## 4. Notes
- **N5 (medium, scope of the theorem route).** The Lean checker pins the state set only up to count, indices, non-emptiness, uniqueness and exact orthonormality; it does not know the physical basis. Demonstration (`fake_states.py`): 433 fake basis states $|k\rangle$, one `p` gate, matching target -> bare Lean `ACCEPT`; `check_certificate` -> rejected ("state 1 differs from the exact physical basis"); but `write_theorem_file` writes `fake_ok` and `lake env lean` proves it (axioms standard + native). So the meaning of `gen_step_ok` rests on the embedded JSON being the exporter's output — verified above (hash + fresh-export equality). Suggest `write_theorem_file` call `_exporter_mismatch` (refuse on mismatch) and/or the header pin a hash of the exact state list.
- **N6 (low).** `check_certificate` raises an uncaught `ZeroDivisionError` on a state coefficient `"1/0"` (`Fraction("1/0")` in `_exporter_mismatch`; the except tuple lacks `ZeroDivisionError`). Not an accept; should return `rejected`.
- **N7 (info).** Step at $\alpha/\beta$ ties is rejected (3.6). The sign-gauge ACCEPT of N5 for diagonal blocks is a property of the claim, not a bug. A failing check does not stop at the first bad state in wall time (all 433 tasks run: 6–12 s on UB), harmless.
- No source or acceptance files edited by me. New: this report, `results/tester_m2_lean_hardening_2l5.json`, `tests/independent/lean_2l4/r2/*`.

## 5. Counts
passed: 6 target acceptance ids, 24 Lean unit, 352 unit, 54 m0/m1, 127 hunt mutations + 13 theorem-route mutations as expected; failed 0; pending 4 (2.L7/2.L8); new failures vs 031: none.

# 022 — M1 audit-fix verification (reports/audits/003: N2, N3, N5, N6, N7, N8)

- Date: 2026-11-05
- Git: HEAD `7a54eaa` plus the uncommitted audit fixes in the working tree (13 modified files: `src/su2plaq/evaluate/sparse_sim.py`, `metrics/logical.py`, `circuits/twelve.py`, `encodings/twelve.py`, `scripts/m1_results.py`, 4 unit-test files, `results/twelve/*.json`, `notes/STATUS.md`)
- Plan in force: `prompts/005-relative-prune-cap.md` (on top of `prompts/002`; addenda 003, 004); acceptance lock `acceptance-v5`
- Mode: step (fix verification)
- Related: `reports/audits/003-m1-twelve-qubit-audit.md`, `reports/tests/021-m1-gate-full.md`, `reports/tests/017`, `018`
- Raw numbers: `results/m1_audit_fixes_*.json`; independent scripts: `tests/independent/audit_fixes/`

## Verdict: FAIL (2 findings, both in the N6 fix; everything else PASS)

1. REGRESSION: a genuine Qiskit gate is now rejected: open-control CX (`qc.cx(a, b, ctrl_state=0)`, `XGate().control(1, ctrl_state=0)`, `XGate().control(1, annotated=True)`). It worked at HEAD.
2. RESIDUAL HOLE: a user subclass of a non-singleton standard class that reuses Qiskit's class name (`RZGate`, `PhaseGate`, `CPhaseGate`, `UGate`, `RXGate`, `CRXGate`) is still trusted by name (wrong gate simulated and counted).

Both are small. Neither touches an M1 number (all M1 circuits use only genuine singleton/standard gate objects).

## Commands

```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
pytest -n auto tests/acceptance                       # 88 collected (m0 34, m1 22, m2 32)
pytest -n auto tests/unit
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
PYTHONPATH=src python tests/independent/audit_fixes/adversarial_n6.py results/m1_audit_fixes_n6.json
PYTHONPATH=src python tests/independent/audit_fixes/subclass_spoof.py results/m1_audit_fixes_subclass_spoof.json
PYTHONPATH=src python tests/independent/audit_fixes/spoof_nonsingleton.py results/m1_audit_fixes_spoof_nonsingleton.json
PYTHONPATH=src python tests/independent/magnetic_1_3/check_recheck_cache_lower.py results/m1_audit_fixes_recheck_lower.json
PYTHONPATH=src python tests/independent/audit_fixes/sim_regression_tolerant.py results/m1_audit_fixes_sim_regression.json   # copy of magnetic_1_3/check_sim_regression.py, full_err returns "REJECTED" instead of raising
   (same two scripts also run against `git archive HEAD src` for a before/after comparison)
PYTHONPATH=src python tests/independent/audit_fixes/check_n5_phases.py results/m1_audit_fixes_n5.json
PYTHONPATH=src python tests/independent/audit_fixes/check_n3_paulo_comparison.py results/m1_audit_fixes_n3.json
PYTHONPATH=src python scripts/m1_results.py --out <scratchpad>/m1out/sub/dir      # N7/N8, reproducibility
```

## Suite results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| acceptance m0 (34) incl. slow | all pass | 34 pass | - | PASS |
| acceptance m1 (22) incl. slow | all pass | 22 pass | - | PASS |
| acceptance m2 (32) | pending (NotImplementedError) | 31 fail with `NotImplementedError` (all 31), 1 passes | - | PENDING (not failures) |
| unit tests | all pass | 173 passed (166 at 021, +7 new from the fixes), 71 s | - | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v5` | - | PASS |
| new failures vs report 021 | 0 | 0 in m0/m1/unit | - | PASS |

`pytest tests/acceptance` total: 57 passed, 31 failed (all `NotImplementedError`, m2), 317 s.

## (1) N6 adversarial: is any gate trusted by name?

Truth for each case: dense `Operator(qc)` for the simulator; for `lower`, the unitary up to a global phase and the gate counts of an independently built reference (every non-standard instruction replaced by its definition, whole-circuit transpile to the same basis). 201 cases in `adversarial_n6.py` + 12 in `subclass_spoof.py` + 14 in `spoof_nonsingleton.py`.

| family | cases | simulator | `lower` / counts | result |
|---|---|---|---|---|
| custom gate named every SIM_BASIS / LOGICAL_BASIS name (18 names x {lower, UPPER, Capitalised} x {random unitary, Clifford+T mix, X-only}) | 136 | by content, error vs `Operator` <= 1e-16 (for comparison, at HEAD 9 of the 10 names tried in the 018 recheck script gave errors 0.27 to 0.71 or crashed) | counts equal reference; unitary error <= 1.7e-16. `lower` rejects (conservatively) 3 cases whose top-level name is exactly `unitary` | PASS |
| parametrised disguises: "rz" = `p(a)` / `rz(2a)` / `rz(a/2)`, "p" = rz, "cp" = crz, "u" = rx, plus `.control(1)` and `.control(1, ctrl_state=0)` of a disguised "rz" | 8 | by content | by content | PASS |
| disguised controlled gates: custom gate named x/z/h/rx with content != the standard one, `.control(k, ctrl_state)` giving names `cx`, `ccx`, `cx_o0`, `ccx_o1`, `cz`, `ch`, `cch`, `crx`, `ccrx`, ... but class `ControlledGate` | 24 | by content | by content | PASS |
| nested disguise: custom "rz" containing custom "cx" containing custom "t" containing custom "h", 3 levels | 1 | by content | by content | PASS |
| fake barrier: `Gate` named `barrier` with content CX | 1 | simulated (not dropped) | counted | PASS |
| fake barrier: bare `Instruction("barrier")` without definition | 1 | rejected | rejected | PASS |
| opaque gate (no definition) named t / cx / rz / unitary / h | 5 | rejected | rejected | PASS |
| `Instruction` (not `Gate`) named "t" with an X definition | 1 | by content | by content | PASS |
| `UnitaryGate` subclass `UG2` | 1 | by content | rejected (policy: `unitary` is not lowerable) | PASS |
| real `XGate` renamed "t", real `TGate` renamed "x", real `RZGate` with mutated params / overwritten instance definition | 4 | the gate's class decides (not its name or instance fields) | same | PASS |
| `AnnotatedOperation` (`RZ.control(2, annotated=True)`) | 1 | rejected | rejected | PASS |
| singleton standard-class subclasses (`TGate`/`XGate`/`HGate`/`CXGate`/`CCXGate`/`SXGate` named like Qiskit's, other module; module forged to `qiskit.*`; `MyT`, `MyH`) with changed `_define` and/or `to_matrix` | 12 | by content (error vs intended content <= 1e-16) | by content | PASS |
| `MyRZ(RZGate)` (different class name), changed `_define` + `to_matrix` | 1 | by content (= RX) | by content | PASS |
| non-singleton subclass reusing Qiskit's class name, other module `userpkg.gates`: `RZGate`, `PhaseGate`, `CPhaseGate`, `UGate`, `RXGate`, `CRXGate` (define-only and with `to_matrix`) | 12 of 12 | 11 of 12 WRONG (only `UGate` with `to_matrix` override is right, since 'u' reads `to_matrix`) | 11 of 12 WRONG (`PhaseGate` ok because p and rz agree up to phase) | **FAIL** |
| `mcx` with 3 or 4 controls inside a custom gate named `cx` / `h` / `t` / `x` / `ccx` / `barrier` / `rz` | 14 | accepted (error vs `Operator` 3e-17 to 1.5e-16, exact); with a non-basis name (`my_wrap`) the same circuit is rejected | accepted (14 or 36 CX) | NOTE |

The two non-PASS rows:

**F1 (FAIL, low severity): name-spoofed subclass.** `is_standard_gate` (`sparse_sim.py:185-198`) checks `isinstance(op, type(ref))` and then `type(op).__name__ in (type(ref).__name__, "_Singleton"+...)`. For non-singleton classes `type(ref)` is the plain class, a user subclass passes `isinstance`, and its `__name__` can equal Qiskit's. Reproducer (`tests/independent/audit_fixes/spoof_nonsingleton.py`):

```
class RZGate(qiskit.circuit.library.RZGate):   # defined in another module
    def _define(self): ... self.definition = (rx(theta) on qubit 0)
# sim error vs the intended content (rx): 0.34;  lower(): 0.34  (silently simulated and counted as rz)
```

Singleton classes are safe (a subclass gets a different dynamic class, `isinstance(op, _SingletonT)` is False). Guess at the fix: require `type(op) is type(ref)` or `type(op).__mro__[1] is type(ref).__mro__[...]`-style identity for the singleton wrapper, or at least `type(op).__module__.startswith("qiskit.")` (the module check is already used for `unitary`; a module can be forged, an identity check cannot). This needs a deliberately hostile program (a class named exactly like Qiskit's, in a user module); Qiskit's own transpiler and Aer also trust names in this case, so I rate it low; but the stated rule was "never silently trusted".

**F2 (REGRESSION, medium severity): open-control CX rejected.** Genuine gates that worked at HEAD (`git archive HEAD src`) are now rejected with `ValueError: custom gate 'cx' has no definition`:

| circuit element | class / name | HEAD | working tree |
|---|---|---|---|
| `qc.cx(0, 2, ctrl_state=0)` | `CXGate` / `cx_o0` | simulated, lowered | `ValueError` (sim and lower) |
| `XGate().control(1, ctrl_state=0)` | `CXGate` / `cx_o0` | simulated | `ValueError` |
| `XGate().control(1, annotated=True)` | `CXGate` / `cx` | simulated | `ValueError` |

Cause (checked): the definition of `CXGate(ctrl_state=0)` is `x, cx, x`; the inner `cx` is a plain (non-singleton) `CXGate` instance, so `isinstance(op, _SingletonCXGate)` is False, `is_standard_gate` is False, and `_expand` then finds no `definition`. All other open-control gates (`ccx_o0/o1/o2`, `ch_o0`, `cz_o0`, `ccz_o1`, `crx_o0`, `cp_o0`, `cswap_o0`, `crz_o0`, `cch_o1`, `ccrz`) are simulated and lowered with errors <= 1.3e-16. Guess at the fix: in `is_standard_gate`, accept `type(op) is type(ref)` or `type(op).__mro__[1] is type(ref)`-equivalent (the plain class that the singleton wraps), i.e. compare to the class object, not only `isinstance` of the singleton wrapper. M1 acceptance and unit tests do not cover `ctrl_state=0` on `cx`; a unit test for it would have caught this. Not silent (an explicit `ValueError`), so it is a false rejection, not a wrong number; it matters for the M2 loop because proposers may use `cx(..., ctrl_state=0)`.

**NOTE N6-b: wide-`mcx` policy bypass.** `_reject_wide_mcx` (`sparse_sim.py:150-166`) does not recurse into definitions of gates whose name is a standard name, so `mcx(3 or 4 controls)` hidden in a custom gate named `cx`, `h`, `t`, `x`, `ccx`, `barrier` or `rz` is accepted while the same gate under another name is rejected. The accepted result is numerically exact here (per-gate transpile on the gate's own qubits has no idle ancillas), but it is the policy that the circuit "must not contain native mcx >= 3" and the CX count (14 for 3 controls, 36 for 4) is Qiskit's mcx synthesis. Guess at the fix: recurse whenever `not is_standard_gate(op)` instead of whenever the name is not standard.

### Regression: genuine standard gates, before vs after (same scripts, HEAD source vs working tree)

| check | HEAD | working tree | result |
|---|---|---|---|
| simulator vs `Operator`, 36 random circuits (24 with foreign gates, seeds 3000..3035), max error | 2.156e-15 | 2.156e-15 (identical per circuit, <= 1e-15) | PASS |
| simulator vs Aer statevector, same 36 | 2.433e-15 | 2.433e-15 | PASS |
| program-order vs DAG-order path | 7.31e-16 | 7.31e-16 | PASS |
| forced-pruning certified bound, 64 896 cases | 0 violations | 0 violations (max err/bound 1.000006) | PASS |
| 24 hostile rejections (mcx>=3, measure, reset, control flow, ...) | all `ValueError` | identical | PASS |
| accepted exact controls (ccx, mcx2, mcp4, rccx, rc3x, c3sx, ...) | <= 1.4e-15 | <= 1.4e-15 | PASS |
| hostile cache cases (same name different content, close params, bound parameter, global phase mix, ...) | <= 6e-16 | <= 4.6e-16 | PASS |
| hostile `ctrl_state_variants` (contains one `cx(ctrl_state=0)`) | 7.6e-16 | REJECTED | **FAIL (F2)** |
| `lower` vs whole-circuit transpile, 30 random circuits (seeds 7000..7029): counts equal | 30/30 | 30/30, cx/t/rz identical to HEAD in 30/30 | PASS |
| `lower` unitary vs original (exact phase), max over the 30 | 1.07e-14 | 1.07e-14 | PASS |
| `lower(build_UB(0.61))`, with/without outer: counts, depth | cx 294, h 178, t 160, tdg 152, x 50, s 8, sdg 8, rz 6, z 4; depth 292 | identical | PASS |
| `lower(paulo_logical(1))` | cx 294, t 152, tdg 144, rz 56, ...; depth 391 | identical | PASS |
| lowered `build_UB` vs `build_UB` on the 625 inner codes | 6.0e-15 | 6.0e-15 | PASS |
| `build_UB` from `to_gate()` against `U_B(0.61)` (cache poisoning test) | ok, 3.6e-13 | ok, 3.6e-13; vs 0.60: rejected (0.020) | PASS |

## (2) N5: global phases

`check_n5_phases.py` (also `results/m1_audit_fixes_n5.json`):

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| raw QPY phase vs `paulo_circuit()` | 2.1316e-14 rad | 2.1316e-14 | 1e-15 | PASS |
| `paulo_circuit(with_outer=True)` phase (was doubled, 4.26e-14, in the audit) | 2.1316e-14 | 2.1316e-14 | 1e-15 | PASS |
| instruction counts, plain vs embedded | 3207 = 3207 | 3207, 3207 | exact | PASS |
| `build_UB(0.61, outer=False/True)`, `build_step` order 1 and 2, outer False/True: phase = sum of parts | 0.0 | 0.0 | 1e-15 | PASS (6 checks) |
| `build_step` with injected nonzero phases (ue, ub) = (0.1, 0.3), (-0.7, 2.0), (3.0, 0.0), orders 1 and 2: phase = ub + 1 or 2 times ue | 0.4/0.5; 1.3/0.6; 3.0/6.0 | 0.4/0.5; 1.2999999999999998/0.5999999999999996; 3.0/6.0 | 1e-15 | PASS (6 checks) |
| dense `Operator` on 7-qubit proxy of the `paulo_circuit` embedding pattern (phase 0.77) | 0 | 0.0 | 1e-14 | PASS |
| dense `Operator` on 3-qubit proxy of the `build_step` pattern (0.2 + 0.5) | 0 | 0.0 | 1e-14 | PASS |

The real phases are 0 or 2e-14 rad, so the tests with injected phases are what actually exercises the bookkeeping.

## (3) N3: Paulo comparison, recomputed with my own code (own `generate_preset_clifford_t_pass_manager` call; own `pygridsynth` loop over the angles of an independent whole-circuit transpile)

Setting: $\beta=1$, per-rotation $\varepsilon$, Qiskit Clifford+T pass manager level 3, seed 12345, `rz_synthesis_error`=$\varepsilon$, `rz_cache_error`=$\varepsilon/10$.

| quantity | JSON / stated | mine | tolerance | result |
|---|---|---|---|---|
| ours `build_UB(1.0)` through Qiskit CT pass manager, $\varepsilon=10^{-6}$: T / CX | 662 / 294 | 662 / 294 | exact | PASS |
| Paulo logical circuit through the same pass manager: T / CX | 1162 / 294 | 1162 / 294 | exact | PASS |
| Paulo's shipped compiled file: T / CX | 1162 / 294 | 1162 / 294 | exact | PASS |
| pygridsynth $T_{\rm total}$, ours ($T_{\rm fixed}=312$, $N_{\rm rot}=6$), $\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$ | 564 / 684 / 812 / 936 | 564 / 684 / 812 / 936 | exact | PASS |
| pygridsynth $T_{\rm total}$, Paulo logical ($T_{\rm fixed}=296$, $N_{\rm rot}=14$) | 872 / 1180 / 1488 / 1736 | 872 / 1180 / 1488 / 1736 | exact | PASS |

Observation: Paulo's pygridsynth total at $10^{-6}$ is 1180 vs his Qiskit-compiled 1162, so the two T counts of his circuit differ by 1.5%; compare Qiskit-to-Qiskit (662 vs 1162, ratio 0.57) or pygridsynth-to-pygridsynth (684 vs 1180, ratio 0.58). Both ratios agree.

## (4) Results JSON, N2, N7, N8

| check | expected | got | result |
|---|---|---|---|
| strict JSON parse (`parse_constant` raising) of `results/twelve/{UE,UB,step}.json`; regex scan for `NaN`/`Infinity` tokens | none | 0 tokens, 0 non-finite floats in all three | PASS |
| outer-row synthesised verdicts (`reason == "writes_outer"`) stored as `{"evaluable": false, ...}` | 4 in UE.json (eps 1e-4,1e-6,1e-8,1e-10), no `ok`/`op_norm_error`/`certified` keys | 4 found at `/extra/outer_electric_row/metrics/t_table[0..3]/synth/verdict`, keys `{evaluable, reason, explanation}`; no unflagged `writes_outer` anywhere | PASS |
| every other verdict block `ok` and `certified` | all true | UE 6/6, UB 7/7, step 10/10 `(ok, certified) = (True, True)` | PASS |
| numbers unchanged vs the 021 results (HEAD files) | only timing, timestamp, commit differ | non-timing changed leaves: 0 in UB and step; UE: 88 removed leaves (the old Infinity/NaN fields) and 8 added (`evaluable`, `explanation`) | PASS |
| N3 additions present (`qiskit_clifford_t_pm_paulo_settings_eps_1e-6`, `t_table_pygridsynth` for both circuits, note) | present | present (UB.json, 77 added leaves) | PASS |
| N7 `n_inner_codes` from `len(enc.inner_codes())` | 625 | 625 | PASS |
| N8 `m1_results.py --out <nested dir outside the repo that does not exist yet>` | runs, writes files, paths valid | rc 0 in 214 s; JSON + qpy + qasm3 written; `files.qpy` holds an absolute path | PASS |
| rerun reproduces `results/twelve` | identical except timing/provenance/paths | JSON: 0 non-timing differing leaves in UE, UB, step (11/11/15 differing leaves all `seconds`, `timestamp`, `files`); all 5 qpy files byte-identical (sha256) | PASS |
| provenance of `results/twelve/*.json` | clean commit | `git_commit 7a54eaa`, `git_dirty true` | OPEN (audit N1: regenerate on the clean commit that gets the `milestone-1` tag) |

## Other observations

- Housekeeping: while preparing a before/after comparison I ran `git stash` on the working tree by mistake and restored it with `git stash pop` within seconds; `git status` shows the same 13 modified files as before and no content was lost. The HEAD comparison afterwards used `git archive HEAD src` extracted into the scratch directory.
- `lower()` rejects a top-level `unitary` but accepts a `UnitaryGate` nested inside a custom gate (lowered by Qiskit's synthesis). Not related to N6; recorded because the top-level policy is not enforced for nested content.
- The scratch directory (`/tmp/claude-1000/.../scratchpad`) already contained files from earlier sessions (e.g. an old `unit.log`); I wrote new logs and did not rely on old ones.

## Failures (short)

| check | expected | got | guessed cause (guess) |
|---|---|---|---|
| open-control `cx` (`cx(..., ctrl_state=0)`, `XGate().control(1, ctrl_state=0)`) | simulate/lower as at HEAD (error <= 1e-15) | `ValueError: custom gate 'cx' has no definition` | `is_standard_gate` tests `isinstance(op, _SingletonCXGate)`; the inner plain `CXGate` of the open-control definition is not an instance, so it is neither standard nor definable |
| non-singleton standard-class subclass reusing Qiskit's class name (`RZGate`, `CPhaseGate`, `RXGate`, `CRXGate`, `UGate`, `PhaseGate`) with other content | simulate by content or reject | simulated as the standard gate (error 0.34 vs intended), counted as the standard gate | the class check compares `type(op).__name__` strings, not class identity or module |

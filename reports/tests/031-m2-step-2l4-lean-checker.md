# Report 031 — M2 step 2.L4: exact Lean certificate checker (tester, mode `step`)

- Date: 2026-11-05
- Git: `7d76375` at report time (working tree dirty: step 2.L4 files uncommitted). Locked tests: `acceptance-v7` (244f52f; it fixes the no-op tampering lines, so `test_lean_certificate_small_accept_reject_na` is now judged normally and PASSES).
- Plan in force: `prompts/006-lean-formal-verification-m2-addendum.md` (§4, §5, §6 row 2.L4, §9). Related: reports/tests/025, 028 (Lean skeleton and theorems).
- Raw numbers: `results/tester_m2_step2l4_lean_checker.json`; independent scripts: `tests/independent/lean_2l4/` (not collected by pytest, not under `tests/acceptance/`).

## VERDICT: PASS (with hardening notes N1–N4; no false accept of a wrong circuit produced by the exporter)

## 1. Commands
```
cd lean && lake build                                              # green, 9089 jobs, 7 s (cache)
lake env lean --deps lean/Su2PlaqCert/*.lean ; grep sorry|admit|native_decide|axiom|Mathlib lean/Su2PlaqCert
pytest -n 4 tests/unit/test_lean_cert_unit.py tests/unit/test_lean_project_unit.py
pytest tests/acceptance/m2/test_lean_formal.py               # all 10 ids
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest -n 8 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 ; pytest -n 8 tests/unit
python tests/independent/lean_2l4/{gen_k.py, gates_test.py, basis_check.py, hunt.py, hunt2.py, hunt_ub.py, hunt_ub2.py, ambig.py, altcheck.py, mkcerts.py, mk_ub.py}
lake env lean --run tests/independent/lean_2l4/KTest.lean kdata.json
```

## 2. Required checks
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `lake build` | exit 0 | exit 0, 7 s (cached) | — | PASS |
| Su2PlaqCert imports | no Mathlib | only `Lean.Data.Json`, `Std.Data.HashMap`, own modules; no `sorry`/`admit`/`native_decide`/`axiom` | — | PASS |
| `test_lean_project_present_and_builds_checker` | pass | pass | — | PASS |
| `test_lean_checker_semantics_match_sparse_sim` | pass | pass | locked | PASS |
| `test_lean_certificate_small_accept_reject_na` (v7) | pass | pass | locked | PASS |
| `test_lean_generic_theorems_standard_axioms` | pass | pass | locked | PASS |
| Lean unit files (cert + project) | pass | 19 / 19 (45 s) | — | PASS |
| all unit tests | pass | 294 / 294 (214 s) (includes parallel compress builder's tests) | — | PASS |
| m0 + m1 non-slow acceptance | green | 54 / 54 (166 s) | — | PASS |
| collect | clean | 102 tests collected | — | PASS |
| `check_lock.py`, `acceptance-check` | OK | LOCK OK; "matches acceptance-v7" | — | PASS |
| PENDING (later steps, not counted) | — | 6 ids of `test_lean_formal.py` (general_circuit, theorem_file_general, polish_rules, program_lemma, round_records, archive_best) fail with later-step content (empty `LEAN_RULES`, `lean=None`, no theorem file; general circuit gives `n_a: unitary_gate`, see N4) | — | PENDING |

## 3. Independent checks
### 3.1 Exact arithmetic (K, Laurent) vs sympy
600 random K pairs (dense, rational-only, no-$\sqrt3$, sparse) and 120 random Laurent pairs (up to 6 terms, exponents in $[-3,3]^2$); expected values from sympy `expand` + coefficient extraction in the basis $(1,i,\sqrt2,i\sqrt2,\sqrt3,i\sqrt3,\sqrt6,i\sqrt6)$.
| check | result |
|---|---|
| Lean `K.add`, `K.mul` (all fast paths), `K.mulGen`, `K.neg`, `K.sub`, BEq vs sympy | 600/600 agree, 0 bad |
| Lean `Lp.add`, `Lp.mul` (both orders), `Lp.scale` distributivity, `mulMono` vs `Lp.mul` | 120/120 agree, 0 bad |
| Python `KNum` add/mul/neg/conj/inv, `Laurent` add/mul vs sympy | 600/600, 120/120 exact |
Normal form unique: the 8 components are a $\mathbb{Q}$-basis of $\mathbb{Q}(i,\sqrt2,\sqrt3)$ (degree 8), so structural equality = field equality.

### 3.2 Gate semantics vs Qiskit (no phase freedom, `checker_eval` evaluated at random $(\theta_\alpha,\theta_\beta)\in[-3,3]^2$, 5 qubits, random qubit assignments and exponent vectors)
| gate | max abs diff | gate | max abs diff |
|---|---|---|---|
| x z s sdg sx rz p cx cz cp swap ccx ccz | 0 | t, tdg | 1.6e-16 |
| h | 1.1e-16 | 10 random 40-gate circuits, all 16 gates | max 4.2e-15 (unitarity 4e-15) |
All 16 kinds PASS (tolerance 1e-12).

### 3.3 False-accept hunt (every row `REJECT` unless "control")
UE certificate (4 gates, 28 qubits, 433 states) — 80 mutations, `tests/independent/lean_2l4/hunt.py`, `hunt2.py`; UB certificate (728 gates, 50 qubits) — 30 + 24 mutations.
| class | cases | outcome |
|---|---|---|
| wrong angle multiple (UE: 6; UB rz: 24 extra) | 30 | all REJECT (odd rz exponent rejected structurally) |
| swapped order, non-commuting (UB) | 5 | all REJECT (one only at state 88: swap matters on some states) |
| swapped order, commuting (control) | 3 | all ACCEPT (correct) |
| missing gate (UE 1, UB 4), extra Z / T / p on data/outer, extra p(any) | 11 | all REJECT |
| ancilla left dirty (x), h on ancilla, cx data to ancilla, flipped mid-circuit; controls: xx, cx cx, z on clean ancilla | 5 REJECT, 3 control ACCEPT | correct |
| wrong claimed phase c (k = ω, −1, 2; exponents ±1 in $\alpha$, $\beta$) | 8 | all REJECT |
| state term moved / swapped state contents / duplicated term | 4 | all REJECT |
| target from another kind (UE vs UB/step, UB vs UE/step), $z_\beta\to z_\beta^{-1}$ | 5 | all REJECT |
| two blocks cover one state, uncovered state, block names state 999 | 3 | REJECT with specific reasons |
| qubit index out of range / negative / 1.5 / string / repeated / arity wrong / unknown gate / angle on angle-free gate | 14 | all REJECT, clear reasons |
| huge exponents ($10^{30}$, cancelling $\pm10^{30}$, phase $10^{40}$), $n_{qubits}=10^9, 63$, state code $2^{70}$ | 7 | all REJECT, no crash/hang (<0.3 s) |
| malformed JSON (truncated, empty, `null`, `[]`, no target/states/gates, schema 2, `1/0`, `abc`, `1.5`, 7-component K) | 14 | all REJECT |
| correct UE, UB, step(order 1), step(order 2) certificates | 4 | all ACCEPT |

Behaviours that the checker ACCEPTS but a reader might not expect (all with a doctored file, none reachable from the exporter):
- **N1 (medium, hardening).** The checker never checks that the state set is the complete 433-state physical basis. (a) `states` shortened together with its blocks: ACCEPT. (b) A wrong circuit (extra $p(\theta_\alpha)$ on data qubit 4) with the certificate restricted to the 164 of 433 states that have no support on that qubit being $|1\rangle$: **ACCEPT** (full 433 states: REJECT, state 72). (c) Duplicate state index `k` leaves a hole (empty state): vacuously ACCEPT. (d) Altered state coefficients are accepted for UE (each $\psi_k$ is an eigenvector, so any vector inside the same electric phase sector passes) — the checker proves "circuit acts as the claimed $V$ on the claimed vectors", the vectors are trusted from the exporter. Python `check_certificate` adds no such check. Mitigation I verified for the honest exporter: exact basis has all 433 states with exact Gram matrix $=\mathbb{1}$ (0 nonzero off-diagonals, 0 diagonals $\ne 1$; same for the encoded states) and ≤2.8e-16 from the float basis. Suggest: checker requires `states.size == 433`, indices $0..432$ each once, non-empty, and exact orthonormality (or a hash of the state list).
- **N2 (low).** Entry row index $i\ge |ks|$ in a target block: `b.ks[i]!` panics ("index out of bounds" on stderr) but the run prints ACCEPT. (Index 5 on a 1-state block maps to the state itself.) Should be REJECT.
- Unreduced rationals (`2/4`) parse to the same value (fine).

### 3.4 Exporter choices
| check | result |
|---|---|
| phase $c$ from float simulation at 3 angle pairs | UE/UB/step: $c=1$, exponents $(0,0)$; float spread ≤1.3e-16; a wrong fit can only cause REJECT (checker verifies $c$ exactly) |
| claim holds at the alternate angle pairs | circuits rebuilt at $(0.91,0.23)$, $(1.70,1.00)$ and nominal; sampled 49 states: UE $2.8\times10^{-17}$, UB $\le1.1\times10^{-14}$, $c=1$ |
| angle ambiguity: UE with $(\alpha,\beta)=(0.5,0.25)$ ($\alpha/\beta=2$) | gate angle $-0.375=-\tfrac34\alpha=-\tfrac32\beta$; smaller denominator picks $\beta$; **correct circuit REJECTED** ("state 16 differs"). $(0.25,0.5)$ and $(0.5,0.5)$ certify. Never a false accept (the certificate is exactly about the instantiated exponents, which equal the real angles at the nominal pair). **N3 (low):** a tie-break preferring the target's own variable ($\alpha$ for UE, $\beta$ for UB) would avoid the false reject; at the nominal $(0.37,0.61)$ ambiguity needs denominators 37/61, not hit. |
| recognition tolerance | `rational_multiple` tol 1e-12: an angle off by <1e-12 is certified as exact (accepted by design; below any ε in the plan). |

### 3.5 Exact basis and blocks
Exact physical basis: 433 states, max $|$exact − float$|$ = 2.8e-16 per entry (≤1e-12 required); 33 425 encoded terms, 10 897 distinct codes. $H_B$ exact: Hermitian (0 violations), 256 nonzeros, **305 blocks** (177 of size 1, 128 of size 2). Spectral projectors exact: $\sum_\lambda P_\lambda=\mathbb{1}$, $\sum\lambda P_\lambda=H$, $P^2=P$, $P_\lambda P_\mu=0$: 0 violations in all 305 blocks. Spectrum $\{-2,-1,-\tfrac12,0,\tfrac12,1,2\}$ with multiplicities $16,96,16,177,16,96,16$ (matches STATUS M0).

### 3.6 Timing (UB/step use `build_UB`/`build_step` with each `crx` replaced by `h·rz·cx·rz·cx·h`, exact; see N4)
| circuit | gates (JSON) | status | wall (export + check) | notes |
|---|---|---|---|---|
| UE(0.37), outer | 4 | certified | 24.2 s (check alone 0.5 s) | done-check ≤120 s |
| UB(0.61) | 728 | certified | 405.9 s (export 27 s) | other jobs running |
| step order 1 | 732 | certified | 647.5 s | machine loaded by 4 parallel mutation checks + pytest |
| step order 2 | 736 | certified | 338.5 s | lightly loaded |
Peak checker memory ≈ 80 MB; certificate JSON 2.5 MB each. Load-free time not separately measured; benchmark mode should do it.

## 4. Notes for the coordinator
- **N4 (for 2.L5).** `build_UB`/`build_step` and the seed `general_circuit` contain `crx`, which `sparse_sim._translate` lowers to a `u` gate, so `certify_circuit_kind` returns `n_a: unitary_gate` (this is exactly what `test_lean_certificate_general_circuit` shows). The exporter must either lower `crx/cry/…` into `h, rz, cx` (exact, angles stay $\beta$-multiples; I verified it gives certified UB/step) or accept it; otherwise 2.L5 cannot pass. Time budget 900 s is plausible but tight under load (UB ≈ 6.5 min, step ≈ 6–11 min).
- Trust base of "certified": gate semantics (verified above), the exact states and exact target (exporter, cross-checked ≤1e-12 vs float at one angle pair, plus my exact Gram / projector identities), and the checker not validating the state set (N1).
- No source or acceptance files were edited by me. New files: `tests/independent/lean_2l4/*`, `results/tester_m2_step2l4_lean_checker.json`, this report.
- My own first-draft mutation list contained three no-op angle mutations (gate 347/349/371 replaced by their own value); they were correctly ACCEPTED and are not counted. They were re-run as 24 real mutations (all REJECT).

## 5. Counts
passed: 4 required acceptance ids + 19 Lean unit + 294 unit + 54 m0/m1 + all independent checks; failed: 0; pending: 6 (later steps); new failures vs report 029/030: none.

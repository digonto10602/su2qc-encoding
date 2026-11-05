# 003 — M1 audit: 12-qubit encoding, general circuit

- Date: 2026-11-05
- Auditor: `auditor` agent (Opus 5.5, high)
- Git: HEAD `7a54eaa`; commit range `milestone-0..7a54eaa` (`src/`, `scripts/`, `docs/METHODS.md`, `prompts/`)
- Plan in force: `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §2.6, §2.11, §4, with addenda `prompts/003` (Gauss tolerance for synthesised circuits), `prompts/004` (leak judged as an amplitude), `prompts/005` (relative prune cap)
- Related: tester reports `reports/tests/015`–`021` (021 = M1 gate full PASS); previous audits `reports/audits/001`, `002`
- Results audited: `results/twelve/{UE,UB,step}.json` (written by `scripts/m1_results.py`)

## Verdict: PASS WITH NOTES

No blocking issue. The physics conventions in the M1 code are correct: electric sign and angle, $\alpha_P=2\beta$, the replacement of `mcrx` (exact, phases included, scratch qubit clean), step ordering, the max-over-groups pruning bound, and the definition of the T totals. One real hole in the evaluator was found (N6: gates are recognised by name only). It does not affect any M1 number, because every M1 circuit uses only standard Qiskit gate objects (checked). It **must be closed before the M2 proposer loop evaluates any program**. The results JSONs must be regenerated at a clean commit before Report 1 (N1).

## Checks run by the auditor (independent of the tester)

| Check | Command / place | Result |
|---|---|---|
| `mcrx` → `rccx`·`crx`·`rccx` on scratch $h$ | dense `Operator`, 4 qubits, θ = 0.7, restricted to $h=0$ in and out | max deviation $1.1\cdot10^{-16}$; amplitude leaked to $h=1$: exactly 0 |
| `cond_h` = controlled-$H$ on $j_xj_y=11$ | dense `Operator` vs `HGate().control(2)` | $1.1\cdot10^{-16}$ |
| $U_B(0.61)$ on the vacuum code, **Aer MPS** engine (independent of the sparse engine) | `save_probabilities` on `d` and on the ancillas, `lower(build_UB(0.61))` | $P(\text{vac})=0.11809239896112$ vs $\cos^2(2\beta)=0.11809239896111$; 16 other codes each $0.055119$ vs $\sin^2(2\beta)/16=0.0551192$; $P(\text{ancillas}=0)=1-6\cdot10^{-14}$. This confirms $\alpha_P=2\beta$ and the closed-sector coupling 2 (METHODS §4) |
| Global phases | `build_UB(0.61).global_phase`, `build_step(...)`, `paulo_circuit()` vs `paulo_circuit(with_outer=True)` | 0, 0; $2.13\cdot10^{-14}$ vs $4.26\cdot10^{-14}$, i.e. doubled (N5) |
| Paulo comparison at the same level | `ct_compile(·, 1e-6)` (seed 12345) on macro-level and on lowered circuits | ours $U_B(1)$: CX 294, T 662 (macro) / 662 (lowered); `paulo_logical(1)`: CX 294, T **1162** (macro, = his metadata) / 1096 (lowered) |
| Gate-name dispatch | custom 1-qubit gate whose content is $X$, renamed `"t"` → `run_batch`, `logical_metrics` | simulated as $T$ (output $|0\rangle$, should be $|1\rangle$), counted as 1 T (N6) |
| M1 circuits use only standard gate objects | every instruction of UE, UE+outer, UB, step 1, step 2, `paulo_circuit()`, synthesised step 2 is an instance of Qiskit's standard class for its name | yes, none non-standard → N6 does not affect M1 numbers |

Note on my run: a first attempt at the Aer check asked for the 34-qubit joint distribution ($2^{34}$ entries) and grew to 60 GB of memory; I stopped my own process (PID 1632139) after about 2 min. Nothing else was affected. The marginal-probability version above is the one I used.

## Checklist

| Item | State | Where |
|---|---|---|
| Electric step: $U_E(\alpha)=e^{-i\alpha H_E^{\rm inner}}$, $j(j+1)=\tfrac34$ ⇒ `p(-3α/4)` on $q_j$ | OK | `circuits/twelve.py:24-28`; METHODS §2; test M1-E1 checks the single-link amplitude $e^{-3i\alpha/4}$ |
| Magnetic step: $\alpha_P=2\beta$, $U_B=e^{+i\beta(\mathrm{Tr}U_P+{\rm h.c.})}$ | OK | `circuits/twelve.py:71`, `:184-193`; checked independently with Aer MPS (closed sector) |
| `mcrx` replacement exact incl. phases; $h$ clean | OK | `circuits/twelve.py:186-190`, `:79-84` (argument below) |
| Step order 1 $=U_B(\beta)U_E(\alpha)$ (electric layer first in the circuit), order 2 symmetric | OK | `circuits/twelve.py:216-231` vs `exact/operators.py:118-128`; M1-S1 rejects the wrong order (error $>10^{-3}$) |
| `paulo_circuit` embedding | OK (global phase doubled, harmless: N5) | `circuits/twelve.py:241-260` |
| Codec / $V_P$ vs Paulo Eq. 31 | OK (unchanged since step 1.1; `describe()` "far end fixed to −" in Paulo labels = $+\tfrac12$ in CG labels, consistent with METHODS §3) | `encodings/twelve.py:151-173` |
| `import_map` lean22 / lean22_v2 angle meaning | ISSUE (NON-BLOCKING for M1, fix before M2 seeding: N4) | `encodings/twelve.py:196-200` |
| Qubit order / little-endian / register relabelling | OK | `encodings/twelve.py:129-149`, `evaluator.py:80-90` |
| Truncation ($j_{\max}=\tfrac12$, prune cap) | OK | prompts/005 cap is rigorous (argument below) |
| Normalisation / expectation values real | OK | P(anc=0)=1 to $6\cdot10^{-14}$; Gram and Gauss values from reports/tests/016 |
| Precision (complex128 reference; aer_mps certified only at tolerances ≥ $10^{-9}$) | OK | `evaluator.py:477-479` |
| Evaluator `dropped_total` = max over groups | OK | `evaluator.py:403` |
| Simulator: program-order lowering, standard-gate-only cache | OK for the cache; ISSUE: gates are dispatched by name only (N6) | `sparse_sim.py:237`, `:263`; `logical.py:65` |
| `synthesize`: error_bound_sum vs error_measured_sum; global phase of words | OK | `cliffordt.py:86-125` |
| T totals: $T_{\rm total}=T_{\rm fixed}+\sum_rT_r(\varepsilon)$ | OK | `cliffordt.py:128-145`; e.g. UB: $312+384=696$ at $\varepsilon=10^{-6}$ |
| Paulo comparison like-for-like | NOTE (how to present it: N3) | `scripts/m1_results.py:111-131` |
| Outer-electric row, synthesised verdicts `writes_outer` | NOTE (correct evaluator behaviour; how to present: N2) | `results/twelve/UE.json` `extra.outer_electric_row` |
| No hard-coded expected numbers | NOTE (one hard-coded count: N7) | `scripts/m1_results.py:86` |
| No silent exception swallowing | OK | `evaluator.py:369` turns any `ValueError` from translation into a rejected verdict (`disallowed_gate`) with its message (strict, not silent); `m1_results.py:53` records the qasm3 export error |
| Seeds fixed and recorded | OK | `SEEDS` in `m1_results.py:31`, stored in every JSON |
| Tests use the production path | OK | M1-E1/B*/S1/T1/P1 call `build_*`, `synthesize`, `evaluate` — the same functions the script uses; the targets come from `exact/operators.target` (route A, cross-checked with route B in M0) |
| Provenance (commit, parameters, seed) | ISSUE (NON-BLOCKING, must fix before Report 1: N1) | all three JSONs: `git_commit b6d5f50`, `git_dirty true` |

## Arguments behind the main OK items

**1. The `mcrx` replacement is exact and $h$ is provably clean.** Qiskit's `rccx` (relative-phase Toffoli, Maslov arXiv:1508.03273) acts as
$$\mathrm{RCCX}|a,b,c\rangle=\begin{cases}i\,|1,1,1\rangle & (a,b,c)=(1,1,0)\\ -i\,|1,1,0\rangle&(1,1,1)\\ -|1,0,1\rangle&(1,0,1)\\ |a,b,c\rangle&\text{otherwise,}\end{cases}$$
so it is Hermitian and its own inverse. With $c=h=0$ on entry: if $ab\ne11$, $h$ stays 0 and no phase is applied, so the controlled rotation does nothing. If $ab=11$, $h\to i|1\rangle$, then $R_x(\theta)$ acts on `side`, then $h\to(-i)(i)|0\rangle=|0\rangle$. The net operator is $|11\rangle\langle11|\otimes R_x(\theta)+(1-|11\rangle\langle11|)\otimes 1$, the same as `mcrx`, with no relative phase left. This needs (i) $h=0$ on entry and (ii) the controls unchanged between the two `rccx`. (ii) holds: `side` $=d_{11}$ differs from $w_6,g_0,g_2$ (`:186-190`), and in `cond_h` the target $x$ differs from $j_x,j_y$ (`_VERTEX_SPEC`, `:51-52`). Each use of $h$ restores it exactly. $h$ starts at $|0\rangle$, so by induction it is clean before and after every block. Checked numerically above ($1.1\cdot10^{-16}$, zero leak), and the evaluator reports `dirty_ancilla` $=0$ for UB and the step.

**2. The max-over-groups `dropped_total` is rigorous** (`evaluator.py:403`, prompts/005 §2). The circuit never writes the outer register (`writes_outer` is rejected), so the pruned output is $U'\Psi=(U+E)\Psi$ with $E=\sum_o|o\rangle\langle o|\otimes E_{r(o)}$, block-diagonal in the outer pattern $o$. Write $\Psi c=\sum_o|o\rangle\otimes P_oc$, where $\Psi$ is an isometry, so $\sum_o\|P_oc\|^2=\|c\|^2$. Then
$$\|E\Psi c\|^2=\sum_o\|E_{r(o)}P_oc\|^2\le\max_r\|E_r\|_2^2\sum_o\|P_oc\|^2=\max_r\|E_r\|_2^2\,\|c\|^2 .$$
Each group's Frobenius bound $t_r=\sqrt{\sum_cd_c^2}\ge\|E_r\|_F\ge\|E_r\|_2$, and each $d_c$ dominates the column error by telescoping (each prune removes a vector whose norm is recorded, and later gates are unitary). Hence $\|E\Psi\|_2\le\max_rt_r$. Block error, leak and span leak are all computed from the same pruned columns, so one $+\max_rt_r$ term bounds the true $\|(U-e^{i\varphi}T)\Psi\|_2$. The cap $10^{-2}\,\mathrm{tol\_err}$ only keeps the simulator's share of the error small. In the shipped results $\max_rt_r\le9.2\cdot10^{-12}$ for every verdict (step, $\varepsilon=10^{-6}$), against caps of at least $10^{-12}$ (exact angles, measured $\le1.5\cdot10^{-13}$) and $10^{-7}$.

**3. `synthesize` handles global phases correctly** (`cliffordt.py:86-125`). It acts on the level-0 lowered circuit, in which every `rz` is an *uncontrolled* single-qubit gate. Each word equals $e^{i\phi_r}R_z(\theta_r)+\Delta_r$ with $\|\Delta_r\|\le\varepsilon$. Dropping $W$ and the $\phi_r$ therefore changes only the global phase of the whole circuit, which the evaluator absorbs into its single $\varphi$, and the triangle inequality gives $\|U_{\rm synth}-e^{i\Phi}U\|\le N_{\rm rot}\varepsilon$. `error_bound_sum` $=N_{\rm rot}\varepsilon$ is the bound behind `synth_tolerances`; `error_measured_sum` $=\sum_r\min_\phi\|W_r-e^{i\phi}R_z(\theta_r)\|$ is a tighter, measured triangle bound ($0.22$–$0.42\times$ the bound). The verdict uses the safe one.

**4. Program-order lowering and the cache** (`sparse_sim.py:179-275`, `logical.py:17-84`). Each standard gate is translated on its own at level 0 and spliced back in place. The DAG is the same as a whole-circuit level-0 transpile, so CX, T, $N_{\rm rot}$ and depth are unchanged (the level-0 basis translator is gate-local). The cache key includes class, name, float parameters, qubit count and control state, and custom gates are never cached. Open-control gates get distinct names (`cx_o0`, `ccz_o2`; checked), so they cannot collide with `cx`/`ccz`. Any topological order is exact; `_schedule` respects per-qubit dependencies. The remaining hole is the name dispatch, N6.

## Issues

### N1 — Results provenance points at a dirty tree (NON-BLOCKING; required before Report 1 / tag)
`results/twelve/{UE,UB,step}.json` → `provenance.git_commit = "b6d5f50"`, `git_dirty = true`. The producing code (`scripts/m1_results.py`, the prompts/005 evaluator) only exists from `7a54eaa`. Rule: every number that leaves the project must trace to a commit, a command and its parameters. Fix: re-run `PYTHONPATH=src python scripts/m1_results.py` on a clean tree at the commit that will be tagged `milestone-1`. Reports/tests/021 shows the output is bit-identical, so only provenance changes. Commit the regenerated files and render Report 1 from them.

### N2 — Outer-electric-row synthesised verdicts (`writes_outer`): behaviour correct, storage and presentation misleading (NON-BLOCKING)
`writes_outer` is the right verdict for this evaluator. A Clifford+T word for $R_z$ contains $H$, which does not commute with $Z$ on the outer qubit, and the encoding treats the outer register as read-only controls (Digonto 2026-11-04). The approximate circuit does act on the outer links. That is physically legitimate (it is those links' own electric evolution), but this evaluator cannot verify it. Its error is still bounded, because the 8 outer words act on qubits that no other gate in that row touches:
$$\big\|U^{\rm synth}_{\rm row}-e^{i\Phi}U_{\rm row}\big\|_2\le(4+8)\,\varepsilon=12\,\varepsilon$$
(triangle inequality over the 12 single-qubit words, METHODS §6 synthesised rule). Problems with how the result is stored: the JSON records `ok=false`, `op_norm_error=Infinity`, `gauss_residual=NaN`, and also `certified=true` (`_early` default). A renderer could show this as a failure, or as a certified one.
Suggested fix: store `status: "not_evaluable"`, `reason: "writes_outer (Clifford+T words put H on outer qubits)"`, `bound: n_rot*eps` and no `ok`/`certified` fields for these four rows. In `_early`, set `certified=False` for every non-simulated verdict.
Report 1: show the outer row as a separate line (METHODS §2: outer phases commute with everything and are excluded from the main counts). Columns: exact-angle verdict (ok, $3.8\cdot10^{-15}$, 128 blocks) | $N_{\rm rot}=8$ extra | $T(\varepsilon)$ = row total − inner total (528−176 = 352, 768−256 = 512, 984−328 = 656, 1248−416 = 832) | synthesised: "not evaluable by the outer-read-only evaluator; bound $12\varepsilon$ by construction". Do not mark these rows as verified.

### N3 — Paulo comparison: what is like-for-like (NON-BLOCKING; presentation)
`UB.json` → `extra.paulo_comparison`. Facts:
- Paulo's file is his notebook circuit at $\beta=1$ ($dt=g=1$), compiled by Qiskit's Clifford+T pass manager (level 3, seed 12345) with `rz_synthesis_error` $=10^{-6}$ **per rotation**, 14 rotations ⇒ unitary error budget $14\cdot10^{-6}$. Measured: block $2.9\cdot10^{-6}$ + leak $7.9\cdot10^{-6}$.
- Ours, `build_UB(1.0)`: same skeleton except the two `mcrx` ⇒ 6 rotations, $T_{\rm fixed}=312$ (Paulo logical: 14 rotations, $T_{\rm fixed}=296$), 34 qubits each, CX 294 each.

Like-for-like rows (same $\beta=1$, same per-rotation $\varepsilon=10^{-6}$, same pass manager and seed, both from the macro-level circuit; my run): **ours 662 T vs Paulo 1162 T, CX 294 vs 294**. With pygridsynth per rotation (METHODS §7 definition): ours $T_{\rm total}=312+372=684$. The JSON has no pygridsynth total for Paulo's logical circuit at $\beta=1$; the estimate is $296+14\times\sim62\approx1.16\cdot10^3$, and the exact number should be added. All of the saving comes from the scratch-qubit replacement of `mcrx` ($14\to6$ rotations at a cost of $+16$ fixed T). At the same per-rotation $\varepsilon$, our total error budget is smaller ($6\varepsilon$ vs $14\varepsilon$), so the comparison does not favour us.
Do not put Paulo's 1162 next to our nominal-angle $T_{\rm total}(\beta=0.61)=696$ without saying the angles differ (at $10^{-6}$ the angle effect is small: 684 vs 696). Do not compare against `t_qiskit` of Paulo's *lowered* circuit (1096; STATUS known issue).
Suggested fix: add `ct_compile(paulo_logical(1.0), 1e-6)` (macro level) and `t_table(paulo_logical(1.0), (1e-6,))` to the JSON, so that every number in the Report-1 comparison table is computed rather than copied from his metadata.

### N4 — `import_map("lean22"/"lean22_v2")`: the angles are right, but the step order is the opposite of ours (NON-BLOCKING for M1; fix before M2 seeds)
`encodings/twelve.py:196-200` returns `kind: "step"` with `alpha_P = 2β`, `electric_p = -0.75α`. The angles match su2qc-trotter: `physics.alpha_of = 2dt/(g_sg_ta)` ⇒ $\alpha_P=2\beta$; `trotter.electric_angle` $=\tfrac32g^2dt/4=\tfrac34\alpha$ applied as `rz(-φ)` $=e^{i\varphi/2}$`p(-φ)`, a global phase away. The data layout is also the same (`qmp/qm/qj` = $3l,3l+1,3l+2$; `LINK_CODE` = 000, 100(−−), 101(−+), 110(+−), 111(++), the same codes as Paulo Eq. 31, only listed in a different local order). **However**, su2qc-trotter's step appends the electric phases *after* the plaquette circuit (`su2trotter/trotter.py:48-58`, docstring "magnetic first, then electric, i.e. U = U_E U_B"; `designs/lean22_v2.py:332-345` `add_electric(build_plaquette(...))`). Its operator is therefore $U_E(\alpha)U_B(\beta)$, not our $U_1=U_B(\beta)U_E(\alpha)$ (METHODS §2). Imported as a `step` seed, it would fail verification with an error of commutator size (0.5–1.7, reports/tests/019). The evaluator would catch this, so it is not silent, but the seed would be wasted and the mismatch could be mistaken for a basis or sign problem. su2qc-trotter's sign/gauge convention for $|mm'\rangle$ has also not been checked against $V_P$.
Suggested fix: import only the plaquette part (`build_plaquette(α_P)` ⇒ `kind: "UB"`) and prepend our `build_UE(α)`. Alternatively, record `"source_step_order": "U_E U_B"` and reverse the order. Add an acceptance-style check that the imported plaquette verifies against `target("UB", β)` before M2 uses it.

### N5 — `paulo_circuit(with_outer=True)` doubles the global phase (NON-BLOCKING)
`circuits/twelve.py:258-259`: `QuantumCircuit(..., global_phase=src.global_phase)` followed by `compose(src, ...)`, which adds `src.global_phase` again (measured $2.13\cdot10^{-14}\to4.26\cdot10^{-14}$ rad). Physically irrelevant (one global phase is allowed, and the value is at round-off level), but wrong if the circuit is ever controlled or its phase compared. Fix: drop the `global_phase=` argument. `build_step` (`:224`) uses the same pattern (`copy_empty_like` keeps `ub.global_phase`, then `compose(ub)` adds it). It is harmless today because `build_UB(...).global_phase == 0`; `QuantumCircuit(*ub.qregs, name="step")` would avoid the latent doubling.

### N6 — Simulator and metrics recognise gates by name only (NON-BLOCKING for M1; **BLOCKING for the M2 loop**)
`sparse_sim.py:237` and `:263` (`if name in SIM_BASIS` → `payload = params`, standard semantics for non-branching names), `logical.py:65` (`if op.name in LOGICAL_BASIS: out.append(op)`), and therefore `synthesize` and `logical_metrics` too. Any instruction whose *name* is in the basis is simulated and counted as the standard gate, whatever its definition. Demonstration: a custom one-qubit gate with content $X$ and `name="t"` is simulated as $T$ (output $|0\rangle$ instead of $|1\rangle$) and counted as 1 T. This is the same class of bug as the cache-key collision fixed in step 1.3 (reports/tests/017). No M1 circuit is affected (all instructions are instances of Qiskit's standard classes; checked for UE, UE+outer, UB, both steps, Paulo's QPY and a synthesised step). In the M2 loop, however, programs come from LLM proposers, and a renamed custom gate would be silently mis-simulated and under-counted.
Fix: in both places, accept a basis name only if `isinstance(op, type(get_standard_gate_name_mapping()[name]))` (with the singleton check already in `decomposition_cache_key`). Otherwise inline `op.definition`, or reject with `disallowed_gate`. Unit test: the renamed-$X$ gate above must give output $|1\rangle$ (or be rejected) and must not count as a T.

### N7 — One hard-coded count in the results script (NON-BLOCKING)
`scripts/m1_results.py:86` writes `"n_inner_codes": 625` as a literal. Use `len(enc.inner_codes())`. The prose note in `encodings/twelve.py:195` ("294 CX, 1162 T") is descriptive text, not used in any computation; it could be read from `_metadata.json`. The Paulo tolerance `2e-5` (`m1_results.py:117`) is the locked M1-P1 tolerance from prompts/004 §table, not an expected answer; acceptable. For the record, `synth_tolerances(14, 1e-6)` would give $1.4\cdot10^{-5}$, and the measured $1.08\cdot10^{-5}$ passes that too.

### N8 — `--out` must be inside the repo (NON-BLOCKING; already reported in reports/tests/021 obs. 1)
`scripts/m1_results.py:48,52` call `qpath.relative_to(ROOT)` without `.resolve()` or a fallback.

## Not issues (checked, recorded so they need not be re-checked)
- `is_clifford_t_angle` tolerance $10^{-9}$ in `synthesize`: an angle within $10^{-9}$ of $k\pi/4$ gets an exact word and is not counted in $N_{\rm rot}$. The resulting deviation ($\le5\cdot10^{-10}$ per such gate) is still measured by the synthesised-circuit verdict and covered by its $+10^{-9}$ slack. No M1 angle is near a multiple of $\pi/4$.
- `evaluator.py:369` (`except ValueError` → `disallowed_gate`) rejects; it never accepts. Not silent.
- Order 2 has $N_{\rm rot}=14$ (two un-merged $U_E(\alpha/2)$ layers). That is correct for a single step. When steps are repeated, the adjacent half-layers merge, which Report 1 may mention.
- The UE synthesised verdicts show leak and Gauss residuals at the $\varepsilon$ level (e.g. Gauss $6.8\cdot10^{-6}$ at $\varepsilon=10^{-4}$). This is expected: an approximate $R_z$ on $q_j$ flips $j$ with amplitude $O(\varepsilon)$, which breaks Gauss's law to first order. It is within the prompts/003 budget.

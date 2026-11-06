# Tester report 028 — M2 steps 2.L2 + 2.L3 (Lean generic theorems and counts)

- Date: 2026-11-05; git: `f5ff810` + uncommitted Lean work (`lean/`, `src/su2plaq/lean/`, `tests/unit/test_lean_project_unit.py`); acceptance-v6
- Plan in force: `prompts/006-lean-formal-verification-m2-addendum.md` (§3 statements, §6 steps 2.L2/2.L3, §9 do-not-retry). Related: reports/tests/025 (2.L1).
- Mode: step. Out of scope (other tester, step 2.3): `src/su2plaq/compress/*`, `evaluator.py states=`.
- Raw numbers: `results/tester_m2_steps2l2_2l3_axioms.json`, `results/tester_m2_steps2l2_2l3_counts.json`; scratch scripts `scratch/t2l23_rccx.py`, `scratch/t2l23_counts.py`, `scratch/t2l23_axioms.py`.

## Commands
```
graphify update . ; graphify query ...                      # orientation
mv lean/.lake/build <scratchpad>/old_build && lake build     # clean build, timed, RSS sampled once per second (ps)
pytest tests/acceptance/m2/test_lean_formal.py::test_lean_generic_theorems_standard_axioms \
       tests/acceptance/m2/test_lean_structure.py::test_lean_counts_kernel_checked \
       tests/acceptance/m2/test_lean_formal.py::test_lean_project_present_and_builds_checker -v
pytest tests/unit/test_lean_project_unit.py -q          (x2, serial)
pytest -n auto tests/unit <the two Lean acceptance tests> -q   (x3, concurrent with the print_axioms processes)
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 ; pytest -m "not slow" tests/acceptance/m2
python scratch/t2l23_rccx.py ; python scratch/t2l23_counts.py ; python scratch/t2l23_axioms.py
diff <(git show 30f84af1:.../Compress2x4/{Bits,Peephole}.lean | sed s/Compress2x4/Su2Plaq/g) lean/Su2Plaq/{Bits,Peephole}.lean   (in su2qc-skqd)
```

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `test_lean_generic_theorems_standard_axioms` | PASS | PASS | – | PASS |
| `test_lean_counts_kernel_checked` | PASS | PASS | – | PASS |
| `test_lean_project_present_and_builds_checker` (regression of 2.L1) | PASS | PASS | – | PASS |
| `tests/unit/test_lean_project_unit.py`, serial x2 | green | 9 passed, 9 passed (23.9 s each) | – | PASS |
| unit suite + the 2 Lean acceptance tests, `-n auto`, x3 | green, no AxiomCheck leftovers | 237 passed (85 s, 71 s, 73 s); no `lean/AxiomCheck*` file remains | – | PASS (AxiomCheck flake of 025-N1 gone) |
| clean `lake build` (`.lake/build` moved away) | rc 0, no Mathlib compile | rc 0, 9089 jobs, ~379 s wall (20:00:03 -> 20:06:22); Counts.lean 365 s, every other `Su2Plaq.*` module 5-13 s | <= 1800 s | PASS |
| peak RSS during `Counts.lean` | builder said ~12 GB | 15.3 GB (15 342 356 kB; includes ~6.9 GB of mmapped Mathlib oleans that every Mathlib-importing module shows, so Counts itself adds ~8.4 GB) | – | note (above builder's figure) |
| `lake build` log | no `sorry`, no errors | 0 `sorry`, 0 errors; linter warnings only (10 unused simp args, 3 deprecated `if_neg`, 1 unused tactic, 1 "never executed", Mathlib "add `module`") | – | PASS |
| collect-only `tests/acceptance` | 102 clean | 102 collected, clean | exact | PASS |
| `check_lock.py`, `acceptance-check` | OK | "LOCK OK", "PASS: matches acceptance-v6" | – | PASS |
| m0 + m1 acceptance, not slow (regression) | all green | 54 passed (145 s) | – | PASS |
| `#print axioms` x 34 (26 generic + 8 counts) | subset of {propext, Classical.choice, Quot.sound} | 26 generic: exactly those three; 8 counts: `propext` only; no `sorryAx`, no `Lean.ofReduceBool`, no `native_decide` axiom | exact | PASS |
| grep `sorry|native_decide|admit|axiom|unsafe|extern|opaque|implemented_by|csimp|macro|elab|#eval` under `lean/Su2Plaq*` | none | none (only `set_option maxRecDepth 100000 / maxHeartbeats 0` in `Counts.lean`) | – | PASS |
| `decide +kernel` vs plain `decide` | no extra axioms | counts theorems (`decide +kernel`) show only `propext`, the same as `dont_care_codes` (plain `decide`) | exact | PASS |
| Qiskit `RCCXGate` vs Lean `RCCX = mono rccxPerm rccxPhase` (16x16, little-endian a+2b+4t+8h) | equal | max abs diff 0.0; Qiskit matrix Hermitian (diff 0.0) and unitary, as Lean proves | 1e-12 | PASS |
| Qiskit `CRXGate(θ)` (control h, target t) vs Lean `ctrl (crxW θ)`, 6 angles | equal | max diff 0 | 1e-12 | PASS |
| Qiskit `RXGate(θ).control(2)` vs Lean `ccrx θ` (8x8) | equal | max diff 1.7e-16 | 1e-12 | PASS |
| Qiskit `RCCX·CRX·RCCX` vs Lean `RCCX·ctrl crxW·RCCX` vs `ccrx ⊗ |0><0|` on h=0 columns | equal | 0 (the two products agree on all 16 columns, not only h=0) | 1e-12 | PASS |
| Lean count definitions transcribed to Python: 433 / 256 / 95 / 2 / 17362 / 3153 / 17 / 3471 | those values | 433, 256, 95, 2, 17362, 3153, 17, 4^6-5^4 = 3471 | exact | PASS |
| same numbers from `refs/su2_plaquette_encodings.py` (`n_intertwiners`, `count_states`, `count_link_label_configs`) | 433 / 2 / (256, 95) | 433 / 2 / (256, 95); corner pairs (b,l)(b,r)(r,t)(t,l) = Lean corners | exact | PASS |
| same from `su2plaq.exact.physical` (`counts`, `s_o_dims`) | 433, 2, 256, 95, 17362, 3153, 17 | identical | exact | PASS |
| support set of the Lean model (`innerSumM >= 1`) vs project support of `s_o_dims > 0` after a per-link sign convention for the outer m | equal | equal, 3153/3153 (found by searching the 2^8 sign flips; best mask overlaps all 3153) | exact | PASS |
| vendored `Bits.lean`, `Peephole.lean` vs sibling commit `30f84af1` with `Compress2x4 -> Su2Plaq` | only namespace/header changes | headers cite `su2qc-skqd`, commit 30f84af1, "only change: namespace"; diffs are: new header, `import` line moved to top, one cross-reference `Sanity.lean -> Structure/Commute.lean`, the trailing `#print axioms` lines removed. Theorem bodies byte-identical | – | PASS |
| m2 Lean/others later steps | PENDING, not failure | 6 Lean tests PENDING (`NotImplementedError`: certify, structure, general_circuit, general_program_path); the other 21 m2 failures are `test_compress_machinery.py` (step 2.3+, other tester) | – | pending |

## Statement review (trust core): Lean statement vs prompts/006 §3 and the evaluator
All 26 + 8 names exist with the locked signature; none is vacuous, `True`-valued or has contradictory hypotheses (each is either instantiated by a later theorem — `sandwich` in `rccx_crx_rccx_eq_ccrx` — or trivially satisfiable, e.g. zero operators / identity isometry).
- `verdict_sound` proves $\|U\Phi-c\Phi V\|\le b+d+l+s$ from $(U+E_p)\Phi=\Phi A+S+X$, $\Phi$ isometry, $\|A-cV\|\le b$, $\|E_p\|\le d$, $\|X\|\le l$, $\|S\|\le s$. The orthogonality hypotheses and $|c|=1$ are unused (confirmed in the proof: only `opNorm_comp_le`, isometry, triangle inequality) — they are harmless extra assumptions; the conclusion is exactly the sum bound. The evaluator (`evaluator.py` lines 14-19) defines `op_norm_error = block_error + dropped_total + leak_amplitude` = $b+d+l$, and states that the code-space leak $s$ is controlled separately by the Gauss check ($\|s\|\le 4\,\texttt{gauss\_residual}$). So the full bound the evaluator relies on is $b+d+l+s$ with $s\le 4\,\texttt{gauss}$, which is exactly what `verdict_sound` + `span_leak_le_four_gauss` give.
- `span_leak_le_four_gauss` is stated for ONE vector $s$ with the spectral-gap hypothesis `(3/4)‖s‖² ≤ ∑‖G_i s‖²` (declared, not proved — as planned). `verdict_sound` needs the operator norm $\|S\|$. The glue "per-state $\Rightarrow$ operator" is not in Lean; it is the known audit-002 R1 caveat (coherent span leak up to $\sqrt{433}$ larger), unchanged by this step.
- `opNorm_le_of_blockdiag`: hypotheses (complete orthogonal idempotent family, block-diagonal $T$) are the correct ones for $\|T\|\le\max_o\|P_oTP_o\|$.
- `synth_bound`: $\|\prod(c_iR_i+\Delta_i)-(\prod c_i)\prod R_i\|\le\sum\|\Delta_i\|$ needs the extra hypothesis $\|W_i\|\le1$ (planned in §3); fine for unitaries/synthesised words.
- `sandwich`, `mono_*`, `rccx_crx_rccx_eq_ccrx`: as in §3; the numerical match to Qiskit above shows the Lean definitions are the real gates. `h_z_h`, `h_rz_h`: $Rz=\mathrm{diag}(e^{-i\theta/2},e^{i\theta/2})$, $Rx=\begin{pmatrix}\cos&-i\sin\\-i\sin&\cos\end{pmatrix}$, correct conventions.
- Vendored CX theorems: `cx_comm_cx` hypotheses ($c\ne t'$, $c'\ne t$) are the correct condition; `cx_comm_diagonal_of_indep` requires the phase to ignore the target bit; both correct.

## Notes (non-blocking; none is a failure of 2.L2/2.L3)
- N1 (counts model, **worth the planner's attention**): the Lean `innerSumM`/`maxPerOuterM` is NOT the number of physical states touching an outer pattern, nor $\dim S_o$. Compared pattern by pattern with `su2plaq.exact.physical` (after a per-link sign mask for the m-label): the support set is identical (3153) and the maximum is identical (17), but for 1952 of the 3153 supported patterns Lean's count is strictly larger than the true number of states with a component there (always `>=`, never smaller). Histograms: Lean `{2:1001, 3:392, 4:968, 5:280, 8:224, 9:32, 16:240, 17:16}` vs project states-touching `{1:976, 2:1073, 3:392, 4:320, 5:280, 8:64, 9:32, 17:16}` (project $\dim S_o$ = same as states-touching here). So `card_supported_outer = 3153` is a correct, independently confirmed statement (set equality); `max_states_per_outer = 17` is correct numerically but is proved for a model that over-counts elsewhere (it is an upper bound that happens to be attained). Guess: the "refined corner rule" only removes the $m_c=m_d$ states in the inner-pair $(0,0)$ case; the analogous restriction for inner pair $(\tfrac12,\tfrac12)$ (J=0 forces opposite m, J=1 allows equal m) is not modelled. The theorem is faithful to its name and to the locked tests; nothing needs changing unless the name `max_states_per_outer` is later quoted as a dimension of $S_o$.
- N2: Counts.lean peak RSS is 15.3 GB (not ~12 GB) and 365 s; the full clean build is ~6.3 min. Machines with < 16 GB RAM will fail this module.
- N3: the Lean "consider adding `module`" warning and the linter warnings above are harmless.
- N4: the clean build is fast only because `.lake/packages` (Mathlib oleans) is already present (see 025-N4).
- N5: the 8 count theorems depend on `propext` only; `decide +kernel` (kernel-evaluated `Decidable` instance) adds nothing beyond a plain `decide`.

## Verdict
PASS for steps 2.L2 and 2.L3: 2/2 named acceptance tests + 2.L1 regression green, Lean unit file 9/9 twice and the full unit suite 237/237 three times under `-n auto` (AxiomCheck flake gone), clean build green in ~379 s, collect 102 clean, lock OK, m0+m1 54/54, 34/34 theorems with standard axioms only, RCCX/CRX/CCRX equal to Qiskit to 0 / 1.7e-16, count values reproduced from three independent sources, vendored files identical to the sibling. 0 new failures vs. report 025; 6 Lean acceptance tests remain PENDING for steps 2.L4-2.L7.

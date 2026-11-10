# Audit 100 — M3 milestone gate, spin-network encoding (desktop track S)

- Date: 2026-11-06 · Auditor: Claude Opus 5.5 (high)
- Git commit: `0d76bcb` (branch `m3-spin-network`, working tree clean); commit range audited `a2ec571..0d76bcb`
- Prompt in force: `prompts/100-spinnet-m3-plan.md` (acceptance-v7); conventions `docs/METHODS.md`, `docs/METHODS-spinnet.md`, prompts/001 §1, prompts/002–006; binding decisions `~/Projects/su2qc-desktop-package/START_HERE.md` §2
- Related: `reports/tests/100`–`106`, `reports/audits/001`–`003`, `reports/research/100`
- Auditor scripts (scratchpad, not committed; logic summarised in §3): `audit_paulo_gauge.py`, `audit_center.py`, `audit_routeA.py`, `audit_twelve_center.py`, `audit_spanleak.py`, run with `PYTHONPATH=src taskset -c 0-9 python <script>` in `su2qc-coding`, single-threaded BLAS, peak RSS < 1 GB.

## Verdict: PASS WITH NOTES

No blocking issue. The encoding, the target, the general circuit, the evaluator path, counts, tolerances and provenance are correct. Four non-blocking notes; two of them (N1, N2) are wording/physics statements that must be fixed before Report 3 is written.

## 1. Checklist

| Item | Status | Evidence (file:line) |
|---|---|---|
| Codec: 12 link bits ($j=\tfrac12\to1$), 4 corner bits ($J_c=1\to1$), outer at $8+k$ | OK | `src/su2plaq/encodings/spinnet.py:49-61`; Lean `corner_jbit_injective`, `corner_bit_needs_four_half` (`lean/Su2Plaq/SpinNet/Counts.lean:67-70`); M3-C1 checks every bit of all 433 codes |
| 433 states = distinct unit codes; label order = route B = route A labels | OK | `encodings/spinnet.py:64-70,104-106` (asserted at construction) |
| Fallback decode of inadmissible codes (fixed in 3.1) | OK | `encodings/spinnet.py:160-185`: $G^z_c$ eigenvalue $\pm\tfrac12$ per end ($m_L=-g$ out, $m_R=+g$ in); see §2.1 — cannot fool the evaluator |
| Target = route B + `gauge_align` (audit 001 N5) | OK | `encodings/spinnet.py:123-131,224-246`; M3-K1 compares with $D^\dagger V_AD$ at 3 angle pairs |
| Sign gauge on Paulo's file | OK (legitimate, β-independent; wording N1/N2) | `tests/acceptance/m3/test_spinnet_external.py:58-64` pins the gauge to exactly one $-1$ per bright pair, dark $+1$; auditor re-check at 5 values of $\alpha_P$ (§2.2) |
| Paulo Eq. 16 normalisation, $\alpha_P=2\beta$ | OK | `scripts/m3_results.py:38`, `circuits/spinnet.py:66`; auditor: $\beta=\alpha_P$ rejected (residual $\ge0.099$) at 5 angles, $\beta=\alpha_P/2$ matched ($\le3.0\cdot10^{-15}$) |
| $U_E$ phase $e^{-3i\alpha/4}$ per $j=\tfrac12$ link | OK | `circuits/spinnet.py:17,27-29` (`p(-3α/4)`, `p(λ)=diag(1,e^{iλ})`); M3-E1 tests the amplitude of code `0b0001` |
| Step order (electric layer first), order-2 symmetric, outer electric row separate | OK | `circuits/spinnet.py:51-64`; target `encodings/spinnet.py:240-245` ($U_BU_E$, $U_E^{1/2}U_BU_E^{1/2}$); outer row `build_UE(..., include_outer_electric=True)` only |
| Walk: $e^{-i\beta kX}\to R_z(2\beta k)$ after $H$; frame; flags; angles solved, not typed | OK | `spinnet/walk.py:22-49,82-96,103-147`; Qiskit $R_z(\theta)=e^{-i\theta Z/2}$ ⇒ $\theta(y)=2\beta k(y)$ correct; frame sends $X^{\otimes4}\to X_0$ (`frame_maps_flip`) |
| Coupling snapping to half-integers | OK | `walk.py:42-45` (raise if off $>10^{-12}$; measured rounding $\sim10^{-15}$) |
| Uncompute: RCCX self-inverse, RC3X not | OK | `walk.py:99-100`; auditor: RCCX Hermitian and $R^2=\mathbb 1$ exactly, $\lVert RC3X^2-\mathbb 1\rVert_{\max}=2.0$ |
| Qubit order / endianness | OK | little-endian codes; Paulo file header "q[0] least significant"; `paulo.py:20-21` map (corner order LL, LR, UR, UL = $c_0..c_3$ matches `CORNER_LINKS`) |
| Counts and T rule $T_{\rm fixed}+\sum_rT_r(\varepsilon)$ (pygridsynth), Qiskit CT cross-check | OK | `scripts/m3_results.py:86-100,113-123`; M3-T1 asserts `t_total = t_fixed + t_rot_pygridsynth`, Ross–Selinger band, 10 % vs Qiskit |
| Gates disguised under standard names; whole-circuit transpile; cache collisions | OK | only `cx,h,x,t,tdg,p,rz,rccx` + expanded RC3X definitions; laptop evaluator follows gate definitions (audit 003 N6 fix); program-order synthesis (M1 fix); RC3X never cached as composite (`build_walk(expand=True)` is the only rc3x path, `circuits/spinnet.py:80`) |
| Pruning accounting / prune cap | OK | e.g. `UB.json` exact verdict `dropped_total` $6.7\cdot10^{-15}$ inside `op_norm_error`, far below cap $10^{-12}$ |
| Tolerances (exact $10^{-10}$; synth $N_{\rm rot}\varepsilon+10^{-9}$; leak as amplitude) | OK (see N3) | `test_spinnet_metrics.py:54-59`; results rows all `ok`, `certified` |
| Normalisation, real/unitary targets | OK | targets from `eigh` of real symmetric $H_B$, $K$ (`encodings/spinnet.py:206-219`) |
| Precision float64/complex128 | OK | all paths numpy float64/complex128; no GPU / float32 |
| Randomness / seeds | OK | seeds in `provenance.seeds` (`transpiler_logical 20261104`, CT 12345); M3-C1 sample seed 20261104 |
| Tests exercise production code (no duplicate implementation, no hard-coded answers) | OK | acceptance tests call `build_UB`, `build_step`, `paulo_circuit`, `evaluate`, `align_inner_block`; angles from `solve_angles` at build time (`circuits/spinnet.py:42-48`) |
| Lean: kernel-checked vs numerical | OK (caveats recorded) | no `sorry`/`native_decide` in `lean/Su2Plaq/SpinNet/`; METHODS-spinnet §7(a)–(e) and §8.7 state the limits; Lean model ↔ Python skeleton tie is outside the test suite (N4) |
| Provenance | OK | `results/spinnet/{UE,UB,step}.json`: `git_commit 7a716fc`, `git_dirty false`; `git diff 7a716fc HEAD -- src scripts lean tests refs` empty |
| File ownership | OK | `git diff --name-status a2ec571..HEAD`: only additions plus `lean/Su2Plaq.lean` (exactly the two import lines), `tests/acceptance/LOCK.json` (m3 entries + `"m3"`, via `tools/lock.py`), `notes/STATUS.md`; no laptop-owned source touched |

## 2. Findings in detail

### 2.1 Can the evaluator be fooled through the fallback decode? No.
The laptop evaluator (`src/su2plaq/evaluate/evaluator.py:309-330, 381-404`) simulates the 47 inner codes, splits every output into (i) amplitude on physical codes of the same outer pattern (the block $A$), (ii) amplitude with an ancilla bit set or an invalid data code (`Xa`, `Xi` → `leak_amplitude`), (iii) amplitude on a valid inner code that is inadmissible for that outer pattern (span leak $S$). Only (i)+(iii) reach `decode_state`, so its `ValueError` branch is unreachable from the evaluator. For (iii) every fallback vector is a common eigenvector of all $G^z_c$ with eigenvalue $\pm k/2$, $k\ge1$ at some corner; the fallbacks are orthonormal and orthogonal to the physical states, so for any superposition $\sum_{c,a}\|G^a_cs\|^2\ge\tfrac34\|s\|^2$ with no cancellation — the hypothesis of prompts/004's $\|s\|\le4\cdot$`gauss_residual` holds. Outer qubits cannot be written (`writes_outer`), so no amplitude can move between outer patterns. The route-A/B gauge inside `decode_state` does not affect the Gauss check (any combination of physical states has zero residual), so it cannot mask anything either.

### 2.2 Paulo's sign gauge is a legitimate, β-independent basis convention
- The locked test does not accept an arbitrary fitted gauge: it requires exactly 8 minus signs, all on bright codes, never both members of a pair (`test_spinnet_external.py:62`). That is exactly the class $D'$ with $D'KD'=-K$, i.e. $U_B(-\beta)=D'U_B(\beta)D'$. The gauge is applied as a fixed diagonal on the data code, outer-independent (`encodings/spinnet.py:248-251`).
- Auditor check (`audit_paulo_gauge.py`): Paulo's 4 `p` angles rescaled to $\alpha_P\in\{0.1,0.37,0.9,1.7,3.0\}$ (they are $\alpha_P\times(\tfrac14,\tfrac12,1,-2)$). At every $\alpha_P$: `align_inner_block` vs $e^{-i(\alpha_P/2)K}$ gives residual $\le3.0\cdot10^{-15}$ with the **same** minus codes $\{8,\dots,15\}$; vs $e^{-i\alpha_PK}$ residual $0.099$–$0.92$ (rejected); and the file equals $e^{+i(\alpha_P/2)K}=U_B(-\beta)$ in route-B signs with **no** gauge ($\max|M-e^{i\varphi}V|\le3.0\cdot10^{-15}$, leak 0). So: angle-linear in $\alpha_P$, $\alpha_P=2\beta$ confirmed, gauge independent of β.
- The minus codes $\{8..15\}$ are exactly the bright codes with $j_l=\tfrac12$ (bit 3 = left link, file `q[3]`). The gauge is therefore the **local** sign convention $(-1)^{2j_l}$ on one link (see N1). It is a basis convention, not a hidden sign error that tests could catch at $j_{\max}=\tfrac12$: for the fixed codec it cannot be distinguished from an overall sign of $\alpha_P$ in Paulo's file; for real initial states and real observables both give identical expectation values, since $e^{+i\beta H}=(e^{-i\beta H})^*$ for real $H$.
- Our own circuit is pinned to the route-B sign: with its 4 `rz` angles negated it is rejected against $U_B(+\beta)$ (error 1.88) and accepted against $U_B(-\beta)$ ($1.1\cdot10^{-14}$). The general-circuit tests B1/B2/S1 use the ungauged route-B target, so a sign error in `build_UB` would be caught.
- Route A is not a "more physical" reference: Paulo's file against the route-A target $DV_BD$ is also rejected (0.1997), because the route-A/B gauge flips the pair sign on 64 of the 128 bright pair instances depending on the outer pattern (an artefact of the "largest component positive" phase rule for corner singlets, METHODS §5).

### 2.3 Lean
Kernel-checked: counts 47/16/31/8, pair-class counts 16/96/16, 256+177 = 433, the two corner lemmas, `frame_maps_flip`, `flags_correct`, `walk_slots_match`, `walk_table_exact`, `table_lengths` (17 theorems, axioms ⊆ {propext}, reports/tests/105, 106). Numerical only: that `couplingTable` equals $2K$ (Python, snapped), the spectrum assignment 16/96/16/177/16/96/16, RCCX relative-phase cancellation, the Hadamards, the sign convention, the whole gate semantics. METHODS-spinnet §7 and §8.7 say this correctly; Report 3 must copy that wording ("pair-class counts kernel-checked; spectrum identification numerical"; "native certificate pending"). No overclaim found in the committed docs.

## 3. Issues

### N1 (NON-BLOCKING; fix before Report 3) — wrong physics statement: "in the 12-qubit encoding this freedom does not exist"
- Where: `docs/METHODS-spinnet.md:17` (last sentence of the "Sign of β is a gauge" paragraph); `prompts/100-spinnet-m3-plan.md:31` §1.3(ii) "(not a physics check; in M1 it was one)"; also the framing "at $j_{\max}=\tfrac12$ … because $K$ is a matching".
- Why it is wrong: the sign flip of β is generated by the centre element $-\mathbb 1\in SU(2)$ acting on **one** inner link $l$. Since $D^j(-U)=(-1)^{2j}D^j(U)$, the unitary $Z_l=(-1)^{2j_l}$ (diagonal in every electric or spin-network basis) maps $U_l\to-U_l$, hence
  $$Z_l\,\mathrm{Tr}\,U_P\,Z_l=-\mathrm{Tr}\,U_P,\qquad Z_lH_BZ_l=-H_B,\qquad [Z_l,H_E]=[Z_l,G^a_c]=0,$$
  so $U_B(-\beta)=Z_lU_B(\beta)Z_l$ for the single plaquette with static outer links **at every $j_{\max}$**, not only because $K$ is a matching. (Source: $D^j(-\mathbb 1)=(-1)^{2j}\mathbb 1$, standard SU(2) representation theory, e.g. Edmonds, *Angular Momentum in Quantum Mechanics*, Ch. 4; the plaquette is a product of four link operators, each odd under $U_l\to-U_l$.) Measured: $\max|Z_lH_BZ_l+H_B|=0.0$ for each of the 4 inner links, in route B and in route A (`audit_center.py`). In the 12-qubit encoding $Z_l$ is a single Pauli $Z$ on the $j$-qubit of link $l$: `Z(q11)·build_UB(0.61)·Z(q11)` (twelve encoding, link $l$ qubits 9–11) is accepted by the evaluator against $U_B(-0.61)$ with error $2.4\cdot10^{-13}$ and rejected against $U_B(+0.61)$ (1.88) (`audit_twelve_center.py`). So the freedom exists there too; M1-P1's "$-\beta$ rejected" also only pins the codec's sign convention (fixed by Paulo's Eq. 31), it was never a physics check of the sign of the coupling.
- Fix: replace the sentence by: "The sign of β is the centre symmetry $(-1)^{2j_l}$ of one inner link ($Z_lH_BZ_l=-H_B$, any $j_{\max}$); it is a basis-sign convention in every encoding; the 12-qubit codec of Paulo Eq. 31 fixes it, the spin-network codec fixes it by the route-B choice. Paulo's 15-qubit file differs from route B exactly by $(-1)^{2j_l}$ on the left link." Optional cheap test (planner): assert `gauge_minus_codes == [bright codes with bit 3]` and $Z_lH_BZ_l=-H_B$ for each inner link.

### N2 (NON-BLOCKING; Report 3 wording) — how to state Paulo's verdict
- Where: `docs/METHODS-spinnet.md:43,106`; `scripts/m3_results.py:146-149` (`gauge_note`, copied into `results/spinnet/UB.json` `extra.comparison.paulo15.gauge_note`).
- Problem: `gauge_note` calls it "a basis-sign convention of the electric basis" and cites "METHODS-spinnet §1.3", which does not exist (it is prompts/100 §1.3); the sign is a convention of the spin-network code basis (equivalently of link $l$'s $j=\tfrac12$ states).
- Suggested Report 3 sentence: "Paulo's 15-qubit file is exact on all 433 open states (error $9.7\cdot10^{-15}$, leak 0, Gauss $5.4\cdot10^{-16}$, outer bits never read) after the fixed, β-independent sign convention $(-1)^{2j_l}$ on the left link; in route-B signs it equals $U_B(-\beta)=e^{+i\beta H_B}$. At fixed codec this cannot be told apart from an overall sign of $\alpha_P$; it does not change any expectation value of a real observable in a real initial state." Fix the `gauge_note` string at the next clean regeneration (no new numbers needed now).

### N3 (NON-BLOCKING; laptop-owned evaluator, merge note) — span leak $S$ is left out of `op_norm_error`, and the Gauss bound for it is not tight enough to certify two synthesised rows
- Where: `src/su2plaq/evaluate/evaluator.py:432-434` (`err_total = err + dropped_total + leak_amp`; `span_leak = w_code - A2` is only a diagnostic), rule from prompts/004 / METHODS §6.
- Why it matters here: for a basis encoding the code-space vectors are orthonormal unit codes, so $S$ (amplitude on inadmissible valid codes) is **exactly** computable, while the prompts/004 chain only gives $\|S\|\le4\cdot$`gauss_residual`. Auditor's exact $\|S\|_2$ (`audit_spanleak.py`, block-diagonal over outer patterns):

  | synthesised circuit | `op_norm_error` | exact $\|S\|_2$ | sum | $4\cdot$gauss | err $+4\cdot$gauss | tol |
  |---|---|---|---|---|---|---|
  | $U_E$, $\varepsilon=10^{-6}$ | $2.183\cdot10^{-6}$ | $3.15\cdot10^{-7}$ | $2.50\cdot10^{-6}$ | $2.23\cdot10^{-6}$ | $4.41\cdot10^{-6}$ | $4.001\cdot10^{-6}$ |
  | step 1, $\varepsilon=10^{-6}$ | $2.381\cdot10^{-6}$ | $3.15\cdot10^{-7}$ | $2.70\cdot10^{-6}$ | $2.05\cdot10^{-6}$ | $4.43\cdot10^{-6}$ | $8.001\cdot10^{-6}$ |
  | $U_E$, $\varepsilon=10^{-4}$ | $1.255\cdot10^{-4}$ | $1.92\cdot10^{-5}$ | $1.45\cdot10^{-4}$ | $1.36\cdot10^{-4}$ | $2.61\cdot10^{-4}$ | $4.0\cdot10^{-4}$ |

  The true combined error (exact sum) is within budget everywhere, and the a-priori synthesis bound $N_{\rm rot}\varepsilon$ also holds. But (a) the reported `op_norm_error` of synthesised $U_E$/step understates the distance by 13–15 %, and (b) for $U_E$ at $10^{-6}$ the Gauss-based soundness chain (METHODS §11.1(c),(d)) gives $4.41\cdot10^{-6}>$ tol, so the verdict is not self-certifying through that chain. The diagnostic `max_span_leak` (difference of weights) cancels to exactly 0 at $\varepsilon\le10^{-8}$ while Gauss shows $1.2\cdot10^{-8}$, so it cannot be used instead. $U_B$ is unaffected ($S=0$, Gauss $5\cdot10^{-16}$).
- Fix (merge note to the laptop; no M3 change): for `is_basis_encoding` encodings, compute $\|S\|_2$ directly from `Om` rows outside each outer pattern's physical rows and add it to `op_norm_error` (exactly as `leak_amplitude`); keep Gauss as the gauge check. Until then, Report 3 should footnote that synthesised $U_E$/step errors exclude a span-leak term of $3.2\cdot10^{-7}$ at $\varepsilon=10^{-6}$.

### N4 (NON-BLOCKING; test gap) — Lean circuit model is tied to the Python skeleton only outside the suite
- Where: `lean/Su2Plaq/SpinNet/Circuit.lean:59-65` (`flagOps`, `walkOps` hand-written) vs `src/su2plaq/spinnet/walk.py:153-163` (`GENERAL7`). The only fidelity check is the tester's `results/spinnet/tester/lean_vs_python_slots.py` (0 mismatches on 256 codes).
- Failure scenario: an edit of `GENERAL7` that rewires a flag but keeps the same solved angles regenerates identical tables; `walk_table_exact` stays green while it no longer describes the circuit, and Report 3 would call a structure "kernel-checked" that is not the shipped one.
- Fix: a unit test that renders `flagOps`/`walkOps` from `GENERAL7` (or parses them from `Circuit.lean`) and compares step by step; or generate them between the existing `-- BEGIN/END generated` markers.

## 4. Minor observations (no action needed for the gate)
- `next-num reports/audits` proposes `004`; the caller's path `100` follows the desktop-track numbering (100–199, STATUS header). Kept as requested.
- `SpinNet.target('UB', ..., include_outer_electric=True)` silently ignores the flag (`encodings/spinnet.py:235-238`); harmless for the commuting outer row, but a `ValueError` would be cleaner.
- METHODS-spinnet §6 quotes "0.25–0.33 of the budget", §8.4 "0.28–0.55"; §8 is declared authoritative, fine.

## 5. Return
VERDICT: PASS WITH NOTES. Blocking issues: none. Notes N1–N4 above (N1, N2 before Report 3; N3 to merge notes; N4 to the planner/builder as a test).

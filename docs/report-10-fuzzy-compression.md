# Report 10 — Fuzzy encoding: compression of the one-Trotter-step circuit

Date: 2026-11-06 · Branch `m9-fuzzy` (on top of tag `milestone-9`) · Numbers committed in `15a12fa` (the JSON provenance of `compressed_step.json` records `git_commit` `7b0e5d0` with a dirty tree; the round and summary files carry their own entry commits) · Plan: `prompts/302-fuzzy-m10-plan.md` (locked tests `tests/acceptance/m10/`, `acceptance-v11`) · Methods: `docs/METHODS-fuzzy.md` F9 · Previous report: `docs/report-9-fuzzy-general-circuit.md`.

Sources of every number: `results/compress/fuzzy_ub/summary.json`, `results/compress/fuzzy_link/summary.json` (written by `python scripts/m10_round.py report --encoding fuzzy_ub|fuzzy_link`), the round files `results/compress/fuzzy_{ub,link}/round-00r.json`, and the composed step `results/fuzzy/compressed_step.json` (written by `python scripts/m10_round.py best-step`). Tester verification: Tester round 3 (`reports/tests/303`, `b4c5c18`): PASS — second-engine rebuild of fuzzy_ub r03-F1/F2/F3-003 op-norm $\le2.2\times10^{-14}$, counts equal to the archive (best 151 CX / 28 rotations / 118 $T_{\rm fixed}$ / 13 qubits); composed step error $1.7\times10^{-14}$, Gauss $5.9\times10^{-15}$ on 40 seeded inputs, 295 CX / 148 rotations (199 CX / 68 rotations inner-only); all §3 numbers match `summary.json` and `compressed_step.json`; unit tests 486, m0–m2 102, m10 10/10 pass; acceptance lock intact. Rounds 1–2: `reports/tests/302` (PASS).

Terms (first use). **Compression loop**: the Gu-et-al.-style search in which language-model "proposer" agents write circuit-building programs and a deterministic evaluator decides validity and cost (prompts/001 §4). **Unit**: a piece of the step compressed on its own (here two, see §1). **Seed**: the starting circuit of the loop. **Polish**: the evaluator's deterministic clean-up passes (gate cancellation), applied before any proposer runs. **Family**: one circuit architecture, followed across rounds. **Key**: the cost tuple compared lexicographically — CNOT count first, then T count at $\varepsilon=10^{-6}$, then CT-depth, then qubits. **Valid**: exact (op-norm error after one global phase $\le10^{-10}$) on the whole unit block at the nominal angles and at the two alternate angle pairs with an identical gate skeleton (so no angle-specific tricks), all work qubits returned to $|0\rangle$, peak qubits within the cap, evaluation under 300 s. **Lean column**: whether a Lean per-circuit certificate exists; `n_a` = not available (the laptop certificate exporter is specific to the 12-qubit encoding), `not_run` = not attempted for that row.

## 1. What was asked
Compress the M9 fuzzy one-Trotter-step circuit (Report 9) with the existing compression machinery, within this session's limits: one ideation pass with at most 4 active families, at most 3 rounds of at most 4 proposers, hard stop for new agent runs at 5 h 15 min (START_HERE §4).

Plan 302 splits the step into two independently compressed units, because the laptop evaluator cannot score a whole fuzzy step (its physical set has about $10^8$ states, Report 9 §2):
- **`fuzzy_ub`** (kind `UB`): $U_B=e^{+2i\beta\square}$ on the 8 row qubits of the 4 inner links, checked as the full $256\times256$ block; up to 32 work qubits allowed.
- **`fuzzy_link`** (kind `UE`): the merged one-link kinetic block $U_K(\kappa_2)U_E(\alpha)=e^{-i(\frac{\alpha}{2}\mathcal K_1+\kappa_2\mathcal K_2)}$ on 4 qubits, checked as the full $16\times16$ block, no work qubits (so it can be reused on every link). In this unit's specification the second angle slot `spec.beta` carries $\kappa_2$, so the three angle pairs are three independent $(\alpha,\kappa_2)$ points and a valid program works for every ratio $r$.

The step is then **composed** (`compose_step`: 12 link blocks + $U_B$, order 1, $r=1$) and re-verified with the M9 step checker.

## 2. What was done
- Step 10.0: hook `src/su2plaq/fuzzy/compress_hook.py` (attribute patches of the laptop's `spec/evaluate/baselines/round` from our own module; no laptop file edited; the exact laptop diff is in `notes/merge-notes-fuzzy.md`), worker hook `src/su2plaq/fuzzy/sitehook/sitecustomize.py`, driver `scripts/m10_round.py`; round-0 seeds (general, general + polish, Qiskit level 3).
- Ideation: one proposer per unit (two in total; family cap 4 kept across both, since plan 302 has two units): `compress/ideation/fuzzy_ub.md` (3 families), `compress/ideation/fuzzy_link.md` (2 families).
- Rounds: `fuzzy_link` 2 rounds (1 proposer each; stopped because the search found no 11-CX circuit), `fuzzy_ub` 3 rounds (3 proposers each). Each round evaluated with `python scripts/m10_round.py round --encoding E --round r --evaluate`, Clifford+T re-verification of the best, and a commit `compress <unit> round 00r`.
- Every proposer program is immutable under `compress/programs/fuzzy_{ub,link}/F*/NNN-*.py`; attempts in `compress/attempts/fuzzy_*.jsonl`, discoveries in `compress/discoveries/fuzzy_*.md`.

## 3. Results

### 3.1 Unit `fuzzy_ub` ($U_B$), before and after
Columns from `results/compress/fuzzy_ub/summary.json` `rows`. T at $\varepsilon=10^{-6}$ is $T_{\rm fixed}+\sum_r T_r(\varepsilon)$ with pygridsynth. Qubits = 8 row qubits + work qubits.

| row | qubits | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | T($10^{-6}$) | CT-depth | verdict | Lean | entry |
|---|---|---|---|---|---|---|---|---|---|
| **before**: general (M9 `build_UB`) | 15 | 1718 | 1826 | 16 | 2822 | 4916 | valid (err $3.8\times10^{-14}$) | not_run | r00-seed-000 |
| general + polish | 15 | 1596 | 1686 | 16 | 2682 | 4912 | valid ($3.8\times10^{-14}$) | n_a | r00-seed-010 |
| Qiskit L3, whole circuit (counts only) | 15 | 1627 | 1742 | 40 | n/a | n/a | unverifiable by the exact engine | n_a | — |
| round 1 best (F1) | 16 | 200 | — | 58 | 3804 | 9501 | valid | — | r01-F1-001 |
| round 2 best (F1) | 14 | 172 | 96 | 44 | 2904 | 7206 | valid | — | r02-F1-002 |
| best of family F1 | 14 | 164 | 112 | 44 | 2920 | 7222 | valid ($6.9\times10^{-14}$) | not_run | r03-F1-003 |
| best of family F2 | 14 | 165 | 106 | 44 | 2914 | 7221 | valid ($7.2\times10^{-14}$) | not_run | r03-F2-003 |
| **after**: GLOBAL BEST (family F3) | **13** | **151** | **118** | **28** | **1902** | **4682** | valid ($6.4\times10^{-14}$, leak 0) | n_a | r03-F3-003 |

12 candidates, 11 valid (the invalid one is the Qiskit L3 seed transpiled in windows of 32 gates, 1629 CX, rejected by the pruning bound — not shown in the table; the whole-circuit L3 row above is counts-only and not an archive candidate). The best is better than the general circuit in every key entry: CX $1718\to151$ ($-91\%$), T($10^{-6}$) $2822\to1902$ ($-33\%$), CT-depth $4916\to4682$, qubits $15\to13$. Clifford+T re-verification of r03-F3-003 at $\varepsilon=10^{-6}$: ok, error $3.4\times10^{-6}\le$ budget $2.8\times10^{-5}$ (28 rotations).

Lineage (CX): seed 1596 → F1 200 (r1) → F1 172 (r2) → F3 151 (r3, parent r02-F1-002); side branches F2: 268 (r1); 172 (r2, child of r01-F1-001) → 165 (r3); F3: 390 → 192.

### 3.2 Unit `fuzzy_link` (one link, $U_KU_E$), before and after

| row | qubits | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | T($10^{-6}$) | CT-depth | verdict | Lean | entry |
|---|---|---|---|---|---|---|---|---|---|
| **before**: general (M9 `link_UE` + `link_UK`) | 4 | 36 | 0 | 10 | 644 | 1515 | valid ($3.4\times10^{-15}$) | not_run | r00-seed-000 |
| general + polish | 4 | 30 | 0 | 10 | 644 | 1511 | valid | n_a | r00-seed-010 |
| Qiskit L3, whole circuit (counts only) | 4 | 24 | 3 | 13 | n/a | n/a | unverifiable by the exact engine | n_a | — |
| best of family F1 (round 1) | 4 | 13 | 0 | 10 | 644 | 1161 | valid ($3.4\times10^{-15}$) | n_a | r01-F1-001 |
| **after**: GLOBAL BEST (family F2, round 2) | 4 | **12** | 0 | 10 | 644 | 1183 | valid ($5.6\times10^{-15}$) | n_a | r02-F2-001 |

5 candidates, 4 valid. CX $36\to12$ ($-67\%$); T unchanged (the 10 rotations are the 10 commuting Pauli strings of $\frac{\alpha}{2}\mathcal K_1+\kappa_2\mathcal K_2$, so the rotation count is fixed by the Hamiltonian); every angle is $\pm\alpha/4$ or $\pm2\kappa_2$. Proposer search (exhaustive within its model of Clifford cosets, `scratch/proposer/fl_gen.py`): no circuit with 10 or 11 CX in that model — evidence, not a proof, that 12 is optimal.

### 3.3 Composed one-Trotter step, before and after (order 1, $(\alpha,\beta)=(0.37,0.61)$, $r=1$)
`results/fuzzy/compressed_step.json` (`composed` vs `general`, which include the 8 outer links) and the unit sums for the inner-only rows. T totals are sums of the pygridsynth unit counts at $\varepsilon=10^{-6}$ (T counts add because every rotation is synthesised separately): before $=2822+4\times644$, after $=1902+4\times644$; with outer links $+8\times644=5152$.

| composed step | CX | $N_{\rm rot}$ | $T_{\rm fixed}$ | T($10^{-6}$), unit sums | depth | qubits | verification |
|---|---|---|---|---|---|---|---|
| **before**, inner links only (M9 `build_step`) | 1862 | 56 | 1826 | 5398 | 2690 | 23 (16 data + 7 work) | Report 9 (`results/fuzzy/step.json`; not in `compressed_step.json`) |
| **after**, inner links only ($151+4\times12$) | **199** | 68 | 118 | **4478** | — | 21 (16 data + 5 work; derived: U_B unit 13 = 8 row + 5 work) | blocks certified (units valid); depth not composed |
| **before**, all 12 links (`general`) | 2150 | 136 | 1826 | 10550 | 2690 | 55 (48 data + 7 work) | err $1.1\times10^{-14}$ (`results/fuzzy/step.json` with outer; Report 9) |
| **after**, all 12 links (`composed`) | **295** | 148 | 118 | **9630** | 255 | 53 (48 data + 5 work) | err $1.7\times10^{-14}$, Gauss $5.9\times10^{-15}$, 40 inputs, seed 20261104 |

The composed after-step has $295=151+12\times12$ CX. The JSON's own `t_estimate` field (8968 after, 9958 before) uses the laptop's per-rotation estimate and is not the pygridsynth number; the table uses the exact unit sums. The step is verified the same way as in M9: every layer block certified exactly, composition sampled (label `blocks_certified_composition_sampled`).

Comparison with KS (12-qubit encoding, Report 1, inner-only step): 294 CX, 952 T. The compressed fuzzy inner step (199 CX) now has fewer CNOTs than the general KS step, but about 4.7 times the T count, because its 68 rotations (vs 10) dominate T. The laptop's compressed 12-qubit step (M2 round 4, master commit `9b5443d`) is CX 111, T 912. Different Hamiltonians; not an efficiency comparison of methods.

### 3.4 Lean column
`n_a` for every fuzzy circuit: the laptop's per-circuit certificate exporter is written for the 12-qubit encoding (433 physical states, its own target blocks) and was not ported this session. All rotation angles of both best circuits are small rational multiples of $\beta$, $\alpha$ or $\kappa_2$ (U_B: $\pm\beta$, $\pm2\beta$, $\pm4\beta$-type; link: $\pm\alpha/4$, $\pm2\kappa_2$), so they are angle-linear and in principle certifiable for all angles. The Lean content behind the fuzzy work remains the kernel-checked link algebra and corner-rule counts of Report 9 §3.7.

## 4. What the result means (physics and circuit findings)
- **$U_B$ is cheap once its sector structure is used.** All three U_B families found the same core facts (DISCOVERY lines in `compress/discoveries/fuzzy_ub.md`): (i) after the three-CNOT parity frame, each of the 8 parity sectors becomes $\sigma_p X_f\otimes$(Bell-pair projectors) under an $f$-controlled permutation of the four $q_2$ wires; (ii) these frames need no sector control, because the middle rotation is the identity outside its sector, so neighbouring frames merge (8 controlled swaps in total, DP-optimal over sector order); (iii) the $t=1$ sectors 2, 3, 6, 7 share one frame and one 12-term phase polynomial; (iv) the final step (F3, round 3): a signed relabelling controlled on $p_r\wedge\neg p_t\wedge\neg f$ maps sectors 1, 5 exactly onto 0, 4, removing two controlled swaps, the $p_r$-split one-hot and two middles. A controlled swap (Fredkin) costs 7 CNOTs in Clifford+T, not 8.
- **Negative results** (from exhaustive searches by the proposers): no single routing of $\le4$ controlled $q_2$ swaps brings all 8 sectors into normal form at once (12.7 M routings searched); sectors 0, 1, 4, 5 have no common frame in pairs {0,4}, {1,5}, {0,1}, {4,5}; replacing Toffolis inside Fredkins by relative-phase Toffolis never pays (the leftover phase does not commute with the rotations).
- **The link block is near-optimal at 12 CX** (§3.2).
- After compression the remaining step cost is dominated by the 12 link blocks (144 of 295 CX) and by T from rotations (148 rotations; $T_{\rm fixed}$ only 118).

## 5. Problems and assumptions
- **Scope of the session limits.** 3 rounds for `fuzzy_ub` (the cap) and 2 for `fuzzy_link`; the loop stopped because of the session's round cap, not because the stop rule (3 rounds without improvement) fired — U_B was still improving in round 3 (172 → 151). Further rounds are likely to gain more.
- **Composed step fixed at $r=1$, order 1.** The link unit itself is valid for all $(\alpha,\kappa_2)$; order 2 was not composed.
- **Lean `n_a`** for all compressed circuits (§3.4).
- **Step verification is sampled** (as in M9): units are certified as full blocks, the 48-qubit composition on 40 seeded inputs.
- **Proposer program technique.** Two families (F2 rounds 2–3) re-synthesise the angle-free segments between rotations with Qiskit's level-3 transpiler at emission time with fixed seeds; validity with an identical skeleton at all three angle pairs was checked by the evaluator, so this is allowed by the rules, but the emitted circuit depends on the Qiskit version (2.5.2).
- **Ideation split** into one proposer per unit (instead of one in total) — a coordinator deviation from START_HERE §4, recorded in `notes/STATUS.md`.
- Tester verification of all elites with a second engine: Tester round 3 (`reports/tests/303`, `b4c5c18`): PASS — second-engine rebuild of fuzzy_ub r03-F1/F2/F3-003 op-norm $\le2.2\times10^{-14}$, counts equal to the archive (best 151 CX / 28 rotations / 118 $T_{\rm fixed}$ / 13 qubits); composed step error $1.7\times10^{-14}$, Gauss $5.9\times10^{-15}$ on 40 seeded inputs, 295 CX / 148 rotations (199 CX / 68 rotations inner-only); all §3 numbers match `summary.json` and `compressed_step.json`; unit tests 486, m0–m2 102, m10 10/10 pass; acceptance lock intact. Rounds 1–2: `reports/tests/302` (PASS).

- Audit 301 note A1 (hook records the per-unit Gauss residual as 0.0 when it is not computed; it should read 'not checked') and A2 (validity is checked at 3 angle points only; the auditor checked the best link program at 7 further $(\alpha,\kappa_2)$ points, max error $7\times10^{-15}$, and the best $U_B$ at 6 further $\beta$, max error $1.1\times10^{-13}$) are open for the next session.
- **Benchmark (gate step 3) not run as a separate tester benchmark** for lack of session time; compression round wall times are in `results/compress/fuzzy_{ub,link}/round-00r.json`, and the M9 fuzzy baseline is `reports/benchmarks/300`.

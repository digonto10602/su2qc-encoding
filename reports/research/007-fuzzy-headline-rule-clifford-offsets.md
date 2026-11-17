# Research 007 — the fuzzy headline rule: constant terms that are multiples of $\pi/2$ in rotation angles

- Date: 2026-11-16. Git commit: `8f61336` (branch `merge-desktop-tracks`; other agents' B7 files uncommitted in the tree). Prompt in force for this note: `prompts/010-fuzzy-headline-rule-clifford-offsets.md` (written in the same run).
- Trigger: `reports/tests/419-consolidation-008-b6.md` finding F2; `prompts/008` §6 (silent on the point); `notes/STATUS.md` "RESTART HERE" item 4. Related: `reports/research/005` §1 (the "0 order flips" measurement this note corrects), `docs/METHODS.md` §11.2 and §12.4, companion note `reports/research/006`.
- No external method is introduced. Standard facts used: Qiskit's $R_z(\varphi)=\mathrm{diag}(e^{-i\varphi/2},e^{i\varphi/2})$, $S=\mathrm{diag}(1,i)$; Ross and Selinger, arXiv:1403.2975 (T count of one synthesised $z$ rotation, already in METHODS §7); Giles and Selinger, arXiv:1212.0506 (Clifford+T matrix entries lie in $\mathbb Z[\tfrac1{\sqrt2},i]$, already in METHODS §11.2).
- Scripts and raw numbers (planner scratch, gitignored): `scratch/planner/c009/proto_offsets.{py,json}` (classification of every fuzzy archive entry), `validate_results.{py,log}` (rankings under both rules, order inversions), `proto_headline_step.{py,json}` (composed steps), `shim/proto/{robust_offsets,headline_step}.py` (reference implementation); input: the tester's cache copy `scratch/t419/rootnew/results/compress/fuzzy_{ub,link}/robust.json` (report 419). Runs: `taskset -c 0-3 tools/run-capped python <script>`, conda env `coding`, BLAS threads 1.

Words used. *Headline* = the valid archive entry with the smallest *robust key* $(\mathrm{CX},\sum_iT_i,\rho,\sum_i\mathrm{depth}_i,\mathrm{qubits})$ over the 20 locked angle pairs (METHODS §12.4); *archive key* = $(\mathrm{CX},T,\mathrm{depth_{CT}},\mathrm{qubits})$ at the nominal pair $(0.37,0.61)$; *$\rho$* = 0 if the program is angle-linear, else 1; *Clifford gate* = a gate that costs no T gate ($H$, $S$, $Z$, CNOT and products); *affine* = linear plus a constant; *offset class* (my label) = the classification of the constants defined in §3.

## 1. The facts

1. **Which entries.** Of the 41 valid `fuzzy_ub` entries 11 have $\rho=1$ under the generic test: `r09-F1-009`, `r09-F2-009`, `r10-F2-010`, `r11-F1-011`, `r11-F2-011`, `r12-F1-012` (archive best), `r12-F2-012`, `r12-F3-012`, `r13-F1-013`, `r13-F2-013`, `r13-F3-013`. All four `fuzzy_link` entries are linear.
2. **Why.** For every one of the 11, each rotation angle is affine in $(\alpha,\beta)$ (fit on the 20 pairs, residual at all 21 pairs $\le1.2\times10^{-14}$), the gate is a plain `rz`, and the constant is $-2$, $-3$ or $-6$ times $\pi/2$ (`proto_offsets.json`; e.g. `r12-F1-012`: 6 of 9 rotations with $-2,-2,-3,-2,-3,-3$, as the tester found; `r13-F3-013`: 3 of 7 with $-3,-2,-2$). No entry has a constant that is not a multiple of $\pi/2$, and no entry is non-affine. The programs say so themselves (`compress/programs/fuzzy_ub/F1/012-…py` line 324: "rz(theta) = rz(theta - k pi/2) S^k (global phase)").
3. **No T cost.** $R_z(\theta+k\tfrac\pi2)=e^{-ik\pi/4}\,R_z(\theta)\,S^k$, so a word that approximates $R_z(\theta)$ to $\varepsilon$ with $t$ T gates gives one for $R_z(\theta+k\pi/2)$ with the same $t$. Measured: the 20 per-pair T counts of `r12-F1-012` and of `r10-F1-010` are the same list (638, 630, 640, 618, 626, 646, …), $\sum T=12\,688$ for both.
4. **What the offsets were for.** The archive key breaks the CX and T tie by `depth_CT` at the nominal pair; rounds 9–13 chose $k$ to shorten the synthesised word layout at $\beta=0.61$: 1546 → 1517 (STATUS 2026-11-14: "depth gains partly come from rz shifts chosen at beta=0.61"). Over the 20 pairs the per-pair depth difference `r12-F1-012` minus `r10-F1-010` is $+11,+10,+16,-9,-13,+7,-21,+6,+22,-18,-6,+1,+2,-19,+4,-13,+29,+2,-3,-2$, sum $+6$: the gain is specific to the nominal angle.
5. **Ranking under the two candidate rules** (`validate_results.log`):

| rule | first six by robust key | headline | order inversions against the archive order (41 entries, 820 pairs) |
|---|---|---|---|
| kept: constant term ⇒ $\rho=1$ | `r10-F1-010`, `r10-F3-010`, `r11-F3-011` $(83,12688,0,30902,10)$; `r09-F3-009` $(83,12688,0,30982,10)$; `r12-F1-012`, `r13-F1-013` $(83,12688,1,30908,10)$ | `r10-F1-010` | 34 |
| extended: Clifford offsets count as linear | same three first; then `r12-F1-012`, `r13-F1-013`, `r13-F2-013` $(83,12688,0,30908,10)$ | `r10-F1-010` | 30 |

   The three entries at the top have the same robust key and the same archive key $(83,638,1546,10)$ but different program files; the tie is broken by the id, as §12.4 prescribes. `fuzzy_link`: headline = archive best `r02-F2-001`, $(12,12576,0,23373,4)$, $\bar T=628.8$, 0 inversions under both rules.
6. **The "0 flips" of research 005 §1** was measured on 2026-11-10 with 11 entries and T only. It is not an error of that note but it is obsolete: with the final archive the depth sums alone reorder 30 pairs.
7. **Brief text.** The paragraph that tells proposers to keep multiples of $\pi/2$ in separate `s`/`sdg`/`z` gates entered the briefs with step B6 (2026-11-16); the fuzzy loop was closed on 2026-11-14. The fuzzy proposers never saw it, so the 11 entries broke no rule that existed for them.

## 2. Candidates

| | K: keep ($\rho=0$ only without a constant term) | E: extend ($\rho=0$ also for Clifford offsets) | N: normalise (rewrite $R_z(\theta+k\pi/2)\to R_z(\theta)S^k$ before judging) |
|---|---|---|---|
| fuzzy_ub headline | `r10-F1-010`, $(83,12688,0,30902,10)$, $\bar T=634.4$ | the same entry and key | the same entry (the rewrite changes depth by at most one gate per rotation; not measured) |
| meaning of "angle-linear" across encodings | one meaning: the form the Lean exporters accept (`lean/certify.py::_classify_angle` and the spinnet/LSH exporters reject a constant term; the registered tests of twelve, spinnet, LSH are those exporters) | two meanings: fuzzy looser than twelve/spinnet/LSH, whose locked hooks cannot follow | one meaning, but the judged circuit is no longer the submitted one |
| Lean (METHODS §11.2) | unchanged | unchanged in code, but the column would say "angle-linear" for programs the exporter answers `non_linear_angle` | needs the rewrite inside hashed exporter code (three exporters) |
| code | none in the rule; one informative classifier | new branch in the rule; must know which gates make an offset Clifford (`rz`, `p`: $\pi/2$; `crz`, `crx`, `cp`: only $\pi$, since $\mathrm{crz}(\pi/2)$ and $\mathrm{cp}(\pi/2)$ are not Clifford) — a wrong table would silently reward a hidden T | rewrite pass + re-verification of every rewritten circuit |
| locked tests | none affected | none affected | none affected, but hashed files change inside the consolidation window |
| risk | a T-free program is labelled "not angle-linear" (fixed by the classifier and the report cell) | the label stops meaning "certifiable as written" | largest |

Error and cost scaling do not differ between the candidates (the rule is a ranking, not a numerical method); the comparison is on meaning, consistency and risk.

## 3. Decision

**K, with an informative classifier.** $\rho$ keeps its definition. New function `robust.angle_offsets(circuits, pairs)` fits $\theta=c_\alpha\alpha+c_\beta\beta+c_0$ per gate parameter and returns the *offset class*: `linear` (no constant, $\rho=0$), `clifford_offset` (affine; every non-zero constant a multiple of $\pi/2$ on `rz`/`p`/`rx`/`ry`, or of $\pi$ on `crz`/`crx`/`cry`/`cp`), `non_clifford_offset` (affine, another constant — e.g. $+\pi/4$, which hides a T gate; or a constant on a gate not in the table), `non_affine`. Reports print "no (Clifford offsets)" instead of "no". Reasons, in order of weight:

1. Both rules give the same headline, the same key and the same $\bar T$ (§1.5); the choice cannot change a reported number. The entry the rule passes over, `r12-F1-012`, differs from the headline by nominal-angle depth tuning that the 20-pair sum already neutralises (§1.4) — the purpose of the robust key.
2. One meaning of the column for all five encodings, equal to "the Lean exporter takes the program as written". The headline `r10-F1-010` has no constants and would be certifiable as written by a future fuzzy exporter built like the others.
3. No change to a rule that five archives, two locked milestones (M4-S8/S9, M6-H1/H2) and the brief paragraph already use.
4. The classifier removes the only real defect of K: the reader of a table can now tell a T-free re-phasing from a fixed-angle trick.

**Effect on the Lean angle-linearity requirement: none.** METHODS §11.2 stands as written: an exporter accepts angles that are rational multiples of $\alpha$ or $\beta$ and answers `non_linear_angle` otherwise. Added remark (METHODS §12.4 amendment): an offset program is still inside what the checker can prove — $e^{i(m\theta+k\pi/4)}=\omega^kz^m$ with $\omega=e^{i\pi/4}\in K=\mathbb Q(i,\sqrt2,\sqrt3)$ is a Laurent monomial over $K$ — but only after the program itself is rewritten with explicit `s`/`z`/`sdg` gates; no exporter is changed.

**Fuzzy headline:** `fuzzy_ub` = `r10-F1-010`, robust key $(83,12688,0,30902,10)$, $\bar T=634.4$, nominal $T=638$, archive key $(83,638,1546,10)$; `fuzzy_link` = `r02-F2-001`, $(12,12576,0,23373,4)$, $\bar T=628.8$, nominal 644. The archive best `r12-F1-012` $(83,638,1517,10)$ stays the GLOBAL BEST row of the table (same CX, same $\sum T$, offset class `clifford_offset`).

**Composed step** (`proto_headline_step.json`; M9 sampled composition check, seed 20261104, 32 random + 8 physical inputs):

| units | err | Gauss | with outer rows: CX, rotations, fixed T, depth, qubits | inner step: CX, rotations, fixed T, qubits |
|---|---|---|---|---|
| headline: `r10-F1-010` + `r02-F2-001` | $1.2\times10^{-14}$ | $5.9\times10^{-15}$ | 227, 129, 72, 151, 50 | 131, 49, 72, 18 |
| archive best: `r12-F1-012` + `r02-F2-001` (the locked `best_step`) | $1.3\times10^{-14}$ | $5.9\times10^{-15}$ | 227, 129, 72, 150, 50 | 131, 49, 72, 18 |
| T-first: `r13-F3-013` + `r02-F2-001` | $1.3\times10^{-14}$ | $5.9\times10^{-15}$ | 233, 127, 80, 180, 50 | 137, 47, 80, 18 |
| general | — | — | 2150, 136, 1826, 2690, 55 | 1862, 56, 1826, 23 |

So quoting the headline instead of the archive best changes one number of Report 10: the logical depth of the composed step, 150 → 151.

## 4. Locked tests

Checked: `tests/acceptance/m2c/test_consolidation_gate.py::test_M2C_G3` asserts that the headline is the minimum of the robust keys that `robust.headline` itself reports, that it equals the track headline for spinnet and rishon, and that `summary.json` carries its id — true under K (and under E); `M2C_G4` verifies the archive best and the headline at unseen angles; it does not depend on the choice of rule (not run here, see §5). `tests/acceptance/m10`: `M10_G1`–`G3` use the archive best and `best_step`; `M10_G3` pins `results/fuzzy/compressed_step.json` to the units of `best_step` — therefore the headline step gets its own function and file, and `best_step`, `compress_hook.py` (hashed) and `compressed_step.json` are not touched. **No locked test changes.** New locked tests: `tests/acceptance/m11/test_headline_rule.py` (H1–H3), described in `prompts/010` §5.

## 5. Uncertain or not done

- The T-count invariance under a Clifford offset is exact for an optimal synthesiser; for pygridsynth 1.2.0 it is measured on these programs (identical per-pair counts), not proved for every angle.
- Candidate N was not prototyped.
- `M2C_G4` on `r10-F1-010` at the two unseen pairs was not run here (it needs the Phase C state); the entry is valid at the nominal and both alternate pairs (archive) and at 20 further pairs its skeleton is unchanged (robust key exists).

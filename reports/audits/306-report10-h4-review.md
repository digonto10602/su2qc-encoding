# Audit 306 — Report 10 update (prompts/010 step H.4): review against research 007 and the result files

- Date: 2026-11-19. Git commit: `689a0ce` (HEAD; branch `merge-desktop-tracks`). Object of review: the **uncommitted** diff of `docs/report-10-fuzzy-compression.md` (+55/−18), written at `70e2e25`.
- Plan in force: `prompts/010-fuzzy-headline-rule-clifford-offsets.md`, §6 row H.4 (items (a)–(f)); done-check "auditor reads the paragraph against research 007".
- Related: `reports/research/007-fuzzy-headline-rule-clifford-offsets.md`, `reports/audits/305-milestone-2c-consolidation.md` (note N8), `reports/tests/428-c3-headline-lean.md`, `reports/tests/429-b7-robust-race-h3.md`, `docs/METHODS.md` §12.4 and its amendment.
- Files checked against: `results/compress/fuzzy_ub/{robust,summary}.json`, `results/compress/fuzzy_link/{robust,summary}.json`, `results/fuzzy/compressed_step.json`, `results/fuzzy/compressed_step_headline.json`, archive entries `compress/archive/fuzzy_ub/entries/{r10-F1-010,r12-F1-012,r13-F3-013,r11-F1-011,r09-F1-009}.json`, `notes/STATUS.md` (lines 24, 49).
- Method: read-only; light Python on one core (`taskset -c 8 python -c ...`, json + itertools only). Line numbers below refer to the working-tree file.

**Verdict: PASS WITH NOTES.** The §3.5 paragraph agrees with research 007 on every point the plan asks for, the physics of the Clifford offsets is correct, the 34 order inversions recount exactly, the $\bar T$ definition is right, and all spot-checked numbers match the files. There are no blocking physics errors. Seven text corrections are required before the coordinator commits (one false provenance statement, two unmarked superseded statements, superseded table rows that can be read as current, one causal claim that the files do not support, and two style-rule violations). All are wording edits, so no fixer run and no re-audit are needed.

## 1. Checklist

| # | Item | Result | Where |
|---|---|---|---|
| 1a | H.4 (a): Table 3.1 gains GLOBAL BEST `r12-F1-012` ("no (Clifford offsets)") and HEADLINE `r10-F1-010` | OK | lines 43–44; extra T-first row line 45; Table 3.1b lines 49–55 |
| 1b | H.4 (b): composed step quoted from the headline units; depth 151 instead of 150; all other counts equal | OK (wording of the stated cause is wrong, R5) | lines 77–85 |
| 1c | H.4 (c): one paragraph: what the offsets are, no T cost, nominal depth gain lost in the 20-pair average, 34 inversions | OK (premise missing, R6; attribution too strong, R5) | line 101 |
| 1d | H.4 (d): T-first `r13-F3-013`, inner step 137 CX, $\bar T=3035.2$ | OK | lines 91, 105 |
| 1e | H.4 (e): Lean `n_a`, no fuzzy exporter | OK | lines 97–99, §5 |
| 1f | H.4 (f): "accepted by Digonto 2026-11-17" (overrides the plan's wording on purpose) | OK, matches `notes/STATUS.md:49`; the six defaults listed match prompts/010 §8 (1)–(6) | line 103 |
| 2 | Offsets paragraph against research 007 | OK on physics and numbers; ISSUE on causal wording (R5) and on a missing premise (R6) | line 101 |
| 3 | Every changed number traced or labelled; T-first composed step (233 / 127 / 80 / 180) labelled as research-007-only | OK for the T-first step (line 91). ISSUE: the footnote (*) wrongly says $T_{\rm fixed}$ and $N_{\rm rot}$ are not stored per entry (R1) | line 47 |
| 4 | $\bar T$ definition (audit 305 N8) | OK | line 89, §5 line 118 |
| 5 | Style rules (plain English, jargon, own labels, LaTeX, sources) | ISSUE: "Clifford offset" is a project label but is not called one; "Pareto" and "word" are not defined (R7) | lines 9/11, 91, 101, 105 |
| 6 | Superseded 2026-11-06 rows and statements clearly marked | ISSUE: rows 38–41 are not covered by the "round 3" marker, and two header statements are now false for the current files (R2, R3, R4) | lines 5, 7, 31, 38–41, 3/25 |

## 2. What I checked and what I found

### 2.1 Physics of the offsets (line 101)
- $R_z(\theta+k\tfrac\pi2)=e^{-ik\pi/4}R_z(\theta)S^k$ with Qiskit's $R_z(\varphi)=\mathrm{diag}(e^{-i\varphi/2},e^{i\varphi/2})$ and $S=\mathrm{diag}(1,i)$. Check: $R_z(k\pi/2)=\mathrm{diag}(e^{-ik\pi/4},e^{ik\pi/4})=e^{-ik\pi/4}\,\mathrm{diag}(1,i^k)=e^{-ik\pi/4}S^k$, and $R_z(\theta)$ commutes with $S$. **Correct.** The T-count argument follows: if a Clifford+T word $W$ (the gate sequence the synthesiser outputs) approximates $R_z(\theta)$ with $t$ T gates, then $WS^k$ approximates $R_z(\theta+k\pi/2)$ up to a global phase with the same $t$.
- Uncontrolled `rz`, `rx`, `ry`, `p` at multiples of $\pi/2$ are Clifford ($R_x(\pi/2)=HR_z(\pi/2)H$, $R_y(\pi/2)$ maps Pauli operators to Pauli operators, $p(\pi/2)=S$). **Correct.**
- Controlled rotations: $\mathrm{crz}(\pi)=|0\rangle\langle0|\otimes I+|1\rangle\langle1|\otimes(-iZ)=(S^\dagger\otimes I)\,\mathrm{CZ}$ and $\mathrm{cp}(\pi)=\mathrm{CZ}$ are Clifford. $\mathrm{cp}(\pi/2)$ is controlled-$S$, which is not Clifford and needs T gates. So "only multiples of $\pi$" is **correct**, and it matches research 007 §2/§3 and the prompts/010 §7 do-not-retry item.
- Missing premise (R6). The paragraph proves "no T cost" for plain $z$-rotations and then gives the gate table, but it never says that every shifted gate in the 11 entries is a plain `rz`. Research 007 §1.2 and the METHODS §12.4 amendment both say so. Without this sentence the reader cannot tell that the uncontrolled rule is the one that applies.

### 2.2 Offset classes and units (recounted from `results/compress/fuzzy_ub/robust.json`)
- Classes: 30 `linear` and 11 `clifford_offset` out of 41 entries. `fuzzy_link`: 4 of 4 `linear`. Matches line 101.
- The set of non-zero units over all 11 entries is $\{-2,-3,-6\}$ (the $-6$ values occur only in `r09-F1-009`). Matches.
- `r12-F1-012` `offset_units` $=[-2,-2,0,0,-3,-2,0,-3,-3]$: 6 of 9 shifted, non-zero units $-2,-2,-3,-2,-3,-3$. `r13-F3-013` $=[0,0,-3,-2,0,0,-2]$: 3 of 7, units $-3,-2,-2$. Both match.
- The 20 per-pair T lists of `r12-F1-012` and `r10-F1-010` are identical, $\sum T=12\,688$ for both. Matches.
- Depth sums: 30 908 for `r12-F1-012` and 30 902 for `r10-F1-010`, difference $+6$. Matches research 007 §1.4.

### 2.3 Order inversions (recount)
Definition used, as in line 101: over the 41 valid entries ($\binom{41}{2}=820$ pairs), count a pair when the archive key (`laptop_key`) and the robust key order it oppositely, skipping pairs tied in either key.

| rule | ties skipped | ties broken by entry id |
|---|---|---|
| kept ($\rho=1$ for any constant) | **34** (10 tied pairs skipped) | **34** |
| alternative (Clifford offsets count as $\rho=0$) | **30** | **30** |

All three statements in line 101 are confirmed: 34, 30, and "stays 34 with the id tie-break". One fact worth adding (optional O1): under the kept rule every one of the 34 inversions is a pair with equal CX and equal $\sum T$. The robust key decides such a pair by $\rho$ and the archive key by nominal CT-depth. So all 34 are an offset entry against an angle-linear entry, and the word "therefore" in line 101 is justified.

### 2.4 Spot checks of numbers (22 checked, all equal to the file)
| Number in the report (line) | File and field | File value |
|---|---|---|
| fuzzy_ub 14 rounds / 42 candidates / 41 valid (3) | `fuzzy_ub/summary.json` `n_rounds`, `n_candidates`, `n_valid` | 14 / 42 / 41 |
| fuzzy_link 3 / 5 / 4 (3) | `fuzzy_link/summary.json` | 3 / 5 / 4 |
| GLOBAL BEST 10, 83, 72, 9, 638, 1517, $5.68813\times10^{-14}$ (43) | `fuzzy_ub/summary.json` `rows[-1]` | equal |
| HEADLINE err $5.43744\times10^{-14}$, key $(83,638,1546,10)$ (44) | entry `r10-F1-010` `verdict_nominal.op_norm_error`, `key` | $5.4374\times10^{-14}$, equal |
| T-first 89, 514, 1242, err $4.36802\times10^{-14}$ (45) | entry `r13-F3-013` | equal |
| robust keys and $\bar T$ 634.4 / 634.4 / 520.0 (53–55) | `fuzzy_ub/robust.json` | equal |
| link headline $(12,12576,0,23373,4)$, 628.8 (57) | `fuzzy_link/summary.json` `headline` | equal |
| invalid candidate = Qiskit L3 windows, 1629 CX (59) | `fuzzy_ub/summary.json` `rows[2]`; 41 entry files, all valid | equal |
| lineage parents r11-F1-011, r09-F1-009, r11-F2-011 (61) | `summary.json` `lineage` | equal |
| headline step 227 / 129 / 72 / 151 / 50, err $1.2047\times10^{-14}$, Gauss $5.866\times10^{-15}$, commit `cd468e2` clean (81) | `compressed_step_headline.json` | equal |
| archive-best step depth 150, err $1.2728\times10^{-14}$, Gauss $5.860\times10^{-15}$, commit `5bbaf0f` (82, 66) | `compressed_step.json` | equal |
| inner 131 / 49 / 72 / 151 / 18, $\bar T$ 3149.6, nominal 3214 (87) | `compressed_step_headline.json` `inner` | equal |
| `t_estimate` 7786 / 9958 (93) | `composed.t_estimate` 7785.5, `general.t_estimate` 9958.1 | equal after rounding |
| tester recomposition 306 h, 36+36 T, seeds 20261104 / 7 (93) | `reports/tests/429` 4a–4c | equal |
| tie `r10-F3-010`, `r11-F3-011` (57); T-first depth 25 084 vs 25 164 (105) | `robust.json`; `reports/tests/428` T-first section | equal |
| percentages $-95.2\%$, $-77.4\%$, $-93.0\%$, $-40.5\%$; ratio 3.4 | arithmetic from the integers | $-95.17$, $-77.39$, $-92.96$, $-40.46$; $3214/952=3.376$ |
| $3035.2=520.0+4\times628.8$; $3149.6-3035.2=114.4$ | arithmetic | equal |

The T-first composed step (233 CX, 127 rotations, 80 fixed T, depth 180, err $1.3\times10^{-14}$) is clearly labelled at line 91 as "from the prototype of research 007 §3, not from a committed result file", and it matches research 007 §3. **OK.**

### 2.5 $\bar T$ definition (line 89; audit 305 N8)
The text says that $\bar T_{\rm inner}=\bar T_{U_B}+4\bar T_{\rm link}$ is a sum of per-unit means, each over that unit's own 20 pairs. It notes that $U_B$ depends only on $\beta$ and that the link is averaged over independent $(\alpha,\kappa_2)$, while the composed step uses $\kappa_2=\alpha/2$. So the sum is not a common-angle average of the composed circuit. This matches N8 and prompts/010 §4.3. Both robust files carry the same `angle_set_sha256` (`769caec1…`), so "the same list" is accurate. **OK.**

## 3. Required corrections (exact line, current text, correct text)

**R1 — line 47, footnote (*) is false about the files.** The archive entries do store both values: `compress/archive/fuzzy_ub/entries/r10-F1-010.json` has `metrics_raw.t_fixed` 72 and `metrics_raw.n_rot` 9, and `r13-F3-013.json` has 80 and 7. `robust.json` `offset_units` also has 9 and 7 elements. The values in the table are right; only their stated source is wrong, and the false source makes committed numbers look like prototype-only numbers.
- Current: "(*) $T_{\rm fixed}$ and $N_{\rm rot}$ are not stored per entry in the archive row; they are read off the composed-step file (§3.3: … hence $N_{\rm rot}=9$ for `r10-F1-010`) and from the T-first composed step of research 007 §3 (fixed T 80, 47 inner rotations, hence 7 rotations; prototype, not in a committed result file)."
- Correct: "$T_{\rm fixed}$ and $N_{\rm rot}$ of the HEADLINE and T-first rows: archive entry fields `metrics_raw.t_fixed` and `metrics_raw.n_rot` (72, 9 and 80, 7). They are consistent with the composed steps ($49=9+4\times10$ inner rotations in `compressed_step_headline.json`; $47=7+4\times10$ in research 007 §3)." Then drop the (*) marks in lines 44–45.

**R2 — line 5, the header statement is now false for the current file.**
- Current: "(the JSON provenance of `compressed_step.json` records `git_commit` `7b0e5d0` with a dirty tree; …)"
- Correct: "(on 2026-11-06 the JSON provenance of `compressed_step.json` recorded `git_commit` `7b0e5d0` with a dirty tree; the file was regenerated since and now records `5bbaf0f`, clean, see §3.3; …)"

**R3 — line 7, unmarked superseded tester statement.** "all §3 numbers match `summary.json` and `compressed_step.json`" is no longer true: the file now holds 227 CX, not 295.
- Current: "Tester verification: Tester round 3 (`reports/tests/303`, `b4c5c18`): PASS — …"
- Correct: "Tester verification **of the 2026-11-06 state** (superseded numbers; current numbers: `reports/tests/428`, `429`): Tester round 3 (`reports/tests/303`, `b4c5c18`): PASS — …"

**R4 — lines 31 and 38–41, superseded rows can be mistaken for current results (checklist item 6).** The marker "Rows marked 'round 3'" does not cover rows 38–41: their labels say "round 1 best", "round 2 best", "best of family F1" and "best of family F2". In the current `summary.json` the row "best of family F1" is `r12-F1-012` with 83 CX, and "best of family F2" is `r13-F2-013` with 83 CX. A reader will take 164 and 165 CX as the current family bests. Also, line 31 says the columns come from `summary.json` `rows`, but rows 38–42 are no longer in that file.
- Line 31 current: "**Rows marked "round 3" are the 2026-11-06 state and are superseded** by the three rows added on 2026-11-19 at the bottom"
- Correct: "**The rows from "round 1 best" to "round-3 best" (entries `r01-…` to `r03-…`) are the 2026-11-06 state; they are no longer in `summary.json` and are superseded** by the three rows added on 2026-11-19 at the bottom"
- Lines 40–41 current: "| best of family F1 |", "| best of family F2 |". Correct: "| best of family F1 at round 3 (superseded) |", "| best of family F2 at round 3 (superseded) |".

**R5 — line 85 (and the same claim at lines 101 and 117): the cause given for the depth difference is not supported by the files.** `r12-F1-012` and `r10-F1-010` are different programs, not one program with and without offsets. They come from different lineages (`r11-F1-011` ← `r10-F2-010`, against `r09-F1-009`). Their Clifford content differs in ways an $S^k$ offset cannot produce: $H$ 50 against 42, $X$ 8 against 4. Their logical depths (all gates counted, each rotation as one gate) are 116 and 121. `notes/STATUS.md:24` says only that the depth gains "partly come from rz shifts chosen at beta=0.61". The composed-step "depth" (150 and 151) is a logical depth, while 1517 and 1546 are CT-depths (layers after T synthesis), so line 85 also mixes two different depth measures. The finding that matters for H.4 is unaffected: the nominal advantage disappears in the 20-pair sum, $30\,908$ against $30\,902$.
- Line 85 current: "The reason is that the depth difference of the two $U_B$ units at the nominal $\beta=0.61$ (1546 against 1517 in CT-depth) comes from the angle offsets of §3.5, which do not survive the 20-pair average."
- Correct: "The two $U_B$ units are different programs (different lineage and Clifford gates, among them the angle offsets of §3.5). At the nominal $\beta=0.61$ the archive-best unit is shorter (CT-depth 1517 against 1546), but summed over the 20 angle pairs it is longer (30 908 against 30 902, §3.5). The composed-step depth here is the logical depth, with each rotation counted as one gate."
- Line 101 current: "The offsets were chosen in rounds 9–13 to shorten the synthesised circuit at the nominal $\beta=0.61$ (CT-depth $1546\to1517$)."
- Correct: "The offsets were chosen in rounds 9–13 to shorten the synthesised circuit at the nominal $\beta=0.61$; together with other changes to the circuit (the archive best is not the headline with offsets added, it descends from a different line), the archive best reaches CT-depth 1517 against 1546 for the headline."
- Line 117 current: "differs from it by Clifford offsets and by a shorter CT-depth at the nominal angle only" → correct: "differs from it in its Clifford gates (including Clifford offsets) and has a shorter CT-depth at the nominal angle only".

**R6 — line 101, add the premise of "costs no T".** After "…(units $-2$, $-3$ or $-6$ in `offset_units`; …)" add: "Every shifted gate in these 11 entries is a plain uncontrolled `rz` (research 007 §1.2; METHODS §12.4 amendment)."

**R7 — style (Digonto's rules: define jargon, mark own labels).**
- Line 11 (Terms): "**Clifford offset**: see §3.5" → "**Clifford offset** (a label of this project, not a standard term): a constant added to a rotation angle that only multiplies the rotation by a Clifford gate; see §3.5". The same note applies to "headline" and "T-first", which are also project labels: add "(project label)" at their definitions.
- Line 101: "a word of $t$ T gates" → "a gate sequence (the synthesiser's output, called a *word*) with $t$ T gates".
- Lines 91 and 105: "Pareto alternative" / "Pareto point" → add at first use: "(a Pareto point is an entry that no other entry beats in both CX and $\bar T$)".

## 4. Optional suggestions
- O1 (line 101): add "All 34 are pairs with equal CX and equal $\sum T$, ranked by $\rho$ in the robust key and by nominal CT-depth in the archive key; the 30 under the alternative rule are ranked by the depth sum instead." This makes the "therefore" self-explanatory. The numbers are from my recount (§2.3).
- O2 (line 3): "fuzzy_ub: 14 rounds … fuzzy_link: 3 rounds" counts round 0 (the seeds), whereas §2 line 25 counts proposer rounds ("`fuzzy_link` 2 rounds", "`fuzzy_ub` 3 rounds"). Add "(`n_rounds` includes round 0, the seeds)" to the banner, and "(2026-11-06 state)" to line 25.
- O3 (line 3): "nothing was recomputed except the order-inversion count" → "nothing was recomputed except the order-inversion count and simple arithmetic (sums, differences, percentages), each marked where it appears".
- O4 (lines 66, 85): "the two differ in one number, the depth" and "every other count equal" are true for the table columns. The Clifford gate counts differ ($H$ 306 against 314, $Z$ 24 against 16, $X$ 16 against 20, $S$ 121 against 120) and so do the verification errors. Write "every other column".
- O5 (§3.3 table header): define "depth" as logical depth (each gate, rotations included, counted as one layer step), as distinct from the CT-depth of Table 3.1.
- O6 (line 101): "and never 0" reads oddly; "(so the two rankings never coincide under either rule)" is clearer.
- O7 (line 11): "Angle pair: a choice $(\alpha,\beta)$" — for the link unit the pair is $(\alpha,\kappa_2)$, from the same list; one clause would cover it.
- O8, outside this diff: `docs/METHODS.md` §12.4 main text still says "0 order flips … among 21, 11, 4 entries". The amendment right below corrects it, so this is fine as is. No action is needed for H.4.

## 5. Severity summary
No BLOCKING issue. R1–R7 are NON-BLOCKING corrections to the text that must be applied before the H.4 commit. They change no number. R1 corrects the stated source of correct values, R2–R4 mark superseded material, R5 removes an unsupported causal claim, and R6–R7 add a premise and jargon definitions.

# Audit 309: milestone M11 (cross-encoding comparison, spectra cross-check, Report 11)

- Date: 2026-11-20. Git commit: `c788a3d` (HEAD; differs from the tester-448 commit `688af32` only in `notes/STATUS.md`). Result files reviewed were generated at `328e071` (clean), committed in `f469d31`.
- Commit range reviewed: `55ed8da` (m11 lock, acceptance-v22) `..HEAD`, restricted to `src/su2plaq/crosscheck/`, `scripts/m11_results.py`, `src/su2plaq/fuzzy/headline_step.py`, the M11-related hunks of `src/su2plaq/compress/robust.py`, `results/crosscheck/*`, and `docs/report-11-cross-encoding-comparison.md`.
- Plans in force: `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` (M11), `prompts/010-fuzzy-headline-rule-clifford-offsets.md` (fuzzy headline rule); locked tests `tests/acceptance/m11` (acceptance-v22; current lock acceptance-v23).
- Related: tester `reports/tests/448-m11-milestone-gate-full.md` (full PASS), `421`, `422`, `423`, `447`; audits `305` (N8, N9), `308` (N2 Pareto label, N8 Gauss-law reliance, depth convention).
- Scratch scripts (session scratchpad, not in the repository): `a309_checks.py` (gauge transport, targets, closed block), `a309_depth.py` (twelve depth tie under two depth conventions). Run with `taskset -c 4-8 tools/run-capped`, 1 BLAS thread. No project file was written except this report.

## Verdict: PASS WITH NOTES

No blocking issue. The code computes what METHODS §13 says. The cross-verdicts compare the right objects: same Hamiltonian, same first-order step $U_B(\beta)U_E(\alpha)$ with inner electric energy only, all 433 Gauss-law states, one free global phase. They are not vacuous: a negative control is rejected at the predicted $2\times10^{-6}$, and the sign transport matters for the twelve pairs. Every number of Report 11 that I recomputed agrees with its source. Report 11 does contain stale or loose sentences (notes N1 to N12). Two of them (N1, N2) state wrong facts about the data and must be corrected before the `milestone-11` tag. They are text edits for the coordinator, not code fixes.

## 1. What was asked

Gate step 2 for M11. Review for silent physics or numerics errors in: (a) the spectra cross-check, in particular whether the cross-verdicts compare the right thing; (b) the Report 11 tables and the headline rules across the five encodings; (c) tester observation O1 (Pareto labels of ties); (d) overreaching physics claims (Gauss-law reliance of the LSH circuit; depth convention $X\to HSSH$).

## 2. What I did

1. Oriented with `graphify query` (crosscheck, `transported_target`, `Encoding.target`). Then I read `crosscheck/{ks,embed,report}.py`, `scripts/m11_results.py`, `evaluate/evaluator.py::evaluate` (phase and error part), the `target`/`gauge` code of `encodings/{spinnet,lsh}.py`, the imports of `lsh/operators.py`, the K4 and T2 tests, METHODS §2, §7 and §13, Report 11, and audit 308 §4–§6.
2. Independent checks (`a309_checks.py`):
   - gauge-sign counts;
   - targets with and without the sign transport for all six ordered pairs;
   - each encoding's own step target against $e^{-i\beta H_B}\,\mathrm{diag}(e^{-i\alpha H_E^{\rm inner}})$ built from `ks_operators`;
   - the distances to the wrong order and to a target that includes the outer electric energy;
   - the closed-sector block from the twelve Hamiltonian.
3. Recomputed the headline and T-first picks and the Pareto ties from `robust.headline(..., compute=False)` for all six archives. For each tied Pareto point I compared the first id with the smallest-robust-key id.
4. Read the own-archive verdict errors of the six headline entries, the provenance of the per-track compressed files, and `spectra.json`/`gate-table.json`.
5. Recomputed every percentage and ratio of Tables 1c and 2 by hand from the cited numbers. All agree.
6. `a309_depth.py`: rebuilt the five tied twelve entries at the 20 locked angle pairs and summed `depth_CT` with $X\to HSSH$ (project convention) and with $X$ as one gate.

## 3. Checklist

| # | Item | Status | Evidence (file:line) |
|---|---|---|---|
| C1 | Equations match METHODS term by term | OK | `crosscheck/ks.py:44-47`: $\tfrac{g^2}2\,\mathrm{diag}(h_E)+H_B/g^2$ (METHODS §2). `ks.py:58-62`: $T_{s\to d}=D_sD_dV_sD_dD_s$ (§13.1). `report.py:74-75`: closed block $\big[\begin{smallmatrix}0&-2/g^2\\-2/g^2&3g^2/2\end{smallmatrix}\big]$, equal to the twelve closed sector to all digits (`a309_checks.py`: $-3.6425, 4.3925$ at $g^2=0.5$). `report.py:175-177`: prediction $-\tfrac{13}{4g^4}w_k$ with $w_k=|v_{1k}|^2$ (loop component) and couplings $(g^2/2-8L/3,\,1/g^2,\,-L)$, shift $8L$ (§13.3). Per link $\{-2L,\tfrac38g^2-2L,+2L\}$, consistent with $H_D^{\rm link}=2(P_+-P_-)$. `embed.py:57-75`: $V$ of §13.2. `embed.py:85-96`: Gram-matrix leak $\lambda_{\max}\big(G-W_c^\dagger W_c\big)$, equal to $\|(1-P^{\otimes4})WV^{\otimes4}\|_2^2$. |
| C2 | Time-evolution sign and ordering | OK | Own targets equal $e^{-i\beta H_B}e^{-i\alpha H_E^{\rm inner}}$ to $\le3.4\times10^{-16}$ for all three KS encodings. Wrong order is at distance 0.990; including the outer electric energy gives distance 1.180. So all three targets are the first-order step with inner electric energy only (METHODS §2), and the cross-verdicts compare like with like. |
| C3 | Basis, index conventions | OK | `embed.py:78-79`: `_kron4` puts link $b$ least significant, as `exact.operators._build_W`. The plaquette residual against `plaquette_W` is $\le4.7\times10^{-16}$ (`spectra.json` `embedding`). All KS operators use the label order of `physical_basis("cg")`. The gauge vectors are real $\pm1$ (`encodings/spinnet.py:138-141`, `encodings/lsh.py:82-85`). |
| C4 | Truncation and cut-offs | OK | $j_{\max}=\tfrac12$ throughout. Limit parameters $L\in\{64,128\}$ (full space) and $16\ldots1024$ (closed sector), as in D5. Closed-sector $L\cdot$dev reaches the prediction as $L$ grows: $-7.0947$ (128), $-7.1009$ (256), $-7.1053$ (1024), against $-7.1067$ at $g^2=0.5$. |
| C5 | Normalisation; real expectation values | OK | Isometry residual $\le4.7\times10^{-16}$. The evaluator removes one global phase from $\mathrm{tr}(V^\dagger A)$ (`evaluate/evaluator.py`, "4: phase and error"). It has no diagonal-gauge freedom, so the sign transport is tested. |
| C6 | Precision | OK | Everything is float64/complex128 (`ks.py:39-41`, `report.py:142`); no lower-precision path. |
| C7 | Randomness, seeds, error bars | OK | Angle set seed 20261107 (`compress/robust.py:33`). Fuzzy composed check seed 20261104, 40 inputs (`results/fuzzy/compressed_step_headline.json`). $\bar T$ is quoted with standard error $s/\sqrt{20}$ (tester 448 recomputed). |
| C8 | Tests test the claim | OK, see N5 | K3, K4 and T2 call the production `evaluate` on `step_circuit` output with all 433 inputs, plus a $\beta+10^{-6}$ mutant (`tests/acceptance/m11/test_cross_ks.py:127-144`; `test_cross_results.py:209-229`). Nothing is hard-coded: picks come from `robust.headline`. N5 is about information content, not correctness. |
| C9 | Provenance | OK, see N6, N7, N10 | `spectra.json` and `gate-table.json`: `328e071`, `git_dirty: false`, one git snapshot before any write (`scripts/m11_results.py:29`, fix `32e431e`). Some commit pins and one wall time in Report 11 are stale or untraceable (N6, N7). |
| C10 | Headline rule applied consistently across encodings | OK | For all six archives, `report._pick` equals `robust.headline(...)["id"]` and `summary.json` `headline`: twelve `r05-F2-005`, spinnet `r02-F1-002`, lsh `r05-F3-005`, rishon `r06-F3-006`, fuzzy_ub `r10-F1-010`, fuzzy_link `r02-F2-001`. No ranked row has a null key. T-first is the key with its first two components exchanged, for all archives (`report.py:250-255`, METHODS §13.6). |

## 4. Answers to the specific questions

### 4.1 Spectra cross-check: right comparison? vacuous?

- **Same Hamiltonian, step and subspace.**
  - Each encoding's operators come from its own code. LSH H_B is from `lsh/operators.py`, which imports nothing from the 6j route; its docstring says it is never built from 6j symbols. Spinnet uses the 6j route, twelve route A.
  - The spectra of the three Hamiltonians agree to $2.8\times10^{-14}$, and spectra do not depend on the gauge signs. That is the gauge-free, independent evidence.
  - The targets are the same first-order inner step (C2). `evaluate` uses all 433 physical columns (`states=None`) and one global phase.
- **Phase handling.** One global phase from the trace (C5). The twelve headline passes with phase $\approx i$ (archive verdict `phase [~0, 1]`), which is allowed. No diagonal gauge is fitted inside `evaluate`, so a missing or wrong transport would show.
- **Is the transport exercised?**
  - Yes for every pair that involves twelve: the untransported targets differ by 1.146 in operator norm (after the best global phase), the transported ones by $\le1.5\times10^{-15}$.
  - No for spinnet and LSH. Their gauge vectors are identical (64 minus signs each, 0 differences), so $D_sD_d=1$ and the untransported targets already agree to $1.2\times10^{-15}$.
  - The headline cross-verdict "spinnet `r02-F1-002` against the LSH target" therefore tests that LSH H_B equals 6j H_B. It does not test any sign conversion (N5).
- **Tolerance against machine precision.**
  - All verdict errors are $4.8\times10^{-15}$ to $2.7\times10^{-13}$, against a tolerance of $10^{-10}$.
  - The mutant shift $\delta=10^{-6}$ gives block error $2.0000000012\times10^{-6}$. This equals $\|H_B\|\delta$ because the $H_B$ spectrum is symmetric (multiplicities $16,96,16,177,16,96,16$), so the optimal global phase cannot reduce the error below $2\delta$. The check is four orders of magnitude above the tolerance and seven above rounding, so it is not blind.
- **Bauer–Fike wording** (Report 11 line 123). Correct as stated. $e^{i\varphi}V$ is unitary, hence normal, so its eigenvector condition number is 1 and every eigenvalue of $A$ lies within $\|A-e^{i\varphi}V\|_2$ of an eigenvalue of $e^{i\varphi}V$ (Bauer and Fike, doi:10.1007/BF01386217).
- **Compression identity, limits, fuzzy sectors.**
  - The stored numbers match METHODS §13.2–13.4. Leaks squared are $\tfrac12,15$; $\tfrac12,\tfrac{33}8$; $1,4$. $L\cdot$dev is 7.0947, 2.1972, 0.7465 against the predictions 7.1067, 2.1956, 0.7443.
  - Fuzzy flavour distances: 0.608 is the smallest non-matching one; the matching ones are $\le1.8\times10^{-15}$.
  - I re-derived the per-link levels $\{0,\tfrac38g^2,4L\}$ and the shifts $24L$ and $8L$ from $H_E^{\rm link}=\tfrac34P_Q$ and $H_D^{\rm link}=2(P_+-P_-)$. The coefficient $\tfrac{13}4$ was re-derived in audit 305; I did not repeat it.

### 4.2 Report 11 numbers

- I recomputed the percentages and ratios of Table 1c and the differences of Table 2 from the cited numbers. Every one agrees: $\times2.65/-62.2\%$, $-1.7\%$, $\times1.74/-42.6\%$, $+94.8\%$, $\times1.38/-27.7\%$, $+139.2\%$, $\times40.9/-97.6\%$, $-97.9\%$, $-93.7\%$, $-96.0\%$, $\times14.2/-93.0\%$, $-89.4\%$, $-41.0\%$, $-832.3$, $-260.8$.
- The T counts are consistent with $T_{\rm fixed}+N_{\rm rot}\times(62\text{ to }64)$ in every row.
- Own-archive verdict errors of the six headlines are $5.1\times10^{-15}$ (spinnet) to $1.39\times10^{-13}$ (rishon), which matches the claim "$5\times10^{-15}$ to $1.4\times10^{-13}$".
- Fuzzy composition: 131 = 83 + 4×12 and 3149.6 = 634.4 + 4×628.8. With outer rows the file gives 227 CX, depth 151, 50 qubits.
- Problems in the text are listed under §5.

### 4.3 Tester O1: Pareto labels of ties

Data (`report._pareto` keeps every tied entry; `gate-table.json` lists them all):

| archive | point (CX, $\bar T$) | tied entries | first by id | smallest robust key | Report 11 label |
|---|---|---|---|---|---|
| twelve | (111, 927.4) | 5 | `r04-F2-004` | `r05-F2-005` (headline) | `r05-F2-005` |
| spinnet | (31, 1092.0) | 5 | `r02-F1-002` | `r02-F1-002` (headline) | `r02-F1-002` |
| spinnet | (32, 847.4) | 5 | `r01-F1-001` | `r05-F3-005` | `r05-F3-005` |
| LSH | (68, 1417.4) | 3 | `r04-F3-004` | `r05-F3-005` (headline) | **`r04-F3-004`** |
| LSH | (71, 1116.0) | 4 | `r02-F1-002` | `r02-F1-002` | `r02-F1-002` |
| fuzzy $U_B$ | (83, 634.4) | 12 | `r09-F1-009` | `r10-F1-010` (headline) | `r10-F1-010` |
| fuzzy $U_B$ | (89, 520.0) | 2 | `r11-F2-011` | `r13-F3-013` (T-first pick) | `r13-F3-013` |

**Judgement.** The correct rule is "label a tied point by the entry with the smallest robust key", which is the ranking order of METHODS §12.4.
- It is the only rule under which the headline and the T-first pick appear on the front under their own names.
- It is what 10 of the 11 labelled points already use (all except LSH 68).
- Audit 308 (c) recommended the same rule for Report 8.
- "First by id" is arbitrary: ids are chronological, not a cost.

The sentence "(ties in both keep the first by id)" in Report 11 line 93 is wrong for 5 of the 7 tied points, and the LSH (68, 1417.4) label is the only label that breaks the correct rule.

**Exact fix** (Report 11, coordinator):
- Line 93: replace "(ties in both keep the first by id)" by "(when several entries share a point, it is labelled by the tied entry with the smallest robust key, i.e. the first in the ranking: the headline or the T-first pick where they are among them; all tied ids are listed in `gate-table.json` `pareto`)".
- Line 99: replace "$(68,1417.4)$ `r04-F3-004` (tied with the headline `r05-F3-005` and `r05-F5-005`)" by "$(68,1417.4)$ `r05-F3-005` (the headline; tied with `r05-F5-005` and `r04-F3-004`)".
- Optional code hygiene, not required: sort ties in `crosscheck/report.py:265` by `(cx, t_mean, robust_key, laptop_key, id)` so that the first tied item in `gate-table.json` is the label. `report.py` is not hashed, but the change regenerates `gate-table.json`, so T1 and T2 must be rerun.

### 4.4 Overreach

- **Gauss-law reliance** (audit 308 N8; N4 below). Two headline circuits read outer qubits: twelve `r05-F2-005` reads 4 and LSH `r05-F3-005` reads 2 (archive verdicts, `outer_bits_read`). Like all project circuits they are exact on the physical (Gauss-law) states only. The LSH headline differs from the step by up to 2.0 on non-physical inputs (audit 308 §5 item 4). Report 11 does not say this.
- **Depth convention.** Two headlines are decided by the depth sum.
  - LSH (Report 11 already says so; audit 308 showed the order is the same with $X$ counted as one gate).
  - Twelve: five entries tie on $(\mathrm{CX},\sum T,\rho)=(111,18548,0)$, and depth sum decides, 34384 against 34404. This changes a Table 1b number: qubits 31 for `r05-F2-005` against 32 for the runner-up.
  - My check (`a309_depth.py`): with $X\to HSSH$ I reproduce 34384, 34404, 34404, 34564, 35004. With $X$ as one gate I get 34099, 34119, 34119, 34279, 34719. The order is the same, so the twelve headline (and its 31 qubits) does not depend on the convention. One sentence should say so (N9).
- **Fuzzy no-limit statement** (line 163). "No choice of $(a,b)$ makes the fuzzy link a KS link" is looser than the lemma.
  - On the $\tfrac12\mathbb 1$ copy, $\mathcal K_2=-4,2,2,2,2=8\,j(j+1)-4$, an affine function of the Casimir. So that copy alone, restricted, *is* KS-like for any $(a,b)$.
  - What fails is that no $(a,b)$ makes one copy the isolated low-energy band with a finite electric coupling (see research 006 §4.3 and METHODS §13.4 (c)).
  - Wording only; it sits under an attribution marker (N11).

## 5. Notes (all NON-BLOCKING; N1 and N2 should be fixed before the `milestone-11` tag)

- **N1 — stale LSH sentence (must fix).** `docs/report-11-cross-encoding-comparison.md:219` says "The LSH compression loop has not run: every LSH compressed number is a placeholder, and the LSH general mean $\bar T$ was not computed". This is false. Line 6, Tables 1–3 and `gate-table.json` (LSH row `final`, $\bar T=592.6$ and $1417.4$) contradict it. Delete the bullet.
- **N2 — stale T-first count (must fix).** Line 93 says the T-first pick "is a different circuit in three of the five archives (twelve, spin network, fuzzy $U_B$)". LSH also differs: `r00-seed-002` against `r05-F3-005`. Fix: "in four of the six archives (twelve, spin network, LSH, fuzzy $U_B$); near-identical for rishon; identical for the fuzzy link".
- **N3 — O1 wording.** See §4.3: the rule sentence and the LSH label.
- **N4 — Gauss-law reliance.** Add one sentence after Table 1b: "The twelve and LSH headlines read 4 and 2 outer-link qubits as controls. Like every circuit of the project, they are exact on the physical (Gauss-law) states only; on non-physical inputs the LSH headline differs from the step by up to 2.0 (audit 308)."
- **N5 — what a cross-verdict adds.** By the triangle inequality, $\|A-\varphi T_{s\to d}\|\le\|A-\varphi V_d\|+\|V_d-T_{s\to d}\|$. A cross-verdict is therefore implied by the circuit's own verdict plus K2 (transported targets, $3.0\times10^{-15}$). It is a consistency check of the delivered circuits, not new evidence.
  - For spinnet and LSH the sign transport is the identity (identical gauge vectors), so "after moving the target between the sign conventions" (line 123) applies only to the pairs with twelve.
  - Suggested addition: "(for spin network and LSH the sign conventions coincide; the transport is non-trivial for the pairs with twelve, where untransported targets differ by 1.15)".
- **N6 — stale or untraceable provenance in Report 11.**
  - (a) Line 71: rishon source "`results/rishon/m6-compressed.json` @ `fcd61dd`". The file now records `072cdfe` (regenerated in `108b458`, numbers unchanged).
  - (b) Lines 3 and 214: "wall time 73.8 s" for `scripts/m11_results.py` is in no committed file. Tester 448 measured 146 s on one core. Cite the source or replace it with the benchmark-307 number.
  - (c) Line 171: "16.003" is cited to `fuzzy.isolated.r1`, but `spectra.json` does not contain the $b\to2b$ ratio. Its source is `reports/tests/422` F2 (16.0029).
  - (d) Lines 117–119: timings 0.35 s and 0.29 s; `spectra.json` has 0.367 s and 0.301 s.
- **N7 — stale Report 6 sentence.** Line 221, "Report 6 (rishon compression) is being drafted in parallel": Report 6 is FINAL (milestone-6, STATUS 2026-11-19). Replace with a pointer to the final Report 6.
- **N8 — overbroad "verified on all physical states".** Line 64, "All circuits verified exact on all physical states": the archive entries are, but the composed fuzzy step is checked on 40 seeded inputs (as its own cell says), and the rishon three-layer step by composition (R16). Qualify the sentence.
- **N9 — twelve depth tie.** Add to the twelve row of Table 1b: "ties four entries on CX, $\sum T$ and $\rho$; chosen by depth sum (34384 against 34404); same order with $X$ counted as one gate (audit 309)". Optionally add that the fuzzy $U_B$ headline ties `r10-F3-010` and `r11-F3-011` on the full robust key and is chosen by the laptop key (prompts/010 §2).
- **N10 — `--root` provenance.** `scripts/m11_results.py` takes the git snapshot from the repository that encloses the current directory, not from `--root`. With `--root` the recorded commit may describe a different tree; tester 448 saw `786b6ae`, `git_dirty: true` in its rerun. Production runs did not use `--root`, so nothing is wrong now. Suggested: record the resolved root path in provenance, and take the snapshot with `git -C <root>` when it is a repository.
- **N11 — fuzzy no-limit wording.** See §4.4. Under the attribution marker; adjust when the attribution is settled.
- **N12 — garbled sentence.** Line 89, "Within block A the compression gives $-62\%$ and $-43\%$ in CX; the spin network ($-43\%$) and LSH ($-28\%$) end at 31 and 68 CX". Better: "Within block A the compression gives $-62\%$ (twelve), $-43\%$ (spin network) and $-28\%$ (LSH) in CX, ending at 111, 31 and 68 CX."
- Outside the M11 physics scope: the builder edits named in tester 448 (`tests/unit/test_rishon_lean_cert_unit.py`, `scripts/summary_table.py`, new `tests/unit/test_summary_table_unit.py`) are still uncommitted at `c788a3d`. Commit them before the tag so that the tagged tree is the tested tree.

## 6. Problems and assumptions

- I did not rerun `scripts/m11_results.py` or any pytest: tester 448 reproduced both files bit for bit. My numerical checks used production readers (`ks_operators`, `Encoding.target`, `robust.headline`, the archive) plus my own synthesis loop for the depth sums. My control run reproduced the archived depth sums exactly.
- I did not re-derive the $\tfrac{13}{4g^4}$ coefficient (done in audit 305) or the flavour-sector lemma; I checked only that the stored numbers agree with METHODS §13.3–13.4.
- The four `[ATTRIBUTION PENDING DIGONTO]` markers and the `[benchmark pending]` and `[AUDIT OF M11 PENDING]` placeholders were not counted as defects, as briefed.

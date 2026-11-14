# Audit 304: rishon milestone-5d (det term $\lambda_D$, prompts/204 steps D1–D7 and C1)

- Date: 2026-11-13 · Auditor (Opus 5.5, high) · Git commit at audit: `b919daa` (branch `merge-desktop-tracks`)
- Commit range: `milestone-5x..HEAD`, det work in `6d9bae8` (D1–D2), `6fea036` (D3–D6), `38cd483` (D6 results), `a97e5b1` (leaving_weight residual form, C1)
- Plan in force: `prompts/204-rishon-det-term-amendment.md` on top of `prompts/203`. Methods: committed `docs/METHODS-rishon.md` R13–R16 (`git show HEAD:docs/METHODS-rishon.md`). The working-tree edit of METHODS-rishon and `prompts/205` (unapproved planner draft) were ignored as instructed.
- Related: `reports/tests/222`, `405`, `410`, `411` (gate step 1, PASS), `reports/audits/200` (N1, origin of the det term), `reports/research/203`.
- Files my runs touched: only `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/drop_check.py` (scratch). No tracked file changed. Cores 14–19, `tools/run-capped` for the 38 432-state basis.

Jargon, once. *Det term*: $\det U_\ell+\det U_\ell^\dagger$ on a link; it moves both rishons of the link to the other end. *Gadget*: the fixed small circuit that implements one link's det rotation. *Frobenius norm* $\|X\|_F$: square root of the sum of all squared matrix entries; always $\ge$ the operator norm $\|X\|_2$ (largest singular value). *Sector codes*: the 6 valid 4-bit link patterns ($A$=3, $B$=12, four quartet codes).

## 1. What I checked independently (beyond reading)

| check | command / file | result |
|---|---|---|
| $\det U$ from my own Jordan–Wigner (JW) build on 4 modes (little-endian, $c_k=\prod_{m<k}Z_m\,\sigma^-_k$) | inline Python, cores 14–19 | single non-zero entry $\det U_{12,3}=+2$, i.e. $\det U=+2\lvert B\rangle\langle A\rvert$ (agrees with METHODS-rishon R13) |
| det gadget `_emit_ud` vs $e^{-i\eta(\det U+\det U^\dagger)}$ on the 6 sector codes, $\eta=0.29$ | same | max entry error $3.3\times10^{-16}$, global phase 1 |
| one-step observables with det at $(0.37,0.61,0.29)$ from a closed form (link layer gives $\cos^4 2\eta$ on vac$_A$, $\sin^4 2\eta$ on vac$_B$; bright $3\times3$ block with $\theta=4\sqrt2\beta$) | inline Python | echo $5.846402035815\times10^{-3}$, $E_{\rm link}=1.1662263715561\times10^{-2}$: equal to `results/rishon/observables_det.json` to 13 digits |
| closed $17\times17$ spectrum at $g^2=1$, $\lambda_D=0.2$ from my own model $H=\tfrac{3g^2}{2}\lvert\ell\rangle\langle\ell\rvert-\tfrac4{g^2}(\lvert\ell\rangle(\langle A\rvert+\langle B\rvert)+{\rm h.c.})+2\lambda_D\sum_\ell X_\ell$ | inline Python | $\{-5.0346,-1.3536,-0.8^{\times4},0^{\times5},0.8^{\times4},1.3868,6.5014\}$: equal to the file |
| does `det_sector_structure` drop det / $H_B$ targets that are not among the physical codes? | `scratchpad/drop_check.py` via `tools/run-capped` | 352 016 codes; det targets dropped: 0 of 2 218 496 (all 12 links); $H_B$ targets dropped: 0 of 320 512 |
| synthesised step3 at $\varepsilon=10^{-4}$: measured sum of per-rotation synthesis errors | `results/rishon/step3.json` t_table | `error_measured_sum` $6.27\times10^{-3}$ (step3), $6.99\times10^{-3}$ (order 2); budgets $1.74\times10^{-2}$, $1.86\times10^{-2}$ |

## 2. Checklist

| item | status | where |
|---|---|---|
| Equations match METHODS-rishon R13 term by term: $H=\tfrac{g^2}2H_E+\tfrac1{g^2}H_B+\lambda_DH_D$, $\det U=2c_{L1}c^\dagger_{R1}c_{L2}c^\dagger_{R2}$ (BCW Eq. 4.6, $N!=2$), $H_D^{\rm link}=2\sigma_x$ on $\{A,B\}$, $U_D=\bigotimes_\ell[\mathbb1+(\cos2\eta-1)P_{AB}-i\sin2\eta\,\sigma_x]$ | OK | `operators.py:242-253` (closed form from the sector `det`, $h^2=4P$), `:256`, `:262` |
| Angle map: $\eta=\lambda_D\,dt$ with no factor $\tfrac12$ (because $e^{-i\,dt\,\lambda_DH_D}=U_D(\eta)$); $\alpha=g^2dt/2$, $\beta=dt/g^2$ unchanged | OK | `operators.py:269-295`, METHODS-rishon R13 |
| Order 1: operator $U_B(\beta)U_D(\eta)U_E(\alpha)$ = circuit order electric, det, magnetic | OK | `operators.py:290`, `circuits/rishon.py:251-254` |
| Order 2: $\eta/2$ on each side of $U_B$ (total $\eta$, not $2\eta$ nor $\eta/4$); target written as $[U_D(\eta/2)U_E(\alpha/2)]U_B[\ldots]$, equal to the METHODS order because $[U_D,U_E]=0$ | OK | `operators.py:292-293`, `circuits/rishon.py:256-260` |
| `prepend_det_layer`: $[U_BU_E]\,U_D=U_BU_DU_E$ (det gadgets first in circuit order, unit gates unchanged, global phase copied) | OK (note N4) | `circuits/rishon.py:216-230`; used only with order 1 in `three_layer.py:92` |
| Gadget: frame CX sends $A\to(1,0,0,0)$, $B\to(0,0,1,0)$, quartet $\to(\cdot,1,\cdot,1)$; $e^{-i\eta X_{L1}X_{R1}}e^{-i\eta X_{L1}X_{R1}Z_{L2}}=e^{-2i\eta X_{L1}X_{R1}}$ on $L_2=0$, identity on $L_2=1$; `rz(2η)` $=e^{-i\eta Z}$ | OK (checked by hand and numerically) | `circuits/rishon.py:176-197` |
| Commutation claims: $[H_D,H_E]=0$ ($A$, $B$ both Casimir 0); $[H_D^{\rm in},H_B^{\rm in}]\ne0$; outer det terms commute with everything (even, link-local operators on different qubits; $H_B$ is inner only) | OK | METHODS-rishon R13; locked DT2 |
| Which subspace: SU(2) Gauss law kept ($[L_a,\det U]=[R_a,\det U]=0$, locked DT1); det acts on the data register only, so the inner-block verdict over the 1296 codes covers all 38 432 physical states (R6 theorem unchanged) | OK | `verify.py:186`, METHODS-rishon R14 |
| Sign convention of $H_D$ | OK | global sign removable by $S=\prod_\ell e^{i\frac\pi4(n_R-n_L)_\ell}$; relative signs between links and $H_B$ are physical and come from one JW map everywhere (closed-block spectrum computed from operators, not typed) |
| Qubit order / endianness: link $\ell$ = qubits $4\ell..4\ell+3$ = $(L_1,L_2,R_1,R_2)$, code $=L_1+2L_2+4R_1+8R_2$; nibble flip $3\leftrightarrow12$ | OK | `physical.py:543-550`, `circuits/rishon.py:182` |
| Outer det row: per-link certificate, fitted phase $\arg\mathrm{tr}(T^\dagger V)$, bound $=\sum_\ell\epsilon_\ell$ (telescoping of a tensor product of unitaries); outer A$\leftrightarrow$B targets are valid outer patterns | OK | `results.py:233-290`; `UD_outer_row_certified.json` bound $4.0\times10^{-15}$ |
| `leaving_weight` residual form $\|(1-PP^\dagger)TP\|_F^2$ | OK with note N2 | `physical.py:555-560` |
| Re-judge rule (rishon prune cap 0.1): cascade order prune → leak → error → Gauss; NaN rejected; shared verdict untouched; cap looser only | OK | `verify.py:125-138`, `:166-186` |
| Truncation: two-rishon link ($N_\ell=2$), no new cut-off; det term on all 12 links as decided | OK / N/A | prompts/204 §0, §14 item 4 |
| Normalisation: observables real ($P=-\tfrac12\mathrm{Re}\langle H_B\rangle$); $P(1)=0$ holds with det (link layer keeps vac$_A$ inside the electric vacua, $H_B$ maps vacua to the loop) | OK | `observables.py`; file values `P(1) = -0.0` |
| Precision: float64 / complex128 on all reference paths; no float32 / GPU path | OK | — |
| Randomness: Gauss sample seed 20261104, eta-set seed 20261110 recorded; outer row exhaustive (seed None, correct) | OK | `three_layer.py:25-28`, result files `seeds` |
| Tests exercise production code (DT4 calls `build_UD`/`build_step`, H4 calls `verify_three_layer`); independent references (tester 222 JW build $6.6\times10^{-15}$; my checks above) | OK | `tests/acceptance/m5/test_rishon_det.py`, `m6/test_rishon_m6_three_layer.py` |
| No hard-coded answers: electric coefficient now computed (`electric_coefficient`), det target from `RishonLink`, closed block from the 1296-dim operators | OK | `operators.py:104-120`, `results.py:271-273` |
| Provenance: D6 files at clean `6fea036`, `git_dirty: false`, command and seeds recorded | OK with note N3 | `results/rishon/{UD,step3,step3_order2,UD_outer_row_certified,observables_det}.json` |
| Synthesised rows at $\varepsilon=10^{-4}$ (tester 411 note 1) | ISSUE, NON-BLOCKING (N1) | `results/rishon/step3.json`, `step3_order2.json`; `evaluator.py:448,477` |
| Replay safety | OK with note N5 | `replay.py:120,143` |

## 3. Issues (none BLOCKING)

### N1 (NON-BLOCKING, reporting) — `step3` / `step3_order2` at $\varepsilon=10^{-4}$: verdict `leak` is a bound artefact of the Aer MPS path, not a physics or synthesis failure
**What.** At $\varepsilon=10^{-4}$ both three-layer steps fell back to the `aer_mps` engine and report `ok: False, reason: leak`, `leak_amplitude` $1.93\times10^{-2}$ vs `tol_err` $=N_{\rm rot}\varepsilon+10^{-9}=1.74\times10^{-2}$ (order 2: $2.29\times10^{-2}$ vs $1.86\times10^{-2}$).
**Why it is not physics.** On `aer_mps` the shared evaluator reports $\sqrt{\max_o W_o}$ with $W_o=\sum_k\|X\psi_k\|^2$ summed over all inputs of an outer group (`evaluator.py:448`, `:477`), i.e. the Frobenius norm $\|X\|_F$, not the operator norm $\|X\|_2$. With 1296 inputs $\|X\|_F$ can exceed $\|X\|_2$ by up to $\sqrt{1296}=36$. A rigorous a-priori bound is smaller than the reported leak alone: with exact circuit $C$ (certified to $4.98\times10^{-13}$) and synthesised rotations $\tilde R_k$,
$$\big\|\tilde C-e^{i\varphi}V\big\|_2\;\le\;\sum_k\big\|\tilde R_k-e^{i\varphi_k}R_k\big\|_2+\|C-e^{i\varphi'}V\|_2\;\le\;6.27\times10^{-3}+5\times10^{-13}<1.74\times10^{-2},$$
using the measured `error_measured_sum` $6.27\times10^{-3}$ of the same file (telescoping, as METHODS §11 `prod_sub_prod_le`; valid if `error_measured_sum` is the per-rotation operator-norm distance up to phase, which is its definition in `metrics/cliffordt.synthesize`). The block error $2.07\times10^{-3}$ and the linear trend of the sparse rows ($\varepsilon=10^{-6}$: leak $1.23\times10^{-5}$ exact) point to a true leak of about $10^{-3}$. The verdict errs on the safe side (false negative), never a false `ok`.
**Fix (minimal, no tolerance change).** Report 5 addendum §3.8 must state: "at $\varepsilon=10^{-4}$ the three-layer steps are not certified by the evaluator (Aer MPS leak bound is a Frobenius bound, $1.93\times10^{-2}$); the telescoping bound from the measured synthesis errors is $6.3\times10^{-3}$; certified at $\varepsilon\le10^{-6}$". Optional (planner decision): rerun those two rows with `engine="sparse"` and a larger `cap`, or have the shared `aer_mps` path compute $\lambda_{\max}(X^\dagger X)$ (prompts/008 consolidation, not rishon). Do not quote "all synthesised rows verified".

### N2 (NON-BLOCKING, robustness) — `det_sector_structure` silently drops targets outside the code union
**What.** `physical.py:539` and `:549` keep only images `tgt` that are among the physical states' codes (`ok = uk[p] == tgt`). Weight that an operator sends to a code outside that set is never formed, so it cannot appear in `leaving_weight`. The docstring calls `leaving_weight` "the largest weight that any det / $H_B$ term sends out of the physical space", which is true only if nothing was dropped.
**Measured.** For the production operators nothing is dropped (0 of 2 218 496 det images, 0 of 320 512 $H_B$ images; `scratchpad/drop_check.py`), so the number $1.6\times10^{-25}$ and the DT5 claim hold. The invariance itself is also proved algebraically ($[L_a,\det U]=[R_a,\det U]=0$, DT1).
**Fix.** Add the squared amplitude of dropped images to `leaving` (or assert `ok.all()`). Because `rishon/physical.py` is in `RISHON_EVALUATOR_FILES`, do it before the C2 replay or not at all; otherwise a new replay tag is needed (prompts/204 §6.2). A unit test with a mutated det (for example $A\to$ an invalid code) would pin it.

### N3 (NON-BLOCKING, provenance) — committed `observables_det.json` still carries the old `leaving_weight` $2.33\times10^{-10}$
**What.** `results/rishon/observables_det.json` (`sector_structure.leaving_weight` = $2.3283\times10^{-10}=2^{-32}$, commit `6fea036`) was produced by the old difference formula; the code since `a97e5b1` gives $1.6\times10^{-25}$. The file is internally consistent with its own commit, and DT5's bound $10^{-9}$ holds, but Report 5 §3.8 must not quote the file's $2.3\times10^{-10}$ as "weight leaving the physical space". Quote $\le1.6\times10^{-25}$ with commit `a97e5b1`, or regenerate the file on a clean commit (`scripts/m5_det_results.py`), keeping the prompts/204 §11 rule that the M5 files are not regenerated.

### N4 (NON-BLOCKING, interface) — `prepend_det_layer` and `verify_three_layer(kind=...)` accept inputs for which the identity $[U_BU_E]U_D=U_BU_DU_E$ does not hold
`prepend_det_layer` (`circuits/rishon.py:216`) does not check that the unit is a first-order step (metadata `order` 1 or a loop unit of kind `step`). `verify_three_layer` takes a `kind` argument (`three_layer.py:51`) but always verifies against kind `"step"`, order 1 (`:92`). A wrong use is caught loudly by `verify` (error $O(1)$), so nothing silent today. Suggest `ValueError` when `kind != "step"` or when `unit.metadata.get("order", 1) != 1`. Neither file is hashed, so this can be done at any time.

### N5 (NON-BLOCKING, process) — replay exit code ignores changed keys; METHODS wording "copied" vs code "moved"
`replay.main` returns 0 when `lost == []` even if an entry has `key_equal: False` (`replay.py:120`, `:143`); prompts/204 §12 says to stop on either condition. Tester C2 must check `key_equal` explicitly (M6_G5 may do so; I did not verify). METHODS-rishon R15 says the old files are "copied" to `pre-204`; plan §6.2 and the code move them. Nothing is lost (git history plus `pre-204`), but if a round fails mid-replay the tree is left half-moved and a rerun refuses (`pre-204` exists): the coordinator should run C2 in a fresh worktree or know the manual recovery.

## 4. Points I was asked to judge
- **Det signs and factors.** $\det U=+2\lvert B\rangle\langle A\rvert$ confirmed by my own JW build; $H_D$ coefficient 1 (BCW $J'$, Wiese $\gamma$); $\eta=\lambda_D\,dt$; order 2 uses $\eta/2$ twice. All correct.
- **Layer order.** The brief's "$U_DU_BU_E$" is not what the code does: the code implements the METHODS operator $U_BU_DU_E$, with det after electric and before magnetic in circuit order, which is correct. The forbidden placement after $U_B$ (prompts/204 §11) does not occur anywhere.
- **Subspace.** SU(2) Gauss law; the det term breaks the corner U(1) charges as documented (431 → rank-3/4 charge change). The inner-block verdict is still sound because the det layer touches only `d`; the outer row writes `o` and is certified separately.
- **Conventions vs twelve / spinnet.** Same angle map and step-order convention as METHODS §2; the Kogut–Susskind columns stay $\lambda_D=0$ comparisons (no KS counterpart). No mismatch.
- **Tester 411 note 1.** A reporting item, not physics (N1).

## 5. Verdict
**PASS WITH NOTES.** No blocking issue. Notes N1 (Report 5 wording for the $\varepsilon=10^{-4}$ rows) and N3 (do not quote the stale $2.3\times10^{-10}$) must go into the Report 5 addendum. If N2 is fixed, it changes the rishon evaluator hash and must be done before C2.

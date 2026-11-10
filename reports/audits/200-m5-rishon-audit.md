# Audit 200: M5 rishon (SU(2) quantum link model) general circuit, milestone gate step 2

- Date: 2026-11-06
- Auditor: Claude Opus 5.5 (auditor role), read-only except this report and `results/rishon/auditor-200-*`
- Commit range: `a2ec571..3bd6748` (branch `m5-rishon`; `6916a49..3bd6748` changes only `notes/STATUS.md`)
- Plan in force: `prompts/200-rishon-m5-plan.md`, plus the one-off test fix `prompts/201-rishon-m5-codec-test-fix.md`. Methods: `docs/METHODS-rishon.md` (on top of `docs/METHODS.md`). Research: `reports/research/200-rishon-qlm-model-and-verification.md`
- Related tester reports: `reports/tests/200` to `206` (steps 5.0 to 5.10, Lean 5.L1 to 5.L3) and `reports/tests/207-m5-gate-full.md` (full gate, PASS)
- Auditor scratch (commands and outputs): `results/rishon/auditor-200-observables.{py,log}`, `results/rishon/auditor-200-sectors.{py,log}`, `results/rishon/auditor-200-degeneracy.{py,log}`

**VERDICT: PASS WITH NOTES.** No blocking issue. The code implements `docs/METHODS-rishon.md` term by term. The circuits are exact for the model as stated. The observable differences from Kogut–Susskind (KS) are physical, not a convention bug. Report 5 must still state several scope points; they are listed as notes N1 to N4 below.

Jargon used here, defined once:
- *Rishon*: a fermion that makes up one end of a gauge link in a quantum link model (QLM).
- *Jordan–Wigner (JW)*: the map from fermion modes to qubits.
- *γ*: the coefficient of the link-determinant term $\gamma\sum_\ell(\det U_\ell+\det U_\ell^\dagger)$, which breaks the extra U(1) symmetry.
- *Inner view*: the 1296 inner link codes treated as the input states for the laptop evaluator.
- *Outer-blind*: a circuit with no gate on any outer-link qubit.
- *Bright pair*: two states that $H_B$ couples to each other.
- *Dark code*: a code that $H_B$ annihilates.

## 1. Checklist

| Item | Verdict | Where / evidence |
|---|---|---|
| Equations match METHODS-rishon: $U_{ij}=c_{L,i}c^\dagger_{R,j}$, $L_a,R_a$ with $T_a=\sigma_a/2$, $H_E=\tfrac12\sum_a(L_a^2+R_a^2)=j(j+1)$, $H_B=-(W+W^\dagger)$, $W=\sum_{abcd}u^b_{ab}u^r_{bc}(u^t_{dc})^\dagger(u^l_{ad})^\dagger$ | OK | `src/su2plaq/rishon/algebra.py:71-80`, `operators.py:85-95,104-121`. Checked by hand: $[L_a,U]_{ij}=-(T_aU)_{ij}$ and $[R_a,U]_{ij}=(UT_a)_{ij}$ follow from the bilinears. The two certificate entries `U00: (2,0,+1),(5,3,-1)` (`lean/Su2PlaqCert/Rishon/HBData.lean`) equal the JW action $c_{L1}c^\dagger_{R1}$ on codes 3 and 9. Plaquette orientation agrees with the geometry: b: c0→c1, r: c1→c2, t: c3→c2, l: c0→c3. Gauge invariance $[W,G^{\rm in}]=0$ was tested (reports/tests/202). |
| Couplings and factors: $\kappa\in\{1^{32},2^{48},4\sqrt2^{1}\}$, rotation angle $2\kappa\beta$, $e^{-i\beta H_B}=e^{+i\kappa\beta(\lvert u\rangle\langle v\rvert+{\rm h.c.})}$ | OK | `operators.py:207-215` (cos/sin form is exact). `circuits/rishon.py:69` sets angle $=-2s\kappa\beta$ for $R_x$. Gate count check: `crx` 81, so `rz` = 162 = 2×81. |
| Is $\beta$ the same parameter as in the laptop's KS code ($\alpha_P=2\beta$)? | OK (meaning). See N2 for normalisation | The same formula $U_B(\beta)=e^{-i\beta H_B}$, $H_B=-(\mathrm{Tr}U_P+\mathrm{Tr}U_P^\dagger)$ is used (`docs/METHODS.md:16,19`; METHODS-rishon R1). KS closed rotation angle is $2\beta$ (so Paulo's $\alpha_P=2\beta$). Rishon closed bright angle is $4\sqrt2\beta$. The ratio comes from the link-operator normalisation, not from a different meaning of $\beta$. |
| Time-evolution sign and Trotter order | OK | $U_E=e^{-i\alpha H_E}$; `build_UE` uses `p(-3α/4)` after CX(L1→L2) (`circuits/rishon.py:7-13`). Parity $n_{L1}\oplus n_{L2}=1$ holds exactly on Q codes 5, 6, 9, 10 and is 0 on A=3 and B=12. Step order 1 = $U_BU_E$ (electric first), order 2 symmetric (`operators.py:225-230`, `circuits/rishon.py:165-171`). |
| Qubit order and endianness: link $\ell$ on qubits $4\ell..4\ell+3=(L_1,L_2,R_1,R_2)$, little-endian, sorted codes = $\mathrm{kron}(l_3,l_2,l_1,l_0)$ | OK | `algebra.py:30-35`, `operators.py:54-70`. The Lean certificate index $\sum_l s_l6^l$ uses the same order. Outer far-end fixing (Q: colour 1 = bit 0) is at `encodings/rishon.py:74-82`. |
| JW strings | OK | Link bilinears and end bilinears are string-free: the strings cancel exactly, and this is checked in Lean by `decide` (`lean/Su2Plaq/Rishon/JW.lean:114,158`). The two-qubit `end_generator` is the same for L and R ends, which is correct because the in-link Z factors cancel. |
| Truncation | N/A | The QLM has no truncation parameter: 6 states per link is the model itself. |
| Normalisation of states | OK | Gram error ≤ 8e-15, Gauss residual ≤ 2.3e-16 on all 38 432 states (reports/tests/201). |
| Observables are real | OK | `observables.py:86,96` take `np.real` of Hermitian expectation values. |
| Precision | OK | complex128 / float64 throughout. There is no GPU or float32 path. |
| Seeds | OK | Gauss sample seed 20261104 and Clifford+T (CT) seed 12345 are recorded in every JSON (`provenance.seeds`). No stochastic estimates are made, so error bars do not apply. |
| Tests run the production code path with independent references | OK | Production $W$ is compared with the pure-numpy `_ref.W_inner` (`tests/acceptance/m5/_ref.py:103`). `inner_target` is compared with `expm` (`test_rishon_operators.py:136`). Circuits are compared with `inner_target` through the production `verify` plus an independent `run_batch` check. |
| No hard-coded answers in source | OK, one minor exception (N7) | `observables.py:37` appends `np.zeros(14)` as a structural fact rather than computing it. |
| Silent exception catching | OK, minor (N8) | `verify.py:129-132` |
| Provenance | OK | All results files carry `git_commit b4c1917`, `git_dirty false`, the command and the seeds. Only `lean_export.py` changed between b4c1917 and HEAD, and the results do not use it (reports/tests/207). |
| Verification soundness (inner view) | OK | For $U=U_{\rm in}\otimes1$, $\|(U-e^{i\varphi}V\otimes1)\Psi\|\le\|M-e^{i\varphi}V_{\rm in}\|_2+\|X\|_2$, because outputs for different outer patterns are orthogonal. Outer reads are rejected (`verify.py:133-135`) and outer writes give `writes_outer` (laptop `evaluator.py:367`). Inner span = 1296 makes the condition necessary as well as sufficient. The bound "Gauss ≤ 2·op_norm_error" is correct because $\|G^a_c\|\le4\cdot\tfrac12=2$. |
| Honest labelling of what is certified vs sampled | OK in code and JSON. N5 for METHODS | `UE_outer_row.json` has `certified:false`, `sampled:true`, `method:outer_electric_check` and an explicit note (`scripts/m5_results.py:99-101,224-226`). |
| T-count accounting $T_{\rm total}=T_{\rm fixed}+\sum_rT_r(\varepsilon)$ and synthesised tolerance $N_{\rm rot}\varepsilon+10^{-9}$ | OK | U_B: 1402 ccx × 7 T + 202 ch × 2 T = 10 218 T. CX: 1402×6 + 1118 + 202 + 200 (cz) + 162 (crx) = 10 094. `t_matches_table` is true in all 20 rows. All synthesised re-verifications pass, and the worst error is ≤ 0.25 of tolerance (e.g. U_B at $\varepsilon=10^{-4}$: $4.05\times10^{-3}\le1.62\times10^{-2}$). |
| Lean | OK, scope notes (N6) | Counts and JW facts are proved by kernel `decide` with standard axioms only. The $H_B$ certificate is `native_decide` (trusts the compiled checker). |

## 2. Answers to the coordinator's specific questions

**Counts.** Reproduced or consistent: 38 432 physical, 4352 closed, U(2) sector 2192, inner span 1296, 81 bright pairs with $\kappa\in\{1\times32,2\times48,4\sqrt2\times1\}$, 990 dark codes. The closed bright block is reproduced exactly (`results/rishon/auditor-200-degeneracy.log`: $g^2=1$ eigenvalues $-4.956356,0,6.456356$, matching METHODS-rishon R4).

**Rishon vs KS observables (`results/rishon/observables.json`).** This is an apples-to-apples comparison in definitions:
- same $\alpha,\beta$ formulas;
- same $U_1=U_B(\beta)U_E(\alpha)$;
- same $E_{\rm link}=\tfrac14\langle H_E^{\rm inner}\rangle$ with $H_E=j(j+1)$ per link;
- same $P=-\tfrac12\langle H_B\rangle$;
- same echo definition;
- each theory starts from its own closed electric vacuum.

I recomputed all 12 rows of each theory from the $3\times3$ and $2\times2$ closed blocks with no project imports. The maximum deviation from the JSON is $4.1\times10^{-15}$ (`python -I results/rishon/auditor-200-observables.py`).

The large difference ($E_{\rm link}(1)=0.0347$ vs $0.6614$) is physical and follows from the closed forms:

$$E^{\rm R}_{\rm link}(1)=\tfrac38\sin^2(4\sqrt2\beta),\qquad E^{\rm KS}_{\rm link}(1)=\tfrac34\sin^2(2\beta).$$

At $\beta=0.61$ the rishon angle is $4\sqrt2\beta=3.451$ rad $=\pi+0.31$, an almost complete half-period, so $\sin^2$ is small (0.0925). The KS angle is $1.22$ rad, where $\sin^2=0.882$. Two causes:
1. The rishon link operator has matrix element 1 between a singlet and the quartet. In KS at $j_{\max}=\tfrac12$ it is $1/\sqrt2$. So $\|\mathrm{Tr}U_P|{\rm vac}\rangle\|=4$ vs 1.
2. ${\rm vac}_A$ is only half bright: ${\rm vac}_A=(|b\rangle+|d\rangle)/\sqrt2$, and the dark half never moves. Together these give a factor $2\sqrt2$ in frequency and $\tfrac12$ in amplitude.

This is not a convention mismatch. Report 5 must say so explicitly; see N2.

**γ = 0.** Yes, it changes physics conclusions, and Report 5 must flag it. Details are in N1.

**Verification soundness and labelling.** Sound as implemented and labelled honestly in code and JSON. The outer electric row is sampled, not certified, and every JSON says so. METHODS-rishon R6 is silent about it (N5).

**Circuits.** Gate counts, angle ratios $2\kappa$ and ancilla count (10 = max controls 11 minus 1) are consistent. One documentation mismatch: the docstring and METHODS say "rccx chain", but the code emits full `ccx` (N4).

**Tester 206 N1** (the certificate's link matrices are data, not tied in Lean to `JW.lean`). I agree it is NON-BLOCKING. I checked two entries by hand (table above), and the tester matched all 16 entries outside Lean with deviation 0. A cheap fix that closes the formal chain is in N6.

## 3. Notes (all NON-BLOCKING)

### N1. γ = 0 makes the dynamics U(2)-invariant. Report 5 must flag this and Digonto should ratify it
Where: `docs/METHODS-rishon.md:15` (R1), `reports/research/200-…:39-41`, `src/su2plaq/rishon/operators.py:266` (`det_term_inner` defined, unused).

- **What changes.** With $\gamma=0$ the corner charges $Q_c$ are conserved. The SU(2)-Gauss space then splits into 431 U(1) sectors, and each one evolves as a U(2) quantum link model with static U(1) background charges. Wiese (arXiv:1305.1602, Sec. 4.3, after Eq. 4.11): "If one wants to construct an SU(N) rather than a U(N) gauge theory, one should explicitly break the additional U(1) symmetry … $\gamma\sum(\det U+\det U^\dagger)$". The model simulated is therefore "SU(2) Gauss law, U(2)-invariant Hamiltonian", not the SU(2) QLM of BCW (Brower–Chandrasekharan–Wiese) with $\gamma\neq0$.
- **Reference state.** The reference ${\rm vac}_A$, with outer links near-end-empty, sits in U(1) sector $Q=(2,2,2,2)$, not in the U(2)-QLM sector $(4,4,4,4)$. Command: `PYTHONPATH=src python results/rishon/auditor-200-sectors.py`. Output: vac_A, vac_B and loop all have $(2,2,2,2)$; the 17 closed references span 15 different sectors. The inner observables are unaffected, because the circuits are outer-blind and the same inner evolution occurs with an outer choice in $(4,4,4,4)$. Report 5 should state this one fact rather than imply that the reference vacuum is "the U(2) sector".
- **γ-dependent results.** The 16-fold electric-vacuum degeneracy per outer choice, the 15 zero levels in the closed spectrum, the half-dark vacuum and the echo values all depend on γ. The det term $2(|B\rangle\langle A|+{\rm h.c.})$ per link mixes the A/B vacua and does not commute with $H_B$ ($\|[D,H_B]\|_2=22.6$).
- **Probe.** Appending a det layer $e^{-i\gamma D}$ to one step at $(0.37,0.61)$ changes the echo $\mathcal L(1)$ from $5.6\times10^{-4}$ ($\gamma=0$) to $7.8\times10^{-3}$ ($\gamma\,dt=0.3$). With $\gamma=0.2$ at $g^2=1$, the number of zero eigenvalues of $H$ on the inner space drops from 15 to 5. Source: same script, `results/rishon/auditor-200-sectors.log`.
- **γ-independent results.** Counts (38 432, 4352, 1296), the $U_E$/$U_B$ circuits and their gate counts. With $\gamma\ne0$ the step would need a third layer: 4 inner A↔B two-level rotations.
- **Fix.** Report 5 §2 and §5 should name the model "SU(2)-Gauss-law QLM with γ = 0 (U(2)-invariant dynamics)" and list which numbers depend on γ. The coordinator should put the γ choice to Digonto, since it was made without him (`notes/STATUS.md` already says "flagged for Digonto"). No code change is needed for M5.

### N2. Equal-β comparison depends on a convention, and Report 5 must explain the factor
Where: research 200 §2 (line 43, "This is a property of the model"), METHODS-rishon R1 ("β is not rescaled").

The QLM plaquette coupling is a free parameter: BCW Eq. 2.5 writes $H=J\sum\mathrm{Tr}[\ldots]$ with any $J$, and Banerjee et al. (arXiv:1211.2242) use $\tfrac1{4g^2}$ with Gell-Mann normalisation. Identifying $J$ with the KS $1/g^2$ with no factor is therefore a choice, not "a property of the model". The plan legitimately forbids rescaling, but Report 5 §3.4 should:
- print the two closed forms;
- state that the bright frequency ratio is $2\sqrt2$ and the bright weight of ${\rm vac}_A$ is $\tfrac12$;
- state that the rishon "plaquette" $\tfrac12(\mathrm{Tr}U_P+{\rm h.c.})$ has operator norm $2\sqrt2$ on the inner space (largest $|\kappa|$ is $4\sqrt2$, halved). That is larger than 2, the bound $|{\rm Re\,Tr}\,g|\le2$ for an SU(2) group element $g$, and larger than 1, the norm of the KS operator on its closed block. So rishon $P$ values above 1 (for example $P(2)=1.2436$ at $(1.70,1.00)$) are not comparable in scale with KS $P$.

Any rescaled column (for example $\beta/(2\sqrt2)$) needs a planner decision.

### N3. "4352-fold vacuum degeneracy" (plan §8 item 4) is wrong wording for Report 5
The electric vacua (states with $H_E=0$, all 12 links of type A/B) number $2^{12}=4096$ (`results/rishon/auditor-200-degeneracy.log`: 4096 of 38 432). The closed sector has $4352=4096+256$ states (the 256 loop states). For the full $H$ at $\gamma=0$, the closed-sector ground level is non-degenerate per outer singlet choice, so it is 256-fold overall, and the 14 dark vacua per outer choice sit at $E=0$ above it. Report 5 §4 should use these numbers, and should say they hold at $\gamma=0$.

### N4. "rccx chain" in docs vs `ccx` in code
`src/su2plaq/circuits/rishon.py:143-144` and `docs/METHODS-rishon.md:67` say "rccx chain". `_pair_ops` (`circuits/rishon.py:108-111`) emits full `ccx` (7 T each), which is what the counts reflect (1402 ccx). This ties to reports/tests/204 N1: rccx was rejected because of the prune cap. Fix: correct the docstring and the next METHODS revision. Report 5 must say "Toffoli (ccx) ladder", not rccx.

### N5. METHODS-rishon R6 does not describe how the outer electric row is verified
The JSON is honest (`certified:false`, `sampled:true`, 3515 sampled 48-bit codes, error $1.4\times10^{-16}$), but R6 never states it. Add one line at the next planner run.

Optional strengthening: the outer row is a product of 12 diagonal 2-qubit gadgets on disjoint qubits, so checking each gadget on its 4 input patterns of $(L_1,L_2)$ certifies all codes exhaustively. A certified row would cost almost nothing.

### N6. Lean scope statements for Report 5's Lean column
- (a) `card_rishon_physical`/`card_rishon_closed` prove the arithmetic identity $\sum_n\mathrm{patternCount}(n)\,2^{\rm zeros(n)}=38\,432$. The step from rishon states to this formula (two singlets per $j=0$ link, the quartet equivalent to a KS $j=\tfrac12$ link) is a documented argument, checked numerically by two routes. It is not proved in Lean.
- (b) `det_u_sector` (`JW.lean:146-151`) proves facts about `detU := 2·U₁₁U₂₂`. The identity $U_{11}U_{22}-U_{12}U_{21}=2U_{11}U_{22}$ (BCW Eq. 4.6) is checked only in Python. Adding it is one more `decide` statement.
- (c) Tester 206 N1: the link data in `HBData.lean` are not tied to `JW.lean` `Uop`, and `Ud = Uᵀ` is not checked. Suggested fix: a kernel `decide` lemma that each `linkOps` entry equals `Uop i j` (or its transpose) restricted to the sector `[3,5,6,9,10,12]` (16 small entries), or an added `Ud = Uᵀ` check in `checkHB`.

None of these affects correctness of the M5 numbers.

### N7. `closed_spectra` types in the 14 zero levels
`src/su2plaq/rishon/observables.py:37` appends `np.zeros(14)` instead of diagonalising the 17×17 closed block. It is true at $\gamma=0$ by the heights argument: only ${\rm vac}_A$ has all heights 0 and only ${\rm vac}_B$ has all heights 2. Still, it is a typed-in structural number. It would silently become wrong if a det term were added. Suggested fix: build the 17×17 block from the 16 vacuum codes plus the loop state and diagonalise it.

### N8. `verify.py:129-132` swallows `ValueError` from `classify_outer_gates`
This is benign. The laptop `evaluate` then repeats the same layout, translation and outer-write analysis and returns `bad_layout`, `disallowed_gate` or `writes_outer` (`evaluator.py:355-370`), so nothing can be accepted silently. It still conflicts with the letter of "never silently catch exceptions in numerical code". Suggested change: catch only `OuterWriteError` and `ValueError` from the layout, and assert `not iv.ok` in that branch.

### Already known, not re-reported
reports/tests/204 N1 to N3, 205 N3, 206 N2, METHODS-rishon R6 wording. I agree with their non-blocking status.

## 4. Reproduction
```bash
cd ~/Projects/su2qc-rishon && source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 10-19 python -I results/rishon/auditor-200-observables.py          # observables vs closed blocks, max dev 4.1e-15
PYTHONPATH=src taskset -c 10-19 python results/rishon/auditor-200-sectors.py  # U(1) sectors of closed refs; gamma probe (14 s, 0.48 GB)
PYTHONPATH=src taskset -c 10-19 python results/rishon/auditor-200-degeneracy.py   # 4096 electric vacua; closed bright block
```

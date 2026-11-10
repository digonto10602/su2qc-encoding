# Report 5 — rishon (quantum link model) encoding: general one-Trotter-step circuit

Date: 2026-11-06 · Written at commit a8f051e (branch `m5-rishon`, desktop track R) · Results commit: b4c1917 (clean, `provenance.git_dirty: false` in all seven files; code changes after b4c1917 do not change any stored number, reports/tests/207 §4 and 208 §5) · Tag: `milestone-5` (a8f051e) · Plan in force: `prompts/200-rishon-m5-plan.md` with the test fix `prompts/201` (locked as `acceptance-v8`)
Every number below is read from `results/rishon/{UE,UB,step,step_order2,UE_outer_row,observables,register_rows}.json` (produced by `PYTHONPATH=src taskset -c 10-19 python scripts/m5_results.py --jobs 6`, log `results/rishon/m5_results-b4c1917.log`, 4131 s wall; seeds 20261104 (transpiler, Gauss sample, outer-row sample) / 12345 (Qiskit Clifford+T pass manager) / 0 in `provenance.seeds`; python 3.12.16, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.2, scipy 1.18.0) unless a report is cited. Verification: tester reports `reports/tests/200`–`208`, audit `reports/audits/200`, benchmark `reports/benchmarks/200`; methods `docs/METHODS-rishon.md` (and the laptop's `docs/METHODS.md`); research `reports/research/200`.
Errors, leaks and Gauss residuals are dimensionless (operator 2-norms or vector norms of unit-norm states); times are in seconds, memory in GB, angles in radians.

## 1. What was asked
Build in Qiskit the circuits for one Trotter step, $U_E(\alpha)=e^{-i\alpha H_E}$ and $U_B(\beta)=e^{-i\beta H_B}$, for the same SU(2) plaquette with 8 outer links as Reports 1 and 3, but in a different theory: the **SU(2) quantum link model** (QLM — a lattice gauge theory whose link variables are built from a few fermions per link, so each link has a finite Hilbert space by construction instead of by truncation), in its **rishon** form (a *rishon* is one of the fermions that live at the two ends of a link; Brower–Chandrasekharan–Wiese, arXiv:hep-th/9704106). Verify the circuits on every state that obeys Gauss's law, count CNOT (CX) and T gates, and compare shared observables with the Kogut–Susskind (KS) theory at $j_{\max}=\tfrac12$ used in Reports 1 and 3 (START_HERE §5; plan 200 §8).

## 2. What was done
- **Model (a decision taken without Digonto; flagged in §5).** Two rishons per link, 2 colours × 2 ends = 4 fermion modes per link, with the rishon number fixed to 2: $\binom42=6$ states per link — two colour singlets ($A$: both rishons at the start, $B$: both at the end, each with $j=0$) and a quartet $Q$ (one rishon at each end, $j_L=j_R=\tfrac12$). KS at $j_{\max}=\tfrac12$ has 5 states per link, so this is a different theory, not a re-encoding. Only the SU(2) Gauss law is imposed, and the determinant coupling is $\gamma=0$ (Wiese, arXiv:1305.1602 §4.3; Banerjee et al., arXiv:1211.2242 for $\det U$ at $N=2$). Hamiltonian in the project normalisation (Paulo Eq. 16): $H=\frac{g^2}2H_E+\frac1{g^2}H_B$, $H_B=-(\mathrm{Tr}U_P+\mathrm{Tr}U_P^\dagger)$, with the same loop orientation and link names as the laptop's `docs/METHODS.md` §1. $\beta$ is **not** rescaled (METHODS-rishon R1).
- **Register.** Jordan–Wigner (JW — the standard map of fermion modes to qubits, one qubit per mode with a string of $Z$ gates carrying the fermion sign) with the 4 modes of each link on consecutive qubits: 12 links × 4 = **48 qubits** (16 inner, 32 outer). Every operator of one link is then a 4-qubit operator on that link alone (*string-free*; proved in Lean, §3.6). A valid link code is one of 6 of the 16 bit patterns; the inner register has $6^4=1296$ valid codes. Each outer link keeps its far end fixed (METHODS-rishon R2), giving 4 valid patterns per outer link.
- **Physical states.** Built corner by corner from the Gauss kernel: **38 432** physical states (three independent routes and a Lean kernel check), of which 4352 are closed (all outer links singlets). The span of their inner parts is the full 1296-code space.
- **Circuits** (`src/su2plaq/circuits/rishon.py`):
  - $U_E$: on a valid code the quartet condition is $n_{L_1}\oplus n_{L_2}=1$, so per inner link CX, `p(−3α/4)`, CX: 8 CX and 4 rotations.
  - $U_B$: the inner magnetic term is a sum of **81 bright pairs** (two-level blocks; §4), $H_B^{\rm in}=-\sum_p\kappa_p(|u_p\rangle\langle v_p|+{\rm h.c.})$. For each pair a Clifford frame maps $u_p,v_p$ to two codes that differ in one pivot bit, a multi-controlled $R_x(-2\kappa_p\beta)$ acts on the pivot (controls built with a Toffoli (`ccx`) ladder on 10 clean ancillas), and the frame is undone. Exact at every $\beta$ by construction. Angles $2\beta$ (×32), $4\beta$ (×48), $8\sqrt2\beta$ (×1).
  - Trotter steps: order 1 is $U_BU_E$; order 2 is $U_E(\alpha/2)U_BU_E(\alpha/2)$.
- **Checker** (`src/su2plaq/rishon/verify.py`, METHODS-rishon R6). The laptop's dense checker would need more than 20 GB at 38 432 states, so the unchanged laptop `evaluate` is run on an *inner view*: its inputs are the 1296 inner codes, its target the inner operator. For circuits that never touch the outer qubits this bound covers **all 38 432 physical states** (a proved inequality, R6 item 1), so the verdict is **certified**. Gauss's law of the outputs is checked on a **sample** of 273 physical states (17 closed + 256 seeded). A circuit passes if (error on the code space) + (leaked amplitude) + (simulator pruning bound) $\le10^{-10}$ for exact angles, or $\le N_{\rm rot}\varepsilon+10^{-9}$ after Clifford+T synthesis, and the sampled Gauss residual is within the same tolerance. The outer electric row writes outer qubits and is checked **separately by sampling** (labelled `sampled: true, certified: false`). *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* the outer electric row is now also **certified** exhaustively, link by link (`results/rishon/UE_outer_row_certified.json`, §3.7).
- **T count:** $T=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$, each rotation synthesised by pygridsynth (Ross–Selinger) and every synthesised circuit re-verified.

## 3. Results at $(\alpha,\beta)=(0.37,0.61)$

### 3.1 Exactness (inner block on all 1296 codes = all 38 432 physical states, sparse engine, every verdict `certified: true`; Gauss on 273 sampled outputs)
Source: `verification` in each JSON. Tolerance $10^{-10}$.

| circuit | error bound (`op_norm_error`) | = block error | + pruning bound | leaked amplitude | Gauss residual (273 states) | ancillas returned clean |
|---|---|---|---|---|---|---|
| $U_E$ | $1.1\times10^{-16}$ | $1.1\times10^{-16}$ | 0 | 0 | $1.8\times10^{-16}$ | — (none) |
| $U_B$ | $3.4\times10^{-13}$ | $4.1\times10^{-14}$ | $3.0\times10^{-13}$ | 0 | $2.3\times10^{-15}$ | yes (0.0) |
| step, order 1 | $4.1\times10^{-13}$ | $4.5\times10^{-14}$ | $3.7\times10^{-13}$ | 0 | $2.7\times10^{-15}$ | yes (0.0) |
| step, order 2 | $4.1\times10^{-13}$ | $4.5\times10^{-14}$ | $3.6\times10^{-13}$ | 0 | $2.3\times10^{-15}$ | yes (0.0) |
| outer electric row ($U_E$ with outer links), sampled | $1.4\times10^{-16}$ (max phase error on 3515 sampled valid 48-bit codes) | — | — | — | — | — |

- Independent checks: the tester rebuilt $U_B$ against $e^{-i\beta H_B}$ on the full 1296 block at four values of $\beta$ ($\le1.6\times10^{-14}$, reports/tests/204), recomputed the soundness bound on 72 independently built 48-qubit physical states, and ran 36 adversarial circuits with 0 false accepts (reports/tests/203, re-run unchanged in 208). The wrong Trotter order is rejected (204).
- The outer qubits are never read or written by $U_B$ and the steps (`outer_bits_read 0`).

### 3.2 Gates (circuits contain only the qubits they touch; outer qubits untouched)
Source: `metrics.logical`. Depth is the lowered depth after Qiskit transpilation to the gate set (macro depth of $U_B$ before lowering: 2402).

| circuit | qubits (data + ancillas) | CX | rotations $N_{\rm rot}$ | fixed T $T_{\rm fixed}$ | depth |
|---|---|---|---|---|---|
| $U_E$ | 16 + 0 | 8 | 4 | 0 | 3 |
| $U_B$ | 16 + 10 | 10 094 | 162 | 10 218 | 13 682 |
| step, order 1 | 16 + 10 | 10 102 | 166 | 10 218 | 13 685 |
| step, order 2 | 16 + 10 | 10 110 | 170 | 10 218 | 13 688 |
| outer electric row (separate) | 48 + 0 | 24 | 12 | 0 | 3 |

$T_{\rm fixed}=1402\times7+202\times2=10\,218$ (1402 Toffolis at 7 T each; audit 200). Gate counts recomputed by the tester from the stored `.qpy` files with an independent transpile agree exactly (reports/tests/205).

### 3.3 T count after Clifford+T synthesis (pygridsynth per rotation; every synthesised inner circuit re-verified and certified)
Source: `metrics.t_table[*].t_total`; the Qiskit Clifford+T pass manager (seed 12345) in brackets for the order-1 step.

| circuit | $\varepsilon=10^{-4}$ | $10^{-6}$ | $10^{-8}$ | $10^{-10}$ |
|---|---|---|---|---|
| $U_E$ | 176 | 256 | 328 | 416 |
| $U_B$ | 17 150 | 20 394 | 23 954 | 27 066 |
| step, order 1 | 17 326 (15 674) | 20 650 (18 938) | 24 282 (22 204) | 27 482 (25 824) |
| step, order 2 | 17 486 | 20 922 | 24 626 | 27 898 |
| + outer electric row (12 rotations, separate row, sampled check) | +528 | +768 | +984 | +1248 |

- Every one of the 16 synthesised inner circuits is certified with error and Gauss residual below $N_{\rm rot}\varepsilon+10^{-9}$. Example: step order 1 at $\varepsilon=10^{-6}$ has error $1.9\times10^{-5}$ against a budget of $1.66\times10^{-4}$; the share of the budget used is 0.04–0.54 (largest: $U_E$ at $10^{-6}$, $2.17\times10^{-6}$ against $4.0\times10^{-6}$; for $U_B$ and the steps 0.05–0.25), and the Gauss residual uses at most 0.044 of its budget (`metrics.t_table[*].synth.verdict`).
- The T count in each synthesised circuit equals `t_total` in every row; the tester reproduced the pygridsynth sums independently (reports/tests/205).
- The 10 218 fixed T gates of the Toffoli ladder are 37 % ($\varepsilon=10^{-10}$) to 60 % ($10^{-4}$) of the total; the rotations contribute $T_r\approx3\log_2(1/\varepsilon)$ each, as in Report 1.
- **Context, not like for like** (different theories; the rishon circuit is the uncompressed round-0 seed for M6). Order-1 step at $\varepsilon=10^{-6}$: KS 12-qubit encoding (Report 1) 34 qubits, 294 CX, 952 T; KS spin-network encoding (Report 3) 15 qubits, 54 CX, 566 T; rishon 26 qubits, 10 102 CX, 20 650 T. The rishon magnetic term has 81 two-level blocks against 8 in the spin-network encoding, and each needs a multi-controlled rotation over a 16-qubit register.

### 3.4 Shared observables versus Kogut–Susskind
Source: `results/rishon/observables.json` (definitions in its `definitions` block and METHODS-rishon R5). State: $n$ first-order steps $U_1=U_B(\beta)U_E(\alpha)$ from the vacuum ($|{\rm vac}_A\rangle$ for the rishon model, all links $j=0$ for KS). $E_{\rm link}=\tfrac14\langle H_E^{\rm inner}\rangle$ (electric energy per inner link); $P=\langle\mathrm{Re\,Tr}\,U_P\rangle=-\tfrac12\langle H_B\rangle$; echo $=|\langle\Omega|U_1^n|\Omega\rangle|^2$ (Loschmidt echo, the probability of returning to the start state). $P(1)=0$ in both theories is an identity (METHODS-rishon R5), so $n=2$ is also shown.

| $(\alpha,\beta)$ | $n$ | $E_{\rm link}$ rishon | $E_{\rm link}$ KS | $P$ rishon | $P$ KS | echo rishon | echo KS |
|---|---|---|---|---|---|---|---|
| (0.37, 0.61) | 1 | 0.03470 | 0.6614 | 0 | 0 | $5.614\times10^{-4}$ | 0.1181 |
| (0.37, 0.61) | 2 | 0.09098 | 0.2257 | 0.7341 | 0.5781 | 0.8725 | 0.6991 |
| (0.91, 0.23) | 1 | 0.3484 | 0.1478 | 0 | 0 | 0.4010 | 0.8029 |
| (0.91, 0.23) | 2 | 0.004132 | 0.01982 | 0.2906 | 0.3183 | 0.9585 | 0.9736 |
| (1.70, 1.00) | 1 | 0.1289 | 0.6201 | 0 | 0 | 0.8192 | 0.1732 |
| (1.70, 1.00) | 2 | 0.2331 | 0.2960 | 1.2436 | 0.7007 | 0.6079 | 0.6054 |

- The $n=1$ rows agree with the closed forms $E_{\rm link}=\tfrac34\sin^2(2\beta)$ (KS) and $\tfrac38\sin^2(4\sqrt2\beta)$ (rishon), echo $\cos^2(2\beta)$ and $\tfrac14(1+\cos4\sqrt2\beta)^2$, to $7.8\times10^{-16}$ (`closed_forms_max_dev_n1`). The auditor recomputed all 24 numbers from the small closed-sector matrices without project code: largest difference $4.1\times10^{-15}$ (audit 200).
- **Why the theories differ so much at equal angles (audit 200):** the rishon rotation angle is $4\sqrt2\beta$ against $2\beta$, because $\|\mathrm{Tr}U_P|{\rm vac}_A\rangle\|=4$ (KS: 1) and only half of the rishon vacuum takes part. At $\beta=0.61$ the rishon angle is 3.45 rad, close to $\pi$, so $E_{\rm link}(1)$ is small. This is the physics of the two models under one convention (equal $\beta$), not a convention error; see §5 on the convention. The rishon plaquette operator has norm $2\sqrt2$ (KS: 1), so rishon values $P>1$ are allowed and are not on the KS scale.

**Closed-sector spectra** of $H(g^2)$ (`closed_spectra`; rishon multiplicities per choice of outer singlets, of which there are $2^8=256$):

| $g^2$ | rishon eigenvalues (multiplicity) | KS eigenvalues (multiplicity) |
|---|---|---|
| 0.5 | −10.9449 (1), 0 (15), 11.6949 (1) | −3.6425 (1), 4.3925 (1) |
| 1.0 | −4.9564 (1), 0 (15), 6.4564 (1) | −1.3860 (1), 2.8860 (1) |
| 2.0 | −1.7016 (1), 0 (15), 4.7016 (1) | −0.30278 (1), 3.30278 (1) |

They match $\lambda=\tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+32g^{-4}}$ (rishon) and $\tfrac34g^2\pm\sqrt{\tfrac9{16}g^4+4g^{-4}}$ (KS) to $1.8\times10^{-15}$ (reports/tests/205, 208). The 15 zero levels are now computed from the full 17-state closed block, not typed in (audit 200 N7, fixed in 86fda8e).

### 3.5 Register rows
Source: `results/rishon/register_rows.json`.

| register | qubits | note |
|---|---|---|
| JW, 4 qubits per link (built) | 48 (16 inner + 32 outer) | the register all circuits above use |
| 6-state codeword, 3 qubits per link | 36 (12 + 24) | size row only; no circuit built (plan 200) |
| touched by the step | 16 data + 10 ancillas | the 32 outer qubits are never touched by $U_B$ or the step |

### 3.6 Lean status (formal verification)
Source: reports/tests/206 (steps 5.L1–5.L3), audit 200 N6. *Kernel-checked* means Lean's trusted kernel evaluated the statement with `decide` (no `native_decide`, no `sorry`). *Native-certified* means the check was compiled and run (`native_decide`), which adds one trusted axiom.

| statement | status | precise caveat |
|---|---|---|
| 38 432 physical, 4352 closed (`card_rishon_physical`, `card_rishon_closed`, `lean/Su2Plaq/Rishon/Counts.lean`) | **kernel-checked**, axioms `[propext]` | proves the counting formula $\sum_n\text{patternCount}(n)\,2^{\text{zeros}(n)}$ evaluated over the KS fusion patterns; the reduction "rishon physical states = this formula" (two singlets per $j=0$ link) is numerical (three routes, reports/tests/201) |
| seven JW facts (`car_4`, `car_8`, `bilinear_string_free_8`, `sector_card`, `u_ladder`, `det_u_sector`, `end_bilinear_local`, `lean/Su2Plaq/Rishon/JW.lean`) | **kernel-checked**, axioms none or `[propext, Quot.sound]` | anticommutation relations on 4 and 8 modes, string-freeness, the 6-state sector, $U$ as a ladder $A\to Q\to B$, end bilinears local; `det_u_sector` proves $\det U|A\rangle=2|B\rangle$ and 0 on the other sector states, not the operator identity $\det U=2U_{11}U_{22}$ (numerical). The plan's table says "six"; its own code block and the locked test name seven |
| $H_B$ bright-pair structure: $16(W+W^{\mathsf T})=\sum_p\kappa_p((4u_p)(4v_p)^{\mathsf T}+{\rm h.c.})$, 162 orthogonal vectors, $\kappa$ multiset $\{1{:}32,2{:}48,4\sqrt2{:}1\}$, 990 dark codes (`rishon_hb_structure`, `lean/certs/rishon-hb-structure.lean`) | **native-certified** (one native axiom) | exact arithmetic in $a+b\sqrt2$; 14 tampered certificates rejected (reports/tests/206). The 8 link matrices are certificate data from Python, not tied in Lean to `JW.lean` (matched outside Lean with deviation 0); the checker module is not in the default `lake build` (built on demand by `check_hb`) |
| per-circuit certificates of $U_E$, $U_B$, step | **PENDING** | wait for the laptop's checker; for $U_B$ the angle $8\sqrt2\beta$ needs a third base angle $e^{i\sqrt2\beta}$ in the checker (request in `notes/merge-notes-rishon.md`) |
| *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* certificate link matrices = JW operators (`hb_link_ops_from_jw`, `hb_link_ops_count`, `lean/Su2Plaq/Rishon/HBLink.lean`) | **kernel-checked**, axioms standard | the 8 sparse link lists of `HBData.lean` equal `Uop`/`Udop` of `JW.lean` restricted to the 6-state sector, with $U^\dagger=U^{\mathsf T}$; closes the caveat of the $H_B$ row above (reports/tests/206 N1). 50/50 mutants rejected (reports/tests/209) |
| *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* $\det U=U_{11}U_{22}-U_{12}U_{21}=2U_{11}U_{22}$ on all 16 link states; $[U_{ij},U_{kl}]=0$ (`det_u_identity`, `u_commute`) | **kernel-checked**, no axioms | closes the `det_u_sector` caveat of the JW row above (audit 200 N6b) |
| *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* corner Gauss kernels: for all 81 corner end configurations $\dim\ker(2G^z,G^+,G^-)$ from the JW generators = SU(2) singlet count (`corner_kernel_dims`, `CornerKernel.lean`; `corner_count_agree`, `Bridge.lean`) | **kernel-checked**, axioms standard | exact integer rank; with `corner_count_agree` this ties the Gauss kernel to the counting function used by `card_rishon_physical`. Still an argument plus numerics, not Lean: the factorisation of the Gauss kernel over the four corners, the grouping of link-type patterns by spin, and the fixed far ends of outer links (audit 201). `cornerCountR` is a definition-for-definition copy of `cornerCount` |
| *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* exact semantics of `build_UE` for all $\alpha$ (`ue_exact_all_codes`, `ue_gadget_sector`, `ue_gates_structure`, `ue_outer_gates_structure`, `card_inner_codes`, `UESemantics.lean`) | **kernel-checked**, axioms none or standard | on all 1296 inner codes the generated gate list (byte-identical to `build_UE`) gives exactly $z^{-3\#Q}$, $z=e^{i\alpha/4}$, as a Laurent-polynomial identity; for the outer row Lean proves only the gate-list structure (12 consecutive gadgets) and the gadget phase on a bare 4-bit code; the action on 48-qubit codes rests on the numerical certificate of §3.7 (audit 201 N1) |

### 3.7 Addendum — M5x wait-time robustness (after `milestone-5`)
Written at commit 8317ac4; plan `prompts/202-rishon-m5x-wait-robustness.md` (locked tests `tests/acceptance/m5x/`, `acceptance-v9`); tester reports 209–212; audit `reports/audits/201` (PASS WITH NOTES). No M5 number above changed (reports/tests/212 recomputed the observables: 0 differences).
- **Outer electric row, certified** (`results/rishon/UE_outer_row_certified.json`, commit 59e863d clean, `PYTHONPATH=src taskset -c 10-19 python scripts/m5x_outer_row.py`, seed 20261104): the row is a product of 12 per-link gadgets on disjoint qubits; each link's exact $16\times16$ operator is compared on its 6 sector codes with $e^{-i\frac34\alpha[\text{type}=Q]}$ after one phase per link, giving errors $\epsilon_\ell$, and $\sum_\ell\epsilon_\ell$ bounds the error on every physical state up to one global phase. Measured: all 12 $\epsilon_\ell=0.0$, bound 0.0 against $10^{-10}$, 0.12 s. Evaluated in float64 with no explicit rounding allowance (rounding at most about $4\times10^{-15}$ per link; audit 201 N3). Mutants: a $10^{-7}$ phase on one outer qubit gives a bound of $1.0\times10^{-7}$; an X gate gives 1.414; a wrong $\alpha$ by $10^{-6}$ gives $9\times10^{-6}$; a cross-link CX is refused (reports/tests/211). The auditor's own 30 random 48-qubit trials found the true error between 0.51 and 1.0 of the bound, never above it.
- **Lean:** 11 new theorems in `lean/Su2Plaq/Rishon/{HBLink,CornerKernel,UESemantics,Bridge}.lean` (rows marked *updated* in §3.6); 7 use no axioms, 4 use the three standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`); no `sorry`, no `native_decide`; per-file elaboration 0.67 s / 0.82 GB, 5.82 s / 2.00 GB, 5.59 s / 1.84 GB, 2.31 s / 6.81 GB; incremental `lake build Su2Plaq` 4.2 s. Mutation evidence: 50/50 (W1) and 30 + 3 of 41 (W2/W3; the 8 survivors change nothing a dimension count can see, reports/tests/210).
- **Dropped:** Lean semantics of $U_B$ (estimated $3\times10^4$ s of kernel time for about 12 000 gates on 1296 codes; `native_decide` is not allowed under `lean/Su2Plaq/`).
- **Still open:** a planner fix for two inconsistencies, neither affecting any result: plan §1 and a locked-test helper describe a fitted per-link phase, while the code uses an anchored phase (both give valid bounds; reports/tests/211). Also pending: the recommended `slow` marker on `T1[step]` (prompts/202 §7), which needs Digonto's approval to re-lock m5.

## 4. Physics findings along the way
- **Two singlets per link.** Each link has two $j=0$ states ($A$, $B$), so every KS physical state with $n_0$ singlet links becomes $2^{n_0}$ rishon states: $N_{\rm phys}=\sum_{\rm KS\ labels}2^{n_0}=38\,432$ (the 433 KS states weighted).
- **Vacua and the closed sector.** There are $2^{12}=4096$ electric vacua (every link $A$ or $B$). The closed sector has $4352=256\times17$ states: per outer singlet choice, the 16 inner vacua and one loop state. Its ground level is 256-fold (one per outer choice). The plan's phrase "4352-fold vacuum degeneracy" (plan 200 §8) is wrong (audit 200 N3).
- **$W$ is a simultaneous raising operator.** With heights $h(A)=0,h(Q)=1,h(B)=2$ on $b,r$ (reversed on $t,l$), $W=\mathrm{Tr}U_P$ raises all four inner heights by one, so $W^3=0$ (METHODS-rishon R4).
- **81 bright pairs.** $H_B^{\rm in}$ has spectrum $\pm4\sqrt2$ (×1), $\pm2$ (×48), $\pm1$ (×32), 0 (×1134) on the 1296 codes; 990 codes are dark (untouched) and 144 zero modes sit inside bright components. Hence $U_B$ is 81 commuting two-level rotations by $2\kappa_p\beta$, the structure the circuit uses.
- **$P(1)\equiv0$** in both theories: $U_E$ only adds a phase to the vacuum, and $U_B$ conserves $H_B$, whose vacuum expectation is 0.
- **U(1) sectors.** With $\gamma=0$ an extra U(1) charge per corner is conserved: the 38 432 states split into 431 sectors; the U(2)-QLM sector (charge 4 at every corner) has 2192 states. The reference vacuum $|{\rm vac}_A\rangle$ is in sector $(2,2,2,2)$, not in the U(2) sector $(4,4,4,4)$ (audit 200 N1).

## 5. Problems and assumptions
- **$\gamma=0$ needs Digonto's approval.** With $\gamma=0$ the dynamics is U(2)-invariant, which is not the SU(2) QLM proper (Wiese arXiv:1305.1602 §4.3). Independent of $\gamma$: the counts, the $U_E$ and $U_B$ circuits and their gate counts. Dependent on $\gamma$: the vacuum degeneracy, the 15 zero levels and the echo (one-step echo $5.6\times10^{-4}\to7.8\times10^{-3}$ at $\gamma\,dt=0.3$; audit 200 N1). Adding the determinant term would be a third Trotter layer and a plan amendment.
- **Comparison at equal $\beta$ is a convention.** The rishon plaquette coupling is a free parameter; we keep $\beta$ unchanged and do not absorb the factor $\|\mathrm{Tr}U_P|{\rm vac}_A\rangle\|=4$ (KS: 1). Research 200 calls this "a property of the model", which overstates it (audit 200 N2).
- **Outer links.** The far end of each outer link is fixed (a model choice, METHODS-rishon R2). The outer electric row is verified by sampling only (3515 codes, seed 20261104), not certified; it could be certified cheaply as 12 independent 2-qubit pieces (audit 200 N5). *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* done — certified per link, error bound 0.0 (§3.7).
- **Gate choice decided by a numerical cap, not by physics.** A relative-phase Toffoli (`rccx`) ladder is exact (block error $3.4\times10^{-13}$) and would cut $U_B$ from 10 094 to 6 866 CX (−32 %) and $T_{\rm fixed}$ from 10 218 to 7 262; it is rejected only because the sparse simulator's pruning bound ($2.3\times10^{-12}$) exceeds the $10^{-12}$ cap (reports/tests/204 N1). Headroom of the shipped circuit to that cap is only 2.6–3.3×. For M6.
- **Qiskit Clifford+T vs pygridsynth:** within the 10 % agreement limit everywhere, but the worst case is 9.61 % ($U_B$ at $\varepsilon=10^{-4}$; reports/tests/205).
- **Results files:** the inner-view verdict nested in each file stores `gauss_residual: NaN` (the inner view does not check Gauss; the outer verdict does), which is not strict JSON; $\kappa=4\sqrt2$ is stored as the key `5.65685425` (reports/tests/205 N3).
- **Plan errata (no effect on results):** "six" JW theorems (seven are locked); "4352-fold vacuum degeneracy" (see §4). METHODS-rishon R6 states the soundness bound as a squared norm while the code sums block error + leak + pruning bound; wording to be fixed by the next planner run. *Updated 2026-11-06 (M5x, prompts/202, reports/tests/209–212, audit 201):* fixed in METHODS-rishon R6 by prompts/202.
- **Benchmarks** (reports/benchmarks/200; i7-12700KF, cores 10–19, medians of 3): physical basis 2.37 s / 0.31 GB (target ≤ 60 s); `verify` at exact angles 4.7 s ($U_E$), 6.4 s ($U_B$), 6.6 s (step), 0.59–0.69 GB; synthesised $U_B$ at $arepsilon=10^{-6}$ 277 s / 1.39 GB; Lean `Rishon.Counts` 8.0 s / 8.3 GB and `Rishon.JW` 61 s / 7.1 GB from source, certificate check 1.4 s. Flags: the M5 fast test suite takes 672 s against the plan's < 10 min, because one T-count test (`T1[step]`, 581–671 s) is not marked slow — a test-plan matter for the next planner run, not a correctness issue; Lean `Counts` from source (8.3 GB) and one pytest process (6.6 GB) leave little headroom under the desktop's 10 GB per-job rule. The 12-qubit tasks of benchmark 002 re-run here give identical errors (2.5–3.5× faster than the laptop, a machine factor).
- **M6 (compression) waits** for the laptop's `milestone-2` bundle in `~/su2qc-sync/inbox/` (waiting since 2026-11-06T03:20; the track stops after 24 h without it).

# Research 006 — cross-encoding comparison: which spectra can be compared, prototypes, and the tables of the final report

- Date: 2026-11-16. Git commit: `8f61336` (branch `merge-desktop-tracks`; working tree holds other agents' uncommitted B7 files and my new `tests/acceptance/m11/`). Prompt in force for this note: `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` (written in the same run).
- Related: `prompts/001` §1 ("Exact per encoding") and §5; `docs/report-{1,3,5,5-addendum,7,9}*.md`; `results/rishon/ks_projection.json`; `reports/research/200` (rishon model), `300` (fuzzy model), `400` (LSH model); companion note `reports/research/007-fuzzy-headline-rule-clifford-offsets.md`.
- Planner scripts and raw numbers (gitignored): `scratch/planner/c009/` — `proto_ks_cross.{py,json}`, `proto_link_compression.{py,json}`, `proto_embed2.py`, `proto_rishon_ks_limit.{py,json}`, `proto_rishon_closed_limit.{py,json}`, `proto_fuzzy.{py,json}`, `proto_fuzzy_gap.{py,json}`, `proto_limits2.py`, `proto_headline_step.{py,json}`, `validate_results.{py,log}`, `out/{spectra,gate-table}.json`, reference implementation `shim/proto/{ks,embed,limits,report}.py` with `shim/shim_plugin.py`. Every run: `taskset -c 0-5 tools/run-capped python <script>` (cap $\le8$ GB), conda env `coding`, BLAS threads 1, machine omnicommander shared with another session (wall times are upper bounds).

Words used. *Kogut–Susskind (KS)* = the standard Hamiltonian lattice gauge theory, here truncated to link spins $j\le\tfrac12$; *quantum link model (QLM)* = gauge theory whose link has a finite Hilbert space built from fermions (*rishons*); *fuzzy gauge theory* = the model of arXiv:2308.05253 whose link wavefunction is a $4\times4$ matrix; *level* = eigenvalue of a Hamiltonian; *closed sector* = states with no flux on the 8 outer links; *isometry* = matrix $V$ with $V^\dagger V=1$; *compression* of $X$ = $V^\dagger XV$; *leak* = $(1-VV^\dagger)XV$; *cross-verdict* (my label) = evaluator verdict of one encoding's circuit against another encoding's target; *headline* = the archive entry a report quotes (smallest robust key, METHODS §12.4); *$\bar T$* = T count at $\varepsilon=10^{-6}$ averaged over the 20 locked angle pairs.

## 1. Sources (all opened and read in this run unless marked "abstract only")

| Source | Used for | Where |
|---|---|---|
| Alexandru, Bedaque, Carosso, Cervia, Murairi, Sheng, "Fuzzy gauge theory for quantum computers", arXiv:2308.05253v4, Phys. Rev. D 109, 094502 (2024), doi:10.1103/PhysRevD.109.094502 (full text read) | (i) Eq. (34): $aH=\tfrac{\eta g^2}2\sum_\ell K(\ell)\pm\tfrac\eta{2g^2}\sum_P\square(P)+{\rm h.c.}$; (ii) Sec. IV: whether the fuzzy theory equals ordinary gauge theory in the continuum limit "is a dynamical question … difficult to settle"; Sec. VI: clear evidence for the correct continuum limit "has not yet been possible"; (iii) Sec. IV B: $K_1$ "does not completely lift the degeneracy of the ground state in the one-plaquette system; a twofold degeneracy … remains", $K_2$ lifts it; (iv) Fig. 3 and text: single-plaquette gap of the fuzzy model with $K_2$ closes as $g^2\to0$ with $a\Delta E\sim g^{14}$ (log-log slope 7 in $g^2$, "fourth-order perturbation theory in $g^4$"), while the gaps of the $j_{\max}$ truncations diverge | §4 |
| Brower, Chandrasekharan, Wiese, "QCD as a quantum link model", arXiv:hep-th/9704106, Phys. Rev. D 60, 094502 (1999) (abstract re-read here; Secs. 2, 4 read for research 200) | the QLM is a different regularisation; ordinary gauge theory is reached by dimensional reduction from a fifth dimension, not by a limit of the link space on a fixed lattice | §5 |
| Brower, Chandrasekharan, Riederer, Wiese, "D-theory: field quantization by dimensional reduction of discrete variables", arXiv:hep-lat/0309182, Nucl. Phys. B693 (2004) 149 (abstract only) | same statement, general form | §5 |
| Wiese, arXiv:1305.1602, Ann. Phys. (Berlin), doi:10.1002/andp.201300104 (Sec. 4.3 read for research 200, 203) | the det term of the SU(2) QLM (project symbol $\lambda_D$) | §3 |
| Zache, Van Damme, Halimeh, Hauke, Banerjee, arXiv:2104.00025, Phys. Rev. D 106, L091502 (2022) (abstract only) | for U(1) quantum link models the route to the Wilson/KS theory is the limit of large link spin $S$; quoted only to say that no analogous large-representation limit exists inside our fixed two-rishon SU(2) link | §5 |
| Bravyi, DiVincenzo, Loss, "Schrieffer–Wolff transformation for quantum many-body systems", arXiv:1105.0675, Ann. Phys. 326 (2011) 2793 (abstract only; standard result) | low-energy effective Hamiltonian of a band separated by a gap $\Delta$: first order $PHP$, second order $O(\|QVP\|^2/\Delta)$ | §3 |
| Bauer, Fike, "Norms and exclusion theorems", Numer. Math. 2 (1960) 137–141, doi:10.1007/BF01386217 (statement checked on the Wikipedia and Encyclopedia of Mathematics pages) | eigenvalues of $A$ lie within $\|A-B\|_2$ of the spectrum of a normal $B$ | §2 |
| Raychowdhury, Stryker, arXiv:1912.06133 (read for research 400) | LSH = the same KS model | §2 |

Not found in the literature (searched: arXiv listing pages of the sources above and their abstracts): the compression identity of §3.1 and the KS limit of the two-rishon SU(2) link with a det term (§3.2), and the flavour-sector statement of §4.1. They are **my own derivations**, checked numerically below; the reports must present them as such.

## 2. Same model (twelve, spinnet, LSH): prototype `proto_ks_cross.py` (peak 0.80 GB)

All three encodings list the 433 states in the label order of `physical_basis(convention="cg")` (checked: label lists equal). Signs: $H_B^{\rm twelve}=D_eH_B^{(e)}D_e$ with $D_e=$ `Encoding.gauge`.

| Check | Result | Tolerance proposed |
|---|---|---|
| largest pairwise difference of the 433 sorted levels of $H(g^2)$, outer electric included, $g^2=0.5,1,2$ | $2.8\times10^{-14}$, $1.2\times10^{-14}$, $2.7\times10^{-14}$ | $10^{-10}$ |
| $\max|H^{\rm twelve}-D\,H^{(e)}D|$ (matrix level) | spinnet $5.3\times10^{-15}$, LSH $1.8\times10^{-15}$ | — (already locked in M3/M7 through `gauge_align`) |
| $H_B$ multiplicities for each encoding | $-2$ (16), $-1$ (96), $-\tfrac12$ (16), 0 (177), $\tfrac12$ (16), 1 (96), 2 (16) for all three | exact |
| $\|T_{s\to d}-V_d\|_2$, six ordered pairs, orders 1 and 2, three angle pairs | $\le3.0\times10^{-15}$ | $10^{-10}$ |
| cross-verdict, general step circuits: twelve vs LSH target; spinnet vs twelve; LSH vs spinnet; twelve vs spinnet | `total_error` $2.72\times10^{-13}$; $1.10\times10^{-14}$; $1.65\times10^{-14}$; $2.72\times10^{-13}$; all `ok`, `certified`; 6.2 s, 0.6 s, 0.5 s, 2.1 s | $10^{-10}$ |
| same circuits, foreign target at $\beta+10^{-6}$ | rejected (`reason` "error"), block error $2.000000001\times10^{-6}$ to $2.000000003\times10^{-6}$ | $[1.9,2.1]\times10^{-6}$ |
| cross-verdict, compressed headline circuits: spinnet `r02-F1-002` vs LSH target; twelve `r05-F2-005` (reads 4 outer bits) vs spinnet target | $4.8\times10^{-15}$ (0.3 s); $1.04\times10^{-13}$ (6.8 s) | $10^{-10}$ |

Why the block error of the negative control is $2\times10^{-6}$: $\|e^{-i(\beta+\delta)H_B}-e^{-i\beta H_B}\|_2=2\sin(\|H_B\|\delta/2)=\|H_B\|\delta+O(\delta^3)$ with $\|H_B\|=2$.
Why no eigenvalues are extracted from circuits: with $B=e^{i\varphi}V$ unitary (normal), Bauer–Fike gives $\min_\lambda|\mu-\lambda|\le\|A-B\|_2$ for every eigenvalue $\mu$ of the circuit block $A$; `total_error` bounds $\|A-B\|_2$. The evaluator does not expose $A$, and changing it would change a hashed file inside the consolidation window (prompts/008 §13) — rejected.

## 3. Rishon (SU(2) QLM + det) against KS

### 3.1 Link compression (prototype `proto_embed2.py`, `shim/proto/embed.py`; < 5 s)
Definition and identities: METHODS §13.2. Measured residuals (max over entries): isometry $4.4\times10^{-16}$; $V^\dagger U_{ab}V-cU^{\rm KS}_{ab}$ $3.3\times10^{-16}$; generators $2.2\times10^{-16}$; $H_E$ $3.3\times10^{-16}$; $[P,L_a],[P,R_a]$ exactly 0; plaquette (625 × 625) $4.7\times10^{-16}$. Leak: $\|(1-P)U_{ab}V\|_2^2=0.500000000000$; $\|(1-P^{\otimes4})WV^{\otimes4}\|_2^2=15.000000000$ (Gram difference). `rishon_minus` needs $c=i$: the map $S=\prod_\ell e^{i\frac\pi4(n_R-n_L)}$ of METHODS-rishon R13 sends $(A+B)/\sqrt2\to-i(A-B)/\sqrt2$ and $U\to iU$. The det term is $+2$ / $-2$ on the two singlets and 0 on the quartet, and commutes with $P$ (measured 0.0). The same statement on the 38 432 physical states is the M5 side check `results/rishon/ks_projection.json` (variant "plus": projected $H_E$ and $H_B$ equal KS to $1.4\times10^{-13}$ and $1.8\times10^{-15}$, leak $\|(1-P)H_BP\|_2=5.2915=\sqrt{28}$).

### 3.2 KS limit with the det term (derivation in METHODS §13.3)
Rule: $\lambda_D=-L$, $c_E=g^2/2-8L/3$, $c_B=1/g^2$; compare $H+24L$ (full) or $H^{\rm closed}+8L$ with KS.

Closed sector, `proto_rishon_closed_limit.py` (17 × 17 from the formula of R13 with independent couplings; its spectrum equals `rishon.operators.closed_block_full` at the project couplings in 9 cases to $10^{-12}$). $L\,(\lambda_k(L)-\lambda_k^{\rm KS})$ for $k$ = lower, upper level against the prediction $-\tfrac{13}{4g^4}w_k$:

| $g^2$ | prediction | $L=128$ | $L=256$ | $L=1024$ | relative error at 256 | slope $128\to256$ |
|---|---|---|---|---|---|---|
| 0.5 | $-5.8933$, $-7.1067$ | $-5.9134$, $-7.0947$ | $-5.9035$, $-7.1009$ | $-5.8958$, $-7.1053$ | 0.17 %, 0.08 % | $-1.0024$, $-0.9987$ |
| 1.0 | $-1.0544$, $-2.1956$ | $-1.0573$, $-2.1972$ | $-1.0559$, $-2.1964$ | $-1.0548$, $-2.1958$ | 0.14 %, 0.04 % | $-1.0019$, $-1.0005$ |
| 2.0 | $-0.06823$, $-0.74427$ | $-0.06832$, $-0.74647$ | $-0.06827$, $-0.74537$ | $-0.06824$, $-0.74455$ | 0.07 %, 0.15 % | $-1.0010$, $-1.0021$ |

The error of the prediction halves with every doubling of $L$ (remainder $O(1/L)$). Third level minus second: $4L-\lambda_{\rm upper}^{\rm KS}+\delta$, $\delta\le0.055$ at $L=128$.

Full space, `proto_rishon_ks_limit.py` (38 432 states; 305 dynamical blocks, largest 4352, dense `eigvalsh` per block; 106 s for 18 diagonalisations, 5.5 s each, peak 0.55 GB). $\max_k|\lambda_k(L)+24L-\lambda_k^{\rm KS}|$ over the 433 lowest levels, times $L$:

| $g^2$ | $L=4$ | 16 | 64 | 128 | slope $64\to128$ | gap to level 434 at $L=128$ |
|---|---|---|---|---|---|---|
| 0.5 | 6.223 | 6.976 | 7.0814 | 7.0947 | $-0.9973$ | 502.47 ($4L-9.53$) |
| 1.0 | 2.195 | 2.206 | 2.1988 | 2.1972 | $-1.0010$ | 504.74 ($4L-7.26$) |
| 2.0 | 0.816 | 0.762 | 0.7487 | 0.7465 | $-1.0043$ | 502.40 ($4L-9.60$) |

At $L=128$ the full-space numbers equal the closed-sector upper-level numbers of the previous table to all digits shown (7.0947, 2.1972, 0.74647): the slowest of the 433 levels is the upper closed-sector level. So the analytic coefficient $\tfrac{13}{4g^4}w_{\rm upper}$ predicts the full-space error to 0.17 %, 0.08 %, 0.30 %.

Reading. In the three-coupling family the rishon model contains the KS $j\le\tfrac12$ theory as an exact limit. At the project's nominal point ($c_E=g^2/2$, $\lambda_D=0.43$) it is far from that limit: Report 5 §3.4 and `ks_projection.json` (step distance 1.990). Honest sentence for the report: "same link algebra after compression, different dynamics; equal only in the limit $|\lambda_D|\to\infty$ with a tuned electric coupling."

## 4. Fuzzy against KS

### 4.1 Link compression and flavour sectors
`proto_embed2.py`: three pairs of embeddings (table in METHODS §13.2), all residuals $\le4.7\times10^{-16}$; leaks exactly $\tfrac12,\tfrac{33}8$ (singlets $\tfrac12\mathbb 1$, $\tfrac12\Gamma_5$) and $1,4$ (flavour copies). `proto_limits2.py`, $r=0$, all 16 flavour patterns $(F_b,F_r,F_t,F_l)$ at $g^2=0.5,1,2$: closed-sector dimension 2 with spectrum equal to the KS block ($\le1.8\times10^{-15}$) for $(+,+,-,-)$ and $(-,-,+,+)$; dimension 4 for $(+,-,-,+)$, $(-,+,+,-)$ (distance of the KS levels from the spectrum 3.69, 1.48, 0.608); dimension 3 for the other twelve (4.17, 2.27, 1.15). Explanation by Gauss's law at the corners: METHODS §13.4 (a). This settles the open observation of Report 9 §3.5.

### 4.2 Isolated plaquette (50 states), gap against coupling (`proto_fuzzy.py`, `proto_fuzzy_gap.py`)
Project normalisation $H=\tfrac{g^2}4\sum_\ell(a\mathcal K_1+b\mathcal K_2)-\tfrac2{g^2}\square$ (the paper's Eq. (34) differs by constant factors, which do not change exponents). Spectra on the 50 states: $\square$: $\pm4$ (2 each), $\pm2$ (12), $\pm1$ (2), 0 (18); $\sum\mathcal K_1$: 0 (16), 4 (16), 6 (16), 8 (2).

| kinetic term | gap $E_1-E_0$ at $g^2=0.15$, 0.2 | exponent $d\ln{\rm gap}/d\ln g^2$ | gap$/(g^2)^7$ | strong coupling |
|---|---|---|---|---|
| $\mathcal K_2$ only ($a=0,b=1$) | $8.405\times10^{-9}$, $6.298\times10^{-8}$ | 7.0004 (then 7.002, 7.007, 7.019 up to $g^2=0.5$) | 0.00492 | gap $\to2g^2$ |
| $\mathcal K_1+\mathcal K_2$ (project, $r=1$) | $8.492\times10^{-9}$, $6.414\times10^{-8}$ | 7.029 | 0.00497 | gap$/2g^2=0.9999973$ at $g^2=16$ |
| $\mathcal K_1+\tfrac12\mathcal K_2$; $\mathcal K_1+2\mathcal K_2$ | $5.307\times10^{-10}$; $1.359\times10^{-7}$ at 0.15 | 7.028; 7.030 | ratio to $r=1$: $1/16.001$; $16.002$ | — |
| $\mathcal K_1$ only ($r=0$) | $\le7\times10^{-15}$ at every $g^2$ tried (0.5 to 16) | — (twofold degenerate ground level) | — | third level 7.81, 3.60, 0.845 above at $g^2=0.5,1,2$ |
| KS closed block, for contrast | $2\sqrt{9g^4/16+4/g^4}$: 26.7, 20.0 | $-1$ | — | gap $\to\tfrac32g^2$ |

These reproduce the paper's three statements: exponent 7 ("slope of 7"), fourth order in the $\mathcal K_2$ coupling (factor 16 per doubling), and the twofold degeneracy left by $\mathcal K_1$. Numerical care: at $g^2=0.15$ the gap is $10^{-9}$ of the level scale; computing the levels of $-\square+\tfrac{g^4}8(a\mathcal K_1+b\mathcal K_2)$ and multiplying by $2/g^2$ keeps the relative error of the gap near $10^{-6}$.

### 4.3 No KS limit inside $a\mathcal K_1+b\mathcal K_2$
Measured (`proto_embed2.py`): $\mathcal K_2=-4$ on $\tfrac12\mathbb 1$, $+2$ on the four states $\mathcal U_{ab}\tfrac12\mathbb 1$ (eigen-residual 0.0), $+4$ on $\tfrac12\Gamma_5$, $-2$ on $\mathcal U_{ab}\tfrac12\Gamma_5$; $\mathcal K_1=\tfrac32$ on all eight flux states; $\langle\mathcal U_{cd}\tfrac12\Gamma_5|\,\mathcal U_{ab}\,|\tfrac12\mathbb 1\rangle=0$ and the mirror element 0. Link levels of $a\mathcal K_1+b\mathcal K_2+4b$ with $a=1-\tfrac43b$: $\{0,\tfrac32^{4},(2+\tfrac43b)^{6},(\tfrac32+4b)^{4},8b\}$: the four states at $\tfrac32$ are the $\Gamma_5$ flux copy, which the plaquette does not reach from the singlet at 0. Scan of the closed sector from $\Omega$ at $g^2=1$ (`proto_fuzzy.py`): with $a=1-\tfrac43b$, $b=32$: lowest levels $-0.031,1.299$ (KS: $-1.386,2.886$) — the trivial limit; with $a=1-4b$ (the $\mathbb 1$ flux copy at the KS energy) the levels run to $-\infty$. Conclusion of METHODS §13.4 (c).

## 5. What can and cannot be compared (design decision (i) of the request)

| Comparison | Status | Evidence |
|---|---|---|
| twelve = spinnet = LSH: all 433 levels, all step unitaries, all circuits | exact agreement, $\le10^{-10}$ | §2 |
| KS link algebra inside the rishon link and the fuzzy link | exact identity (compression), leak quantified | §3.1, §4.1 |
| rishon $\to$ KS: 433 lowest levels | limit $|\lambda_D|\to\infty$ with tuned electric coupling, error $\tfrac{13}{4g^4}w/L$ | §3.2 |
| fuzzy $r=0$, flavour sectors $(\pm,\pm,\mp,\mp)$: closed sector | exactly the KS block | §4.1 |
| fuzzy with $\mathcal K_2$: weak-coupling gap | qualitatively opposite to KS: closes as $g^{14}$, KS diverges as $4/g^2$ (the design aim of the fuzzy model, paper Sec. IV) | §4.2 |
| electric energy of one flux link, $\tfrac38g^2$ (fuzzy: the $\mathcal K_1$ part), and of the closed loop, $\tfrac32g^2$ (fuzzy: at $r=0$) | equal in all three models (Reports 5, 9) | existing |
| closed-sector spectra at equal $g^2$ (KS 2 levels; rishon 17; fuzzy 9 or 12), shared observables after one step, state counts, gate counts across models | different physics: tabulate side by side, never as agreement or as efficiency | Reports 5, 9; `ks_projection.json` |
| continuum limit | not testable on one plaquette; QLM: dimensional reduction (hep-th/9704106, hep-lat/0309182); fuzzy: conjecture (2308.05253 Sec. IV, VI) | §1 |

## 6. Tables of the final report (design decision (ii))

Decision: **one gate table in three model blocks** (A like for like; B and C marked "different model"), a second table for the CX-first against T-first picks, a third for the spectra cross-check. Prototype values, produced by `validate_results.py` from the committed general-circuit files and the tester's scratch copy of the robust caches (`scratch/t419/rootnew`, evaluator hashes of step B6; the final numbers must come from `results/compress/<enc>/robust.json` after prompts/008 Phase C):

| block | encoding | general step: qubits, CX, rotations, fixed T, $T(10^{-6})$ | headline: entry, qubits, CX, $T$ nominal, $\bar T$ | T-first pick: entry, CX, $\bar T$ | missing |
|---|---|---|---|---|---|
| A | twelve | 34, 294, 10, 312, 952 | `r05-F2-005`, 31, 111, 912, 927.4 | `r00-seed-001` (imported seed lean22_v2), 162, 666.6 | Phase C cache |
| A | spinnet | 15, 54, 8, 56, 566 | `r02-F1-002`, 17, 31, 1086, 1092.0 | `r01-F5-001`, 46, 486.7 (not angle-linear) | — |
| A | LSH | 19, 94, 8, 88, 598 | pending (M8; round-0 best known 71 CX) | pending | Report 8 |
| B | rishon (QLM + det) | 26, 10 134, 174, 10 218, 21 146 (two-layer unit: 10 102, 166, 10 218, 20 650) | `r04-F1-004`, 53, 228, 846, 843.8; with det layer 260 CX, 1342 nominal (tester's run) | same entry (one point) | Report 6: replay C2, `three-layer.json` |
| C | fuzzy ($r=1$) | 23, 1862, 56, 1826, 5398 | `fuzzy_ub:r10-F1-010` + 4 × `fuzzy_link:r02-F2-001`: 18 qubits, 131 CX, 49 rotations, 72 fixed T, 3214 nominal, $\bar T=634.4+4\times628.8=3149.6$ | `fuzzy_ub:r13-F3-013` (89 CX, 514 nominal, $\bar T$ 520.0) + 4 links: 137 CX, 3090 nominal, $\bar T=3035.2$ | Report 10 update, `compressed_step_headline.json` |

Composed fuzzy steps verified in `proto_headline_step.py` with the M9 sampled composition check (seed 20261104, 40 inputs): headline units err $1.2\times10^{-14}$, Gauss $5.9\times10^{-15}$, with outer rows 227 CX, 129 rotations, depth 151, 50 qubits; archive-best units ($U_B$ `r12-F1-012`) identical counts, depth 150; T-first units 233 CX with outer rows, 137 inner.

CX–$\bar T$ Pareto fronts (same scratch caches): twelve (111, 927.4), (121, 745.6) `r02-F4-002`, (162, 666.6); spinnet (31, 1092.0), (32, 847.4), (34, 665.6), (42, 609.1), (44, 553.1), (46, 486.7); rishon (228, 843.8); fuzzy_ub (83, 634.4), (89, 520.0); fuzzy_link (12, 628.8).

## 7. Validation of the locked tests before the builder starts

Reference implementation served under the production names by `scratch/planner/c009/shim/shim_plugin.py`:
`PYTHONPATH=scratch/planner/c009/shim tools/pytest-safe -p shim_plugin -n 4 -m "not slow" tests/acceptance/m11/test_cross_ks.py tests/acceptance/m11/test_cross_models.py` → 21 passed in 107 s (4 workers, shared machine; slowest: E3 51 s, F2 37 s, K3[twelve] 16 s); `test_headline_rule.py::test_M11_H1` → passed in 0.7 s. Whole folder with the plugin, slow tests included (`-n 4`, log `shim_full_run.log`): 24 passed, 9 failed with `PENDING:` (K4 × 3, H2 × 2, H3: no cached headline; R1, T1, T2: result files missing), 121 s; slowest F2 68 s, E3 43–67 s per coupling, K3[twelve] 24 s on the shared machine. Without the plugin: `tools/pytest-safe -n 2 tests/acceptance/m11` → 33 failed, 33 messages starting `PENDING:`; `pytest --collect-only -q tests/acceptance` → 407 tests, no error; `python tools/check_lock.py` → LOCK OK (m11 is not locked yet). The checkers of `test_cross_results.py` and the H2 logic were run on prototype files by `validate_results.py` (log beside it). Not validated end to end (they need files that do not exist yet): K4, H2, H3, R1, T1, T2 as pytest items; their logic was exercised by `validate_results.py` (cross-verdicts of the two existing headline circuits at both angle pairs, both checkers, the H2 assertions) and `proto_headline_step.py` (the H3 numbers).

# Report 12 — Final project report: one SU(2) plaquette in five encodings, verified and compressed

- **Date:** 2026-11-22.
- **Git commit:** `3ccce75` (branch `merge-desktop-tracks` = `master`; `git rev-parse --short HEAD`). Nothing was computed for this report: every number is copied from a committed file named next to it. "Trivial arithmetic" (a sum, difference or percentage of cited numbers) is marked where it appears.
- **Tags:** `milestone-0`, `milestone-1`, `milestone-2`, `milestone-2-gate`, `milestone-2c`, `milestone-3`, `milestone-4`, `milestone-5`, `milestone-5x`, `milestone-5d`, `milestone-6`, `milestone-7`, `milestone-8`, `milestone-9`, `milestone-10`, `milestone-11` (at `9b83d10`). Latest lock of the acceptance tests: `acceptance-v23`.
- **Plans in force** (the table in `notes/STATUS.md`, updated with the tags `milestone-2c` and `milestone-6`, which exist but are missing from that table; one plan series per track, by number range):

| Track | Range | Plan in force | Locked tests | Milestones done |
|---|---|---|---|---|
| twelve (M0–M2) + cross-track | 000–099 | `prompts/006` (+007 m9 erratum, 008 consolidation, 009 final report M11, 010 fuzzy headline rule) | m0, m1, m2, m11 | milestone-0, -1, -2, -2-gate, -2c, -11 |
| spin network (M3/M4) | 100–199 | `prompts/104` (§11 errata E1–E3) | m3, m3x, m4 | milestone-3, -4 |
| rishon (M5/M6) | 200–299 | `prompts/205` on 204 on 203 | m5, m5x, m6 | milestone-5, -5x, -5d, -6 |
| fuzzy (M9/M10) | 300–399 | `prompts/302` | m9, m10 | milestone-9, -10 |
| LSH (M7/M8) | 400–499 | `prompts/402` on 401 (on 400) | m7, m8 | milestone-7, -8 |

- **Detailed reports (this report only summarises them):** Report 1 `docs/report-1-twelve-qubit-general-circuit.md`; Report 2 `docs/report-2-twelve-qubit-compression.md`; Report 3 `docs/report-3-spinnet-general-circuit.md`; Report 4 `docs/report-4-spinnet-compression.md`; Report 5 `docs/report-5-rishon-general-circuit.md` and its addendum `docs/report-5-rishon-general-circuit-addendum-det.md`; Report 6 `docs/report-6-rishon-compression.md`; Report 7 `docs/report-7-lsh-general-circuit.md`; Report 8 `docs/report-8-lsh-compression.md`; Report 9 `docs/report-9-fuzzy-general-circuit.md`; Report 10 `docs/report-10-fuzzy-compression.md`; Report 11 `docs/report-11-cross-encoding-comparison.md` (FINAL; the authority for every cross-encoding number below).
- **Milestone-11 gate:** tester `reports/tests/448` (PASS: 407 of 407 locked acceptance tests, 1235 unit tests), audit `reports/audits/309` (PASS WITH NOTES), benchmark `reports/benchmarks/307` (PASS).

**How numbers are written.** Gate counts (CX, T, rotations, qubits) are exact integers, so they carry no uncertainty. Errors are dimensionless operator norms (the largest possible deviation of the circuit from the exact target over unit-length inputs, after removing one overall phase); the pass tolerance is $10^{-10}$ unless stated. The only quoted uncertainty is the standard error of $\bar T$ (defined below). Angles are in radians.

## Terms (each defined once)

- **Plaquette, inner and outer links.** The smallest closed loop of a square lattice: 4 *inner* links; 8 *outer* links leave its 4 corners (two per corner), 12 links in total.
- **SU(2) gauge theory, Kogut–Susskind (KS) Hamiltonian.** The standard lattice Hamiltonian $H=\frac{g^2}{2}H_E+\frac{1}{g^2}H_B$ with electric part $H_E=\sum_\ell j_\ell(j_\ell+1)$ and magnetic (plaquette) part $H_B=-(\mathrm{Tr}\,U_P+\mathrm{h.c.})$; $g^2$ is the coupling (Paulo Eq. 16; `docs/METHODS.md` §2). Each link carries a spin $j$; the *truncation* $j_{\max}=\tfrac12$ keeps $j\in\{0,\tfrac12\}$.
- **Gauss law, physical state.** At each corner the total SU(2) charge of the links meeting there must be zero. States that obey this are *physical*. KS at $j_{\max}=\tfrac12$ on this plaquette has $433$ physical states (Report 1; Lean-counted).
- **Trotter step.** One factor of the product formula that approximates the time evolution by alternating simpler exponentials. Here the first-order step is $U_B(\beta)\,U_E(\alpha)$ with $U_E(\alpha)=e^{-i\alpha H_E}$, $U_B(\beta)=e^{-i\beta H_B}$, $\alpha=g^2dt/2$, $\beta=dt/g^2$; the electric layer acts first. *Nominal angles:* $(\alpha,\beta)=(0.37,0.61)$, with alternates $(0.91,0.23)$ and $(1.70,1.00)$ (`prompts/001` §1).
- **Encoding.** A rule that stores the physical states in qubits. The five: **twelve** = Paulo's 12-qubit encoding, 3 qubits $(j,m,m')$ per inner link (Digonto's decision 2026-11-04); **spin network** = one qubit per link plus one per corner (the corner's coupling of its four spins, from $6j$ recoupling coefficients); **LSH** = loop-string-hadron encoding (Raychowdhury and Stryker, arXiv:1912.06133): gauge-invariant integer "loop numbers" on split corners, 3 qubits per site; **rishon** = the SU(2) *quantum link model* (QLM; a gauge theory whose link space is built from fermions called rishons at the two link ends; Brower, Chandrasekharan, Wiese, arXiv:hep-th/9704106) plus the determinant ("det") term $\lambda_DH_D$ (Wiese, arXiv:1305.1602), 4 qubits per link; **fuzzy** = the fuzzy gauge theory of Alexandru et al. (arXiv:2308.05253), whose link state is a $4\times4$ matrix (4 qubits per link), with kinetic terms $\mathcal K_1+r\mathcal K_2$, $r=1$.
- **CX (CNOT).** The two-qubit controlled-NOT gate, the costly gate on most hardware; the project compares it first.
- **Clifford+T, T gate, gridsynth.** The Clifford+T gate set (H, S, CX and T) is the usual gate set of an error-corrected machine; the T gate is its expensive gate. A rotation by an arbitrary angle must be approximated by a string of these gates. **pygridsynth** (version 1.2.0) is the program that does this with the Ross–Selinger algorithm (arXiv:1403.2975). The **T count at accuracy** $\varepsilon$ is $T=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$: T gates already in the circuit plus those of every synthesised rotation, about $3\log_2(1/\varepsilon)$ per rotation. Here $\varepsilon=10^{-6}$ per rotation, written $T(10^{-6})$.
- **$\bar T$.** The mean of $T(10^{-6})$ over 20 fixed random angle pairs (seed 20261107, $\alpha\in[0.05,2.0)$, $\beta\in[0.05,1.2)$), quoted $\pm$ its standard error $s/\sqrt{20}$ ($s$ = sample standard deviation of the 20 values; Report 11, Terms). It removes the luck of one angle pair.
- **Ancilla.** A helper qubit that starts and must end in $|0\rangle$.
- **Compression loop, proposer, archive, entry, family.** The program search of Gu, Kemeny, Yelin and Lukin (arXiv:2610.22367): AI *proposer* sessions (Claude Code agents) write small Python programs that build a circuit; a fixed *evaluator* checks each circuit exactly on all physical states (error $\le10^{-10}$ after one global phase, ancillas back to $|0\rangle$, same gate skeleton at three angle pairs) and scores it; valid circuits are kept in an *archive* as *entries* with ids like `r05-F2-005` (round 5, family F2, program 005). *Families* (F1, F2, ...) are design lines; the labels are the project's.
- **Robust key, headline, T-first pick, Pareto point (project labels, not standard terms).** The *robust key* of an entry is $(\mathrm{CX},\ \sum_{i=1}^{20}T_i,\ \rho,\ \sum_i\mathrm{depth}_i,\ \text{qubits})$, compared first entry first; $\rho=0$ if every rotation angle is a linear function of $\alpha,\beta$ with no constant term (*angle-linear*), else $\rho=1$. The *headline* of an archive is its valid entry with the smallest robust key (CX first). The *T-first pick* is the entry with the smallest $\sum T_i$, then CX. A *Pareto point* is an entry not beaten in both CX and $\bar T$ by another (`docs/METHODS.md` §12.4; `prompts/010`).
- **Lean certificate.** Lean 4 is a proof assistant. *Kernel-checked* = proved by Lean's small trusted core from definitions. *Native-certified* = a compiled checker program written in Lean, run through `native_decide`, accepted a certificate stating the exact action of one circuit's gate list on every physical state, for all angles of its angle-linear gate family; the trust root is the Lean compiler plus the checker source (`docs/METHODS.md` §11.5). `n_a` = no certificate exists for that circuit.

## 1. What was asked

Goal (`notes/STATUS.md` "Goal"; plan `prompts/001-plaquette-five-encodings-plan.md`, approved by Digonto 2026-11-04): for one SU(2) plaquette with 8 outer links at $j_{\max}=\tfrac12$, and for each of five encodings (twelve, spin network, rishon, LSH, fuzzy), (a) build the circuits of one Trotter step, verify them on every Gauss-law state, count CX and T gates, and report; (b) compress them with a Gu-et-al.-style LLM program-search loop and report before and after. Digonto later added (decision 2026-11-16, option (c)) a final cross-encoding comparison of gate counts and energy spectra, which is Report 11. This report closes the project.

## 2. What was done

### 2.1 Shared machinery
One evaluator for the tests and all loops (`docs/METHODS.md` §6, §9, §12): exact sparse state-vector simulation on all physical states; pass if error + leaked amplitude + simulator pruning bound $\le10^{-10}$ at exact angles, or $\le N_{\rm rot}\varepsilon+10^{-9}$ after Clifford+T synthesis ($N_{\rm rot}$ = number of rotations). Independent second engines (the testers' own simulators, Qiskit-Aer) re-checked every delivered circuit. Lean 4 proved the state counts and circuit structure (kernel-checked) and certified single circuits (native-certified) where an exporter exists. A consolidation (`prompts/008`) moved all encodings onto one registry and one headline rule.

### 2.2 Per encoding: general circuit, verification, counts
Counts at the nominal angles, $\varepsilon=10^{-6}$; source `results/summary/encodings-gate-counts.md` Table 1 (commit `b8e8d76`) unless stated. **Qubit counts in this section follow the summary table** (`step.json`: the register qubits of the step, without the outer-link register); the main table of §3.1 follows Report 11 and `robust.json`, which add the evaluator's whole outer-link register (16 qubits for twelve, 8 for spin network, 12 for LSH, 32 for rishon) whether or not the circuit reads it. The fuzzy inner step has no outer register in either column, so its two numbers agree.

- **Twelve (Report 1; `results/twelve/step.json` @ `a9702e5`).** $U_E$ = one phase per inner link; $U_B$ = Paulo's notebook ported, his two multi-controlled rotations replaced by an exact `rccx`–`crx`–`rccx` form. Step: 34 qubits (12 data + 22 helpers, outer links read only), 294 CX, 10 rotations, $T(10^{-6})=952$, error $2.7\times10^{-13}$ on all 433 states. Like for like with Paulo's compiled $U_B$ ($\beta=1$, same Qiskit Clifford+T pass): 662 T against 1162 T at the same 294 CX (Report 1 §3.4).
- **Spin network (Report 3; `results/spinnet/step.json` @ `d82a472`).** A 3-CX frame turns the pair flip into one $X$; seven flag ancillas; a 4-rotation phase walk with angles solved from the plaquette matrix, $(-\tfrac72,-1,3,\tfrac32)\beta$. Step: 15 qubits, 54 CX, 8 rotations, $T(10^{-6})=566$, error $1.1\times10^{-14}$ on 433 states.
- **Rishon (Report 5 + addendum; `results/rishon/step.json` @ `b4c1917`, `step3.json` @ `6fea036`).** 48-qubit Jordan–Wigner register (the standard fermion-to-qubit map); $U_B$ = 81 commuting two-level rotations, each a multi-controlled rotation with a Toffoli ladder. Two-layer step $U_BU_E$: 26 qubits touched, 10 102 CX, 166 rotations, $T(10^{-6})=20\,650$, error $4.1\times10^{-13}$. With the det layer $U_D$ (Digonto 2026-11-10): 10 134 CX, 174 rotations, $T(10^{-6})=21\,146$, error $5.0\times10^{-13}$. Verified on all 1296 inner codes, which by a proved inequality covers all $38\,432$ physical states (METHODS-rishon R6); Gauss law of outputs checked on 273 sampled states.
- **LSH (Report 7; `results/lsh/step.json` @ `76fd221`).** A *transcoder* (project label; `cx, cx, rccx` on each of the 4 sites, 5 CX and 4 T per site, 20 CX and 16 T in all) rewrites LSH bits into spin-network bits, then comes the spin-network walk, then the inverse transcoder (the two transcoders add 40 CX and 32 T; Report 7 §3.4). Step: 19 qubits, 94 CX, 8 rotations, $T(10^{-6})=598$, error $1.6\times10^{-14}$ on 433 states. 433 physical states counted twice in Lean by different rules.
- **Fuzzy (Report 9; `results/fuzzy/step.json` @ `8e71c38`, dirty tree, reproduced by tester 301).** $U_B=e^{+2i\beta\square}$ built from three conserved parities and 8 sectors with Clifford sector unitaries (only 16 angle-dependent rotations). Inner step: 23 qubits, 1862 CX, 56 rotations, $T(10^{-6})=5398$, error $1.0\times10^{-14}$. The layers are certified as full unitaries; the composed step is checked on 40 seeded inputs only (label `blocks_certified_composition_sampled`).

### 2.3 Compression loops
| loop (report) | rounds run | programs / candidates / valid | why it stopped | headline entry |
|---|---|---|---|---|
| twelve, step (Report 2) | 0–5 | 17 / 22 / 22 | coordinator judgement ("plateau", three families at 111 CX), accepted by Digonto 2026-11-10 (`notes/STATUS.md`) | `r05-F2-005` |
| spin network, step (Report 4) | 0–5 | 16 / 23 / 23 | stop rule: 3 rounds without a better robust key (18 of 20 sessions) | `r02-F1-002` |
| rishon, unit $U_BU_E$ (Report 6) | 0–6 | 19 / 24 / 23 | stop rule: 20-session limit; round 6 still improved | `r06-F3-006` |
| LSH, step (Report 8) | 0–6 | 19 / 29 / 29 | stop rule: 20-session limit (`stop.json`, reason `max_sessions`) | `r05-F3-005` |
| fuzzy $U_B$ unit (Report 10) | 0–13 | – / 42 / 41 | closed by Digonto 2026-11-14 ("stop fuzzy since it did not move"; CX and T unchanged since round 9) | `r10-F1-010` |
| fuzzy link unit (Report 10) | 0–2 | – / 5 / 4 | no 11-CX circuit found by an exhaustive search in the proposer's model | `r02-F2-001` |

Sources: the "What was done" sections of Reports 2, 4, 6, 8, 10 and `results/summary/encodings-gate-counts.md` Table 2 ("State" column). The fuzzy step was compressed as two units because the evaluator cannot score a whole fuzzy step; the step is the composition $U_B$ unit $+\,4$ link units (inner) or $+\,12$ link units (all links).

## 3. What the results mean

### 3.1 Main table: general against compressed headline
Copied from Report 11 Tables 1a, 1b, 1c (numbers committed at `328e071`, regenerated clean, `results/crosscheck/gate-table.json`), with the same block grouping. Unit counted: first-order step on the 4 inner links, nominal angles, $\varepsilon=10^{-6}$; outer-link rows are separate (Report 11 Table 1c). Qubits = data + the whole outer-link register of the evaluator (16, 8, 12, 32 qubits for twelve, spin network, LSH, rishon; none for the fuzzy inner step) + ancillas, as the evaluator counts them; only the twelve and LSH headlines actually read outer qubits (4 and 2). Each cell reads "general $\to$ headline".

**Warning (Report 11 §3.2).** Block A is one theory (KS) written three ways and its rows are comparable like for like. Blocks B and C are *different models* with other state counts ($38\,432$ and $101\,197\,218$ against 433), other Hamiltonians and other registers. **Ratios between rows of different blocks are not efficiency statements.** Percentages are within one row only.

| block | encoding (unit) | qubits | CX (change) | rotations | $T(10^{-6})$ nominal | $\bar T\pm$ s.e. (change) | error general / headline | Lean general / headline |
|---|---|---|---|---|---|---|---|---|
| A (KS) | twelve | $50\to31$ | $294\to111$ ($-62.2\%$) | $10\to13$ | $952\to912$ | $943.2\pm2.3\to927.4\pm2.7$ ($-1.7\%$) | $2.7\times10^{-13}$ / $1.0\times10^{-13}$ | native-certified / native-certified |
| A (KS) | spin network | $23\to17$ | $54\to31$ ($-42.6\%$) | $8\to17$ | $566\to1086$ | $560.6\pm1.6\to1092.0\pm3.1$ ($+94.8\%$) | $1.1\times10^{-14}$ / $5.1\times10^{-15}$ | certified (compiled checker) / native-certified |
| A (KS) | LSH | $31\to24$ | $94\to68$ ($-27.7\%$) | $8\to22$ | $598\to1396$ | $592.6\pm1.6\to1417.4\pm8.0$ ($+139.2\%$) | $1.6\times10^{-14}$ / $1.4\times10^{-14}$ | native-certified / native-certified |
| B (QLM, different model) | rishon, unit $U_BU_E$ | $58\to52$ | $10\,102\to216$ ($-97.9\%$) | $166\to10$ | $20\,650\to832$ | $20\,620.2\pm58.8\to829.8\pm2.2$ ($-96.0\%$) | $4.1\times10^{-13}$ / $1.35\times10^{-13}$ | native-certified / native-certified (three-angle checker) |
| B (QLM, different model) | rishon, three layers with det | $58\to52$ | $10\,134\to248$ ($-97.6\%$) | $174\to18$ | $21\,146\to1328$ | $21\,121.0\to1330.6$ ($-93.7\%$; no s.e. quoted) | $5.0\times10^{-13}$ / $1.54\times10^{-13}$ | certified by composition (both) |
| C (fuzzy, different model) | fuzzy, inner step (composed) | $23\to18$ | $1862\to131$ ($-93.0\%$) | $56\to49$ | $5398\to3214$ | $5336.2\pm17\to3149.6\pm16$ ($-41.0\%$) | $1.0\times10^{-14}$ / $1.2\times10^{-14}$ (both on 40 seeded inputs) | `n_a` / `n_a` |
| C | fuzzy $U_B$ unit | $15\to10$ | $1718\to83$ | $16\to9$ | $2822\to638$ | $2821.0\to634.4\pm3.2$ | $3.8\times10^{-14}$ / $5.4\times10^{-14}$ | `n_a` |
| C | fuzzy link unit (used 4 times inner, 12 times in all) | $4\to4$ | $36\to12$ | $10\to10$ | $644\to644$ | $628.8\to628.8\pm3.8$ | $3.4\times10^{-15}$ / $5.5\times10^{-15}$ | `n_a` |

Sources per row: Report 11 Table 1a/1b/1c; errors from `results/summary/encodings-gate-counts.md` (general rows of Table 1, headline rows of Table 2), except rishon headline $1.35\times10^{-13}$ (Report 6 §3.7) and three-layer $1.54\times10^{-13}$ at the nominal triple (Report 6 §3.2, `results/compress/rishon/three-layer.json` @ `086c0fd`); fuzzy $U_B$ qubits (15 and 10) from summary Table 2 and `results/compress/fuzzy_ub/robust.json`, its general $\bar T$ from Report 11 Table 2. The fuzzy composed $\bar T$ is a sum of per-unit means ($634.4+4\times628.8$), not one average over a common angle set (Report 11 §3.6; audit 305 N8); its $\pm16$ and $\pm17$ assume independent unit scatter. Every archive headline (the six unit rows) is exact on all physical states of its encoding with error between $5.1\times10^{-15}$ and $1.4\times10^{-13}$ (audit 309 §4.2); the composed rows are checked differently (fuzzy on 40 seeded inputs; rishon three layers by composition, $1.54\times10^{-13}$). With the outer rows the composed fuzzy step is $2150\to227$ CX ($-89.4\%$), 50 qubits (Report 10 §3.3).

**Reading the table.**
- **Block A:** the loop cut CX by $62\%$ (twelve), $43\%$ (spin network) and $28\%$ (LSH), to 111, 31 and 68 CX. The spin network is the cheapest KS circuit in CX. LSH ends 37 CX above the spin network because 37 of the 40 transcoder CX survive the loop (Report 8 §3.2: wrapped spin-network headline 71 CX, LSH headline 68 CX).
- **CX was bought with T in two of three KS encodings:** spin network and LSH raised $\bar T$ by factors 1.95 and 2.39 (trivial arithmetic on the table); twelve kept it about equal ($-1.7\%$). This follows from the project's cost order (CX first, `prompts/001`), not from physics (§3.2).
- **Rishon and fuzzy** shrank most ($-97.9\%$ and $-93.0\%$ in CX) because their general circuits were built one block at a time without using structure; the loops found that structure (81 pairs reduced to one rotation on one qubit for rishon, Report 6 §3.5; 8 parity sectors sharing frames for fuzzy, Report 10 §4).

### 3.2 CX first against T first (Report 11 Table 2)
| archive | headline (CX, $\bar T$) | T-first pick (entry, CX, $\bar T$) |
|---|---|---|
| twelve | (111, 927.4) | `r00-seed-001` (imported seed), 162, 666.6 |
| spin network | (31, 1092.0) | `r01-F5-001`, 46, 486.7 (not angle-linear) |
| LSH | (68, 1417.4) | `r00-seed-002` (wrapped spin-network seed), 84, 585.1 |
| rishon unit | (216, 829.8) | `r06-F1-006`, 218, 829.2 (practically the same point) |
| fuzzy $U_B$ | (83, 634.4) | `r13-F3-013`, 89, 520.0 (not angle-linear: Clifford offsets) |
| fuzzy link | (12, 628.8) | the same entry `r02-F2-001` |

Source: Report 11 §3.3, read from `results/compress/<enc>/robust.json`; figure `results/crosscheck/tradeoff.pdf`. Under a T-first cost the answer changes for twelve, spin network, LSH and fuzzy $U_B$. A *Clifford offset* (project label) is a constant multiple of $\pi/2$ added to a rotation angle; it costs no T gate (Report 10 §3.5).

### 3.3 Spectra cross-check (Report 11 §3.4; `results/crosscheck/spectra.json` @ `328e071`, clean)
Verdicts, each with its tolerance:
- **Same model (twelve, spin network, LSH): exact agreement.** The 433 levels of $H(g^2)$ built by the three encodings' own code differ by at most $2.8\times10^{-14}$, $1.2\times10^{-14}$, $2.7\times10^{-14}$ at $g^2=0.5,1,2$ (tolerance $10^{-10}$). Nine cross-verdicts (each encoding's circuit judged against another encoding's target; three general, six headline) all pass with errors $\le2.7\times10^{-13}$; a negative control with $\beta+10^{-6}$ is rejected at the predicted $2.0\times10^{-6}$ (window $[1.9,2.1]\times10^{-6}$). Audit 309 N5: a cross-verdict follows from the circuit's own verdict plus target agreement, so it is a consistency check, not new evidence.
- **KS link inside the rishon and fuzzy links: exact identity with a large leak.** A $16\times5$ isometry $V$ (a matrix with $V^\dagger V=1$) maps the 5 KS link states into each model's 16-dimensional link; the compressed operators equal the KS ones to $\le4.7\times10^{-16}$ (tolerance $10^{-12}$). The *leak* (the part that leaves the embedded space) is not small: squared plaquette leak 15 (rishon), $\tfrac{33}{8}$ and 4 (two fuzzy embeddings). At the nominal angles the rishon step is at distance 1.990 from the KS step.
- **Rishon to KS: a limit of a three-coupling family.** With $\lambda_D=-L$, $c_E=\frac{g^2}{2}-\frac{8L}{3}$, $c_B=\frac{1}{g^2}$, the 433 lowest levels tend to KS with error $\propto1/L$; measured slopes of $\ln(\mathrm{dev})$ against $\ln L$: $-0.9973$, $-1.0010$, $-1.0043$ (tolerance $0.02$ around $-1$); coefficient matches $\frac{13}{4g^4}w_{\rm upper}$ to $0.17\%$, $0.08\%$, $0.30\%$ (tolerance $1\%$). It needs $c_E<0$, so it is a property of the model family, not of the project's nominal point.
- **Fuzzy to KS.** At $r=0$ only 2 of the 16 flavour sectors (sign patterns of $\Psi\mapsto\Psi\Gamma_5$ per link) reproduce the KS closed block, to $1.8\times10^{-15}$ (`reports/tests/422` F1; `spectra.json` stores $\le8.9\times10^{-16}$ for these two sectors); the others miss by $\ge0.608$ (locked $\ge0.5$). No KS limit exists inside $a\mathcal K_1+b\mathcal K_2$. The fuzzy gap closes at weak coupling like $(g^2)^7$ (measured exponent $7.0286$, tolerance $7\pm0.06$) while the KS gap diverges, the design aim of the fuzzy model (arXiv:2308.05253).
- **Not comparable** (Report 11 §3.4 3e, §3.5): state counts, closed-sector spectra at equal $g^2$ outside the relations above, one-step unitaries at equal angles, gate counts across blocks, and any continuum-limit statement (not testable on one plaquette).

### 3.4 The four project derivations (Report 11 §3.4 and §4; attribution decided by Digonto 2026-11-20)
Derived in the planning research `reports/research/006`, checked numerically in `reports/tests/421` and `422`, and stated as results of this project; none was found in the literature searched (research 006 §1).
1. The KS link is an exact compression of the rishon link and of the fuzzy link ($V^\dagger XV=X^{\rm KS}$ for link and plaquette operators) — Report 11 §3.4 3b.
2. The rishon model reaches KS in the large-det limit with $L\big(\lambda_k(L)-\lambda_k^{\rm KS}\big)\to-\frac{13}{4g^4}w_k$ (Schrieffer–Wolff perturbation theory, arXiv:1105.0675; re-derived by hand in audit 305) — 3c.
3. Only 2 of the 16 fuzzy flavour sectors match KS at $r=0$ — 3c, statement A.
4. No fuzzy-to-KS limit exists inside $a\mathcal K_1+b\mathcal K_2$ — 3c, statement B.

### 3.5 Verification behind the numbers
Each milestone listed here passed a full test run and an audit, and all except M10 a benchmark (M5x, not listed, has no benchmark either): twelve M2 (tester 039–042, audit 004, benchmark 003); spin network M4 (tester 404, audit 302, benchmark 301); rishon M6 (tester 435, audit 307, benchmark 305); LSH M8 (tester 446, audit 308, benchmark 306); fuzzy M10 (tester 303 for the gate, 428/429 for the later headline-rule update, audits 301 and 306; no separate M10 benchmark, Report 10 §5); M11 (tester 448, audit 309, benchmark 307). All audits returned PASS WITH NOTES, none blocking.

## 4. Problems, limits and assumptions

**Search limits.**
- **No loop reached a proven optimum.** Twelve stopped by coordinator judgement (accepted by Digonto 2026-11-10) and fuzzy $U_B$ by Digonto's decision (2026-11-14); spin network, rishon and LSH stopped by rules (no gain for 3 rounds; 20-session limit), and rishon still improved in its last round (Reports 2 §4.3, 4 §2, 6 §2, 8 §2, 10 §5). Floors stated by proposers are search results, not proofs. The one tester-confirmed negative result (no 67-CX LSH circuit) covers one 64-point walk space only (Report 8 §4 item 6).
- **CX-first against T-first.** All headlines are CX-first picks; T-first picks are different circuits for four archives (§3.2), and only archive entries were compared — a T-focused search could find lower T (Report 11 §4 (iv)).
- **Only the first-order step was compressed**, at the nominal angles with three-pair skeleton checks; order-2 steps were not compressed, nor were the KS and rishon outer rows (the fuzzy outer links reuse the compressed link unit: 96 of the 227 CX of the full fuzzy step).

**Scope of correctness.**
- **Gauss-law reliance.** Every circuit is exact on physical states only. The twelve and LSH headlines read 4 and 2 outer-link qubits as controls; on non-physical inputs the LSH headline differs from the exact step by up to 2.0 (audit 308; Report 11 §3.2).
- **Rishon and fuzzy are different models from KS** (§3.3); their gate counts are not comparable with block A. The rishon nominal det coupling $\lambda_D=0.43$ ($\eta=0.29$) is a generic test value, not a physical coupling (Report 5 addendum §5).
- **Fuzzy step checked by sampling.** The composed fuzzy step (general and headline) is verified layer by layer exactly but as a whole only on 40 seeded inputs (Reports 9 §3.1, 10 §5). No Lean certificate exists for any fuzzy circuit (`n_a`: no exporter).
- **Rishon three-layer step certified by composition** of the unit certificate and the det-layer certificate (METHODS-rishon R16); no single Lean theorem states the composite. Rishon Gauss checks use 273 sampled states; the 38 432-state coverage rests on the inner-block inequality (R6).
- **Lean trust limits.** Certificates hold for the angle-linear gate family read off the circuit; that the program emits this family at every angle is confirmed numerically at a finite set of angle pairs (25 in Report 6 §3.0, 23 in `docs/METHODS-rishon.md` R12), not proved. Pinned targets are tied to the Hamiltonians numerically, not by a Lean theorem (Reports 4 §3.8, 6 §3.8).
- **Fuzzy general numbers** come from a dirty tree (`8e71c38`), reproduced to identical numbers by tester 301 (floats compared at relative $10^{-9}$); used only as the "before" column (Report 11 §4).

**Defaults, now accepted by Digonto.** These planner and coordinator defaults were used without asking and stated in the reports (Digonto's decision of 2026-11-16); Digonto accepted them: `prompts/009` §13 and `prompts/010` §8 on 2026-11-17, `prompts/204` §14 (rishon) on 2026-11-20, and on 2026-11-22 all of the following (`notes/STATUS.md` Decisions):
- fuzzy: $r=\kappa_2/\kappa_1=1$, plaquette sign and factor $H_B^{\rm fz}=-2\square$, the paper's Gauss orientation (Report 9 §5; METHODS-fuzzy F3);
- LSH: `prompts/400` §10 D1–D8 (e.g. the (inner $\mid$ outer) corner splitting) and `prompts/401` §12 D1–D13 (Reports 7 §4, 8 §5);
- consolidation `prompts/008` §15 (it lists D1–D16; `notes/STATUS.md` 2026-11-16 names D1–D10; Report 4 §4), and `prompts/104` §9 defaults.

Not covered by these acceptances: the planner additions of `prompts/402` §11 (Report 8 §5), which remain stated defaults.

**Other limits listed in the reports.** T counts depend on pygridsynth 1.2.0 (the Qiskit pass agrees to $\pm6$ T per rotation, METHODS 7); a different 20-pair draw would move $\bar T$ by about its standard error. Proposer wall time and token cost were never recorded (Reports 2, 4, 6, 8). Audit 301 notes A1 (unit Gauss residual stored as 0.0 when not computed) and A2 (validity at 3 angle points) remain open for fuzzy (Report 10 §5).

**Open hygiene notes (no result affected).**
- Audit 308 N2: `results/lsh/m8-before-after.md` calls `r04-F3-004` "the headline" (tie sort); the headline is `r05-F3-005` (`m8-compressed.json::extra.headline` is authoritative). N4: `rs_split.structure()` sets sites and qubits touched by formula, not from the operator. N5: the LSH certificate no-rewrite rule can keep stale `git_dirty: true` provenance.
- Fixed on 2026-11-22 after drafting this report (the earlier reports were edited; no number changed): Report 11 §4 (iii) now gives each loop's true stop reason (twelve and fuzzy $U_B$ by decision; spin network, rishon, LSH by rule); Report 11 Table 2 explains that the valid seed `r00-seed-qiskit_l3` of twelve and LSH has no robust key, hence 21 of 22 and 28 of 29 ranked entries; the Report 5 addendum marks its round-4 rishon figures (`r04-F1-004`, 228 / 260 CX) as superseded by Report 6; Report 2 records Digonto's acceptance of its stop (2026-11-10); Report 4 cites the commit `5bbaf0f` that `m4-compressed.json` now records; `CLAUDE.md` gives the true peak memory of the large acceptance tests (Lean m3 7.4 GiB, `M9_C1` 5.2 GiB); the summary table (`results/summary/encodings-gate-counts.md`) reads the Lean status of the general circuits from their certificate files (twelve, spin network, rishon and LSH certified, fuzzy `n_a`, as in Report 11 Table 1a) and names the source in a new column; `scripts/m11_results.py --root` records the git state of the root it reads (audit 309 N10). Checks: `reports/tests/450` (this report's numbers) and `reports/tests/451` (the two code fixes).

## 5. How to reproduce

Environment and commands (from `CLAUDE.md`; Python 3.12, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0 — never upgrade):
```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/check_lock.py && ~/.claude/bin/acceptance-check     # lock check (expects acceptance-v23)
tools/pytest-safe -n 8 tests/unit                                 # unit suite
tools/pytest-safe -n 8 tests/acceptance                           # full acceptance suite (milestone gate)
python scripts/m11_results.py      # regenerates results/crosscheck/{spectra,gate-table}.json, tables.md, tradeoff.pdf
python scripts/summary_table.py    # regenerates results/summary/encodings-gate-counts.{md,json,pdf}
```
- **Never** run the acceptance suite with bare `pytest -n auto`: `tools/pytest-safe` and `tools/run-capped <cmd>` run jobs inside a memory-capped systemd slice (24 GB), so a runaway job loses one worker, not the session (`CLAUDE.md`). Long jobs (compression rounds, Lean builds) go through `tools/run-capped`.
- Expected costs: `scripts/m11_results.py` $76.9$ s (range $[76.3,78.6]$ s, 6 runs, one core, peak 1.08 GB; benchmark 307); regenerated numbers equal the committed files in all 2243 compared values (tester 448). Per-track result scripts are `scripts/m1_results.py`, `m3_results.py`, `m4_results.py`, `m5_results.py` (4131 s, Report 5), `m5_det_results.py` (55 531 s, Report 5 addendum), `m6_results.py`, `m7_results.py`, `m8_results.py`, `m9_results.py`, `m10_round.py`.
- After any code change: `graphify update .`.

# Report 2 — 12-qubit encoding: compressing the one-Trotter-step circuit

Date: 2026-11-06 · Repository commit at writing: b74446d · Tag: `milestone-2` · Plan: `prompts/001` §5, `prompts/002` §5 (step 2.8) + addenda `003`–`006`
Every number is read from a committed results file and cited; "trivial difference" means a subtraction or percentage of two cited numbers. Main table: `results/compress/twelve/summary.json` (all 22 candidates, 6 rounds; rendered by `python -m su2plaq.compress.report --encoding twelve --kind step`). Per-round data: `results/compress/twelve/round-000.json` … `round-005.json`. Archive: `compress/archive/twelve/` (entry `r05-F2-005` evaluated at commit d05f973; seeds at a4c28a6; qiskit 2.5.2, aer 0.17.2, pygridsynth 1.2.0; seeds 20261104 / 12345 / 0). Verification: tester reports 039–042, audit 004 (PASS WITH NOTES), benchmark 003.

## 1. What was asked
Report 1 gave a correct but long circuit for one first-order Trotter step $U_B(\beta)\,U_E(\alpha)$ of the SU(2) plaquette in Paulo's 12-qubit encoding (3 qubits per inner link). The task of M2 was to **compress** it: fewer CNOT gates (CX, the two-qubit gate that dominates error-corrected cost) and fewer T gates (the expensive non-Clifford gate), without losing exactness on any of the 433 physical (Gauss-law-satisfying) states. The method is the program-search loop of Gu, Kemeny, Yelin and Lukin (arXiv:2610.22367): AI "proposer" agents write small Python programs that build a circuit; a fixed evaluator checks each one exactly and scores it; the best are kept in an archive and fed back into the next round.

## 2. What was done
- **Machinery** (M2 steps 2.1–2.6). A circuit builder and macro-gate library, an oracle for the exact target, one evaluator for the tests and the loop, a result archive and cache, and a table renderer. Evaluator rule: a candidate is *valid* only if its error is $\le10^{-10}$ on all 433 states at three angle pairs $(\alpha,\beta)=(0.37,0.61),(0.91,0.23),(1.7,1.0)$, the three circuits have the same gate skeleton, ancillas end clean, Gauss's law holds, and the outer links are only used as controls (METHODS §9).
- **Cost key** (METHODS §7, §9): lexicographic $(\text{CX},\,T_{10^{-6}},\,\mathrm{depth}_{\rm CT},\,\text{qubits})$. Here $T_{10^{-6}}$ is $T_{\rm fixed}$ plus the T gates pygridsynth needs for each rotation to accuracy $\varepsilon=10^{-6}$; $\mathrm{depth}_{\rm CT}$ is the depth of the synthesised Clifford+T circuit. **CX is compared first, T second.**
- **Loop on `twelve`/`step`.** Round 0: five seeds (below). One ideation session (`compress/ideation/twelve.md`, from the task spec alone). Rounds 1–5: one proposer per family, F1–F4 (families are different datapath designs; the labels are ours). In total 17 proposer programs (4+4+3+3+3), all valid (`summary.json`: `n_valid` 22 of `n_candidates` 22, seeds included).
- **Stop.** After round 5 (see §4.3).

## 3. Results at $(\alpha,\beta)=(0.37,0.61)$, $\varepsilon=10^{-6}$ unless stated

### 3.1 Before/after (source: `summary.json::rows`, with entry ids)
Qubits are data 12 + outer links 16 (read-only: only used as CX controls) + ancilla. Total = `qubits` in `summary.json`; ancilla = total $-28$ (trivial difference; for the best checked against its program, which allocates three ancillas `tau0`, `z`, `pb`, and against tester 041 §2a).

| row (entry id) | data+outer+anc = total | CX | $N_{\rm rot}$ | $T_{\rm fixed}$ | $T(10^{-6})$ meas. | $T_{\rm est}(10^{-6})$ | $T(10^{-10})$ meas. | depth$_{\rm CT}$ |
|---|---|---|---|---|---|---|---|---|
| general (`r00-seed-000`) | 12+16+22 = 50 | 294 | 10 | 312 | 952 | 909.9 | 1352 | 1421 |
| general + polish (`r00-seed-010`) | 12+16+22 = 50 | 294 | 10 | 312 | 952 | 909.9 | 1352 | 1421 |
| Qiskit L3, windows of 32 (`r00-seed-qiskit_l3`) | 12+16+22 = 50 | 290 | 10 | 302 | 918 | 899.9 | 1310 | 1387 |
| lean22_v2 seed (`r00-seed-001`) | 12+16+7 = 35 | 162 | 8 | 160 | 660 | 638.4 | 986 | 1029 |
| lean22 seed (`r00-seed-002`) | 12+16+10 = 38 | 210 | 8 | 192 | 704 | 670.4 | 1026 | 1148 |
| best F1 (`r02-F1-002`) | 12+16+7 = 35 | 124 | 16 | 104 | 1114 | 1060.7 | 1754 | 2195 |
| best F2 (`r05-F2-005`) | 12+16+3 = 31 | 111 | 13 | 104 | 912 | 881.3 | 1456 | 1663 |
| best F3 (`r04-F3-004`) | 12+16+4 = 32 | 111 | 13 | 104 | 912 | 881.3 | 1456 | 1664 |
| best F4 (`r05-F4-005`) | 12+16+4 = 32 | 111 | 13 | 104 | 912 | 881.3 | 1456 | 1672 |
| **global best (`r05-F2-005`)** | **12+16+3 = 31** | **111** | **13** | **104** | **912** | **881.3** | **1456** | **1663** |

Verdict and Lean status of the same rows (one evaluator, exact sparse engine, 433 inputs at the nominal pair and both alternates):

| row | verdict: operator-norm error, leaked amplitude | Lean status |
|---|---|---|
| general / general + polish | valid, $2.69\times10^{-13}$, 0 | not run |
| Qiskit L3 windowed | valid, $3.61\times10^{-13}$, 0 | not run |
| lean22_v2 / lean22 | valid, $2.14\times10^{-13}$ / $2.96\times10^{-13}$, 0 | not run |
| best F1 / F3 / F4 | valid, $8.27\times10^{-14}$ / $8.49\times10^{-14}$ / $2.10\times10^{-13}$, 0 | not run |
| best F2 = global best | valid, $1.00\times10^{-13}$, 0 (alternate pairs $9.57\times10^{-14}$, $1.10\times10^{-13}$: `compress/archive/twelve/entries/r05-F2-005.json`) | **certified** (§6) |

Notes on the rows.
- **Why "windowed" for Qiskit L3.** Qiskit's optimisation level 3, applied to the whole circuit, moves Hadamard gates around so that one input state spreads over more than $10^6$ amplitudes; the exact sparse engine cannot check that. So the baseline was optimised in windows of 32 gates and each result checked. The whole-circuit version is in `summary.json` as counts only, marked unverifiable (CX 290, $T_{\rm fixed}$ 294, $N_{\rm rot}$ 10, $T_{\rm est}$ 891.9); it is not part of the comparison.
- **lean22 / lean22_v2.** Plaquette circuits imported from the earlier su2qc-trotter project. They apply the electric layer *after* the plaquette ($U_EU_B$ order), so only their plaquette part was imported ("plaquette only") and our $U_E$ was placed in front, giving $U_BU_E$ (`compress/programs/twelve/seed/001-lean22_v2.py`, `002-lean22.py`; Report 1 §5).
- **$T_{\rm est}$** is the estimate $T_{\rm fixed}+3N_{\rm rot}\log_2(1/\varepsilon)$ (METHODS §7). It is 3–4 % below the measured value for the best (881.3 vs 912).
- Percentages (trivial differences), global best vs general: CX $294\to111$ ($-62\%$), qubits $50\to31$ ($-38\%$), $T_{\rm fixed}$ $312\to104$ ($-67\%$), $T(10^{-6})$ $952\to912$ ($-4.2\%$), $T(10^{-10})$ $1352\to1456$ ($+7.7\%$), $\mathrm{depth}_{\rm CT}$ $1421\to1663$ ($+17\%$). Against the best seed by key, `lean22_v2`: CX $162\to111$ ($-31\%$), but $T(10^{-6})$ $660\to912$ ($+38\%$) and depth$_{\rm CT}$ $1029\to1663$. **The loop minimised CX first and traded T for CX; the lean22_v2 seed still has the lowest T of all 22 candidates.**

### 3.2 Paulo's circuit (own column; not like-for-like with the table above, audit 004 N1)
| | qubits | CX | $N_{\rm rot}$ | $T$ (Qiskit Clifford+T pass manager, $U_B$ only, $\beta=1$) | depth (same pass) | verdict at its own angle |
|---|---|---|---|---|---|---|
| Paulo, compiled file | 34 = 12+22 (50 counting the 16 outer links) | 294 | fixed angle, 0 free | 1162 | 2549 | valid, error $1.08\times10^{-5}$ (`summary.json`, row `paulo34`) |

The 1162 is Paulo's $U_B$ alone, at $\beta=1$, through Qiskit's pass manager. It is **not** a pygridsynth count, **not** the step (our rows include the four electric rotations, about 256 T at $10^{-6}$, Report 1 §3.3), and not at $\beta=0.61$. The like-for-like comparison is $U_B$ only, $\beta=1$, same Qiskit pass, $\varepsilon=10^{-6}$, seed 12345: **ours 662 T vs Paulo 1162 T, CX 294 vs 294** (`results/m1_audit_fixes_n3.json`, checks "ours via Qiskit CT (T)" and "paulo_logical via same CT (T)"; Report 1 §3.4). We did **not** run the compressed best's $U_B$ part through that pass, so "912 vs 1162" must not be read as a saving; the only established ratio is 662 vs 1162 for the *uncompressed* general circuit.

### 3.3 Outer-link electric phases (8 phase gates, separate row)
These are diagonal phases on the 8 outer-link $j$ qubits. They are not part of the evaluated step (the evaluator targets the inner links; Report 1 §3.3). `results/twelve/UE.json::extra.outer_electric_row` (commit a9702e5) holds the circuit for all 12 links: 0 CX, 12 rotations, $T(10^{-6})=768$, $T(10^{-10})=1248$. With the inner four ($256$ and $416$, Report 1 §3.3) subtracted, the 8 outer gates add $+512$ T at $10^{-6}$ and $+832$ T at $10^{-10}$. They can be appended to any row, so the totals with outer phases are (trivial sums, not separately verified): general $952+512=1464$, best $912+512=1424$ at $10^{-6}$; general $1352+832=2184$, best $1456+832=2288$ at $10^{-10}$. Their Clifford+T form puts H gates on the outer qubits, which the checker cannot evaluate; the tester verified them by hand (reports/tests/021, cited in Report 1).

## 4. How the search went
### 4.1 Round by round (best key = (CX, $T_{10^{-6}}$, depth$_{\rm CT}$, qubits); `round-00N.json::best_key`)
| round | best key | best entry | what changed | Lean check of the best, s |
|---|---|---|---|---|
| 0 (seeds) | (162, 660, 1029, 35) | `r00-seed-001` | start | 0 |
| 1 | (126, 738, 1226, 36) | `r01-F2-001` | four new datapaths; F2 finds a 2-CX leg map | 85.2 |
| 2 | (120, 912, 1671, 33) | `r02-F2-002` | CX $-6$ but T $+174$ (13 rotations) | 78.8 |
| 3 | (112, 912, 1648, 33) | `r03-F3-003` | F3 finds a 5-CX "clean" corner frame | 86.9 |
| 4 | (111, 912, 1664, 32) | `r04-F2-004` | clean frame + in-walk AND; three families converge on CX 111, T 912 | 87.6 |
| 5 | (111, 912, 1663, 31) | `r05-F2-005` | no CX or T gain; one qubit and one depth level fewer | 352.1 |

CX fell $162\to126\to120\to112\to111\to111$; $T$ went $660\to738\to912$ and then stayed. Five entries tie at (111, 912) with depth$_{\rm CT}$ and qubits: `r04-F2-004` (1664, 32), `r04-F3-004` (1664, 32), `r04-F4-004` (1694, 32), `r05-F2-005` (1663, 31), `r05-F4-005` (1672, 32) (round files, reports/tests/041 §2c). `r04-F2-004` and `r04-F3-004` are near-duplicates (98 % common gate subsequence); the others are different CX networks (tester 041 §4).

### 4.2 Lineage of the global best (`summary.json::lineage`)
$$\texttt{r01-F2-001}\;\to\;\texttt{r02-F2-002}\;\to\;\texttt{r03-F2-003}\;\to\;\texttt{r04-F2-004}\;\to\;\texttt{r05-F2-005}$$
with (CX, T): (126, 738), (120, 912), (119, 912), (111, 912), (111, 912). `r01-F2-001` declares no parent (its program says `PARENT = None`; the ideation read no seeds; audit 004 N8), so the chain starts from the ideation, not from a seed. Ideas crossed families: the 5-CX clean corner frame came from F3 (`r03-F3-003`), the in-walk AND from F2 and F4 (`r03-F2-003`, `r03-F4-003`), and `r04-F2-004` combines them (`compress/discoveries/twelve.md`).

### 4.3 Stop decision (audit 004 N11)
The METHODS §9 stop rules (6 rounds for the first encoding, 3 rounds with no better key, or 20 proposer sessions) had **not** fired after round 5 (5 loop rounds, 17 sessions; round 5 improved depth and qubit count). The coordinator stopped the loop by judgement ("plateau"): three independent families converged on the same (111, 912), and the round-5 proposers each reported a floor for their skeleton (§5). It is recorded in `notes/STATUS.md` (2026-11-06) as a coordinator decision, not a rule; it is awaiting Digonto's confirmation.

## 5. What the compressed circuit does, and why T barely dropped
(Sources: the program's own SUMMARY/DISCOVERY lines, `compress/programs/twelve/F2/005-outer-t2-peephole.py`; physics re-derived at the level of the argument in audit 004 §B. Names `pa`, `pb`, `z`, `tau` are the proposers' labels, not standard terms.)

1. **Structure of the target.** The 433 physical states split into 128 *bright pairs* (a state and its partner with all four inner $j$ labels flipped; $H_B$ acts as a $2\times2$ block) and 177 *dark states* ($H_B=0$): $2\cdot128+177=433$. The block couplings are $\pm2,\pm1,\pm\tfrac12$ with multiplicities $16,96,16$ per sign (tester 041; Lean-proved spectrum).
2. **Corner types.** Each plaquette corner has two inner legs. Call $t_c=1$ if the two links at corner $c$ carry different $j$ (a "diff" corner; our label). Gauss's law gives $t_c=j_A\oplus j_B=j_{o_A}\oplus j_{o_B}$ (inner or outer legs), hence an even number $n_1\in\{0,2,4\}$ of diff corners, with $1,6,1$ pairs per block and coupling modulus $|\kappa|=2\cdot2^{-n_1/2}=2,1,\tfrac12$. The compressed circuit realises $\kappa=2,\;-(-1)^{t_2},\;-\tfrac12$ for $n_1=0,2,4$ (signs are gauge at $j_{\max}=\tfrac12$, audit 001 N5).
3. **Corner frame.** At each corner a 5-CX gadget rotates the leg pair so that, after flipping all four inner $j$ bits, **only one qubit flips** ($F=q_5$): the bright $2\times2$ block becomes $H_B=\kappa\,g\,X_F$, with $g=1$ on bright pairs and $g=0$ on dark states. Flag qubits mark dark corners (3 ancillas `tau0`, `z`, `pb`; the pair AND `pa` is computed inside the walk).
4. **Walsh walk.** $e^{-i\beta\kappa(x)X_F}$ with $\kappa$ depending on four bits $(p_a,p_b,z,t_2)$ is written as a sum of 9 parity terms (a Walsh–Hadamard expansion). A Gray-code walk of CX gates through the 9 parities applies the 9 rotations $r_z$ on $F$ in turn. 9 magnetic rotations plus the 4 electric ones gives $N_{\rm rot}=13$, all with angles $a\alpha+b\beta$ (tester 041 §2d: denominators $\le8$; electric $-\tfrac34\alpha$, magnetic $b\in\{\pm\tfrac14,\pm\tfrac12,\pm\tfrac34\}$). One CZ cancels a leftover sign from the in-walk AND (audit 004 §B.5).
5. **Outer bits.** $t_2=q_{21}\oplus q_{23}$ and $t_0=q_{13}\oplus q_{15}$ are read from the outer $j$ qubits as CX controls (Gauss law above). This replaced a copy ancilla and gave 31 qubits (round 5). The best reads 4 outer bits (13, 15, 21, 23) and never changes them (tester 041 §2a).
6. **CX count.** 48 forward CX per side + a 15-CX walk $=111$ (`compress/discoveries/twelve.md`, entry r04-F4-004).

**Why T dropped only $952\to912$.** $T=T_{\rm fixed}+\sum_rT_r(\varepsilon)$ and each non-Clifford rotation costs about $3\log_2(1/\varepsilon)\approx60$ T at $10^{-6}$ (METHODS §7). The general circuit had 10 rotations, the compressed one 13: $T_{\rm fixed}$ fell by 208 ($312\to104$), but rotation T rose by 168 ($640\to808$, trivial differences from `summary.json`), net $-40$. Compression traded multi-controlled operations, which cost many *fixed* T gates and CX, for the nine-term walk, whose terms are separate rotations. The proposers' floor arguments (`compress/discoveries/twelve.md`, entries r05-F4-005, r05-F2-005):
- over the relevant bits the minimum Walsh support is 9; supports of 8 terms need at least 2 more in-walk Toffoli-type gates, and 6 or 4 terms need extra AND features, each at least 4 CX more;
- the electric layer stays at 4 rotations, and no electric term merges with the walk;
- phase-folding finds no further T or rotation merges ($T_{\rm fixed}=104$ is fold-optimal), and pygridsynth counts do not change under $\pi/2$ angle shifts;
- a numerical search for a corner gadget with fewer CX (using outer reads) found none.

These are search results, not proofs, and hold for this datapath. At $\varepsilon=10^{-10}$ the extra rotations cost more than the fixed T saved ($1352\to1456$).

## 6. Verification
- **Evaluator (every entry).** 433 states $\times$ 3 angle pairs; operator-norm error, leaked amplitude and Gauss residual within $10^{-10}$ (audit 004 §A: `n_inputs` = 433 at all three pairs for all 22 entries). Best: $1.00\times10^{-13}$.
- **Independent engines** (reports/tests/039, 040, 041): an own sparse simulator with its own gate-lowering table, and Qiskit-Aer statevector, on all 433 states at all three pairs for every loop entry (rounds 1–5, 17 entries). Maxima over the 9 entries of rounds 3–5 (041 §2a): total error $1.48\times10^{-14}$ (own) and $8.19\times10^{-15}$ (Aer), block error $\le2.1\times10^{-14}$, ancilla leak exactly 0, Gauss residual $\le1.8\times10^{-15}$, outer register unchanged ($\le2.8\times10^{-14}$, no new outer patterns). Wrong circuits are caught: one T deleted gives error 0.39, a dropped ancilla CX gives leak 1.0, wrong angles give 1.18 (041 §2b).
- **Metric recount.** CX, $T_{\rm fixed}$, $N_{\rm rot}$, depth and qubits agree between our lowering, Qiskit and the archive; pygridsynth $T$ agrees exactly for all 9 (041 §2c).
- **Clifford+T circuit.** With rotations replaced by pygridsynth words the best has error $3.73\times10^{-6}$ (`round-005.json`; tester's own check $2.74\times10^{-6}$) against the budget $N_{\rm rot}\varepsilon+10^{-9}=1.3\times10^{-5}$.
- **Global phase.** All statements are "up to one global phase": the evaluator fits one phase per circuit; pygridsynth drops the phase $e^{i\pi/4}$; the Lean certificate of the best has $c=i$ (audit 004).
- **Lean certificate** (`compress/lean/certs/step-o1-ca5c0f1a907a.json`; checker sha256 `befbd27e…`; 352.1 s recorded, 350 s quiet machine per benchmark 003, 611 s loaded per tester 041). It states that the 31-qubit, 432-gate list maps each of exactly 433 states to the exact target block, as sparse exact vectors over the whole register. So exactness on the 433 states, zero leakage and clean ancillas hold **for every real $(\alpha,\beta)$ of the angle-linear gate family** (exponent tables read off the circuit). It first checks that the Gram matrix is the identity, each state lies in one target block, and SHA-256 pins on states and target match. Tester 041 §3 re-ran it (ACCEPT), tied it to the program gate by gate (0 mismatches) and showed five deliberately broken certificates are rejected. Certificates also exist for the best of rounds 1–4 (`r01-F2-001`, `r02-F2-002`, `r03-F3-003`, `r04-F2-004`).
- **Trust limits (METHODS §11.5).** (i) The 433 states and exact target blocks come from Python (`su2plaq.lean.exact`), are pinned by hash and cross-checked against the float code to $\le10^{-12}$ at one angle pair; the projectors $P_\lambda$ are not derived inside Lean. (ii) "For all angles" refers to the angle-linear family extracted at the nominal angles; the program's behaviour at other angles rests on the numerical skeleton and alternate-pair checks. (iii) The Lean inequality contains a span-leak term that the evaluator's error omits (bounded by $4\times$ the Gauss residual). The checker is a compiled program trusted through Lean's `native_decide`.

## 7. Cost of the loop
- **Agents.** 17 proposer sessions in rounds 1–5 (4, 4, 3, 3, 3) plus one ideation session. Proposer wall time and tokens were **not recorded**.
- **Compute** (benchmark 003 §2, from `round-00N.json::wall_s`, `lean_seconds`; 12 logical CPUs, shared machine, so loop-time walls): round 0: 163.8 s; round 1: 529.3 s (85.2 s Lean); round 2: 135.2 s (78.8); round 3: 137.3 s (86.9); round 4: 136.9 s (87.6); round 5: 526.7 s (352.1). Rounds 1–5 sum to 1465.4 s, about 24 min (trivial sum). Round 1 is long because of heavy F1-style circuits that read all 8 outer bits (about 240 s each on a loaded machine); round 5 because of the 352 s Lean check of the 31-qubit best.
- **One evaluation of the global best** (fresh process, no cache, 3 runs): median 36.8 s [36.82, 36.97], peak about 379 MB; the loop-time value was 36.2 s ($+1.8\%$). No benchmarked quantity slowed by more than 10 % since Report 1; the unit suite grew from 178 tests (59.9 s) to 401 tests (about 382–397 s, 6.7 GB at 12 workers), not like-for-like (benchmark 003 §1, §3).

## 8. Problems and assumptions
Audit 004 (13 notes, none blocking). **Fixed** (reports/tests/042): N1 (Paulo's 1162 only in its own column), N2 (certificate rebuild checks the program hash), N7 (cache key includes package versions), N13 (relative certificate path), plus METHODS notes N3, N4, N6, N9, N12. **Left open:**
- **N5.** The validity rule does not require angle-linearity, and $T$ is measured only at the nominal pair. A program could in principle hit Clifford angles only at $(0.37,0.61)$. Not exploited: all 9 recent entries are exactly linear (041 §2d) and the Lean exporter recovers the same exponents. Needs a planner decision.
- **N6.** depth$_{\rm CT}$ depends on a convention ($X\to HSSH$ in the synthesised words). The winner among the five tied entries is decided by 1663 vs 1664 levels; with $X$ counted as one gate the best would have 1642 (041 §2c). Treat the five as tied in (CX, T).
- **N8.** The round-0 seeds carry evaluator hash `810e86f2…`, older than `0bd7e7d9…`; the only change in between is the rendered text in `compress/spec.py`, so no seed number changes (audit 004, "What I did" item 3). Round-1 entries record no parent.
- **N10.** The Lean count values are typed in `src/su2plaq/lean/structure.py:417–424`, tied to the Lean statements by a locked test; planned to be parsed from `Counts.lean` instead.
- **N11.** The stop was a judgement (§4.3), awaiting Digonto's confirmation.
- **Not done.** (a) The compressed best's $U_B$ part at $\beta=1$ through Paulo's Qiskit pass was not run, so there is no like-for-like compressed-vs-Paulo T ratio. (b) Only the first-order step was compressed, at $\varepsilon=10^{-6}$ in the key. (c) The loop did not minimise T first; a T-first key might favour the lean22-type seeds (guess, untested).
- **Assumptions.** The 433-state test covers the whole physical space at $j_{\max}=\tfrac12$ (Report 1). The round files record `git_dirty: true` (programs and briefs were uncommitted while a round ran); the archive's program hashes tie each entry to its file. After this report was drafted, `--certify-best` re-certified `r05-F2-005` (certified, 351.1 s) and stored `program_file_sha256` `4f7fcb1e…`, `gates_sha256` `ca5c0f1a…` and a relative `cert_path` in its archive entry; no number above changed.

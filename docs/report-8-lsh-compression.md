# Report 8 — loop-string-hadron (LSH) encoding: compressing the one-Trotter-step circuit

Date: 2026-11-20 · Repository commit at writing: `e729f15` (branch `merge-desktop-tracks`, host omnicommander) · Tag: `milestone-8` at [TAG: milestone-8 commit] · Plans in force: `prompts/401-lsh-m8-compression-plan.md` on `prompts/400-lsh-m7-plan.md`, with `prompts/008` for the shared registry, headline rule and replay, and `prompts/002`–`008` for the shared machinery · Conventions: `docs/METHODS-lsh.md` L10, L12–L16 and `docs/METHODS.md` §6–§9, §11, §12 · Related reports: Report 7 (`docs/report-7-lsh-general-circuit.md`, the general LSH circuit and the transcoder); Report 4 (`docs/report-4-spinnet-compression.md`, whose 31-CX headline is wrapped here); Reports 2 and 6 (`docs/report-2-twelve-qubit-compression.md`, `docs/report-6-rishon-compression.md`, the same loop on other encodings).
Verification: tester reports `reports/tests/436` (steps 8.2–8.4), `437` (round 0), `438`–`439` (rounds 1–2), `440` (the results script), `441`–`444` (rounds 3–6, with 444 also covering the 21-toggle search). Milestone gate: [GATE: tester 445 full — counts and verdict]; audit [GATE: audit NNN verdict and notes]; benchmark [GATE: benchmark NNN]. Research: `reports/research/401-lsh-m8-compression.md`.

**Where the numbers come from.** Every number is read from a committed file and cited. "Trivial difference" means a subtraction, ratio or percentage of two cited numbers; such numbers are marked. No test, evaluator run, compression round or Lean check was run for this report.
- **Headline and main table.** Sources: `results/lsh/m8-compressed.json` and `results/lsh/m8-before-after.md`. They were produced by `python scripts/m8_results.py` on the clean commit `b422e78` (`provenance.git_dirty: false`, host omnicommander, python 3.12.16, numpy 2.5.4, scipy 1.18.1, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, wall 5.7 s, peak 288 MB) and committed in `2b0a311`. The headline circuit is also stored as `results/lsh/m8-headline-step.{qasm3,qpy}` (QPY sha256 `19f2d533…`).
- **Per-round data.** `results/compress/lsh/round-000.json` … `round-006.json` (round 0 by `python -m su2plaq.lsh.loop seed`, rounds 1–6 by `python -m su2plaq.lsh.loop round --round r`; commits `70ab721`, `98f01f1`, `df95e14`, `09cec7f`, `7a10110`, `1e0b171`, `1e765f1`). Stop record: `stop.json`. Robust-key cache: `robust.json`. Table: `summary.json` (29 candidates, 29 valid).
- **Archive and search records.** Archive `compress/archive/lsh/entries/*.json`; programs `compress/programs/lsh/`; attempts log `compress/attempts/lsh.jsonl`; discoveries `compress/discoveries/lsh.md`; ideation `compress/ideation/lsh.md`; evidence for the 21-toggle search `results/compress/lsh/evidence/r06-F3-exh21/`.
- **Lean.** Theorem file `lean/certs/lsh-best-step.lean`; certificate `results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json`.
- **Seeds and hashes.** Seeds (`m8-compressed.json::provenance.seeds`): 20261104 (transpiler lowering), 0 (trial subset), 20261107 (the 20 angle pairs). The LSH evaluator hash `88e0d76b…` and the spec hash `a16c8a0a…` are the same in all seven round files (tester 444 check 3).
- **Units.** Errors, leaks and Gauss residuals are dimensionless (operator 2-norms, or vector norms of unit-norm states). Angles are in radians, times in seconds. Depth is counted in gate layers.

## 1. What was asked

The LSH encoding (loop-string-hadron: the SU(2) plaquette described by integer loop, string and hadron quantum numbers; Raychowdhury–Stryker, arXiv:1912.06133) was built in Report 7. It uses a 24-qubit register:
- 12 data qubits, made of 4 "in" sites × 3 loop-number bits $(\ell_{pn},\ell_{nv},\ell_{vp})$;
- 12 outer qubits, which may be read but never written.

A **Trotter step** is one factor of the product formula that approximates $e^{-iHt}$. Here the step is the first-order step $U=U_B(\beta)\,U_E(\alpha)$: electric layer first, then the magnetic (plaquette) layer, at the nominal angles $(\alpha,\beta)=(0.37,0.61)$.

Milestone M8 asked for this step to be **compressed** with the program-search loop of Reports 2, 4 and 6 (Gu, Kemeny, Yelin, Lukin, arXiv:2610.22367). In that loop:
- AI "proposer" sessions write small Python programs that build a circuit;
- a fixed evaluator checks every program exactly on all 433 physical states (states that obey the Gauss law) and scores it;
- the best programs are kept in an archive and fed back to the next round.

The aims were fewer CX gates (the two-qubit controlled-NOT, the main cost), then fewer T gates (the expensive non-Clifford gate of the Clifford+T gate set), then fewer qubits.

**What the loop could gain** (`prompts/401` §1.2). With the (inner $\mid$ outer) pairing, the LSH basis is the spin-network basis written in another bit code. So the best circuit known in advance is the spin-network headline of Report 4 (31 CX) placed between the per-site **transcoder** and its inverse. The transcoder is the M7 circuit `cx, cx, rccx` per site; the pair costs $+40$ CX and $+32$ T. That gives **71 CX**.

The loop therefore asks how much of the transcoder cost is forced by the LSH register. Report 8 must state three numbers: 31 (spin network), 71 (wrapped) and $X$ (LSH headline), with $\texttt{native\_gain\_cx}=71-X$ and $\texttt{overhead\_cx}=X-31$.

The required content (`prompts/401` §5):
- what was done: registry entry instead of a shim, seeds, families, rounds, stop reason, per-round verification, Lean;
- the before/after table and the three numbers;
- the CX-versus-$\bar T$ front, saying what the headline costs in T;
- the per-round table, the second-engine summary, and the Lean status with the trust label "native-certified, first-order step";
- findings, with proposer claims labelled as such;
- the uniform-splitting row and the limit of the comparison;
- problems and assumptions: the defaults of §12, the meaning of `n_a`, and audit-303 items N3, N5, N6.

## 2. What was done

- **Registry entry instead of a shim** (`prompts/401` §1.4, step 8.R).
- A *shim* is a track module that patches shared code at run time.
- The LSH encoding was instead added as one data entry `name="lsh"` in the shared table `src/su2plaq/encodings/registry.py` (line 94), plus `NOMINAL_ANGLES["lsh"]=(0.37,0.61)` in `encodings/base.py`. The rest of the shared code learns the encoding from that entry.
- This was committed with `prompts/008` step B1 on 2026-11-14 (tester 413).
- Locked tests M8-E1 and M8-E2 check that a fresh Python process with the stock worker evaluates LSH programs with nothing patched (tester 436, PASS).
- The LSH loop driver `src/su2plaq/lsh/loop.py` and the Lean exporter `lsh/lean_export.py` decide no verdict and are in no hash list. Six LSH files plus the shared files form the evaluator hash `88e0d76b…`.
- **Validity rule** (METHODS-lsh L12). A program is *valid* only if all of the following hold:
- On all 433 physical states, at $(0.37,0.61)$ and with the same gate skeleton at $(0.91,0.23)$ and $(1.70,1.00)$, `total_error` ≤ $10^{-10}$. The total error is block error + simulator pruning bound + leaked amplitude + span leak, up to one global phase.
- The Gauss residual is ≤ $10^{-10}$. A final state that breaks the Abelian Gauss law or the flux cap is an error.
- Helper qubits (*ancillas*) end in $|0\rangle$.
- Outer qubits are never written. They may be used as controls.
- Only the allowed gates are used, with at most 56 qubits.
- Lean never changes a verdict.
- **Cost key, as in Reports 2, 4 and 6.**
- The *archive key* is lexicographic $(\mathrm{CX},T_{10^{-6}},\mathrm{depth}_{\rm CT},\text{qubits})$ at the nominal pair.
- $T_{10^{-6}}=T_{\rm fixed}+\sum_rT_r$. $T_{\rm fixed}$ is the T gates written in the circuit, e.g. 4 per Toffoli of the cheap kinds below. $T_r$ is what the synthesiser pygridsynth (Ross–Selinger algorithm) needs for rotation $r$ at accuracy $\varepsilon=10^{-6}$.
- $N_{\rm rot}$ is the number of rotations that are not multiples of $\pi/4$. $\mathrm{depth}_{\rm CT}$ is the circuit depth after synthesis. $T_{\rm est}=T_{\rm fixed}+3N_{\rm rot}\log_2(1/\varepsilon)$ is an estimate.
- **CX is compared first.** This is a project choice (`prompts/001`), not physics.
- **Headline rule** (METHODS-lsh L14; `prompts/008` §6). The *headline* is the valid entry with the smallest *robust key*
$$k_{\rm rob}=\Big(\mathrm{CX},\ \sum_{i=1}^{20}T_{10^{-6}}(\alpha_i,\beta_i),\ \rho,\ \sum_{i=1}^{20}\mathrm{depth}_{\rm CT}(\alpha_i,\beta_i),\ \text{qubits}\Big).$$
- The 20 angle pairs come from seed 20261107, with $\alpha\in[0.05,2.0)$ and $\beta\in[0.05,1.2)$ (set sha256 `769caec1…`).
- $\rho=0$ if the Lean exporter can write a certificate for the nominal circuit, i.e. the circuit is *angle-linear* (every angle a rational multiple of $\alpha$ or $\beta$); otherwise $\rho=1$.
- $\bar T=\tfrac1{20}\sum_iT_{10^{-6}}(\alpha_i,\beta_i)$ is called "T_avg".
- Audit-302 hardenings: the skeleton must be identical over the 20 pairs and at the nominal and alternate pairs (N2), and the binding fields sit inside the certificate (N3).
- **Stop rule** (METHODS-lsh L14).
- The loop ends after round 8, or at 20 proposer sessions (ideation counts as one), or after 3 rounds in a row without improvement.
- "Improves" compares $(\mathrm{CX},\sum T,\rho,\text{qubits})$ lexicographically, **without depth**.
- A $\sum T$ change of at most $20N_{\rm rot}$ at unchanged CX, $N_{\rm rot}$ and $T_{\rm fixed}$ counts as a tie.
- **Round 0, seeds** (`round-000.json`, tester 437): ten candidates, all valid.
- The general step of Report 7 (`general`), and the same after the loop's polish pass and after Qiskit level 3 in windows of 32 gates.
- Four `spinnet_v2` skeletons wrapped by the transcoder (`wrap_pairs9`, `wrap_flags4`, `wrap_flags5`, `wrap_flags6`).
- Three programs of the closed spin-network loop, pinned by sha256 and wrapped: `wrap_sn_headline` (= Report 4 headline `r02-F1-002`), `wrap_sn_r05F3`, `wrap_sn_r02F5`.
- Two external rows were never archived: Paulo's 15-qubit file wrapped (kind $U_B$ only, fixed $\beta=-0.05$) and the whole-circuit Qiskit level-3 transpile (counts only).
- Best of round 0: `r00-seed-005` = `wrap_sn_headline`, key $(71,1118,2276,25)$, as predicted.
- **Ideation** (`compress/ideation/lsh.md`, one proposer session, 2026-11-19, from the task spec only). Five families. "Kind" is the planner's label (`prompts/401` §1.7): *transcoding* means a spin-network-style walk after recoding all four sites; *native* means working on the raw loop-number bits without ever holding the complete spin-network code. All family names are the proposers' labels, not standard terms.
- F1, recode–gate fusion (transcoding);
- F2, swap-diagonal frame (native);
- F3, minimal-AND synthesis (native);
- F4, three-product cleaning (native);
- F5, dead-syndrome multiplexer (transcoding).
- As run, the F3 programs build a "3-AND fold frame" (the proposer's label) that is close to the ideation's F4 idea. F1's round-5 program and F5's round-5 program used F3's native frame (`r05-F1-004`, `r05-F5-005`, parent `r04-F3-004`). Family label and kind therefore do not match one-for-one; this is judged from the programs' SUMMARY lines (§5).
- **Rounds 1–6** (`prompts/401` §1.7): one proposer session per active family.
- Round 1: F1–F5. Round 2: F1–F5.
- From round 3: the best three families by robust key, F1, F3, F5.
- Round 3: F3, F5. The F1 session was stopped by the usage guard before it wrote a program (`notes/STATUS.md`, 2026-11-19 15:40).
- Round 4: F1, F3, F5. Round 5: F1, F3, F5. Round 6: F3 only (one session left).
- Totals: 19 proposer programs (5+5+2+3+3+1), 29 candidates with the ten seeds, **29 valid** (`summary.json`).
- Sessions: 1 ideation + 19 = **20 of 20** (`stop.json`).
- **Session counting.** The code counts a session as a distinct (round, family) pair in the attempts log, i.e. sessions that wrote a program. The round-3 F1 session that wrote nothing is therefore **not counted**. Counting launched sessions would give 21 (tester 441 O2). This matches the M4-G3 definition "one program per proposer session", but `prompts/401` §1.6 does not say so explicitly.
- **Stop.**
- `stop.json`: `stop: true`, reason `max_sessions` (20 sessions), streak 2 (of 3), after round 6 of at most 8.
- The tester re-derived this record independently (tester 444 checks 19–20), and locked test M8-G3 passed (tester 444 check 21).
- This is a rule stop, not a sign that the search had converged (§5).
- **Per-round verification** (tester reports 437–444). For every new entry the testers checked:
- program sha256 equal to the archive;
- rebuild through the stock worker;
- their own lowering and their own sparse engine on all 433 states at three pairs;
- a second engine (Qiskit-Aer statevector, §3.6);
- a recount of CX, T and depth;
- the robust key and their own derivation of the stop record;
- their own final-state Gauss check;
- that no proposer committed anything to `src/` or `tests/`.
- **Lean.** Each round certified its new best with the compiled checker `su2plaq_cert_lsh`. After the last round, `python -m su2plaq.lsh.loop certify-headline` ran in a clean worktree at `1e765f1` (step 8.8, commit `b422e78`). It wrote the bound certificate and the theorem file `lean/certs/lsh-best-step.lean` (§3.7).

## 3. Results and what they mean

All numbers are at $(\alpha,\beta)=(0.37,0.61)$, order 1, $\varepsilon=10^{-6}$ unless stated.

### 3.0 In plain words
- The loop found a 68-CX circuit, `r05-F3-005`. It is exact on all 433 physical states and uses 24 qubits: 12 data + 12 outer, no ancilla.
- The wrapped spin-network circuit had 71 CX, so the loop removed **3 of the 40 transcoder CX**: $\texttt{native\_gain\_cx}=3$. The LSH register still costs **37 CX more** than the spin-network optimum: $\texttt{overhead\_cx}=37$.
- The 3 CX were bought with T and depth. Against the wrapped seed:
- $\bar T$ rose from 1124.0 to 1417.4 ($+26.1\,\%$, trivial difference);
- $\mathrm{depth}_{\rm CT}$ rose from 2276 to 3210 ($+41.0\,\%$, trivial difference).
- Under a T-first cost the headline would not be chosen (§3.3).
- The circuit is a native design: it works on the raw loop-number bits and never builds the complete spin-network code. It reads two outer qubits of site 0 as controls only.
- It is native-certified in Lean for all angles of its angle-linear family (first-order step).
- A complete search confirmed by the tester shows that inside this design's 64-point walk space no 67-CX version exists. That is a statement about this one design space, not a lower bound for all circuits (§4).

### 3.1 Before/after table
Source: `results/lsh/m8-before-after.md`, which reproduces `m8-compressed.json::extra.before_after`.

Notes on the columns:
- Qubits = 12 data + 12 outer (read-only) + ancillas: $31=24+7$, $27=24+3$, $25=24+1$, $24=24+0$ (split checked against `metrics.logical.ancilla` for the headline; trivial difference otherwise).
- The family rows are the best entry of each family by the robust key.
- Lean column: `certified` = native-certified (§3.7); `not_run` = the loop made no certificate for that entry; `n_a` = no certificate is possible or meaningful.

| row (entry) | qubits | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | $T(10^{-6})$ | $\bar T(10^{-6})$ | $T_{\rm est}(10^{-6})$ | $T(10^{-10})$ | depth$_{\rm CT}$ | verdict (error) | Lean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| general (`r00-seed-000`) | 31 | 94 | 88 | 8 | 598 | 592.6 | 566.4 | 916 | 880 | valid ($1.64\times10^{-14}$) | not_run |
| general + polish (`r00-seed-010`) | 31 | 94 | 88 | 8 | 598 | 592.6 | 566.4 | 916 | 880 | valid ($1.64\times10^{-14}$) | not_run |
| Qiskit L3, windows of 32 (`r00-seed-qiskit_l3`) | 31 | 94 | 88 | 8 | 598 | – | 566.4 | 916 | 880 | valid ($1.82\times10^{-14}$) | not_run |
| Qiskit L3, whole circuit (counts only) | 31 | 94 | 88 | 8 | – | – | 566.4 | – | – | unverifiable | n_a |
| `wrap_pairs9` (`r00-seed-001`) | 27 | 74 | 56 | 13 | 864 | 879.4 | 833.3 | 1408 | 1615 | valid ($1.08\times10^{-14}$) | not_run |
| `wrap_flags4` (`r00-seed-002`) | 27 | 84 | 80 | 8 | 586 | 585.1 | 558.4 | 912 | 888 | valid ($1.21\times10^{-14}$) | not_run |
| `wrap_flags5` (`r00-seed-003`) | 27 | 82 | 72 | 9 | 638 | 641.1 | 610.2 | 1008 | 1027 | valid ($1.22\times10^{-14}$) | not_run |
| `wrap_flags6` (`r00-seed-004`) | 27 | 76 | 64 | 10 | 690 | 697.6 | 661.9 | 1106 | 1139 | valid ($1.13\times10^{-14}$) | not_run |
| **`wrap_sn_headline` (`r00-seed-005`)** | 25 | **71** | 48 | 17 | 1118 | 1124.0 | 1064.5 | 1816 | 2276 | valid ($8.87\times10^{-15}$) | certified |
| `wrap_sn_r05F3` (`r00-seed-006`) | 25 | 72 | 56 | 13 | 864 | 879.4 | 833.3 | 1408 | 1570 | valid ($9.49\times10^{-15}$) | not_run |
| `wrap_sn_r02F5` (`r00-seed-007`) | 25 | 74 | 64 | 10 | 690 | 697.6 | 661.9 | 1106 | 1134 | valid ($1.09\times10^{-14}$) | not_run |
| Paulo 15-qubit file wrapped, $U_B$ only, $\beta=-0.05$ (external) | 31 | 108 | 96 | 4 | 348 | – | 335.2 | 510 | 746 | valid at its own angle ($1.32\times10^{-14}$) | n_a |
| best F1 (`r02-F1-002`) | 25 | 71 | 40 | 17 | 1110 | 1116.0 | 1056.5 | 1808 | 2291 | valid ($7.21\times10^{-15}$) | certified |
| best F2 (`r02-F2-002`) | 26 | 72 | 44 | 19 | 1242 | 1248.1 | 1180.1 | 2020 | 2614 | valid ($1.56\times10^{-14}$) | not_run |
| best F3 (`r05-F3-005`) | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3210 | valid ($1.44\times10^{-14}$) | certified |
| best F4 (`r02-F4-002`) | 24 | 73 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3218 | valid ($1.25\times10^{-14}$) | not_run |
| best F5 (`r05-F5-005`) | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3220 | valid ($1.27\times10^{-14}$) | not_run |
| global best by archive key (`r05-F3-005`) | 24 | 68 | 24 | 22 | 1396 | 1417.4 | 1339.5 | 2312 | 3210 | valid ($1.44\times10^{-14}$) | certified |
| **headline by robust key (`r05-F3-005`)** | **24** | **68** | **24** | **22** | **1396** | **1417.4** | **1339.5** | **2312** | **3210** | valid ($1.44\times10^{-14}$, leak 0) | **certified** |

Notes on the rows:
- **Polish and windowed Qiskit L3 change nothing** (94 CX, 598 T, depth 880, the same as general).
- **Whole-circuit Qiskit level 3** hoists Hadamard gates so that one input spreads over more than $10^6$ amplitudes, which is beyond the exact sparse engine. Only counts are shown (`round-000.json::external`).
- **The windowed L3 seed has no $\bar T$.** It is listed under `extra.unrankable`. It is a circuit-valued seed without a program file (tester 437 O2), so it cannot be rebuilt at the 20 pairs. That reason is my reading of the files.
- **Paulo's row is not like-for-like.** It is $U_B$ alone at its own fixed $\beta=-0.05$, which equals $+0.05$ in the spin-network gauge (METHODS-lsh L5). The step rows include the electric layer and use $\beta=0.61$.
- **The general row's Lean cell.** It says `not_run` because the loop certifies only each round's best. The same circuit is native-certified as an M7 result (Report 7 §3.6, `results/lsh/step.json::extra.lean`).
- **The best F2 row is a hybrid.** F2 was meant to be native, but `r02-F2-002` puts the swap-diagonal frame on site 1 and a Margolus transcoder on sites 0, 2 and 3 (its SUMMARY line).
- **The general check against M7.** `extra.m7_general_check`: the general row's 94 CX, $T_{\rm fixed}=88$ and $N_{\rm rot}=8$ equal `results/lsh/step.json`.

**Headline against its comparison rows** (all trivial differences):

| comparison | CX | $T(10^{-6})$ | $\bar T$ | $T(10^{-10})$ | depth$_{\rm CT}$ | other |
|---|---|---|---|---|---|---|
| vs wrapped seed `r00-seed-005` | $71\to68$ ($-4.2\,\%$) | $1118\to1396$ ($+24.9\,\%$) | $1124.0\to1417.4$ ($+26.1\,\%$) | $1816\to2312$ ($+27.3\,\%$) | $2276\to3210$ ($+41.0\,\%$) | $N_{\rm rot}$ $17\to22$; $T_{\rm fixed}$ $48\to24$; qubits $25\to24$ |
| vs general | $94\to68$ ($-27.7\,\%$) | – | $592.6\to1417.4$ ($+139.2\,\%$) | – | – | qubits $31\to24$ |

### 3.2 The three numbers (`m8-compressed.json::extra.vs_spinnet`)

| quantity | value | source |
|---|---|---|
| spin-network headline `r02-F1-002` (Report 4) | 31 CX, $\bar T=1092.0$ | `vs_spinnet.spinnet_headline` |
| the same circuit wrapped by the transcoder, `r00-seed-005` | 71 CX $=31+40$, $\bar T=1124.0$ | `vs_spinnet.wrapped`, `transcoder` (40 CX, $T_{\rm fixed}=32$) |
| LSH headline `r05-F3-005` | **68 CX**, $\bar T=1417.4$ | `vs_spinnet.lsh_headline` |
| $\texttt{native\_gain\_cx}=71-68$ | **3** | `vs_spinnet.native_gain_cx` |
| $\texttt{overhead\_cx}=68-31$ | **37** | `vs_spinnet.overhead_cx` |
| $\bar T$ of LSH headline − wrapped | $+293.4$ | `native_gain_t_avg` $=-293.4$ |
| $\bar T$ of LSH headline − spin-network headline | $+325.4$ ($+29.8\,\%$, trivial) | `overhead_t_avg` |
| $\bar T$ of wrapped − spin-network | $+32.0$ (the transcoder's fixed T) | `wrapped_minus_spinnet_t_avg` |

Reading (the file's own sentence): "the loop removed 3 of the 40 transcoder CX; the LSH register still costs 37 CX beyond the spin-network optimum."

The 71-CX entry `r02-F1-002` of this loop (§3.4) is still a wrapped spin-network design: it keeps the transcoder and merges a walk toggle. All of the 3-CX gain comes from the native F3 frame.

### 3.3 CX versus $\bar T$: the trade-off front, and what the headline costs
Source: `m8-before-after.md` ("CX versus T_avg front") and `m8-compressed.json::extra.pareto_cx_tavg`.

An entry is on the *Pareto front* if no other valid entry has both fewer-or-equal CX and lower-or-equal $\bar T$.

| CX | $\bar T(10^{-6})$ | entry | family / round | Lean |
|---|---|---|---|---|
| 68 | 1417.4 | `r04-F3-004` (tied with the headline `r05-F3-005` and with `r05-F5-005` on CX and $\bar T$) | F3 / 4 | certified |
| 70 | 1354.3 | `r03-F3-003` | F3 / 3 | certified |
| 71 | 1116.0 | `r02-F1-002` | F1 / 2 | certified |
| 72 | 879.4 | `r00-seed-006` (`wrap_sn_r05F3`) | seed | not_run |
| 74 | 697.6 | `r00-seed-007` (`wrap_sn_r02F5`) | seed | not_run |
| 82 | 641.1 | `r00-seed-003` (`wrap_flags5`) | seed | not_run |
| 84 | 585.1 | `r00-seed-002` (`wrap_flags4`) | seed | not_run |

What the front shows:
- **The headline is the CX minimum of the front and has the largest $\bar T$ on it.** Going from 72 CX (`wrap_sn_r05F3`) to 68 CX saves 4 CX and costs $+538.0$ in $\bar T$ ($+61.2\,\%$, trivial difference).
- **Under a T-first cost model the headline would not be chosen.** The project ranks CX first (`prompts/001`), so it is.
- The wrapped seed `r00-seed-005` (71, 1124.0) is not on the front: `r02-F1-002` has the same CX and lower $\bar T$.
- The general circuit (94, 592.6) is dominated by `wrap_flags4` (84, 585.1).

**Why T rose.** $T=T_{\rm fixed}+\sum_rT_r$, at about 62–63 T per rotation:
- headline: $(1396-24)/22=62.4$ per rotation;
- wrapped seed: $(1118-48)/17=62.9$ per rotation (trivial differences from §3.1).

The native frame halves the fixed T ($48\to24$) but needs 22 rotations instead of 17, so rotation T grows by $1372-1070=302$. The net is $+278$ (trivial differences). The extra rotations, not the CX gates, are the cost.

That this is structural and not angle luck: $\bar T=1417.4$ lies within 22 of the nominal $T$ (1396), inside the noise band of L14.

### 3.4 How the search went
Sources:
- the round files, which give `best_key` (archive key), `wall_s` (evaluator wall only, not the proposer sessions) and `lean_seconds`;
- `stop.json`, which gives the headline record and `improved`;
- the commit messages of the round commits, which give the cumulative sessions;
- the synthesis re-verification of each round's new best: the circuit with every rotation replaced by its pygridsynth word at $\varepsilon=10^{-6}$, against the budget $N_{\rm rot}\varepsilon+10^{-9}$.

| round | families (programs) | valid / new | best archive key (CX, $T$, depth$_{\rm CT}$, qubits) | headline (robust key) | improved | streak | sessions | synthesis check | wall (s) | Lean (s) | tester |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | seeds | 10 / 10 | (71, 1118, 2276, 25) | `r00-seed-005` (71, 22480, 0, 46384, 25) | yes | 0 | – | $4.61\times10^{-6}\le1.70\times10^{-5}$ | 15.2 | 1.03 | 437 |
| 1 | F1 F2 F3 F4 F5 | 5 / 5 | unchanged | `r00-seed-005` | no | 1 | 6 | – | 7.0 | 0 | 438 |
| 2 | F1 F2 F3 F4 F5 | 5 / 5 | (71, 1110, 2291, 25) | `r02-F1-002` (71, 22320, 0, 46684, 25) | yes | 0 | 11 | $5.61\times10^{-6}\le1.70\times10^{-5}$ | 13.7 | 3.04 | 439 |
| 3 | F3 F5 (F1 stopped, no program) | 2 / 2 | (70, 1338, 3047, 24) | `r03-F3-003` (70, 27086, 0, 60193, 24) | yes | 0 | 13 | $7.45\times10^{-6}\le2.10\times10^{-5}$ | 6.3 | 2.09 | 441 |
| 4 | F1 F3 F5 | 3 / 3 | (68, 1396, 3221, 24) | `r04-F3-004` (68, 28348, 0, 63598, 24) | yes | 0 | 16 | $8.10\times10^{-6}\le2.20\times10^{-5}$ | 6.0 | 0.89 | 442 |
| 5 | F1 F3 F5 | 3 / 3 | (68, 1396, 3210, 24) | `r05-F3-005` (68, 28348, 0, 63378, 24) | no (tie) | 1 | 19 | $8.10\times10^{-6}\le2.20\times10^{-5}$ | 6.2 | 0.90 | 443 |
| 6 | F3 | 1 / 1 | unchanged | `r05-F3-005` | no | **2** | **20 = stop** | – | 1.9 | 0 | 444 |

In words: CX went $94$ (general) $\to71$ (round 0, wrapped seed) $\to71\to71\to70\to68\to68\to68$. Round by round:
- **Round 1: no gain.** The five families gave 73, 80, 76, 74 and 73 CX (`r01-F1…F5-001`). The F3 program `r01-F3-001` (76 CX) was the first native frame: the raw $\ell_{nv}$ parity folded into site 0, Margolus Toffolis on sites 1–3, and a collapse onto one qubit. In it, a 17-term Walsh multiplexer cost 30 CX.
- **Round 2: $-8$ fixed T at 71 CX.** `r02-F1-002` merges the first walk toggle into a collapse CX as a CZ gate ("free end", the proposer's label). This is a $CZ\cdot CX$ identity the tester checked exactly (tester 439). It keeps 71 CX with $T_{\rm fixed}$ $48\to40$ and robust $\sum T$ $22480\to22320$. That is an improvement by the rule, but about 0.7 % of T (tester 439 O1). Also in round 2, `r02-F3-002` and `r02-F5-002` re-emitted the seed circuit: F3 literally, F5 up to commuting gates (tester 439). Their SUMMARY lines call them "negative-result carriers" after searches found nothing cheaper.
- **Round 3: first CX gain, native.** `r03-F3-003` keeps the 46-CX frame of `r01-F3-001` and re-tours its multiplexer with an exact Held–Karp tour of 24 toggles. It uses site 0's two outer qubits as walk generators: 70 CX, $T=1338$. `r03-F5-003` is a structural variant of `r02-F1-002` with no gain (tester 441).
- **Round 4: 68 CX.** `r04-F3-004` is the same frame gate for gate with a new 22-toggle walk, found by simulated annealing over toggle sequences. Simulated annealing (SA) is a randomised search. `r04-F1-003` and `r04-F5-004` are structural variants of existing 71-CX designs with no gain (tester 442).
- **Round 5: depth-only tie.** `r05-F3-005` is `r04-F3-004` with the four electric phases moved ahead of the Toffolis across commuting gates (tester 443: exact commutator 0.0). $\mathrm{depth}_{\rm CT}$ drops $3221\to3210$ ($-0.34\,\%$, trivial difference). Nothing else changes. The headline rule uses depth, so the headline id moved to `r05-F3-005` (depth sum 63378 vs 63598). The stop rule ignores depth, so round 5 is "no improvement". The last improvement is credited to round 4. `r05-F5-005` (68 CX, depth sum 63578) is a third tie, differing from `r04-F3-004` in two collapse CX. `r05-F1-004` (76 CX) is a probe of another Toffoli control pattern.
- **Round 6: last session, negative-result carrier.** `r06-F3-006` keeps the frame with a different 22-toggle walk: 68 CX, $T=1528$, 24 rotations, robust key $(68,30888,0,69806,24)$. It is valid but not a candidate. It carries the 21-toggle search of §4.

**Lineage** (`m8-compressed.json::extra.lineage`; parent → child, (CX, $T$ nominal)):
- **Headline:** `r01-F3-001` (76, 1338; no parent) $\to$ `r03-F3-003` (70, 1338) $\to$ `r04-F3-004` (68, 1396) $\to$ **`r05-F3-005`** (68, 1396) $\to$ child `r06-F3-006` (68, 1528).
- **F1:** `r01-F1-001` (73, 1056) $\to$ `r02-F1-002` (71, 1110) $\to$ `r04-F1-003` (71, 1110) and `r05-F1-004` (76, 1784).
- **F5:** `r01-F5-001` (73, 1442) $\to$ `r02-F5-002` (71, 1118, seed copy). Then `r03-F5-003` and `r04-F5-004` took `r02-F1-002`'s line, and `r05-F5-005` took `r04-F3-004` as parent (migration).
- **F2:** `r01-F2-001` (80) $\to$ `r02-F2-002` (72).
- **F4:** `r01-F4-001` (74) $\to$ `r02-F4-002` (73).
- F2 and F4 were not among the best three families after round 2 and ran no further sessions.
- The seeds were not parents of any proposer program (every round-1 entry has `parent: null`).

### 3.5 What the headline circuit does
Source:
- the program `compress/programs/lsh/F3/005-alpha-early-walk22.py` (sha256 `5b00e6e7…`, 91 lines) and its SUMMARY and DISCOVERY lines;
- `m8-compressed.json::metrics`;
- METHODS-lsh L12 (ii).

The testers confirmed the circuit, its counts and the gate-list facts below (testers 441–444). The explanation of why it works is the proposer's and was **not** independently derived. Labels such as "fold frame", "pivot", "walk", "toggle" and "free end" are the proposers', not standard terms.

1. **Frame, 46 CX and $T_{\rm fixed}=24$.**
 - CX gates fold the raw $\ell_{nv}$ parity $p=\bigoplus_c\ell_{nv}(c)$ into site 0. On bright codes this parity is the class bit $[k=+1]$ (L13 (iii)).
 - On each of sites 1–3, CX gates form the site's flux bits, and one **Margolus Toffoli** acts. This is a real-phase relative-phase Toffoli: the Toffoli gate up to a $-1$ sign on one input pattern, 3 CX and 4 T (Margolus construction). It takes the place of the transcoder's `rccx`, whose $\pm i$ phases would not cancel in this frame (tester 438 O1; DISCOVERY of `r01-F3-001`).
 - A *collapse* (CX onto qubits 9, 6, 3) puts the plaquette move of all 16 bright codes onto one qubit, the *pivot* (qubit 0).
 - Everything is undone after the walk. Six Margolus Toffolis × 4 T give $T_{\rm fixed}=24$.
 - Gate count, forward and back: $2+3+3\times5+3=23$ CX each way, so 46 (count of the program lines; equals the key).
2. **Walk, 22 CX.** Between two Hadamard gates on the pivot sits a *Gray-code walk*: a sequence of 22 CX "toggles" from single-wire parity qubits onto the pivot, with an $R_z(c\beta)$, $c=\pm\tfrac14$, at 18 of the positions. The first rotation is at the start point, which is reached by a CZ merged into the collapse CX.
 - The 18 rotations build the coupling as a **Walsh series** (a sum of parity terms $\sum_xc_x(-1)^{x\cdot L}$; Welch et al., arXiv:1306.3991).
 - The walk works over the points of $\mathbb F_2^6$ with bits $(p,y_1,y_2,y_3,e,\ell_{2v}(0))$.
 - Target values on the 37 label values (tester 444 part 2(b)): $g(0)=-4$, $g(16)=g(48)=-1$, $g(1)=g(17)=g(49)=+2$, all other labels 0.
3. **Outer qubits.** The walk uses the two outer qubits of site 0, $\ell_{2v}(0)$ (q13) and $\ell_{v1}(0)=\ell_{2v}(0)\oplus e$ (q14), as CX controls only: q13 3 times and q14 5 times (tester 444 check 9 on the child, which mirrors them).
 - They are never a target and carry no one-qubit gate.
 - Deleting or re-routing those CX gives error $2.0$ (testers 441–444). So the reads are used and needed.
 - The evaluator reports `outer_bits_read 2`, 4 blocks, method `physical`.
4. **Electric layer.** Four phases $p(-\tfrac34\alpha)$, one per site, act on flux wires that the Toffolis use only as controls. They were moved ahead of the Toffolis in round 5, which is the only change from `r04-F3-004`.
5. **Counts** (`metrics.macro_counts`): cx 68, h 50, s 26, sdg 25, rz 18, p 4, t 12, tdg 12; depth 96 before synthesis; 24 qubits, 0 ancillas.
 - $\mathrm{CX}=46+22=68$.
 - $N_{\rm rot}=18+4=22$.
 - $T_{\rm fixed}=12+12=24$ (trivial sums, equal to the key).

**The headline at four accuracies** (`m8-compressed.json::metrics.t_table`). "Synth. error" is the error of the circuit after every rotation is replaced by its pygridsynth word; its budget is $N_{\rm rot}\varepsilon+10^{-9}$ (trivial arithmetic). Every synthesised circuit has verdict `ok` with span leak 0.

| $\varepsilon$ | $T_{\rm fixed}$ | $N_{\rm rot}$ | $T$ (pygridsynth) | $T_{\rm est}$ | synth. error (budget) |
|---|---|---|---|---|---|
| $10^{-4}$ | 24 | 22 | 956 | 901.0 | $6.32\times10^{-4}$ ($2.2\times10^{-3}$) |
| $10^{-6}$ | 24 | 22 | 1396 | 1339.5 | $8.10\times10^{-6}$ ($2.2001\times10^{-5}$) |
| $10^{-8}$ | 24 | 22 | 1828 | 1778.0 | $6.03\times10^{-8}$ ($2.21\times10^{-7}$) |
| $10^{-10}$ | 24 | 22 | 2312 | 2216.5 | $1.03\times10^{-9}$ ($3.2\times10^{-9}$) |

**Outer-site electric row** (`extra.outer_electric_row`; M7 result `results/lsh/UE.json`, commit `76fd221`, unchanged by the loop):
- 0 CX, 20 rotations, reads 12 outer bits;
- exact-angle error $7.7\times10^{-16}$, Gauss residual $5.6\times10^{-16}$;
- $T=880$ at $10^{-4}$ and $1280$ at $10^{-6}$.
- Its synthesised form writes the outer register and is **not verifiable** by this evaluator (`reason: writes_outer`; audit 303 N5). Only its T cost is reported.

### 3.6 Verification (second engine and checks, per round)
- **Evaluator, every entry.** All 29 entries are valid at the three pairs (`summary.json`).
- Headline (`m8-compressed.json::verification`): 433 inputs, `total_error` $1.44\times10^{-14}$, block error $6.1\times10^{-15}$, pruning bound $8.3\times10^{-15}$, leak 0, span leak 0, Gauss residual $5.7\times10^{-16}$, global phase $1+3.3\times10^{-17}i$.
- At the alternate pairs: $1.30\times10^{-14}$ and $1.50\times10^{-14}$ (`extra.verdicts_alt`).
- **Testers' own engine.** Their own 24-bit codes, own `expm` target and own gate walk, on all 433 states at three pairs, native and lowered. Maximum error per round:
- round 1: $6.4\times10^{-15}$ (438);
- round 2: $6.4\times10^{-15}$ (439);
- round 3: $6.4\times10^{-15}$ (441);
- round 4: $6.1\times10^{-15}$ (442);
- round 5: $6.6\times10^{-15}$ (443);
- round 6: $6.4\times10^{-15}$ (444).
- The wrong-sign target ($-\beta$) is 0.89–1.88 away, so the check can fail.
- **Second engine, Qiskit-Aer statevector.** Aer is Qiskit's high-performance simulator; a statevector run holds the full amplitude vector. Circuits that never touch the outer register were checked on the 47 inner codes (data + ancilla qubits). Circuits that read outer qubits were checked on **full 24-qubit seeded states** across the four $(q13,q14)$ sectors plus mixtures, because the 47-code check does not apply to them.

| round (tester) | Aer mode | max error | other |
|---|---|---|---|
| 0 (437) | 47 inner codes, 9 programs + L3 seed, 3 pairs | $6.3\times10^{-15}$ | headline seed $3.2$–$3.8\times10^{-15}$; ancilla leak $\le6.5\times10^{-31}$ |
| 1 (438) | 47 codes for F1, F2, F4, F5, 4 pairs; F3-001 on 12 full states (seed 20261119) | $4.1\times10^{-15}$; full $2.5\times10^{-15}$ | outer-weight change $\le4.0\times10^{-16}$ |
| 2 (439) | 47 codes, 4 pairs (no program reads outer qubits) | $4.3\times10^{-15}$ | – |
| 3 (441) | F3-003 on 12 full states (seed 20261120); others 47 codes | $2.8\times10^{-15}$ | outside-code weight $\le5.3\times10^{-15}$ |
| 4 (442) | F3-004 on 12 full states (seed 20261120) | $2.9\times10^{-15}$ | outer-weight change $\le5.3\times10^{-16}$ |
| 5 (443) | all three programs on 12 full states (seed 20261121) | $2.7\times10^{-15}$ | outer-weight change $\le4.7\times10^{-16}$ |
| 6 (444) | F3-006 on 12 full states (seed 20261121) | $2.4\times10^{-15}$ | Abelian-Gauss weight 0.0 |

- **Counts, robust keys, stop record.** In every round the testers recomputed CX, $T_{\rm fixed}$, $N_{\rm rot}$, $T$, $\mathrm{depth}_{\rm CT}$ and qubits with their own lowering and own pygridsynth, and all were equal to the archive. Robust keys from the stock worker were equal to `robust.json`. Their own derivation of the stop record was equal to `stop.json` (tester 444 checks 12–20).
- **Programs and provenance.** Program sha256 on disk equals the archive and the round file for every new entry. No proposer committed to `src/`, `tests/` or `lean/` (tester 444 check 27).
- **Hashes.** The evaluator hash `88e0d76b…` is the same in all round files, entries and `robust.json` (tester 444 check 3).
- **Milestone gate.** Gate tester: [GATE: tester 445 full — counts and verdict]. Audit: [GATE: audit NNN verdict and notes]. Benchmark: [GATE: benchmark NNN].

### 3.7 Lean status (trust label: native-certified, first-order step)
**Definitions.**
- *Kernel-checked*: Lean's small trusted core re-verified the proof by computation, with only the standard axioms.
- *Native-certified*: the compiled Lean checker `su2plaq_cert_lsh` accepted an exported certificate, and the theorem file proves `Su2PlaqCert.LSH.checkJsonString certJson = true` by `native_decide`. The trust is in the Lean compiler and the checker source, not only in the kernel.

**The headline is native-certified, not kernel-checked.**

- **Headline `r05-F3-005`: `certified`** (`m8-compressed.json::extra.lean`).
- Certificate `results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json` (sha256 `b05ef21d…`): 215 gates, 24 qubits (12 data + 12 outer), 433 states, base $(d_\alpha,d_\beta)=(4,8)$. Checker sha256 `16b3278f…`.
- Theorem `lsh_best` in `lean/certs/lsh-best-step.lean` (sha256 `dae606e5…`), first line `-- entry r05-F3-005, program sha256 5b00e6e7…`.
- Elaborated with return code 0 in 0.96 s.
- `#print axioms` gives the three standard axioms `propext`, `Classical.choice`, `Quot.sound`, plus one native axiom `lsh_best._native.native_decide.ax_1_1`.
- **Binding** (audit 302 N3, made inside the proved literal):
- `entry_id` `r05-F3-005`;
- `program_file_sha256` `5b00e6e7…`;
- `git_dirty: false`, `git_commit` `1e765f1`;
- `matches_headline: true`.
- The locked test M8-L5 compares the gate records with fresh exports of the rebuilt program at two angle pairs (METHODS-lsh L15).
- **What it covers.** Exact arithmetic over Laurent polynomials in $e^{i\alpha/d_\alpha}$, $e^{i\beta/d_\beta}$. So it holds for **all** real $(\alpha,\beta)$ of the angle-linear gate family the program emits, for the **first-order step** $U_BU_E$ only.
- **Other certificates.** The loop certified each round's new best: `r00-seed-005`, `r02-F1-002`, `r03-F3-003`, `r04-F3-004`.
- The testers re-ran the compiled checker: ACCEPT. Four mutated certificates per round: REJECT (testers 439, 441–443).
- The $-\beta$ circuit and a CX-swapped gate list are `rejected` (tester 436).
- Rows marked `not_run` were not certified inside the loop.
- **Trust limits** (METHODS-lsh L10, L15; Report 7 §3.6):
1. The target is pinned by SHA-256 of the exporter's exact route-B target, cross-checked numerically to $10^{-12}$. No Lean theorem derives the LSH coupling from the vertex factors; that tie is numerical.
2. "All angles" means the angle-linear family read at the nominal pair.
3. Lean never decides validity; the numerical evaluator does.

### 3.8 Uniform Raychowdhury–Stryker splitting: a structure row, not a circuit
Source: `m8-compressed.json::extra.uniform_split`, METHODS-lsh L16.

At corners 1 and 3 the uniform splitting of Raychowdhury–Stryker re-pairs the link ends (inner, outer $\mid$ inner, outer). The change of basis is a corner recoupling $R$, and $H_B^{\rm RS}=R^{\mathsf T}H_BR$.

| splitting | non-zeros | max per row | non-zero rows | moduli | inner patterns depending on outer spins | sites / qubits touched |
|---|---|---|---|---|---|---|
| uniform RS (corners 1, 3 repaired) | 400 | 4 | 324 | $\tfrac14,\tfrac{\sqrt3}4,\tfrac12,\tfrac34,\tfrac{\sqrt3}2,1,\tfrac32,\sqrt3,2$ | 16 of 47 | 6 / 18 |
| ours, (inner $\mid$ outer) | 256 | 1 | 256 | $\tfrac12,1,2$ | none | 4 / 12 |

- The two have the same spectrum (difference $3.3\times10^{-15}$). Circuit: **not built**.
- **The LSH-versus-spin-network comparison holds for the (inner $\mid$ outer) splitting only.** A circuit in the uniform splitting would have to write outer-site qubits; that would be a sixth encoding and is not planned (`prompts/401` §12 D10).

## 4. Findings

**DISCOVERY lines.** Full text is in `compress/discoveries/lsh.md` (49 lines from 19 entries). All are **proposer claims**, except where a tester confirmed them as stated below.

1. **The raw parity is a free class bit (confirmed as circuit fact).** Folding the four raw $\ell_{nv}$ bits into site 0 gives the class bit $p$. The rotation angle on bright codes depends on $p$ (and $e$) only. With that fold, three Toffolis on sites 1–3 suffice to put the move on one qubit (`r01-F3-001`, `r01-F4-001`).
 - Tester 442: frame identity confirmed. This uses the kernel-checked facts of L13 (iii) (`coupling_by_y_weight`, `y_parity_invariant`).
2. **Margolus Toffolis are needed (confirmed).** Qiskit's `rccx` leaves $\pm i$ pair-phase ratios in the fold frame; the real-phase Margolus Toffoli (3 CX, 4 T) is exact there (`r01-F3-001`, `r01-F4-001`). Tester 438 O1: F3 and F4 use no `rccx`, and the circuits are exact.
3. **Free CZ end (confirmed as an exact identity).** A walk toggle next to the pivot's Hadamard can be merged as a CZ into a pivot-controlled collapse CX for free (`r01-F5-001`, `r02-F1-002`). Tester 439: $CZ\cdot CX$ = `s, sdg, cx, s` exactly; removing the CZ gives error 2.0.
4. **Choose the walk and the support together (proposer claim).** Searching toggle sequences directly (SA) beats "choose the Walsh support, then tour it": 22 against 24 toggles (`r04-F3-004`). The 22-toggle walk exists (tester 442); the method claim was not tested.
5. **The 18 rotations (proposer claim, not tested).** In the 64-point walk space the minimum Walsh support is 16 (HiGHS-optimal). HiGHS is an open-source linear and mixed-integer optimiser. All 8 such supports tour at ≥ 24 toggles. So a 22-toggle walk needs ≥ 18 rotations, and the headline's 18 is optimal (`r05-F3-005`).
6. **No exact walk of ≤ 21 toggles: CONFIRMED by tester 444, within its stated scope.**
 - **Statement.** In the F3 frame's walk space, with points $(p,y_1,y_2,y_3,e,\ell_{2v}(0))\in\mathbb F_2^6$, generators $p,y_1,y_2,y_3,e,\ell_{2v}(0),\ell_{v1}(0)$, both ends free in $\{0,e\}$, a rotation allowed at every visited point, and cost = number of toggles, no walk of ≤ 21 toggles has a visited set whose parity characters reproduce the target on the 37 labels. So **67 CX ($46+21$) is impossible inside this frame's walk space.**
 - **Method** (proposer's program in `results/compress/lsh/evidence/r06-F3-exh21/`, rebuilt and rerun by the tester).
   - Every walk must visit all 16 classes of $\mathbb F_2^6/\langle e,\,p{+}y_1{+}y_2{+}y_3{+}\ell_{2v}(0)\rangle$. The tester verified this with exact rational arithmetic: 16 of 16 classes are necessary. The proposer calls each class a "cocircuit"; that word is the proposer's.
   - So the walk's shadow on the 5-cube is a closed walk of even length $m\in\{16,18,20\}$ with at most $21-m$ extra $e$-moves.
   - A complete C depth-first enumeration covers $9.81\times10^{9}$ phase-1 nodes plus $9.55\times10^{7}$ phase-2 nodes, split over 7 parts. It found 0 walks in every split, with counts equal to the proposer's logs digit for digit.
 - **Cross-checks.**
   - Floating-point feasibility was checked against exact rank modulo $2^{61}-1$ on every call in two splits: 0 mismatches in about $3\times10^7$ calls.
   - Removing the class-cover bound (≤ 19 toggles) or the superset pruning (≤ 20 toggles) changes no feasible set.
   - An independent exact brute force agrees on 13 positive controls and finds nothing on more than 25 000 closed 5-cube walks ($2.2\times10^8$ lifts; part of this was sampled).
   - The search re-finds the known 22-toggle walks.
 - **Scope.** Only this 64-point space. Not covered: the $u,v,w$ wires, the outer bits of sites 1–3, other free toggles, flags or ancillas, other frames. **This is not a CX lower bound for the circuit family** (tester 444 O3; METHODS-lsh L12 (vii)).
7. **$U_E$ needs 4 rotations (tester-confirmed).** On the 47 inner codes, $\sum_cN_n(c)$ is not a constant plus 1, 2 or 3 parity characters. It is exactly a constant plus the 4 characters $\chi_{\ell_{pn}\oplus\ell_{nv}}(c)$ (residual $6.8\times10^{-15}$; tester 444 (d)6, model "constant plus $k$ parity characters").
8. **Weak negatives, not bounds.** Several "no walk found" statements of F1 and F5 (rounds 1–5) come from time-limited MILP (mixed-integer linear programming) or simulated annealing. The proposers themselves call several of them weak, because the same searches failed to re-find walks known to exist (`r04-F1-003`, `r05-F1-004`, `r02-F5-002`).

**Kernel-checked facts given to the proposers and used.** These are in `lean/Su2Plaq/LSH/Facts.lean`, kernel-checked, `decide` (METHODS-lsh L13); the mapping to the headline below is mine, read from the program comments and the ideation, not a formal dependency.
- `inner_codes_from_rules`: the code list is the rule-defined set.
- `coupling_zero_iff_dark`, `dark_site_is_and`: a code is dark iff some site has $\ell_{nv}\wedge\ell_{vp}$. The headline's $y_c$ wires are these per-site AND flags.
- `coupling_by_y_weight`, `y_parity_invariant`: the class bit is the raw $\ell_{nv}$ parity $p$, the headline's site-0 fold.
- `move_per_site`: the move flips $\ell_{pn}$ where $w=0$ and $\ell_{nv},\ell_{vp}$ where $w=1$. This is the frame's collapse.
- `eight_differences`: no CNOT-only frame exists, so some Toffolis are unavoidable.
- `link_bit_two_ways`: the Abelian Gauss law as a parity. The relation $\ell_{v1}(0)=\ell_{2v}(0)\oplus e$ used for the outer pair is a Gauss identity checked numerically by the tester (tester 444 part 2(b): $q_{14}=q_{13}\oplus q_9$ on all 433 states), not a Lean theorem.

**The limit of the comparison.** "31 / 71 / 68" compares LSH with the spin-network encoding in the (inner $\mid$ outer) splitting, where the LSH basis is the spin-network basis in another bit code (§3.8). Under the uniform RS splitting the operator is denser (400 vs 256 non-zeros) and touches 6 sites instead of 4; no circuit exists for it here.

## 5. Problems and assumptions

- **Expected conflict with locked test M8-G2 (gate item; not run for this report).**
- `tests/acceptance/m8/test_lsh_m8_gate.py::test_M8_G2` runs Aer on data + ancilla qubits only. Its helper asserts that no gate touches an outer qubit: "a circuit that reads outer qubits … fails here with a message (a planner decision, not a skip)".
- The headline and archive best `r05-F3-005` reads q13 and q14 as CX controls (§3.5). So M8-G2 is expected to fail on it by design.
- `prompts/401` §9 lists "the archive best or headline touches the outer register" as **stop and return to the planner**, and §12 D11 says such a best "goes back to the planner".
- The per-round testers covered these circuits with full 24-qubit Aer states (§3.6), so the physics check exists; the locked test does not accept it.
- Outcome: [GATE: tester 445 full — counts and verdict].
- **Defaults of `prompts/401` §12, taken without asking ("default, not reviewed by Digonto").** `notes/STATUS.md` 2026-11-13 lists D1–D13 "for Digonto". The acceptance of 2026-11-17 covered `prompts/009` and `prompts/010` only.
- **D1:** target = full LSH-register first-order step, transcoder included.
- **D2:** Phase 0 first; registry entry inside the 008 window; rounds after the freeze; no shim.
- **D3:** ten seeds, including three pinned spin-network programs.
- **D4:** robust-key headline with the audit-302 hardenings N2, N6, N3.
- **D5:** stop rule without depth, noise band $20N_{\rm rot}$; 8 rounds / 3 without gain / 20 sessions.
- **D6:** at least two native families, one kept from round 3.
- **D7:** `stamp="encoding"`, six LSH evaluator files, `loop.py` and `lean_export.py` unhashed.
- **D8:** Lean facts in `Facts.lean`, theorem `lsh_best`, no-rewrite rule.
- **D9:** audit N8/N4 handled by new locked tests.
- **D10:** uniform splitting as a structure row only.
- **D11:** Aer on data + ancilla at the gate (see the first item).
- **D12:** Paulo's file as an external $U_B$ row at $\beta=-0.05$; order 2 and the outer electric row outside the loop.
- **D13:** file numbers.
- **What `n_a` means.** `n_a` ("not applicable") is the Lean status when the exporter cannot write a certificate:
- `non_linear_angle…`: some rotation angle is not a rational multiple of $\alpha$ or $\beta$;
- `phase_not_in_K`: the global phase is not in the exact number field;
- `too_many_qubits`.
- Such an entry gets $\rho=1$ and ranks behind an angle-linear tie, but it stays valid (Digonto 2026-11-05: angle-linearity preferred, not required).
- In M8 no ranked entry is `n_a`: all 28 ranked entries are angle-linear (`extra.ranking`). `n_a` appears only on the two external rows, where no certificate is meaningful.
- **Audit 303 wording items N3, N5, N6: already fixed by Report 7** (§2, §3.3, §3.6, §4); restated here where they apply.
- **N3:** the word "certified" has two meanings. In the verdict columns and `verification.certified`, it is the **numerical evaluator's** verdict. In the Lean column, it is the compiled checker. Only the Lean meaning carries the trust label of §3.7.
- **N5:** the synthesised outer electric row is not verifiable by the evaluator (§3.5).
- **N6:** route A and LSH differ by a diagonal $\pm1$ sign matrix; 64 of the 128 bright pairs of physical states have opposite matrix-element sign, and which member of a pair carries the minus is a choice of the alignment routine (Report 7 §2). Nothing in M8 depends on it.
- **The depth tie-break is below noise.** `r05-F3-005`, `r04-F3-004` and `r05-F5-005` are equal on $(\mathrm{CX},\sum T,\rho,\text{qubits})$. The headline is picked by summed depth: 63378 vs 63598 vs 63578, a 0.3 % difference, below the 0.6 % synthesis-word noise of L14 (tester 444). This changes no CX or T number in this report.
- **Table quirk in `m8-before-after.md`.** The front table lists `r04-F3-004` as its first row and then says "the first row is the headline". The headline is `r05-F3-005`; it ties `r04-F3-004` on CX and $\bar T$. `m8-compressed.json::extra.headline` is authoritative.
- **The loop stopped by the session limit, not by saturation.** The last improvement was round 4 (68 CX); rounds 5–6 were variants and a negative-result carrier. A different search (more sessions, other frames, a T-first key) could find other points; the 21-toggle result closes only one design space.
- **Session accounting.** The round-3 F1 session stopped by the usage guard wrote no program and is not counted (§2). Counting launched sessions would have stopped the loop one session earlier; the stop reason would not change.
- **Provenance.**
- Round files record `git_dirty: true`, because the round outputs were uncommitted when written. Entries record false. Each result is bound by its program sha256 and the evaluator hash (tester 444 checks 17, 29).
- The per-round certificates carry `program_file_sha256` but no `entry_id`, which only the step-8.8 certificate has (tester 436 O1). The final binding reads `matches_headline: true`.
- The slow test M8-G3 rewrites `stop.json` (same content) and created `summary.json` on the real tree (tester 444 O1).
- numpy 2.5.4 and scipy 1.18.1 are recorded, while the project notes say 2.5.2 and 1.18 (as in Reports 4 and 6).
- **Source inconsistency (minor).** Tester 439 O2 says `r02-F4-002` has "the identical key (73, …) as F4-001". The archive gives `r01-F4-001` 74 CX and `r02-F4-002` 73 CX (`extra.lineage`, `extra.ranking`). This report uses the archive.
- **Scope.** First-order step $U_BU_E$ only. The second-order step and the outer electric row were not compressed (D12). All statements are up to one global phase. The 12 outer qubits are counted in "qubits", and the headline reads two of them as controls, which the spec allows ("outer qubits may be used as controls only").
- **Not recorded.** Proposer wall time and token cost of the 20 sessions; they dominate the loop's cost. Evaluator wall per round was 1.9–15.2 s (§3.4).


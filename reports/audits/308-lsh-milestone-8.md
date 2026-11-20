# Audit 308 — LSH milestone 8 (compression loop, amended gate test M8-G2, headline Lean certificate, Report 8 draft)

- Date: 2026-11-20
- Auditor: Claude Opus 5.5 (auditor role)
- Commit audited: `a5a9fce` (`git rev-parse --short HEAD`), branch `merge-desktop-tracks`, clean tree at start and end (I ran no pytest, so no spinnet certificate was rewritten; `git status --short` empty at the end).
- Commit range: the LSH/M8 part of `milestone-7..a5a9fce` (179 commits in total).
- Plan in force: `prompts/402-lsh-m8-g2-erratum.md` (G2 erratum) on `prompts/401-lsh-m8-compression-plan.md` (§9 and the rest), base `prompts/400`. Lock: `acceptance-v23`.
- Related reports: `reports/tests/445` (gate full, G2 red by design), `reports/tests/446` (gate re-run on v23, PASS), `reports/tests/437`–`444` (rounds 0–6), `reports/audits/303` (LSH M7), `reports/audits/305` (milestone-2c, shared modules), `reports/audits/307` (rishon M6).
- My scripts and outputs (session scratchpad, not committed; deterministic, no random numbers):
  `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/audit308_check.py` (+ `.json`), `audit308_counts.py` (+ `.json`), `audit308_nonphys.py`.
  Environment for all runs: conda env `coding`, `PYTHONPATH=src`, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`, `taskset -c 0-8 tools/run-capped python <script> <out.json>`.

## Verdict: PASS WITH NOTES

I found no blocking issue. The headline circuit `r05-F3-005` implements the M7 one-step unitary exactly on the whole physical subspace. I checked this with my own simulator at 29 angle pairs, including four outside the spec range. All reported counts reproduce. The headline selection and the stop rule are applied correctly. The Lean theorem proves what the certificate claims, with the stated axioms. The amended G2 test is exhaustive on the physical subspace and is sound. There are nine notes (N1–N9), mostly wording for Report 8 and two small code hygiene points. I do **not** believe any acceptance test or tolerance is wrong.

## 1. What was asked

Gate step 2 of milestone 8 (LSH compression track), per the coordinator's brief. The scope:
- the LSH code `src/su2plaq/lsh/{loop,rs_split,lean_export}.py` and `scripts/m8_results.py`;
- the G2 amendment in `tests/acceptance/m8/test_lsh_m8_gate.py`;
- the Lean theorem file and the headline certificate;
- METHODS-lsh L12;
- the M8 result files and the loop records;
- the headline program and the 21-toggle negative-result evidence;
- the shared compress modules, if no earlier audit covered them.

The four physics questions are answered in §4 and the draft Report 8 items (a)–(g) in §5.

## 2. What I did

- Oriented with graphify (`graphify query` on outer reads in the shared evaluator, `graphify explain certify_headline`, `graphify query` on depth_CT). Then I read: `prompts/402` (all), `prompts/401` (all, incl. §9 and §12), `notes/STATUS.md`, tester reports 445 and 446 (observations), and the G2 test (`test_lsh_m8_gate.py:81-412`). I also read the headline program, the Lean checker `lean/Su2PlaqCert/LSH/Check.lean`, the depth code (`compress/metrics.py`, `metrics/cliffordt.py:86-126`), and `lsh/loop.py` (`stop_key`, `improves`, `stop_record`, `stop_state`). Further: `lsh/lean_export.py:145, 465-511`, `lsh/rs_split.py`, `scripts/m8_results.py:170-200, 270`, METHODS-lsh L12, METHODS §7, the ideation file and the evidence folder.
- **Shared modules.** Audit 307 did *not* review the shared compress modules (it is rishon-specific). Audit 305 (milestone-2c) reviewed `compress/{provenance,evaluate,archive,round,baselines,report,robust,replay}.py` and `evaluate/evaluator.py` up to `48e5f7f`. `git diff --stat 48e5f7f HEAD -- src/su2plaq/compress src/su2plaq/evaluate src/su2plaq/encodings` shows only `replay.py`, `robust.py` and `round.py`, all from one commit, `1feb746` (audit 305 N2–N7 fixes, tester 431). I reviewed those hunks:
  - `program_changed` in `replay.problems`;
  - `robust_constants_sha256` as a cache key;
  - the `chmod` to `0666 & ~umask` in `_atomic_write_text`;
  - `round.check_program_sha`.

  All are correct. `spec.py`, `evaluate.py` and `baselines.py` did not change after `48e5f7f`. Otherwise I reviewed only the LSH use of the shared modules.
- **Freeze.** `git log 70ab721..HEAD -- src` (from the round-0 commit on) shows one commit, `2b7c68d`, which touches only `rishon/lean_cert.py`. No LSH or shared hashed file changed during the loop.
- **Own physics check** (`audit308_check.py`). I wrote a sparse full-register statevector simulator: a dictionary from basis index to amplitude. Gate matrices come from `qiskit.quantum_info.Operator`; the contraction is my own. It uses neither Aer nor the project engine. It runs the headline, rebuilt by the stock worker `_build_in_subprocess`, and the M7 reference circuit `circuits.lsh.build_step(α, β, 1, with_outer=True)` on all 433 physical codes of the full register. Neither circuit is reduced in any way. The pairs: the 3 spec pairs, the 2 generality pairs (seed 20261110), the 20 angle-set pairs (seed 20261107), and 4 out-of-range pairs $(-1.3,2.7)$, $(5,-4)$, $(\pi,\pi)$, $(0,\pi/2)$. Negative control: the headline built at $-\beta$. 15 s wall.
- **Own enumeration of the gauge-invariant subspace.** I enumerated all bit patterns of the 24-qubit register allowed by the LSH rules (inline script, command in §4.1). The rules: in-site codes with $N_p=\ell_{vp}+\ell_{pn}\le1$ and $N_n=\ell_{pn}+\ell_{nv}\le1$; out-site codes with $N_1,N_2\le1$; the Abelian Gauss law on the four inner links and the four virtual links.
- **Non-physical inputs** (`audit308_nonphys.py`): headline vs the M7 circuit with q14 flipped.
- **Recount** (`audit308_counts.py`). CX, $T_{\rm fixed}$ and $N_{\rm rot}$ via Qiskit `count_ops` of the project lowering. $T$ via `pygridsynth.gridsynth_gates` called directly. $\mathrm{depth}_{\rm CT}$ via the project's `synthesize`, and via two variants: the gridsynth letter $X$ as one `x` gate, and letters in written order. Done for the seed `r00-seed-005`, the headline and the two tied 68-CX entries, at the nominal pair and the 20 angle-set pairs.
- **Lean.** `cd lean && ../tools/run-capped lake env lean certs/lsh-best-step.lean` (`#print axioms`). I also compared the JSON literal inside the theorem file with the certificate file.
- **Stored circuit.** I loaded `results/lsh/m8-headline-step.qpy` and compared its gate list with the rebuilt headline, and loaded `m8-headline-step.qasm3` and counted its gates.
- **$U_E$ claim.** Exhaustive least squares over the 255 distinct non-constant parity characters on the 47 inner codes.

## 3. Checklist

| # | Item | Result | Where |
|---|---|---|---|
| C1 | Equations match METHODS term by term | OK | Target `encodings/lsh.py:188-196`: $U=U_B(\beta)U_E(\alpha)$, $U_E=\mathrm{diag}\,e^{-i\alpha H_E^{\rm inner}}$, $U_B=e^{-i\beta H_B}$ by `eigh`. Headline electric phases are `p(-0.75*alpha)` on each $f_c$: $H_E^{\rm inner}=\tfrac34\sum_cN_n(c)$ with $N_n=\ell_{pn}\oplus\ell_{nv}$ on valid sites. Walk rotations $\pm\beta/4$ give $2K$ on labels: $g(0)=-4$, $g(16)=g(48)=-1$, $g(1)=g(17)=g(49)=+2$, i.e. $2k$ for $k\in\{-2,-\tfrac12,+1\}$ (METHODS-lsh L13). |
| C2 | Time-evolution sign and ordering | OK | Electric layer first (`_compose`, order 1: `U @ UE(alpha)`). The headline at $-\beta$ is $1.878$ away from the target (my check), so the sign is resolved. |
| C3 | Basis and index conventions | OK | Code bit $i<12$ on `layout.data[i]`, bit $12+j$ on `layout.outer[j]` (`encodings/lsh.py:209-224`; G2 `test_lsh_m8_gate.py:225, 287-289`). q13, q14 = outer bits 1, 2 of site 0 = $(\ell_{2v}(0),\ell_{v1}(0))$. My enumeration with link direction $c\to c{+}1$ reproduces the production 433-code set exactly; the other direction does not. Qiskit little-endian is used consistently. |
| C4 | Truncation / cut-offs | OK, see N1 | $j_{\max}=\tfrac12$ (flux cap $\le1$ on physical links). G2 amplitude threshold $10^{-13}$ (N1). |
| C5 | Normalisation, phases | OK | One global phase per $433\times433$ matrix in G2 §3.2, in my check, and in Lean (`phase` field $k=1$, $m=(0,0)$). Sector-resolved errors in my check are equal ($\le7.4\times10^{-15}$ each) and cross-sector amplitudes are exactly 0. |
| C6 | Precision | OK | complex128 everywhere; Lean exact over Laurent polynomials; no GPU path. |
| C7 | Randomness | OK | Seeds 20261107 (angle set), 20261110 (generality pairs), 20261120 (G2 states), 20261104 (lowering), 0 (trial). Recorded in `m8-compressed.json::provenance.seeds` and in the test constants. |
| C8 | Tests exercise the production path | OK | G2 rebuilds through `compress.evaluate._build_in_subprocess` (`test_lsh_m8_gate.py:108-111`). The static scan is computed independently of `evaluator._outer_reads`. Aer is independent of the project engine. The target is shared with the evaluator (stated in 402 §4); my check adds the M7 circuit as an independent reference. |
| C9 | Provenance | OK, see N5 | `m8-compressed.json`: commit `b422e78`, `git_dirty: false`, command `python scripts/m8_results.py`. Headline certificate: `1e765f1`, `git_dirty: false`, `entry_id` and `program_file_sha256` bound. QPY gate list = rebuilt headline (215 gates, global phase 0). |
| C10 | No hard-coded expected numbers in source | OK, see N4 | `scripts/m8_results.py` has no literal counts. `vs_spinnet` raises if wrapped CX $\ne$ spin-network CX + transcoder CX. `rs_split.structure()` computes `sites_touched` from a formula (N4). |
| C11 | Hash freeze / no proposer commits in `src/`, `tests/` | OK | Freeze held from round 0 on (§2). Tester 444 check 27 and my `git log` agree. |

## 4. Answers to the four physics questions

### 4.1 Q1: same one-step unitary as the M7 reference on the physical subspace, and the role of q13/q14

**Result: yes.** The tolerance is $10^{-10}$; measured values are a few $10^{-15}$. Command: `taskset -c 0-8 tools/run-capped python audit308_check.py audit308_check.json`.

| comparison (433 physical codes, full 24-qubit register, one global phase) | max over 29 angle pairs |
|---|---|
| headline vs `enc.target` | $7.4\times10^{-15}$ |
| M7 circuit `build_step(…, with_outer=True)` vs `enc.target` | $9.4\times10^{-15}$ |
| headline vs M7 circuit | $1.1\times10^{-14}$ |
| leak (weight off the 433 codes), ancilla weight, change of the outer pattern | $0$, $0$, $0$ (exactly) |
| amplitude between different $(q_{13},q_{14})$ sectors | $0$ (exactly) |
| per-sector error (sectors of 190, 92, 92, 59 states) | $\le7.4\times10^{-15}$ each, same phase |
| negative control: headline built at $-\beta$ vs target at $+\beta$ | $1.878$ |

The 29 pairs include the 3 spec pairs, the 2 generality pairs of M8-G4, all 20 robust-key pairs and 4 out-of-range pairs. The largest out-of-range value is $8.7\times10^{-15}$ (headline vs target $\le6.3\times10^{-15}$). This supports the Lean "all angles" claim numerically.

**Is the 433-code set the whole subspace the gauge projector keeps?** Yes. Enumerating the LSH rules gives exactly 433 patterns, identical to `enc.physical_vectors().codes`. The rules: valid site codes with flux $\le1$ on physical links, the Abelian Gauss law on the inner links ($N_n(c)=N_p(c{+}1)$), and on the virtual links ($\ell_{nv}+\ell_{vp}=\ell_{2v}+\ell_{v1}$ at each corner). The SU(2) Gauss law is automatic in LSH variables (METHODS-lsh). The 433 codes contain 47 distinct data codes and 305 distinct outer patterns. So "states outside the inner code that the gauge projector keeps" do not exist beyond these 433 basis codes and their superpositions. A check of all 433 columns, with leak and outer-change bookkeeping, covers every physical state by linearity.

**Relation to q13/q14.** The headline reads $\ell_{2v}(0)$ (q13, 3 times) and $\ell_{v1}(0)$ (q14, 5 times), only as CX controls. It uses the site-0 virtual-link Gauss identity
$$\ell_{v1}(0)\oplus\ell_{2v}(0)=\ell_{nv}(0)\oplus\ell_{vp}(0)=e ,$$
which follows from $N_v^{\rm in}(0)=N_v^{\rm out}(0)$. I checked $\ell_{nv}(0)+\ell_{vp}(0)=\ell_{2v}(0)+\ell_{v1}(0)$ on all 433 codes: True. Consequence: the headline is correct **only** on the physical subspace, and it should be. With q14 flipped (non-physical inputs that break the site-0 virtual-link Gauss law), the headline and the M7 circuit differ on 327 of 433 inputs, by up to $2.0$ in 2-norm (`audit308_nonphys.py`). This is allowed: the target is defined only on the physical subspace (METHODS-lsh L12, spec "outer qubits may be used as controls only"), and the outer register is never changed.

**Does the amended G2 prove what prompts/402 says?** Yes (code `test_lsh_m8_gate.py:163-364`):
- **Static scan** (`outer_reads`, `:163-183`). This is the exact criterion $[g,Z_q]=0$ on each gate's own matrix (bit $p$ of the matrix index = gate qubit $p$, Qiskit convention). It rejects any gate that can change an outer bit. A composite gate that is diagonal in an outer qubit as a whole counts as a read, even if it writes and un-writes internally. That is the correct semantic notion: the gate cannot change the bit.
- **433-code check** (`aer_outer_read_check`, `:186-259`). It produces every column of $W$ restricted to the physical subspace. Every output amplitude above the threshold falls into exactly one class: ancilla $\neq0$, read bits changed, non-physical code (leak), or a matrix entry. The only premise is that untouched outer qubits factor out, and it is enforced (`:205`: every gate must act on data, ancilla or read qubits). The code handles all four sectors and their relative phases (one global phase), so it is exhaustive.
- **10-state full-register check** (`:262-336`). It removes even the factorisation premise for 10 random states that span all 433 codes and all 305 outer patterns. It is a sample, as 402 says. Its role is confirmation, not proof.
- **Gap?** Taken together, a circuit that only reads q13/q14 cannot act wrongly on any gauge-invariant state and still pass. The 433 columns cover the whole gauge-invariant subspace (my enumeration), and the per-column leak and outer bookkeeping catches outputs outside it. The only quantitative caveat is N1 (threshold bookkeeping), which does not change any conclusion.

### 4.2 Q2: counts of seed and headline, and the depth offset of 3

Command: `taskset -c 0-8 tools/run-capped python audit308_counts.py audit308_counts.json` (pygridsynth 1.2.0, $\varepsilon=10^{-6}$). All values agree exactly with the archive keys, `robust.json`, `m8-compressed.json` and the draft report.

| entry | CX | $T_{\rm fixed}$ | $N_{\rm rot}$ | $T(10^{-6})$ nominal | $\sum_{20}T$ | $\bar T$ | depth$_{\rm CT}$ nominal | $\sum_{20}$depth$_{\rm CT}$ | qubits |
|---|---|---|---|---|---|---|---|---|---|
| `r00-seed-005` (wrapped seed) | 71 | 48 | 17 | 1118 | 22480 | 1124.0 | 2276 | 46384 | 25 |
| `r05-F3-005` (headline) | 68 | 24 | 22 | 1396 | 28348 | 1417.4 | 3210 | 63378 | 24 |
| `r05-F5-005` | 68 | 24 | 22 | 1396 | 28348 | 1417.4 | 3220 | 63578 | 24 |
| `r04-F3-004` | 68 | 24 | 22 | 1396 | 28348 | 1417.4 | 3221 | 63598 | 24 |

The CX count is the same at all 21 pairs, so the skeleton is the same. By hand from the program: CX $=23$ frame forward $+\,22$ walk $+\,23$ frame back $=68$. $T_{\rm fixed}=6$ Margolus Toffolis $\times\,4=24$. $N_{\rm rot}=18$ walk rotations $+\,4$ electric phases $=22$. Traceability: commit `b422e78` (clean), `python scripts/m8_results.py`; round commits listed in Report 8 §0.

**Depth offset (tester 445 O4), explained.** The project's `synthesize` (`metrics/cliffordt.py:112-113`) replaces the pygridsynth letter $X$ by $H\,S\,S\,H$: 4 layers instead of 1, so $+3$ depth per $X$ on the critical path. Tester 445 used one `x` gate. This convention is documented in METHODS §7 (line 71, "$X\to HSSH$", already flagged by audit 004 N6). Counting $X$ as one gate I get exactly the tester's numbers: 3207 (nominal) and 62910 (20-pair sum). The written-order variant gives the same depths.

The offset is **not constant**. For the headline it is $+3$ at the nominal pair (one $X$ on the critical path) but $+468$ over the 20-pair sum, $+23.4$ per pair on average. For the wrapped seed it is $+33$ at nominal (2276 vs 2243; 14 $X$ letters in its words). The ordering of the three tied entries is the same under both conventions: $62910<63110<63130$ vs $63378<63578<63598$. So the headline choice does not depend on the convention. Tester 445's phrase "a constant offset of about 3 per circuit" holds for the nominal headline only (N3).

### 4.3 Q3: headline selection and stop-rule credit

- **Ranking** (`robust.json`, `m8-compressed.json::extra.ranking`). The three 68-CX entries tie exactly on $(\mathrm{CX},\sum T,\rho,\text{qubits})=(68,28348,0,24)$, with equal nominal $T=1396$, $N_{\rm rot}=22$ and $T_{\rm fixed}=24$. The fourth key component (depth sum) decides: 63378 (`r05-F3-005`) < 63578 (`r05-F5-005`) < 63598 (`r04-F3-004`). So the robust key is applied correctly, and the headline equals the archive best by archive key, since nominal depth $3210<3220<3221$. The decisive depth difference is 0.35 % of the sum, below the 0.6 % synthesis-word noise of L14. Report 8 §5 says so.
- **Stop rule** (`lsh/loop.py:161-176` against `prompts/401` §1.6). The code matches: lexicographic on $(\mathrm{CX},\sum T,\rho,\text{qubits})$; and with CX, $N_{\rm rot}$ and $T_{\rm fixed}$ all equal, a $\sum T$ change $\le20N_{\rm rot}$ is a tie decided by $(\rho,\text{qubits})$. Applied to `stop.json`:
  - Round 2: `r02-F1-002` has $T_{\rm fixed}$ 40 vs 48, so the structures differ and the comparison is lexicographic; $22320<22480$, so it improves.
  - Round 3: $70<71$, improves. Round 4: $68<70$, improves.
  - Round 5: `r05-F3-005` vs `r04-F3-004` has the same structure, $|\Delta\sum T|=0$ and equal $(\rho,\text{qubits})$, so it does not improve.
  - Round 6: unchanged.
  - Result: streak 2, sessions 20, reason `max_sessions`.

  The credit to round 4 is consistent: the last improving record is `r04-F3-004`, and round 5 only changed the headline id by the depth tie-break, which the stop rule ignores by design.

### 4.4 Q4: Lean theorem `lsh_best`

- My run of `lake env lean certs/lsh-best-step.lean` prints: `'lsh_best' depends on axioms: [propext, Classical.choice, Quot.sound, lsh_best._native.native_decide.ax_1_1]`. These are the three standard axioms plus exactly one `native_decide` axiom.
- The `certJson` literal, parsed, is identical to `results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json`. Both sha256 values match `m8-compressed.json::extra.lean`: certificate `b05ef21d…`, theorem file `dae606e5…`. The first line names `r05-F3-005` and program sha256 `5b00e6e7…`, which equals the file on disk.
- **What it states** (`Check.lean:16-90`). The 433 states and the target are pinned by SHA-256 to the M7 exact route-B data (`Pins.lean`), with base $(d_\alpha,d_\beta)=(4,8)$, a multiple of the target base $(4,4)$. For every state $k$, the exact Laurent-polynomial replay of the 215 gates on the 24-qubit register equals $c\sum_{k'}V_{k'k}\psi_{k'}$, with one phase $c$ (here $c=1$). Equality of full vectors excludes leak. States with ancilla support are refused.
- So the theorem states exactly what the certificate claims: for every $(\alpha,\beta)$, the gate family of the program, read at the nominal pair, is the first-order step on the physical subspace. The outer reads are inside the replayed register and need no extra argument. The trust root is the Lean compiler plus the checker source (native-certified, not kernel-checked), as the report says.

## 5. Report 8 draft (`docs/report-8-lsh-compression.md`): items (a)–(g) and further corrections

- **(a) Three-way tie at 68 CX: confirmed.** `r04-F3-004`, `r05-F3-005` and `r05-F5-005` are equal on (CX 68, $\sum T$ 28348, $\rho$ 0, qubits 24) and also on nominal $T$ 1396, $N_{\rm rot}$ 22 and $T_{\rm fixed}$ 24. Depth sums: 63598, 63378 and 63578. Refinement: add that the order is the same under the $X$-as-one-gate depth convention ($62910<63110<63130$, this audit), so the choice is not a convention artefact, even though it is below synthesis noise.
- **(b) Aer full-state checks from round 1: confirmed.** `r01-F3-001` reads q13 (6 CX controls, tester 438 check 11). Tester 438 check 10 ran 12 seeded full 24-qubit states (seed 20261119), max error $2.5\times10^{-15}$. Report 8 §3.6 row 1 and METHODS-lsh L12 already say this. Fix any sentence that says the full-state checks began in round 3.
- **(c) Pareto wording: confirmed, with the cause.** `scripts/m8_results.py:178-190` sorts ties by `id`, so `r04-F3-004` is kept and the headline is not listed. Line 270 then says "the first row is the headline". Minimal fix: break ties in `pareto_front` by robust key (the ranking order), or list all tied entries. Alternatively change the sentence to "the first row ties with the headline". Report 8 §3.3 and §5 already describe this correctly.
- **(d) Depth offset of 3: explained in §4.2.** It is the documented $X\to HSSH$ convention (METHODS §7). It is $+3$ at the nominal pair for the headline only, $+468$ over the 20-pair sum, and $+33$ for the seed. If Report 8 mentions tester 445 O4, give these numbers and drop "constant".
- **(e) F3 as run is the ideation's family 4: confirmed and refined.**
  - The ideation's family 4 ("three-product cleaning with free class bit", `compress/ideation/lsh.md:83-96`) folds $\ell_{nv}(1..3)$ into site 0, uses three Toffolis on sites 1–3, collapses, and names the Margolus Toffoli as the fix for the `rccx` phases. That is exactly the F3 frame (`r01-F3-001` SUMMARY). The F4 family's own first program `r01-F4-001` builds the same frame.
  - F3 reaches family 3's *goal* (fewest ANDs: 3 per side, the ideation's lower bound "cleaning $\ge3$ products"), but not by family 3's *method*: no SAT or XOR-AND search is reported.
  - Suggested wording: "F3 as run built the ideation's family-4 frame (as did F4 in rounds 1–2), which meets family 3's AND-count goal."
- **(f) D1–D13 "default, not reviewed by Digonto": confirmed.**
  - STATUS Decisions 2026-11-16 item (4) says the 401 D1–D13 are stated as defaults. The 2026-11-17 acceptance covers only 009 and 010.
  - Refinement: D11 is no longer a pure default. Digonto chose "Planner amends M8-G2" on 2026-11-20, and `prompts/402` amends D11. The 402 §11 points are planner choices not reviewed by Digonto and should be listed as such: (1) the exhaustive 433-code check added beyond the approved full-register run; (2) diagonal-in-outer counts as a read; (3) outer-reading circuits with ancillas go back to the planner.
- **(g) G2 placeholder: confirmed.** Insert the `prompts/402` §7 headline table, which tester 446 reproduced to the printed digits:

| pair | §3.2 error | §3.3 error | §3.3 outer-pattern probability change | weights |
|---|---|---|---|---|
| $(0.37,0.61)$ | $2.98\times10^{-15}$ | $1.80\times10^{-15}$ | $7.8\times10^{-17}$ | 0 |
| $(0.91,0.23)$ | $2.59\times10^{-15}$ | $1.46\times10^{-15}$ | $6.1\times10^{-17}$ | 0 |
| $(1.70,1.00)$ | $3.10\times10^{-15}$ | $2.20\times10^{-15}$ | $8.0\times10^{-17}$ | 0 |

  Add one line for the mutants (17 circuits, all with the expected pass or fail, tester 446). Also replace: the first bullet of §5 ("Expected conflict with locked test M8-G2"); the §3.6 sentence "because the 47-code check does not apply to them" (now: "checked on all 433 physical codes on data + read outer qubits, and on 10 seeded full-register states, `prompts/402`"); and the D11 bullet.
- **Further corrections, physics and numbers** (all non-blocking):
  1. §3.3, "within 22 of the nominal $T$ … inside the noise band of L14". The L14 band is defined for $\sum T$ differences between two records at fixed structure, not for mean against nominal. Better: "$\bar T$ differs from the nominal $T$ by 21.4 T (1.5 %)".
  2. §3.0 and §4 item 6, "no 67-CX version exists" inside the walk space. Honest as written with the scope list. Add the remaining model assumptions to the scope list: single pivot; toggles only from the 7 single-wire generators; the target $g$ on the 37 labels fixed, i.e. no sign freedom from changed frame phases; the 46-CX frame fixed. The evidence (`x3.c` header, `X21_*.txt`: `found=0`, `mismatches=0`; `L22_0.txt` re-finds the 22-toggle walk) supports exactly this statement. So the scope statement is honest: it claims completeness only "for this model".
  3. §4 item 7, $U_E$ needs 4 rotations: independently confirmed. With 1, 2 or 3 characters plus a constant, the minimum least-squares residual on the 47 inner codes is $5.79$, $4.24$ and $3.00$. With the four $\chi_{\ell_{pn}\oplus\ell_{nv}}(c)$ it is $5.9\times10^{-15}$ (inline script, this audit). The 255 distinct non-constant characters agree with the proposer's count.
  4. §3.5 item 3, "$\ell_{v1}(0)=\ell_{2v}(0)\oplus e$": it is the site-0 virtual-link Gauss law; confirmed on all 433 codes (§4.1). Suggest adding that the circuit is therefore correct only on Gauss-law states, which is all the spec requires (§4.1, non-physical inputs differ by up to 2.0).
  5. §3.8, "touches 6 sites / 18 qubits": `rs_split.structure()` sets these from a formula, `2 + 2*len(RS_CORNERS)` (N4), not from the operator. Say "by construction".
  6. No other number errors: every number I spot-checked agrees with its source. That covers §3.1 rows, §3.2, §3.3 front, §3.4 round table and sessions 6/11/13/16/19/20, §3.5 counts, §3.7, the L12 means 3168.9 and 2319.2, and the percentages +26.1 %, +41.0 %, +61.2 %, −4.2 %.

## 6. Notes (none blocking)

- **N1 — G2 amplitude threshold bookkeeping (inherited, no action needed now).**
  - Where: `test_lsh_m8_gate.py:240` (and the old helper `:146`).
  - Amplitudes $\le10^{-13}$ are dropped before the matrix is formed. With at most 433 entries per column this can hide up to $\lVert\Delta M\rVert_2\le\lVert\Delta M\rVert_F\le433\times10^{-13}=4.3\times10^{-11}$, so the operator-norm statement is "$\le10^{-10}+4.3\times10^{-11}$".
  - The per-column leak weight $\le10^{-20}$ bounds the leak block only as $\lVert(1-P)WP\rVert_2\le\sqrt{433\times10^{-20}}=2.1\times10^{-9}$. This is the per-state convention of `prompts/004`, as in the old 47-code path ($6.9\times10^{-10}$).
  - Measured: errors $\le3.1\times10^{-15}$, weights exactly 0, so no verdict depends on it. I do not consider the tolerance wrong. If a future circuit lands near $10^{-10}$, compute the leak block in operator norm.
- **N2 — Pareto tie order** (`scripts/m8_results.py:178-190, 270`). See (c).
- **N3 — Depth offset wording** (tester 445 O4). The offset is not constant (§4.2). The convention is documented in METHODS §7.
- **N4 — `rs_split.structure()`** (`src/su2plaq/lsh/rs_split.py:77-79`). `sites_touched`, `qubits_touched` and the `_ours` values are formulas or constants, not computed from $H_{\rm RS}$. The values (6/18 vs 4/12) are right by construction: the plaquette passes through both split sites at corners 1 and 3. Compute them from the operator's support, or label them "by construction".
- **N5 — Certificate no-rewrite rule can keep stale provenance** (`src/su2plaq/lsh/lean_export.py:145, 465-511`). `VOLATILE_PROVENANCE` includes `git_commit` and `git_dirty`. A fresh clean export that differs from an existing certificate only in those fields leaves the old values on disk, e.g. `git_dirty: true`. The headline certificate is unaffected: its new binding fields forced a rewrite, and it records `1e765f1`, clean. Three per-round certificates record `git_dirty: true` (`0320e89c1271`, `43bdeb21d084`, `96f37437a2e6`); Report 8 §5 already mentions this. Suggested fix: when the stored file has `git_dirty: true` and the fresh one `false`, rewrite.
- **N6 — Planner additions in 402 §11 should be named in Report 8** as not reviewed by Digonto. See (f).
- **N7 — Shared modules.** Reviewed only where changed after audit 305 (`1feb746`). No issue found. This closes the brief's question: audit 307 did not review them; audit 305 did, up to `48e5f7f`.
- **N8 — Outer-reading headline depends on the Gauss law** (§4.1). This is correct and allowed. Report 8 should say it in one sentence, so that nobody runs the circuit on unprojected states expecting the M7 behaviour.
- **N9 — Byproducts.** I ran no pytest and no project result script; my runs wrote only into the session scratchpad. `git status --short` is empty at the end. No `results/spinnet/certs/*.json` was rewritten by this audit.

## 7. Problems and assumptions

- My simulator uses Qiskit's `Operator` for the gate matrices: the definitions of standard gates and of the program's macros. The contraction, phase fit and bookkeeping are my own. The target is the shared `enc.target`, cross-checked against the M7 circuit, which audit 303 validated against route B.
- I did not re-run the locked G2 test (tester 446 ran it: 1 passed, 114 s, 1.64 GiB). I reviewed its code and reproduced its conclusion with an independent engine.
- I did not re-run the C search of the 21-toggle evidence. I judged its scope from the source header, the logs and tester 444's rerun.

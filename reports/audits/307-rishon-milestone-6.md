# Audit 307 — rishon milestone 6 (compression loop, Lean three-angle checker, Report 6 draft)

- Date: 2026-11-19
- Auditor: Claude Opus 5.5 (auditor role)
- Commit range: `milestone-5d..16b0a93` (HEAD at start `16b0a93`; at the end `7afc110`, the three commits in between, `ec38370`, `58e4574`, `7afc110`, are STATUS and LSH only, no rishon file)
- Plan in force: `prompts/205` on `prompts/204` (step C6) on `prompts/203` (row 6.8)
- Related: reports/tests/427 (replay), 432 (round 5), 433 (round 6), 434 (Lean checker), 435 (gate full, PASS); reports/audits/304 (milestone-5d)
- My own check: script `audit307_check.py` + output `audit307_check.json` in the session scratchpad (`/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/`, script sha256 prefix `5625fa2b44acaca8`; not committed, the caller asked for the report only; the method is written out in Appendix A so it can be rerun). Run with `taskset -c 0-5 tools/run-capped python audit307_check.py out.json`, PYTHONPATH=src, conda env `coding`, threads 1. Deterministic (no random numbers).

## Verdict: PASS WITH NOTES

No blocking issue. The evaluator physics is sound, no proposer touched `src/`, the result tables are traceable to a clean commit, the prune-cap change altered exactly the verdicts the plan predicted, the Lean trust base is sound, and the headline `r06-F3-006` is exact at two angle pairs that no one used before, checked with my own simulator and my own Jordan–Wigner target. Twelve notes, most of them wording corrections for Report 6 and METHODS-rishon.

## 1. What was asked

The milestone-6 gate audit (prompts/203 row 6.8, prompts/204 C6): (1) evaluator physics of `rishon.compress.evaluate`; (2) no proposer commits in `src/su2plaq`; (3) provenance of every table number in `results/rishon/m6-compressed.json` and `m6-before-after.md`; (4) prune-cap bookkeeping (1 % to 10 %); (5) the Lean three-angle checker and its trust base; (6) re-verify the headline at unused angles and the three-layer composition; (7) the round-5/6 tricks: any assumption that holds only on sampled states?; (8) spot-check the Report 6 draft.

## 2. What I did

- Oriented with graphify (`graphify query` on the rishon evaluator and on lean_cert), then read: `docs/METHODS-rishon.md` R1–R6 and R10–R16; prompts/203 §3.2, row 6.8; prompts/204 §6.2–§6.4, C4–C6; reports/tests/434, 435.
- Read the code: `src/su2plaq/rishon/compress/evaluate.py` (all), `src/su2plaq/rishon/verify.py:1-210`, the shared cascade `src/su2plaq/evaluate/evaluator.py:97-104, 505-600`, `src/su2plaq/encodings/rishon.py:42-61, 186-260`, `src/su2plaq/rishon/lean_cert.py:108-335, 435-482, 805-858`, `lean/Su2PlaqCert/Rishon/{Check3,Gates3,Pins3}.lean` (all), `scripts/m6_results.py:260-345`, `src/su2plaq/rishon/compress/three_layer.py:30-70`.
- `git log milestone-5d..HEAD -- src/su2plaq` (17 commits) and the file lists of the two program commits (`bef04cd`, `7cfe759`).
- Read `replay-204.json`, the 23 archive entries, the 7 round files, `robust.json`, `three-layer.json`, `m6-compressed.json`, `m6-before-after.md`; current `rishon.compress.code_hash()`.
- Independent physics check (Appendix A): headline unit and three-layer step at $(\alpha,\beta)=(1.13,0.47)$ and $(2.71,0.083)$, $\eta=0.71$, with a negative control.

## 3. Checklist

| # | Item | Result | Where |
|---|---|---|---|
| C1 | Equations in code match METHODS-rishon term by term | OK | targets: `lean_cert.py:205-232` ($U_B$, $\cos\kappa\beta-1$, $i\sin\kappa\beta$), `:235-249` ($U_E$, exponent $-3\#Q$ at base $\alpha/4$), `:252-272` ($U_D$, $\cos2\eta$, $-i\sin2\eta$), `:297-319` (step orders 1 and 2); my JW build agrees (Appendix A) |
| C2 | Time-evolution sign and ordering | OK | unit $U_BU_E$ (electric first), three-layer = det layer in front, $[U_D,U_E]=0$ (`circuits/rishon.py:216`); my check uses $e^{-i\beta H_B}e^{-i\eta H_D}e^{-i\alpha H_E}$ and $e^{-iHt}$ sign; $\beta\to-\beta$ control fails (error 1.6 and 0.90) |
| C3 | Basis/index conventions | OK | link qubits $(L_1,L_2,R_1,R_2)=(4\ell..4\ell+3)$, little-endian; sorted-code index $=\sum_\ell s_\ell6^\ell$ used by `_ud_entries` (`lean_cert.py:262`) is consistent with Lean `innerCodes` (`Check3.lean:42-49`) |
| C4 | Truncations / cut-offs consistent with plan | OK | prune cap $0.1\,$`tol_err` (`verify.py:20, 161-166`); 62-qubit engine limit; `max_den` 64 |
| C5 | Normalisation, phases | OK | one global phase fitted; headline phase $1$ ($\arg=-8\times10^{-17}$ in my check) |
| C6 | Precision | OK | float64/complex128 everywhere; Lean exact over $K=\mathbb Q(i,\sqrt2,\sqrt3)$; no GPU path |
| C7 | Randomness | OK | seeds 20261104, 20261107, 20261110, 12345, 0 recorded in `m6-compressed.json::provenance.seeds` |
| C8 | Tests exercise the production path | OK | tester 434 ran mutants through the raw compiled checker; tester 435 recount from qpy; my check uses the archived program + production `Builder`, but my own simulator and target |
| C9 | Provenance | OK with note | `m6-compressed.json`: `fcd61dd`, `git_dirty: false`, command recorded; round files dirty (N4) |
| A1 | Evaluator physics (inner-block soundness, Gauss sample, prune cap, outer rule, ancilla rule, three pairs) | OK | Section 4.1 |
| A2 | No proposer commits in `src/su2plaq` | OK | Section 4.2 |
| A3 | Provenance of table numbers | OK with notes | Section 4.3 |
| A4 | Prune-cap bookkeeping | OK | Section 4.4 |
| A5 | Lean three-angle checker trust base | OK with notes | Section 4.5 |
| A6 | Headline physics at unused angles; three-layer composition | OK | Section 4.6 |
| A7 | Round-5/6 tricks | OK | Section 4.7 |
| A8 | Report 6 draft | corrections listed | Section 5 |

## 4. Findings per scope item

### 4.1 Evaluator physics (`rishon.compress.evaluate` → `rishon.verify.verify`)

- **Inner-block soundness.** `verdict` (`evaluate.py:67-80`) calls `RV.verify` with the spec's kind, angles and order and the oracle target; `verify` (`verify.py:140-209`) first rejects any outer read (`classify_outer_gates`, `evaluator.py:97-103`: any diagonal gate on an outer qubit is a read, any non-diagonal one raises `OuterWriteError` → `writes_outer`), then runs the shared `evaluate` on the inner view (1296 codes, outer bits 0). For an outer-blind circuit $U=U_{\rm in}\otimes\mathbb 1_{\rm outer}$ and any physical $\Psi=\sum_o|o\rangle\otimes\psi^o$, the outputs for different $o$ are orthogonal, so
$$\|(U-e^{i\varphi}V_{\rm in}\otimes\mathbb 1)\Psi\|\le\|M-e^{i\varphi}V_{\rm in}\|_2+\|X\|_2+d$$
  (METHODS-rishon R6), and the code reports exactly this sum as `op_norm_error` (`evaluator.py:522`). OK.
- **Ancilla rule.** Ancilla weight and weight on invalid codes both go into $\|X\|_2$ (`leak_amplitude`, `evaluator.py:515-521`); any of it above `tol_err` rejects (`:569`). OK.
- **Prune cap.** A shared `pruning_bound` (cap $10^{-12}$) is re-judged with cap $10^{-11}$ by the same cascade (`verify.py:125-137`), written as `not (x <= bound)` so NaN/inf are rejected. `certified` is computed before the cascade (`evaluator.py:566`), so a re-judged verdict carries a meaningful flag. `prune_fraction` below the shared value raises (`verify.py:162-164`). OK. The re-judge omits the shared last step `span_leak` (N9).
- **Gauss sample.** 17 closed + 256 seeded states (seed 20261104), outputs assembled from the code block (`verify.py:95-113`); block exactness already implies $\|G^a_cU\Psi\|\le2\,$`op_norm_error`, so the sample is a cross-check, as METHODS states. OK.
- **Three-angle validity.** Skeleton identity and verdicts at nominal plus two alternate pairs are in the shared `evaluate_program`; the archive entries carry `verdict_nominal`, two `verdicts_alt` and `skeleton_equal`. OK.
- `to_verdict` now gives `total_error = inf` on early verdicts (carry-over from report 414 fixed, `evaluate.py:54`). OK.

### 4.2 No proposer commits in `src/su2plaq`

`git log milestone-5d..HEAD -- src/su2plaq`: 17 commits, all builder/coordinator steps with tester reports in their messages (B1–B7, C1, C4, M11 11.0–11.7, audit-304/305 fixes). The two proposer-program commits `bef04cd` (round 5) and `7cfe759` (round 6) touch only `compress/programs/rishon/F*/00[56]-*.py`. The hashed evaluator files did not change after the replay: `rishon.compress.code_hash()` today `5f5decfa…ef23` equals `replay-204.json::evaluator_sha256`, all seven round files and all 23 archive entries. OK.

### 4.3 Provenance of table numbers

- `results/rishon/m6-compressed.json`: `git_commit fcd61dd`, `git_dirty false`, `command "python scripts/m6_results.py"`, `quick false`, seeds, versions, wall 93.2 s. `m6-before-after.md` is rendered by the same run (header line). The script reads every number from the archive, round files, `robust.json`, `three-layer.json` and the M5/M5x row files, and recomputes the headline metrics from the rebuilt program after a sha256 check (`scripts/m6_results.py:322-345`); grep finds no hard-coded result number in it or in `three_layer.py`. Tester 435 recomputed 74 of 74 numbers. OK.
- Upstream inputs (round files, replay record, archive entries) were written with `git_dirty: true` (N4). They are bound to their code by the evaluator hash and to their programs by program sha256, so the numbers are traceable; the dirty flag is informational.
- The outer rows cite their own commits (`59e863d`, `6fea036`) and certified files. OK.

### 4.4 Prune-cap bookkeeping (old 1 % versus new 10 %)

`replay-204.json` (19 entries, rounds 0–4, `prune_fraction 0.1`): exactly three verdicts changed, all round-0 seeds:

| entry | old (cap $10^{-12}$) | new (cap $10^{-11}$) | `dropped_total` |
|---|---|---|---|
| `r00-seed-001` (rccx) | `pruning_bound` | valid $(6874,17694,31954,58)$ | $2.91\times10^{-12}$ |
| `r00-seed-002` (mcx) | `pruning_bound` | valid $(7360,18180,32428,58)$ | $2.69\times10^{-12}$ |
| `r00-seed-qiskit_l3` | `pruning_bound` | `eval_budget` (time limit, prompts/205) | $3.79\times10^{-12}$ |

The other 16 keep identical keys (`key_equal` true for all 16), `lost: []`, best before = after = `r04-F1-004`. `n_pruning_bound` is 0 in all seven round files. This matches prompts/204 §6.2 as corrected by research 204. OK.

### 4.5 Lean three-angle checker (`lean/Su2PlaqCert/Rishon/*.lean`, `rishon/lean_cert.py`)

- **What `check` accepts** (`Check3.lean:90-129`): structural validation (≤ 62 qubits, 16 data, 0 outer, gate arity/range/even `rz` exponent), the certificate's `states` must equal the checker's own `innerCodes` (`:95`), the target must hash to the pinned SHA-256 for its kind/order after exact division by the base ratio (`:74-86`), then for every code the exact sparse output must equal phase × target column. Because the expected vector has keys only on inner codes with ancilla bits 0, "ancillas clean" and "no weight outside the code space" are part of the same equality. Equality is structural on canonical forms, so it can only be too strict (false reject), never too loose. The phase $k\,z^{\mathbf m}$ is free but must satisfy the exact identity for every code; with unitary gate semantics this forces $|k|=1$. **Sound.**
- **Gate semantics** (`Gates3.lean:54-89`): reuse the laptop's matrices; `rz` uses half exponents with an evenness check. OK.
- **"For all angles" argument.** A Laurent-polynomial identity in $(z_\alpha,z_\beta,z_\gamma)$ holds under *every* substitution, in particular $z_\gamma=e^{i\sqrt2\beta/d_\gamma}$; algebraic independence (from $\sqrt2\notin\mathbb Q$) is not needed for soundness, only for the converse (that the checker is not too strict). METHODS-rishon R12 and Report 6 §3.8 state the implication the wrong way round (N2). Not a soundness problem.
- **Pinned targets built from floats.** `_ub_entries` (`lean_cert.py:205-232`) takes the float bright-pair vectors $u_p,v_p$ from `operators.bright_pairs()`, rounds to 13 digits and recognises each amplitude as an element of $K$ with denominator ≤ 48 (`_exact_amp`, `:169-175`); the only built-in guard is `_check_cross`, a comparison at **one** angle pair (nominal) to $10^{-12}$ (`:275-294`). The risk is a wrong recognised coefficient pinned as truth. My judgement: the evidence suffices. (a) Tester 434 §2a compared all five pinned targets against an independent dense `expm` at 5 random angle triples: max entry difference $\le2.0\times10^{-15}$. If the pinned matrix differed from the true one as a function, the difference would be a finite sum $\sum_nc_ne^{i\omega_n\beta}$ (frequencies in $\mathbb Z+\sqrt2\,\mathbb Z$) with coefficients $c_n\in K$ of small height. Such a sum vanishes only at isolated points, and its non-zero coefficients are far above $10^{-15}$, so agreement to $2\times10^{-15}$ at 5 random points rules it out. (b) My check adds a fully independent path for the `step` order-1 pin. Lean proves circuit = pinned target as an identity, and I found circuit = my own JW target ($e^{-i\beta H_B}e^{-i\alpha H_E}$ from fermion operators built from scratch, not from `RishonLink`) at two new pairs to $1.1\times10^{-14}$. Hence pinned target = independent target at those pairs too. The tie between pin and Hamiltonian remains numerical, not a Lean theorem (Report 6 already says so). One wording fix: the pins are not "generated from closed forms" (N1).
- **§6.4 angle-fit rule** (`lean_cert.py:814-857`): the program is rebuilt at the 20 angle-set pairs, the skeleton must be constant, and the nominal fit must reproduce each rotation angle to $10^{-9}$; `certify_circuit` then requires the exporter's fits to equal the confirmed fit. Correct for circuits whose rotation gates the exporter emits unchanged (`p`, `rz`, as in the headline; tester 434 §6 confirmed the headline's exponents independently at 9 pairs). For lowered controlled rotations the comparison is on the unlowered gates while the exporter re-recognises the lowered angles (N6). `recognise_angle` deliberately does not recognise $\alpha$+$\beta$ combinations without a $\sqrt2\beta$ part (N7).
- Tester 434's mutation campaign (1 994 mutants, 0 wrong accepts) and tamper control on the theorem file are adequate.

### 4.6 Headline `r06-F3-006` re-verified at unused angles (Appendix A)

| circuit | $(\alpha,\beta[,\eta])$ | $\|M-e^{i\varphi}V\|_2$ | max weight leaving the code space / ancillas | outer qubits touched | phase $\varphi$ |
|---|---|---|---|---|---|
| unit $U_BU_E$ | (1.13, 0.47) | $1.11\times10^{-14}$ | 0 | none | $-8\times10^{-17}$ |
| three-layer $U_BU_DU_E$ (`prepend_det_layer`) | (1.13, 0.47, 0.71) | $1.21\times10^{-14}$ | 0 | none | $-1\times10^{-16}$ |
| unit | (2.71, 0.083) | $1.03\times10^{-14}$ | 0 | none | $4\times10^{-16}$ |
| three-layer | (2.71, 0.083, 0.71) | $1.20\times10^{-14}$ | 0 | none | $3\times10^{-16}$ |
| negative control: target with $\beta\to-\beta$ | (1.13, 0.47) / (2.71, 0.083) | 1.62 / 0.905 | 0 | – | – |

Tolerance $10^{-10}$; all 1296 codes; my simulator dropped at most $8.7\times10^{-16}$ (2-norm per column). Sanity of my target: $H_B$, $H_E$, $H_D$ leave the 1296-code space invariant exactly (0.0); $H_E$ diagonal with values $\{0,\tfrac34,\tfrac32,\tfrac94,3\}$; extreme $H_B$ eigenvalues $\pm5.656854249492$ $=\pm4\sqrt2$ (METHODS-rishon R4). The circuit has 52 qubits, touches 0–15 and 48–51 only, 406 instructions. Inner span = full code space (R3), so exactness on all codes is exactness on all 38 432 physical states.

**Three-layer composition (R16).** The argument is correct. If circuit 1 maps each code $c$ to $k_1\sum_{c'}(V_1)_{c'c}|c'\rangle$ with clean ancillas, and circuit 2 does the same with $V_2$, then by linearity the sequence maps $c$ to $k_1k_2\sum(V_2V_1)_{c'c}|c'\rangle$. With $V_1=U_D(\eta)$ (the det layer runs first) and $V_2=U_BU_E$ this gives $U_BU_EU_D=U_BU_DU_E$, because $U_D$ acts only within the $\{A,B\}$ link types, where $\#Q$ is unchanged, so $[U_D,U_E]=0$. The two certificates use independent formal variables, so the result holds for all $(\alpha,\beta,\eta)$. Numerically confirmed above at $\eta=0.71$, a value outside the nominal/alternate set.

### 4.7 Round-5/6 tricks: assumptions that hold only on sampled states?

None found. The tricks (closed-sector skip of the c0 C2H with T/T$^\dagger$ phase restore; the `rccx(Z, !q3 -> q13)` restore with the closed-dark mark; CY gauge merge; RC3X) are judged by the inner-block verdict, which is **exhaustive** over the 1296 codes at three pairs, not sampled. Lean also checks them as an exact identity for all angles. My check confirms them at two further pairs with a second engine and target. They rely on two facts: (i) every inner component of a physical state is a valid code (R2/R3; invalid nibbles are don't-care), and (ii) relative phases of `rccx`/RC3X are absorbed into signs of rotation angles that stay linear in $(\alpha,\beta,\sqrt2\beta)$. Both hold for all physical states. The only sampled check, the Gauss residual on 273 states, is implied by block exactness. Tester 433's four surviving mirror-pair deletions are free cancelling $X\,X$ pairs on idle qubits (no physics content).

## 5. Report 6 draft (`docs/report-6-rishon-compression.md`): corrections (not edited)

| line | text now | correction | source |
|---|---|---|---|
| 3–4, 186, 191 | `[GATE: …]` placeholders | fill from reports/tests/435 (PASS; m6 33/33, m5 56, unit 1201, lock v22, theorem re-elaborated in 48 s with the same 4 axioms) and this audit (PASS WITH NOTES) | reports/tests/435 |
| 180 | "error $\le2.13\times10^{-13}$ … at the three angle pairs (largest `r02-F4-002`)" | $\le2.14\times10^{-13}$: `r02-F4-002` is $2.125\times10^{-13}$ at nominal but $2.142\times10^{-13}$ at $(1.70,1.00)$ | `compress/archive/rishon/entries/r02-F4-002.json::verdicts_alt[1]` |
| 175 | Walsh angles "$\tfrac12(\pm\beta\pm4\sqrt2\beta)$" | only two of the four sign combinations occur: $\pm\tfrac12(\beta+4\sqrt2\beta)$ | tester 434 §6 |
| 190 (and 37) | "Because $\sqrt2$ is irrational the identity … holds for **all real** $(\alpha,\beta)$" | the identity holds under every substitution; irrationality is only needed for the converse. Also qualify "all real $(\alpha,\beta)$": the certificate covers the angle-linear gate family with the nominal skeleton; that the *program* emits this family is confirmed at the 20 + 3 pairs (and 2 more in audit 307), not proved for every $(\alpha,\beta)$ | N2 |
| 195 | Pins "generated from closed forms by … `compute_pins`" | generated from the float bright-pair vectors of `operators.bright_pairs()`, each amplitude recognised as an element of $K$ (denominator ≤ 48) and checked against the float target at the nominal pair to $10^{-12}$; independently confirmed by tester 434 (5 random triples, $\le2\times10^{-15}$) and audit 307 (circuit vs own JW target at 2 new pairs, $\le1.2\times10^{-14}$). Same wording sits in `scripts/m6_results.py` `TRUST_ROOT` and hence in `m6-compressed.json::extra.lean.trust` | N1 |
| 232 | round-5/6 files dirty because "programs uncommitted at evaluation time" | wrong for rounds 5–6: the recorded HEADs `bef04cd`/`7cfe759` are the commits that added those programs, and `git_dirty` varies *within* a round (`r05-F1-005`, `r06-F1-006` false; `r05-F3-005`, `r06-F3-006` true), so the dirt came from files written during the run (the round's own outputs or parallel agents). Suggested: "dirty for files outside the hashed evaluator; each result is bound by evaluator hash `5f5decfa…` and program sha256" | archive entries `git_dirty`, `git_commit` |
| 82–84 vs `m6-before-after.md` | Report: "certified (composition)" | the md (and its NOTE line) says plain `certified` for the three-layer rows; make the md say "certified (composition of unit + det certificates, METHODS-rishon R16)" too | N10 |
| 143 | "22 of the 23 … angle-linear; exception `r01-F2-001`" | correct (`robust.json`); add that $\rho=1$ can also mean an $\alpha+\beta$ angle, which `recognise_angle` does not recognise by design, not only a non-linear angle | N7 |

Numbers spot-checked and correct: §3.0 ratios (46.8×, 31.8×, 24.8×, factor 740); §3.1 table rows against the md; verdicts at the alternates $1.39$/$1.36\times10^{-13}$; macro counts (130 cx, 26 rccx, 8 ch, 56 x, 60 h, 38 t, 38 tdg, 19 s, 19 sdg, 2 z, 6 rz, 4 p; $130+78+8=216$ CX; $76+104+16=196$ $T_{\rm fixed}$); three-layer errors $1.54/1.59/1.57\times10^{-13}$, Gauss $\le1.07\times10^{-15}$; headline `dropped_total` $1.21/1.26/1.22\times10^{-13}$, three-layer $1.38$–$1.44\times10^{-13}$; $82.5\times$ and $8.3\times$ below the caps; largest proposer `dropped_total` $1.96\times10^{-13}$ (`r02-F4-002`); `n_pruning_bound` 0 in rounds 0–6; replay table; round-best $T$ sequence and rotation counts 166, 12, 14, 14, 10, 10, 10; smallest nominal $T$ is the headline's 832 (next 840).

## 6. Notes (all NON-BLOCKING)

- **N1 — pin provenance wording.** `scripts/m6_results.py:53` (`TRUST_ROOT`) and Report 6 l.195 say the pins come from "closed forms". They come from lattice recognition of float eigenvectors (`lean_cert.py:169-175, 205-232`), guarded in code by a single-angle cross-check (`:275-294`). The evidence that they are right is the tester's and this audit's independent numerical checks (§4.5). Fix: wording only. Optional hardening: let `_check_cross` also compare at the two alternate pairs, and at one triple with an irrational $\beta$, so the code guard does not rest on one point.
- **N2 — direction of the "for all angles" argument.** METHODS-rishon R12 ("Soundness of the 'for all angles' reading: … algebraically independent … therefore implies") and Report 6 l.190. Correct statement: an identity in $K[z_\alpha^{\pm1},z_\beta^{\pm1},z_\gamma^{\pm1}]$ implies the identity at every substitution, in particular $z_\gamma=e^{i\sqrt2\beta/d_\gamma}$; the independence of $z_\beta,z_\gamma$ (from $\sqrt2\notin\mathbb Q$) makes the condition also necessary (the checker is complete for angle-linear circuits). Also state the scope: the certificate is about the gate family with the recorded exponents.
- **N3 — scope of "for all $(\alpha,\beta)$" for the program.** The certificate is about the exported gate family. That the program builds exactly this family at other angles is confirmed at the 20 angle-set pairs (`confirm_angle_fit`) plus the 3 evaluation pairs, not proved. It is adequate, but reports should say "the circuit family is certified for all angles; the program was confirmed to emit it at 23 pairs".
- **N4 — dirty upstream provenance.** Round files 0–6, `replay-204.json` and 19 of 23 archive entries have `git_dirty: true`. Mitigated by the evaluator hash and program sha256; the final tables are clean. Recommendation for later loops: compute the dirty flag over tracked files excluding the round's own output paths, or record `git status --porcelain` in the provenance so "dirty" can be judged.
- **N5 — `certify_circuit` without `angle_fit` certifies at the nominal pair only** (tester 434 N1). The circuit-valued seeds (general, rccx) are certified that way; their circuits come from `build_step`, whose angles are linear by construction, and the general-step theorem file was produced the same way. Acceptable; Report 6 l.194 already states the exemption.
- **N6 — §6.4 rule compares unlowered fits** (`lean_cert.py:846-851`: `rotation_fits(qc)` on the Qiskit gates) while the exporter emits exponents re-recognised on the *lowered* gate list (`_gate_records3`, `:449-480`). For `crz`/`crx`/`cp` lowered to half-angle `rz`, the two can in principle pick different aliases at the rational nominal pair ($61\alpha=37\beta$ exactly). Effect: a wrong alias would almost surely make Lean reject (false negative), and if accepted it is a true statement about the alias family, so a mislabel, never a wrong "exact" claim. Not exercised by the headline (only `p`, `rz`). Minimal fix: confirm the *emitted* per-op exponents directly, i.e. evaluate the certificate's $\mathbf m\cdot\theta$ against the lowered circuit's angles at each of the 20 pairs. Tester 434's `e2e_float` does this by hand.
- **N7 — `recognise_angle` ignores $\alpha+\beta$ combinations without $\sqrt2\beta$** (`lean_cert.py:108-147`, deliberate). A legitimate merge of an electric phase into a magnetic rotation (e.g. by `merge_adjacent_rotations`) would get $\rho=1$ and Lean `n_a`. This makes the rule incomplete, never unsound. Mention in Report 6 §3.4 and METHODS R12.
- **N8 — slow mutants.** Wrong certificates can run > 900 s (tester 434 N3). The outcome is `failed`, never `certified`. Fine.
- **N9 — `_rejudge` omits the shared `span_leak` step** (`verify.py:125-137`; shared order `evaluator.py:567-578`). Harmless here: on the inner view the span is the full code space (METHODS-rishon R3), so `span_leak` is 0. Add one line to `_rejudge` (`if not iv.total_error <= tol_err: return "span_leak", …`) or an assertion, so a future non-full view cannot skip it.
- **N10 — md Lean column for three-layer rows** says `certified`, not "certified (composition)" (`scripts/m6_results.py`, row rendering near `:183-185`). Wording.
- **N11 — Pins3 is not covered by any evaluator hash** (by design: Lean never decides validity). The certificate records `checker_sha256` (`6c3c62be…c24c7e`), which binds the pins through the binary. Fine; mention in METHODS R12 that the binding is through `checker_sha256`.
- **N12 — qubit-count conventions** (tester 435 O5): `UD.json`/`step.json` use 16/26 logical qubits, compress keys use 48/52/58. Report 6 §3.2 uses 48 for the det layer, consistent with the key; one sentence suffices.

## 7. Blocking issues

None.

## Appendix A — independent check (method, so it can be rerun)

- **Target.** 16 inner qubits, $2^{16}$-dimensional sparse matrices. $c_k=\big(\prod_{m<k}Z_m\big)\sigma^-_k$ with $\sigma^-=|0\rangle\langle1|$ (bit 1 = occupied) built directly as signed permutation matrices. Mode index $4\ell+\{0,1\}$ for $L_{1,2}$, $4\ell+\{2,3\}$ for $R_{1,2}$. $U^{(\ell)}_{ij}=c_{L,i}c^\dagger_{R,j}$, $(U^\dagger)_{ij}=(U_{ji})^\dagger$, $W=\sum_{abcd}U^{(b)}_{ab}U^{(r)}_{bc}(U^{(t)\dagger})_{cd}(U^{(l)\dagger})_{da}$, $H_B=-(W+W^\dagger)$; $H_E=\sum_{\ell\le3}\tfrac12\sum_a(L_a^2+R_a^2)$ with $L_a=\sum_{ij}(\sigma_a/2)_{ij}c^\dagger_{L,i}c_{L,j}$; $H_D=\sum_{\ell\le3}(\det U+\det U^\dagger)$ with $\det U=U_{11}U_{22}-U_{12}U_{21}$. Restricted to the 1296 sorted codes, then `scipy.linalg.expm`. No `su2plaq.rishon.operators`, no `RishonLink`.
- **Simulator.** numpy sparse vectors over (input column, 52-bit key); each instruction's matrix from `qiskit.quantum_info.Operator(instruction.operation)` (little-endian over its qargs), applied by local-index gather and `np.unique` merge; amplitudes $<10^{-15}$ dropped and tallied; circuit global phase applied at the end. No `su2plaq.evaluate.sparse_sim`.
- **Circuit.** `load_program("compress/programs/rishon/F3/006-closed-mark-in-restore.py").build(rishon_spec("step").with_angles(a, b)).circuit()`; three-layer via `su2plaq.circuits.rishon.prepend_det_layer(unit, 0.71)`.
- **Metric.** $M_{c'c}$ = output amplitude on code $c'$ (ancillas and bits ≥ 16 zero) for input code $c$; $\varphi=\arg\mathrm{tr}(V^\dagger M)$; error $\|M-e^{i\varphi}V\|_2$; leak = per-column weight on any other key. Wall 3.6–8.7 s per case on one core.

M3 done (milestone-3, Report 3, incl. 3.L3); laptop milestone-2 merged; M4 in progress: round 0 committed (best pairs9 CX 34); ideation committed (F1-F5); round 1 proposers F1, F2, F3, F5 running; round-0 tester (reports/tests/112) running; 4.L1/4.L2 Lean next.
- NOTE (coordinator, 2026-11-06T19:00 clock time): the HH:MM stamps on entries written after ~16:00 today were estimated, not read from the clock, and several are later than the real time; the git commit times are authoritative.
- 2026-11-06T14:25 merged laptop master 5111d69 (tag milestone-2, bundle laptop-milestone-2-20261106-1211) with --no-ff; no conflicts; our STATUS kept; LOCK.json regenerated with tools/lock.py (identical to the auto-merged one, LOCK OK); laptop acceptance-v7 fetched as tag laptop-acceptance-v7 (name clash with ours).
- 2026-11-06T14:45 tester full after merge FAIL 618/619 (reports/tests/108): M3-L3 now un-pended by laptop checker -> step 3.L3 builder attempt 1; acceptance-check needs a new acceptance tag after merge (do it together with m4 lock).
- 2026-11-06T15:20 planner M4 -> prompts/104, reports/research/102, tests/acceptance/m4 (17 tests); locked acceptance-v10 (acceptance-check PASS). Counters reset. Plan §9 decisions taken by default (Digonto may override): keep lakefile [[lean_exe]] append (listed in merge notes); final-best angle-linearity n_a not reject; no ~/.claude/agents/proposer.md edit, coordinator names the candidate command in every proposer prompt; flags5/flags6 included as seeds.
- 2026-11-06T16:30 step 3.L3 tester PASS (reports/tests/109): 640 passed; own checker su2plaq_cert_spinnet (laptop's pins twelve); 93/103 wrong-circuit probes rejected, rest correctly certified/n_a; pins match independent route-B target to 1.8e-15. Plan §10 diffs copied into merge notes.
- 2026-11-06T17:10 steps 4.0/4.1 builder attempt 1: S0, S7 PASS; S2 (and S5) blocked by locked-test vs laptop sandbox conflicts (programs import su2plaq.circuits.spinnet outside the import whitelist; WRITING_PROGRAM uses builtin open, rejected as contract before the audit guard). Per Digonto's stuck rule: planner fixing the m4 tests (erratum), then manual m4 re-lock + acceptance-lock.
- 2026-11-06T17:30 planner erratum E1 (prompts/104 §11): S2/S5 programs now proposer-style gate-list splices (no whitelist widening; S2 also asserts that importing su2plaq.circuits.spinnet is refused), writer via builder.pathlib. m4 re-locked by hand -> acceptance-v11 (only test_spinnet_compress.py hash changed; acceptance-check PASS). FOR DIGONTO REVIEW: this locked-test change was made under the stuck->planner rule without asking. Counters reset.
- 2026-11-06T18:20 steps 4.2/4.3 builder attempt 1: S1, S3, S4, S5 PASS; S6 FAIL by test conflict (asserts 8 negatives in the 433-state gauge; 8 is the inner-code count, a correct 433 gauge has 128). Planner asked for erratum E2 (stuck rule). Builder deviations noted: own angle-linear fit for qiskit_l3 seed; local copies of twelve-hardcoded baselines helpers; paulo15 report row text bug is laptop item §10.5.
- 2026-11-06T18:40 planner erratum E2 (prompts/104 §11): S6 now checks gauge per inner code (8 minus codes 8..15) and per state (128, re-derived from codes). m4 re-locked by hand -> acceptance-v12. FOR DIGONTO REVIEW (stuck->planner rule).
- 2026-11-06T19:55 4.2/4.3 tester PASS (reports/tests/111), committed 2fd5b3d. Round 0 real run 15 s / 0.83 GB on clean tree -> c9ad8d0: 7 valid seeds, keys as research 102 §3, global best spinnet_v2_pairs9 (34, 832, 1597, 19); general + pairs9 Lean certified. Proposer sessions used: 1 (ideation).
- 2026-11-06T20:45 ideation (proposer session 1): F1 dimer frame + 2 flags (est. ~35-36 CX, 10 rot), F2 single flag, F3 numerical don't-care, F4 dark re-encoding (qubits only), F5 T-lean. Round 1: F1, F2, F3, F5 (sessions 2-5); F4 not run in round 1 (its stated gain is qubit count only, last key component; budget 20 sessions). Proposer sessions used: 5/20. Rounds without improvement: 0.

# Desktop track S — spin network — branch `m3-spin-network` (clone `~/Projects/su2qc-spinnet`)

Coordinator: desktop session, started 2026-11-05 from `~/Projects/su2qc-desktop-package/START_HERE.md`. Numbers: prompts/reports 100–199. Cores 0–9, `pytest -n 10`. Env: `source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding`. Merge notes: `notes/merge-notes-spinnet.md`.

## Current milestone / step
M3 — plan `prompts/100-spinnet-m3-plan.md` (acceptance-v7, 24 m3 tests). Steps 3.0+3.1 PASS (reports/tests/100). Step 3.2 PASS (reports/tests/101). Steps 3.3–3.5 PASS (reports/tests/102). Steps 3.6, 3.7, 3.L1, 3.L2 PASS (reports/tests/103–105). M3 gate done: tester full (reports/tests/106), audit PASS WITH NOTES (reports/audits/100; N1 → prompts/101 erratum, N2, N4 fixed d82a472; N3 → merge notes), benchmark (reports/benchmarks/100), tag milestone-3 (526503a), Report 3 (docs/report-3-spinnet-general-circuit.md). 3.L3 PENDING on the laptop's checker. While waiting for milestone-2: wait-time plan `prompts/102-spinnet-m3-wait-lean-structure.md` (m3x tests, acceptance-v8): W1 K from 6j in Lean, W2 exact gate semantics of build_UB, W3 H_B eigenbasis/multiplicities on 433 states, W4 bridge. W0–W4 PASS (reports/tests/107). Docs done (METHODS §9.7–9.8, Report 3 §3.5 addendum). M3x complete; outgoing bundle refreshed. Remaining wait-time work: benchmarks/robustness only if useful; M4 waits for milestone-2.

## Pending notes
- Laptop-owned flaky unit test `tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers` fails when the short commit hash contains "c1" (merge notes).
- Tester data goes to `results/spinnet/tester/` (track-owned), not `results/tester/`.

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|

## Desktop log
- 2026-11-06: M3x W0–W4 PASS (reports/tests/107): 12 new kernel-checked theorems (standard axioms; no native_decide): K derived from Racah 6j + F-symbols equals the exported table; ub_exact_all_codes = Laurent identity in z=e^{iβ/4} ⇒ build_UB maps every valid code to e^{−iβK}|y⟩ for all β with clean ancillas; H_B eigenvectors on 433 states with multiplicities 16/96/16/177/16/96/16. Not in Lean: orthogonality/completeness ⇒ spectrum (numerical), route A↔B, Lean↔Qiskit gate-matrix tie (numerical, 2.2e-16), RCCX relative phases (cancel; caught by the matrix tie). 20 tester mutants: 15 caught by Lean, 5 by the numerical ties. prompts/103 fixed two m3x test slips (acceptance-v9).
- 2026-11-06: planner prompts/102 + reports/research/101 + tests/acceptance/m3x (4 tests) + METHODS-spinnet §9; locked acceptance-v8 (83e6d80). Lean prototype (Mathlib-free, decide): 11 theorems in 19.4 s / 1.94 GB.
- 2026-11-06: M3 gate complete → tag milestone-3; Report 3 written; outgoing bundle in ~/su2qc-sync/outbox/. Inbox empty → M4 waiting (watcher every 30 min).
- 2026-11-06: M3 3.L1+3.L2 PASS (reports/tests/105): 12 count theorems + 5 circuit-structure theorems, axioms ⊆ {propext}; tables copied from Python are only checked for self-consistency with the Lean gate model; the 16/96/16/177/16/96/16 spectrum is NOT kernel-checked (pair-class counts only) — say so in Report 3. coupling_table now snaps to half-integers (raise if off > 1e-12); results regenerated on clean commit.
- 2026-11-06: M3 step 3.7 PASS (reports/tests/104): results reproducible (all numeric fields identical on rerun), 133 numbers independently recomputed.
- 2026-11-06: M3 step 3.6 PASS (reports/tests/103): spinnet_v2 vendored gate-for-gate (angles = −2× sibling's: Paulo normalisation × route-B gauge); exact on all 433 (≤ 3.4e-15); β=0.61 counts pairs9 34 CX/9 rot/24 T_fixed, flags4 44/4/48, flags5 42/5/40, flags6 36/6/32; T_total(1e-6) pairs9 576, flags4 298; sibling archive T at β=1 reproduced (600/352/416; flags4 296 vs archive 290, likely a post-synthesis T cancellation there); synthesised ε=1e-6 certified.
- 2026-11-06: M3 steps 3.3–3.5 PASS (reports/tests/102): E1, B1 ×4, B2, B3, S1 ×2 green (T1 already green); Aer on all 433 states: U_E phase e^{−3iα/4} exact; U_B error ≤ 5.5e-15 at 4 β; steps ≤ 4.4e-15 at 3 angle pairs; wrong order / −β / reversed product rejected (≥ 0.5); Trotter slopes 1.98 (order 1), 2.98 (order 2). Counts: U_B 54 CX, 4 rot, 56 T_fixed, 7 anc, depth 67; step order 1/2: 54 CX, 8/12 rot. Two session crashes were OOM kills of the tester's verify script (dense Gauss product ~17–29 GB), fixed in the script; memory guard installed.
- 2026-11-06: M3 step 3.2 PASS (reports/tests/101): P1 green — Paulo's 15-qubit file (68 CX, 64 T, 4 rot) valid on the open 433 states up to a sign gauge (all 8 bright pairs −1 ≡ β→−β): error 9.7e-15, leak 0, Gauss 5.4e-16, outer bits read 0; raw target rejected (0.19967 = 2 sin 2β at β=0.05). build_walk(GENERAL7) exact (≤ 2e-14) at β ∈ {0.4, 0.61, 1, 2}; angles (−7/2, −1, 3, 3/2)β; 54 CX, 4 rot, 56 T_fixed, 7 anc, depth 67.
- 2026-11-06: M3 steps 3.0+3.1 PASS (reports/tests/100): C1, K1 green; fallback decode fixed by builder (prototype let 60–76 inadmissible codes overlap physical states up to 0.354; now Gram = 1 to 7.3e-15 on 12 032 codes, Gauss ≥ ½ on all 11 599 inadmissible); route B vs A after gauge 1.4e-15; unit 236/237 (laptop flake). Commit 33d7dba.
- 2026-11-06: planner prompts/100 + reports/research/100 + docs/METHODS-spinnet.md + tests/acceptance/m3 (24 tests, all PENDING); locked acceptance-v7 (a3bfda5). Findings: general U_B prototype 54 CX, 4 rotations (−7/2, −1, 3, 3/2)β, 56 T_fixed, exact 1.4e-14; Paulo's 15-qubit file valid on the open 433 states up to a per-pair sign gauge (err 9.8e-15); spinnet_v2 pairs9 34 CX/9 rot, flags4 44 CX/4 rot. Laptop-owned diffs wanted → merge notes.
- 2026-11-05: desktop setup done (`~/su2qc-sync/setup-log.md`); baseline on fresh clone: m0+m1 56/56 incl. slow, unit 216/216, lock PASS acceptance-v6.

---
# Laptop STATUS at branch point (a2ec571), kept for reference

# STATUS — su2qc-encoding

Last updated: 2026-11-04 (coordinator)

## Goal
One SU(2) plaquette with 8 outer links (12 links, 4 four-valent corners), $j_{\max}=1/2$.
For each of five encodings, in order — (1) Paulo's 12-qubit, (2) spin network, (3) rishon,
(4) loop-string-hadron, (5) fuzzy — build in Qiskit 2.5.2 / Aer 0.17.2 the one-Trotter-step
circuits $U_E(\alpha)=e^{-i\alpha H_E}$, $U_B(\beta)=e^{-i\beta H_B}$, verify on every Gauss-law
state (433 physical states), count CNOT and T gates → report; then compress with a
Gu-et-al-style LLM loop (in-session proposer agents, deterministic evaluator) → report.
Full plan: `prompts/001-plaquette-five-encodings-plan.md`.

## Plan in force
`prompts/002-m0-m2-foundation-twelve-qubit-compression.md` (planner kickoff; refines prompts/001 M0–M2).
Acceptance tests locked as `acceptance-v4` (86 tests, M0–M2; v3 = prompts/003 Gauss rule, v4 = prompts/004 leak as amplitude). M3–M10 still per prompts/001.

## Current milestone / step
M2 — compression machinery (step 2.1) and Lean track (step 2.L1) in parallel (two builders).

## Open failures (attempt counters)
| Check | Builder attempts | Tester rounds w/o progress | Fixer runs | Notes |
|---|---|---|---|---|
| M2 2.3 evaluate robustness N1 file I/O, N2 SHA race, N4 synth-cache trust (reports/tests/027) | 1 | 0 | 0 | physics + target ids green |

## Decisions
- 2026-11-05 (Digonto): Lean 4 formal verification added to M2 (prompts/006): kernel-checked generic theorems + counts; per-circuit certificates via compiled checker ACCEPTED, labelled 'native-certified'; final best circuit: angle-linearity preferred, not required ('Lean: n_a' allowed). proposer.md got a Lean paragraph (coordinator edit).
- 2026-11-04 (Digonto): restart from the plaquette note; old 2×2-lattice work archived (tag `archive-2x2-lattice`), reference paper kept in `refs/`.
- 2026-11-04 (Digonto): "12-qubit" = Paulo's definition (3 qubits per inner link, $(j,m,m')$); the circuit changes only the 12 inner qubits but may read the outer links as controls; correctness on all 433 physical states. NOT the note's one-label-per-link register.
- 2026-11-04 (Digonto): order of work = per encoding (general circuit → report → compress → report), 12-qubit first.
- 2026-11-04 (Digonto): compression proposer = Claude Code agents in-session; coordinator creates the `proposer` agent role and guard-hook entry in `~/.claude` itself (plan §3 step 2.0).
- Plan §1/§8 defaults: Paulo Eq. 16 normalisation; nominal angles $(\alpha,\beta)=(0.37,0.61)$ + alternates; $\varepsilon=10^{-6}$ in the loop; cost order CNOT > T > depth > qubits; `pytest -n auto`; outer electric phases reported as a separate row.
- T-count rule: $T_{\rm total}=T_{\rm fixed}+\sum_{\rm rot}T_r(\varepsilon)$, $T_r\approx3\log_2(1/\varepsilon)$ (Ross–Selinger), measured with pygridsynth; the "$+3\ln\varepsilon$" form was wrong (sign, base, multiplicity).

## Known issues
- Benchmark 002 flags: Paulo-QPY evaluate peak RSS +33 % (1.1→1.5 GB) and warm logical_metrics/t_table +6 ms per call (program-order lower) — watch in M2.
- M2 prerequisite (audit 003 N4): su2qc-trotter lean22/lean22_v2 apply the electric layer AFTER the plaquette (U_E U_B, opposite of our U_1); import only the plaquette part and prepend our build_UE.
- Fixed prune cap TOL_PRUNE = 1e-12 rejects step order 2 at ε=1e-4 (max dropped 2.6e-12) although op_norm_error 5.8e-4 ≤ 1.4e-3 and dropped is already inside op_norm_error (reports/tests/020): RESOLVED: prompts/005, acceptance-v5, implemented (reports/tests/021).
- Audit 002 R1: span-leak bound ‖s_k‖ ≤ 4·gauss_residual is per state; coherent span leak could be ≤ √433 × larger — optional operator-norm Gauss residual (one 433×433 Gram). Non-blocking; raise with planner before M2 loop.
- Audit 002 R2: aer_mps `certified` threshold is engine_accuracy 2e-10, but METHODS/prompts/004 say 1e-9 minimum → fix in M1 step 1.1 (require min tol ≥ 1e-9 for aer_mps; do not change engine_accuracy, M0-E5 asserts ≤ 2e-10).
- M1-O1 expects the full 6561-entry dim S_o table (zeros included); `s_o_dims` returns only 3153 supported keys → fix in M1 step 1.8 (also unit test `test_physical_unit.py:59` 1<=v → 0<=v).
- results JSON writes non-strict Infinity/NaN for failed verdicts; fine for Python consumers.
- Ross–Selinger band lower edge 3·log2(1/ε)−4 is violated by 1 of 24 angles at ε=1e-10 (T=94 < 95.7); not a tested M0 case — check whether M1-T1 asserts the band at 1e-10 before M1 step 1.7 (reports/tests/012).
- `t_table()['t_qiskit']` compiles the level-0 lowered circuit (1096 T on Paulo's circuit) — not comparable with Paulo's metadata (1162, from `ct_compile` on the original).
- M1-T1 for UE/UB needs the sparse engine (aer_mps uncertifiable at synth tolerances when N_rot < 15 at ε=1e-6): the M1 UB builder must keep rotation targets on few reused qubits (sparse state grows 2^k in distinct rotation qubits; 14 distinct → cap exceeded). reports/tests/011.
- Aer MPS engine accurate only to ~1e-11–2e-10 (reports/tests/008): METHODS corrected by coordinator; evaluator must record engine and not certify 1e-10/1e-12 verdicts with aer_mps. Next planner run: confirm engine-specific tolerance policy.
- Note §5 register table vs its bullets (q-deformed 16 vs 12; spin network 20 vs 16): the script's register sizes are upper bounds. Not blocking (q-deformed not in scope).
- Paulo (Fig. 2) vs note §4.2 on whether the spin-network plaquette depends on the outer links: SETTLED by M0-X5 (reports/tests/006): in the (inner|outer) pairing H_B is block-diagonal in outer spins, 128 blocks all equal to one 47×47 K (2.7e-15), J conserved → Paulo right; in a mixed pairing amplitudes depend on outer spins → note §4.2 right there.

## Next action
Auditor M1 → small fixes (outer-row synthesised verdicts flagged 'writes_outer' → mark not-verifiable; m1_results --out path) → benchmark → tag milestone-1 → Report 1.

## Log
- 2026-11-04: old work archived (commits 30acd44, 92a5b67, tag `archive-2x2-lattice`) and removed from the tree.
- 2026-11-04: `python3 -I refs/su2_plaquette_encodings.py` (numpy 2.5.2, 0.7 s): every number in note §5 reproduced.
- 2026-11-04: exploration of Paulo's notes, Gu et al., and sibling projects (su2qc-trotter, su2qc-skqd, su2qc-paulo-code, su2qc-qcadvantage); plan 001 designed and approved.
- 2026-11-04: plan step 2.0 done early (coordinator, outside the repo): `~/.claude/agents/proposer.md` created (Opus 5.5, high); `WRITE_ALLOW["proposer"] = ["compress/programs/", "compress/ideation/", "scratch/"]` added to `~/.claude/hooks/guard.py` (checked: denies `src/` and `tests/acceptance/`, allows `compress/programs/`); proposer row added to the roles table in `~/.claude/CLAUDE.md`.
- 2026-11-04: planner kickoff launched (prompts/002, METHODS, locked M0–M2 tests); design reports parked in `scratch/design-A-physics.md`, `scratch/design-B-compress.md`.
- 2026-11-04: planner kickoff done: `reports/research/001-…`, `prompts/002-…`, `docs/METHODS.md`, 84 locked tests. Findings: Paulo's Fig. 2 claim holds in the (inner|outer) pairing (prototype residual 3e-15); Paulo's 34-qubit circuit verified vs $U_B(\beta=1)$ to 2.9e-6 (Aer MPS); Paulo Eq. 25 missing a conjugate (typo, harmless); native Qiskit `mcx` (≥3 controls) excluded from the gate set (not Clifford+T exact).
- 2026-11-04: `acceptance-lock` → `acceptance-v1` at 003cc3a; project `CLAUDE.md` written.
- 2026-11-04: M0 step 0.1 PASS (reports/tests/001); `tools/lock.py` → LOCK.json, re-locked as `acceptance-v2` (c48e549).
- 2026-11-04: M0 step 0.2 geometry PASS (reports/tests/002): G1, G2 green; outer far ends = pseudo-sites ('ext', i) (builder's choice; later spin-network code must skip them).
- 2026-11-04: M0 step 0.3 algebra PASS (reports/tests/003): A1–A3 green; independent checks ≤ 8.9e-16 (Haar-quadrature U, 570 6j vs sympy, V_P vs Paulo Eq. 28/29).
- 2026-11-04: M0 step 0.4 physical states PASS (reports/tests/004): C1–C6, X1 green; independent recount 433/2/256/95/17362; Gauss ≤ 5.2e-16, Gram ≤ 7.3e-15. Claim (i) data: inner span rank = 625 (full); 3153 of 6561 outer patterns allowed; dim S_o ∈ {1..5, 8, 9, 17}, closed = 2.
- 2026-11-04: M0 step 0.5 operators PASS (reports/tests/005): X2,X3,X7,X8 green; W leak 1.1e-15; closed block exact incl. sign; H_B spectrum −2(16) −1(96) −½(16) 0(177) ½(16) 1(96) 2(16); ‖U2−U1‖ slope → 2.
- 2026-11-04: M0 step 0.6 route B PASS (reports/tests/006): X4–X6 green; spectra A vs B ≤ 1.1e-14; K = 8 bright 2×2 pairs (couplings 2, 1×6, ½) + 31 dark rows. Caveat: K is a matching, so A/B comparison tests moduli, not signs (sign anchored by vacuum amplitude +1).
- 2026-11-04: M0 step 0.7 tester FAIL (reports/tests/007): E1/E2 green, vs Aer 3.2e-15 on 36 circuits; pruning without accounting can bias op-norm (constructed 4e-10); native mcx≥3 silently wrong (Qiskit uses idle qubits as clean ancillas); aer_check.py still a stub. Sent back to builder (attempt 1).
- 2026-11-04: M0 step 0.7 recheck PASS (reports/tests/008): relative pruning + certified `dropped_l2` bound (64 896 forced-pruning cases, 0 violations); mcx≥3 rejected (hole: inside custom gates → fix in 0.8); aer_check built. Counters reset.
- 2026-11-04: M0 step 0.8 tester (reports/tests/009): E3–E5 green, 125 adversarial checks; F1 SERIOUS (non-default register order → silent false accept) sent to builder, fixed, recheck running. F2: fixed Gauss tol 1e-10 fails M1-P1 for Paulo's synthesised circuit (residual 1.16e-10) → Digonto decided: Gauss tol for synthesised circuits = N_rot·ε + 1e-9; planner amending locked tests.
- 2026-11-04: planner addendum prompts/003 + reports/research/002: Gauss tol for synthesised circuits = N_rot·ε+1e-9 (M1-P1, M1-T1), `synth_tolerances`, `Verdict.tolerances`, `certified` includes tol_gauss; M0-E5 aer_mps clause moved 1e-10→1e-9 (engine floor 2e-10; flagged loosening). Re-locked as acceptance-v3 (05f0391). Next: after 0.8 recheck, builder implements prompts/003 §4.
- 2026-11-04: M0 step 0.8 evaluator PASS (reports/tests/009, 010, 011): F1 fixed (24-order fuzz identical), prompts/003 interface in; Paulo's QPY under amended M1-P1: ok, certified, err 2.905e-6, Gauss 1.16e-10 (aer_mps, 108 s). Counters reset.
- 2026-11-04: M0 step 0.9 metrics PASS (reports/tests/012): counts = Qiskit on 30 random circuits; macro costs match METHODS; T per rotation measured (24 angles): 1e-4 42.6 [38,48], 1e-6 62.8 [56,66], 1e-8 82.6 [78,86], 1e-10 101.9 [94,106] vs 3log2(1/ε) 39.9/59.8/79.7/99.7; Paulo's circuit reproduced exactly by ct_compile (cx 294, T 1162, depth 2549).
- 2026-11-04: M0 step 0.10 + M0 gate tester full PASS (reports/tests/013): m0 33/33 incl. slow, 131 unit, no regression vs 001–012; full m0 run 28 s.
- 2026-11-04: M0 audit PASS WITH NOTES (reports/audits/001): physics conventions all correct; N1 leak tolerance compares probability (1e-12) vs amplitude error (1e-10) → ancilla leak amplitude up to 1e-6 accepted. Digonto decided: count leak as amplitude, combined bound ‖A−e^{iφ}V‖+√λmax(X†X) ≤ tol_err. N2–N4, N7–N9 code fixes sent to builder; N5 (spin-network signs are gauge at jmax=½) and N6 (compress TaskSpec needs tol_gauss, gauss=True) noted for M2/M3.
- 2026-11-04: planner prompts/004 + reports/research/003: op_norm_error = block_error + dropped_total + ‖X‖₂ ≤ tol_err; tol_leak removed; span leak bounded by Gauss (‖s‖ ≤ 4·gauss_residual); auditor case cry(1.9e-6) now rejected (9.5e-7); Paulo QPY combined 1.08e-5 ≤ 2e-5. Re-locked acceptance-v4 (35bd2a6). Open (stop-and-ask if hit): sum vs RSS for synthesised circuits (√2 slack); aer_mps leak floor beyond bond 16.
- 2026-11-04: audit fixes N2–N4/N7–N9 + step 0.11 leak-as-amplitude: tester full PASS (reports/tests/014): m0 34/34, unit 140; leak = sin(θ/2) exactly; cry(1.9e-6) rejected; Paulo QPY ok/certified: block 2.905e-6 + leak 7.851e-6 = 1.076e-5 ≤ 2e-5 (84 s, aer_mps). aer_mps bound pessimism ≤ √17 (prompts/004 text corrected 16→17).
- 2026-11-04: M0 audit recheck PASS WITH NOTES (reports/audits/002): combined bound correct, aer_mps bound valid (ratio ≤ √17), N2–N4/N7–N9 resolved; new non-blocking R1, R2. Benchmark launched.
- 2026-11-04: M0 benchmark baseline (reports/benchmarks/001): physical_basis 0.30 s cold; evaluate identity 6.7 s cold / 2.0 s warm (inner_span), 1.4/0.9 s (physical); Paulo QPY aer_mps 83 s; m0 suite 33 s, unit 48 s; physics unchanged. M0 gate complete → tag milestone-0.
- 2026-11-04: M1 step 1.2 electric PASS (reports/tests/015): U_E = 4×p(−3α/4), error 1.2e-13, leak 0; cx 0, n_rot 4, depth 1; T(ε) inner at α=0.37: 176/256/328/416 at ε=1e-4/1e-6/1e-8/1e-10 (estimate 160/239/319/399); outer row +8 rotations (T 528/768/984/1248 total for 12). Waiting on step 1.1 tester before committing both.
- 2026-11-04: M1 step 1.1 codec + audit R2 PASS (reports/tests/016): codec = Paulo Eq. 31 exactly; 433 vectors Gram 3e-15, Gauss 5.4e-16; aer_mps certified only at tol ≥ 1e-9. Steps 1.1 + 1.2 committed.
- 2026-11-04: M1 step 1.3 tester FAIL (reports/tests/017): build_UB exact at β=0.4/0.61/1/2 (block 1.7e-14), composition ok, paulo_logical + ct_compile reproduce Paulo (294 CX, 1162 T); build_UB(0.61): cx 294, n_rot 6 (all on d[11]), t_fixed 312, depth 292, 34 qubits; T(ε)=560/696/820/936. Failures: decomposition-cache key collision (silent wrong result for same-named custom gates); synthesize() whole-circuit lowering hoists Hadamards → T1[UB] unsimulable on sparse. Sent to builder (attempt 1). Digonto asked about lean22: pending his choice whether to add lean22/lean22_v2 as comparison rows in Report 1 (planned as M2 seeds).
- 2026-11-04: M1 step 1.3 recheck PASS (reports/tests/018): cache keyed on standard gates only, program-order lowering; T1[UB] certified on sparse (ε=1e-6: 1.854e-6 ≤ 6.0e-6, 3.6 s). Step 1.4 tests (B2–B4) green and covered by reports 017/018. Steps 1.3 + 1.4 committed.
- 2026-11-05: M1 steps 1.5 + 1.6 PASS (reports/tests/019): build_step exact (2.7e-13) both orders at 3 angle pairs; wrong order rejected (0.51–1.74); order 2 = UE(α/2)UB UE(α/2) gate for gate; ‖U2−U1‖ ≈ 3αβ; paulo_circuit ok/certified 1.0756e-5 (aer_mps 84 s). Step counts (0.37,0.61): cx 294, T_fixed 312, n_rot 10/14, T_total(1e-6) 952/1224. Committed.
- 2026-11-05: M1 steps 1.7 + 1.8 PASS (reports/tests/020): full 6561 dim S_o table (independent, both conventions); T tables verified 16/16 cells; error_measured_sum = 0.22–0.42 × n_rot·ε. Committed.
- 2026-11-05: M1 step 1.9 built (scripts/m1_results.py → results/twelve/{UE,UB,step}.json; M1-R1 green); uncommitted, waiting on the prune-cap change before regenerating.
- 2026-11-05: step 1.9-pre (prompts/005) + 1.9 results + M1 gate tester full PASS (reports/tests/021): m0+m1 56/56 incl. slow, unit 166; results script reproducible bit-for-bit; 64 numbers recomputed independently. Outer-row synthesised verdicts are writes_outer (Rz words contain H on outer qubits) — tester computed them by hand, all within budget.
- 2026-11-05: M1 audit PASS WITH NOTES (reports/audits/003): conventions all correct; mcrx→rccx·crx·rccx exact; U_B(0.61) vacuum P = cos²(2β) via Aer (α_P=2β confirmed); like-for-like Qiskit CT at β=1, ε=1e-6: ours 662 T vs Paulo 1162 T, both 294 CX. Notes N2,N3,N5–N8 to builder; N6 (name-only gate recognition) fixed now since it blocks M2; N1: regenerate results on a clean tree before Report 1.
- 2026-11-05: M1 audit fixes tester (reports/tests/022): N2, N3 (662 vs 1162 T; pygridsynth 564/684/812/936 vs 872/1180/1488/1736), N5, N7, N8 PASS; N6 FAIL (open-control cx rejected; forged class names; mcx bypass) → builder attempt 1.
- 2026-11-05: M1 audit fixes recheck PASS (reports/tests/023): N6 class-identity predicate, open-control gates exact, mcx bypass closed; evaluator follows gate definitions (matches QPY/QASM export); results unchanged numerically. Committed; results regenerated on the clean commit next.
- 2026-11-05: results/twelve/* regenerated on clean commit a9702e5 (single provenance snapshot, git_dirty False for all three).
- 2026-11-05: M1 benchmark (reports/benchmarks/002): no >10 % slowdown on calls >100 ms; physics unchanged; m0+m1 suite 200 s. Report 1 written; tag milestone-1.
- 2026-11-05: planner prompts/006 + reports/research/004 + METHODS §11; re-locked acceptance-v6 (aee6057). Planner note: the '41 bright pairs, couplings 1, ½, ¼' (from Paulo's notebook block structure) was not reproduced on the 625-code inner operator (128 edges, all modulus ½; pairs/cliques structure) — certify whatever the exporter computes.
- 2026-11-05: M2 step 2.1 spec + oracle PASS (reports/tests/024); notes: spec should also state the synthesised-circuit rule and the prune cap (folded into 2.2).
- 2026-11-05: Lean step 2.L1 PASS (reports/tests/025): clean lake build 22 s with copied Mathlib oleans, Su2PlaqCert Mathlib-free, axiom classifier right; 2.L2 built (12 generic theorems, standard axioms) — 2.L1+2.L2+2.L3 to be tested/committed together. Desktop package (~/su2qc-desktop-package, make_package.sh) to be rebuilt after that commit so it carries the Lean skeleton.
- 2026-11-05: M2 step 2.2 builder PASS (reports/tests/026): 189 adversarial checks; mcx chain exact k≤6 (CX 6+6(k−2), T 7+8(k−2)). Note for 2.3: evaluator must use qc.num_qubits and re-check gates itself. Desktop package START_HERE.md rewritten for two parallel tracks (spin network M3/M4 + rishon M5/M6) — rebuild package after the Lean commit.
- 2026-11-05: M2 step 2.3 tester FAIL on robustness (reports/tests/027): proposer file I/O not blocked, SHA time-of-check race, corrupt synth-cache trusted; physics fine (--full timing 18–20 s, --trial 5–6 s on the step circuit). Builder attempt 1.
- 2026-11-05: Lean steps 2.L2 + 2.L3 PASS (reports/tests/028): 26 generic theorems + 8 kernel-checked counts, standard axioms only; clean lake build 379 s, Counts.lean peak RSS 15.3 GB. Note for planner: Lean innerSumM over-counts per-outer states (support 3153 and max 17 still correct). Lean 2.L1–2.L3 committed.

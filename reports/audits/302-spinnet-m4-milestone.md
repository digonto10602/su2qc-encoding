# Audit 302 — spinnet milestone 4 (LLM compression of the spin-network step, headline Lean certificate, results)

- Date: 2026-11-11 · Auditor: Claude Opus 5.5 (high) · Mode: milestone gate step 2 (read-only except this report)
- Git: HEAD `4733370` (branch `merge-desktop-tracks`; working tree has uncommitted LSH/Lean-structure edits from other agents, none in the audited paths). Commit range `milestone-3` (`de8de22`) .. `4733370`. Results provenance commit `b0d3db7` (stored by `232bb5e`).
- Plan in force: `prompts/104-spinnet-m4-plan.md` with §11 errata E1–E3 (on `prompts/100`–`103`); conventions `docs/METHODS.md`, `docs/METHODS-spinnet.md` §1–§10; lock `acceptance-v18`.
- Related: `reports/tests/110`–`118` (rounds 0–5, headline rule, 4.L/4.7), `reports/tests/404` (M4 gate full PASS, 149/149 acceptance, 932 unit), `reports/audits/100` (M3 audit; sign-of-$\beta$ gauge N1).
- Numbering note: `~/.claude/bin/next-num reports/audits` returned 302 (per-folder counter), which falls in the fuzzy range 300–399 of the track table in `notes/STATUS.md`; the coordinator may want to record that.

## 1. What was asked
Look for silent physics or numerics errors in the spinnet M4 diff: signs, factors of 2, angle conventions, normalisation, Trotter order, whether the evaluator compares against the right target on all 433 Gauss-law states (the states that satisfy the Gauss law at every corner), ancilla cleanliness, the robust key (the ranking that adds up T over 20 seeded angle pairs, seed 20261107, at $\varepsilon=10^{-6}$), the stop rule (3 rounds without robust improvement), soundness of the Lean certificate (does `checkJsonString` / `write_theorem_file` really tie the theorem to the headline program and target; can a wrong circuit be labelled certified), provenance, honesty of the Report-4 statements on CX vs T, and notes for the consolidation plan `prompts/008`.

## 2. What I did
1. Read STATUS, `notes/STATUS-spinnet-m3-m4.md`, `prompts/104` (incl. §11 E1–E3), `prompts/103`, `docs/METHODS-spinnet.md` §1–§7 and §10, tester reports 118 and 404. Oriented with `graphify query "spinnet loop robust_metrics headline certify"`.
2. Read the new code in full: `src/su2plaq/spinnet/loop.py` (1072 lines), the M4 part of `src/su2plaq/spinnet/lean_export.py` (L339–753), `lean/Su2PlaqCert/SpinNet/{Check,Main,Pins}.lean`, `scripts/m4_results.py`, the headline program `compress/programs/spinnet/F1/002-dimer-linear-corner-walk.py`, the locked test L5, and the laptop-side `evaluator.py` / `compress/metrics.py` hunks that the spinnet verdicts depend on.
3. Checked that the frozen files did not change: `git diff milestone-3..HEAD --stat -- src/su2plaq/encodings src/su2plaq/circuits src/su2plaq/spinnet/{walk,trotter_v2,paulo}.py` lists only fuzzy/LSH/rishon files. The spinnet `code_sha256` is `7f5bb7f8e6…` in all six round files and in `robust.json`. The laptop `evaluator_sha256` is `0bd7e7d91d9d…` in all rounds, in all 23 archive entries, and equal to the current `provenance.code_hash()`.
4. **Independent binding and tamper probe** (my script, `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/audit/probe_bind.py`, run with `PYTHONPATH=src taskset -c 0-1 tools/run-capped python …`, about 1 min):
   - The JSON text inside `lean/certs/spinnet-best-step.lean` is byte-identical to `results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json` (sha256 `1445a52a…`, which matches `extra.lean.cert_sha256` in `results/spinnet/m4-compressed.json`).
   - I rebuilt the headline program (file sha256 `750151e9…`, the archived value) through the worker at $(0.37,0.61)$ and at a pair outside the spec, $(1.3,0.17)$, and re-exported each. The gate records (gate, qubits, angle exponents), the phase and the target blocks are **identical** to the theorem's certificate at both pairs. Target kind `step`, order 1, base $(d_\alpha,d_\beta)=(4,8)$, 17 qubits, 87 gates.
   - I fed the compiled checker `su2plaq_cert_spinnet` with the original and ten tampered certificates. Original: `ACCEPT`. Rejected (`REJECT`): sign of one `rz` exponent flipped; every `rz` sent to $-\beta$ (i.e. $U_B(-\beta)$); one electric `p` dropped; kind relabelled `UB` (target pin mismatch); order relabelled 2 (base mismatch); extra `x` on the ancilla (dirty ancilla); extra `x` on outer qubit 8 (outer write); electric layer moved after the plaquette ($U_EU_B$ instead of $U_BU_E$); global-phase exponent shifted; one of the 433 states dropped.
5. Recomputed the angle set from `numpy.random.default_rng(20261107)` (`alpha = uniform(0.05,2.0,20)`, then `beta = uniform(0.05,1.2,20)`). It equals `robust.json["angle_set"]["pairs"]` exactly (sha256 prefix `769caec1c2738356`). I listed the full robust ranking from `results/compress/spinnet/robust.json` (§5).
6. Read the before/after rows of `results/spinnet/m4-compressed.json` and the external rows of `results/compress/spinnet/round-000.json` side by side (this is how issue N1 was found).

## 3. Checklist

| # | Item | Verdict | Where / evidence |
|---|---|---|---|
| 1 | Equations match METHODS term by term | OK | Electric layer `p(-0.75*alpha)` on the 4 link qubits gives $e^{-i\alpha\,j(j+1)}$, with $j(j+1)=\tfrac34$ (headline program L27; METHODS-spinnet §4). Walk `rz(2c*beta)` gives $e^{-i\beta kZ}$ under $R_z(\theta)=\mathrm{diag}(e^{-i\theta/2},e^{i\theta/2})$ (program L43). Exact target: $U_E\mapsto z_\alpha^{-3n}$ with $z_\alpha=e^{i\alpha/4}$; $U_B=\sum_\lambda P_\lambda z_\beta^{-4\lambda}$ with $z_\beta=e^{i\beta/4}$; order-1 step shifts by $-3n_{k_j}$ (the column, so $U_E$ acts first); order 2 shifts by $-3(n_i+n_j)$ at $d_\alpha=8$ (`lean_export.py:423-446`). All of this equals $e^{-i\beta H_B}e^{-i\alpha H_E}$ and $e^{-i\alpha H_E/2}e^{-i\beta H_B}e^{-i\alpha H_E/2}$. Cross-checked against the float target to $\le10^{-12}$ (`:447-456`). |
| 2 | Time-evolution sign and Trotter order | OK | Target `UB @ UE(alpha)` (`encodings/spinnet.py:239-258`, frozen). The certificate rejects $U_EU_B$ and $U_B(-\beta)$ (probe, §2.4). $-\beta$ remains a codec convention (audit 100 N1), as METHODS-spinnet §2 says. |
| 3 | Basis / index conventions | OK | Canonical frame: data 0–7, outer 8–15, ancilla 16+ via `layout_of` (`lean_export.py:539-547`). The headline writes the corner qubit `d[4]` temporarily (`rccx(1,2,4)`, then uncomputes). That is allowed: the only forbidden write is to `o`, and the checker and evaluator see exactness on all 433 states. |
| 4 | Truncation / cut-offs | OK | $j_{\max}=\tfrac12$ is fixed by the encoding. Prune cap and support cap are the laptop's; `dropped_total` $3.3\times10^{-15}$ for the headline (`m4-compressed.json` verification). |
| 5 | Normalisation; real where required | OK | 433 unit codes; the Gram check inside the checker (`Check.lean` `gramError`). Couplings snapped to rationals with denominator $\le2$ (`lean_export.py:363-376`). |
| 6 | Evaluator compares against the right target on all 433 states | OK | Full mode passes `states=None`, so every column is checked (`compress/evaluate.py:172-185`; `evaluator.py` diff). The headline uses `method inner_span` with `outer_bits_read 0`, `n_blocks 1`. That is equivalent to all 433 states by M3-K1 (every outer block is the restriction of $e^{-i\beta K}$). G2 (tester 404) re-checks with Aer on all 433 states. |
| 7 | Ancilla cleanliness | OK | Evaluator: leak 0, `dirty_ancilla 0.0`. Exact checker: the dirty-ancilla tamper is rejected (§2.4). |
| 8 | Precision | OK | Evaluator complex128; certificate exact (Laurent polynomials over $\mathbb Q(i,\sqrt2,\sqrt3)$). |
| 9 | Randomness / seeds | OK | Angle-set seed 20261107 recorded in `robust.json`, `summary.json["headline"]`, `m4-compressed.json` `seeds.angle_set`; recomputation matches exactly (§2.5). Trial seed 0, transpiler 12345. |
| 10 | Robust key computation | OK with note N2 | `loop.py:796-830`: T from laptop `metrics(measured=True)` at `spec.eps` $=10^{-6}$ per pair; sums over 20 pairs; $\rho$ from the exporter. Gap: the nominal circuit is left out of the skeleton-equality check (N2). |
| 11 | Stop rule | OK | Robust keys (§5): round 3 best is $(31,21840,1,\cdot)$, worse than $(31,21840,0,46024,17)$ because $\rho=1$. Round 4 the same. Round 5 `r05-F2-005` $(31,21840,0,46104,17)$ is worse only in summed depth. So rounds 3, 4, 5 brought no robust improvement and the loop stopped, as E3 Decision 2 specifies (counter $=1$ entering round 4). Sessions 18/20, rounds $\le8$. |
| 12 | Lean certificate soundness | OK with note N3 | The theorem's JSON equals a fresh export of the archived headline program at two angle pairs (§2.4). The pins fix the states and the (kind, order) target. Tampering is rejected. The chain from program to label is sound: `certify_best` rebuilds with `expected_sha256` (`loop.py:983`), and `m4_results` refuses a certificate whose `program_file_sha256` differs (`scripts/m4_results.py` `_lean_block`). Only the program-file sha sits in a comment line, outside the proved statement (N3). |
| 13 | Tests exercise the production path | OK with note N3 | S8/S9/L5/R1 call `loop.robust_metrics/headline`, `report_table`, the real archive and the real checker. L5 checks only that the theorem file *names* the headline (`test_spinnet_compress_lean.py:196`), not that its gates are the headline's. My probe closes that gap for the present file. |
| 14 | No hard-coded answers in source | OK | Facts are parsed from the Lean statements and cross-checked against Python (`loop.py:250-300`). `m4_results` types no numbers. |
| 15 | Provenance | OK with notes N1, N5 | `m4-compressed.json`: commit `b0d3db7`, `git_dirty False`, host, command, versions. The round files for rounds 1–5 say `git_dirty True` because the proposal files were uncommitted at evaluation; each entry carries its program sha256, so it stays traceable (N5). |
| 16 | Frozen files unchanged during M4 | OK | §2.3. |
| 17 | Report-4 statements honest | OK with notes N1, N4 | METHODS-spinnet §10.6 states the CX-for-T trade plainly. Two statements in the results files need fixing or qualifying (N1, N4). |

## 4. Issues

### BLOCKING
None.

### NON-BLOCKING

**N1 — `scripts/m4_results.py:82-84`: the Paulo 15-qubit and Qiskit-whole rows of the before/after table lose their T values, and `qiskit_l3_whole` shows a mislabelled depth.**
`_external_rows` reads `m.get("t_measured").get("1e-06")`. The dict comes in-process from `loop._external_rows`, where `metrics()` keys `t_measured` / `t_estimate` by the **float** `1e-06`. Only the JSON-serialised copies have string keys. Result: in `results/spinnet/m4-compressed.json` and `m4-before-after.md`, `paulo15` has `t_1e-6: None`, `t_est_1e-6: None`, `t_1e-10: None`. The same circuit in `results/compress/spinnet/round-000.json` has `t_measured {"1e-06": 316, "1e-10": 478}`, matching METHODS-spinnet §5 ($64+252=316$).
In the same row builder, `qiskit_l3_whole` (counts only, `measured=False`) prints `depth_CT 67`. That number is the lowered logical depth (`compress/metrics.py`, `depth_ct = lm["depth"]` when not measured), so it is not comparable with the 861 of the general circuit. Report 4 is to be rendered from `m4-compressed.json` (plan §5), so as things stand it would either lack Paulo's T or need numbers typed by hand.
Fix: in `_external_rows` look up both key types (`d.get(1e-6, d.get("1e-06"))`), or round-trip `metrics` through `json.loads(json.dumps(...))` first. Print `-` for `depth_ct` when `metrics["measured"]` is False. Regenerate the results on a clean commit. Test: a unit test asserting that the `paulo15` row has `t_1e-6 == 316` (it is measured, so deterministic with pygridsynth 1.2.0).

**N2 — `src/su2plaq/spinnet/loop.py:816-817`: the robust key's skeleton check leaves out the nominal circuit.**
`robust_metrics` builds the 20 angle-set circuits plus the nominal one (`[*specs, sp]`). It then tests `skeleton_equal` over the 20 only (`circuits[:-1]`) and takes CX and qubits from pair 0. E3 Decision 1 says "the skeleton must be identical at every pair (the laptop's 'no fixed-angle tricks' rule extended to the set)". The laptop rule only ties the skeleton across the three spec pairs. So a program with one skeleton at the three spec pairs and another everywhere in the angle set would be ranked by a circuit other than the one that was validated and certified. Nothing like that is in the archive: the robust CX equals the laptop-key CX for all 23 entries (§5), and the headline's certificate equals its rebuild at $(1.3,0.17)$ (§2.4). Fix: one line, `skeleton_equal = len({... for c in circuits + [nominal]}) == 1` (optionally also the two spec alternates). Test: extend S8's "skeleton changes at the median $\beta$" case with a program whose skeleton changes only at $\beta=0.61$.

**N3 — the theorem statement binds the certificate JSON, not the archive entry. The program-file identity is only a comment.**
`lean/certs/spinnet-best-step.lean` proves `Su2PlaqCert.SpinNet.checkJsonString certJson = true`. What that means — kind `step`, order 1, the 433 pinned states, the pinned route-B target — sits inside the JSON and the pins. That is sound (the pins reject relabelling, §2.4). But the link to entry `r02-F1-002` and to program sha256 `750151e9…` is the first-line comment (`write_theorem_file`, `lean_export.py:739`), and the locked L5 test checks only that comment (`test_spinnet_compress_lean.py:196`). Also, the certificate's own field `program_sha256` (`ec21654e…`) is the gate-list hash, a different thing under the same name (known issue "2.L8" in STATUS).
Suggested hardening (for prompts/008): (a) write `entry_id` and `program_file_sha256` into the certificate's `provenance` before export, so they sit inside the proved literal; (b) rename the gate-list field to `gates_sha256`; (c) add a test that re-exports the rebuilt headline and compares `gates` with the theorem literal (my probe, §2.4, is that test).

**N4 — Report-4 wording to keep honest (statements, not code).**
- The headline buys **CX and qubits, not T**. Its CX: 31, against 54 (general, $-43\%$) and 34 (pairs9, $-9\%$). Qubits: 17 against 23 and 19. Its T: $\bar T(10^{-6})=1092.0$, against 560.6 (general) and 847.4 (pairs9) — $+95\%$ and $+29\%$ (from `robust.json`; tester 118 quotes $+92\%$ using the nominal 1086/566). METHODS-spinnet §10.6 says this correctly. Report 4 should also show the CX–$\bar T$ Pareto front from `robust.json` (§5). The front is: 31/1092.0 (`r02-F1-002`, headline), 32/847.4 (`r05-F3-005`, angle-linear), 34/665.6 (`r02-F5-002`), 42/609.1 (flags5), 44/553.1 (flags4), 46/486.7 (`r01-F5-001`, not angle-linear, Lean `n_a`). The general circuit (54/560.6) is dominated by flags4. Under a T-first cost model the headline would not be chosen.
- `extra.at_paulo_beta` (31 CX, $T_{10^{-6}}=1106$) is the **step** with the electric layer. Paulo's file is $U_B$ alone (68 CX, 316 T). Report 4 must not put these side by side as like-for-like. The JSON note says so; the report text should too.
- The header of `m4-before-after.md` says "$\bar T$ does not" depend on pygridsynth's word length. More exact wording: $\bar T$ still comes from pygridsynth, but it cannot be tuned by per-angle offset tables (E3 error analysis: $\sigma/\sqrt{20}\lesssim1$ T per rotation).
- Trust wording for the certificate: "native-certified (compiled checker + `native_decide`; the target pins are SHA-256 of the Python exact exporter's route-B target, cross-checked numerically to $10^{-12}$ and by the tester to $1.8\times10^{-15}$)". No Lean theorem links the pinned target to the kernel-checked 6j-derived $K$ (`Recoupling.lean`); that tie is numerical. Do not write "kernel-checked headline".
- The compressed program ignores `spec.order`. Every M4 claim is for the first-order step $U_B(\beta)U_E(\alpha)$. A request for order 2 would be rejected by the evaluator, not silently wrong. Say "order 1" in the headline sentence.

**N5 — provenance and environment details (record only).**
(a) `round-001..005.json` say `git_dirty True` (proposal files uncommitted at evaluation; tester 117/118 noted it). (b) The provenance records numpy 2.5.4, while project `CLAUDE.md` says numpy 2.5.2 — the doc is stale or the env drifted. (c) Three archive entries (`r00-seed-000`, `r00-seed-001`, `r01-F1-001`) carry absolute `cert_path`s under `/home/digonto/Projects/su2qc-spinnet/…`. The files exist under `results/spinnet/certs/` with the same basenames and the tester re-ACCEPTed them. But `round.resolve_cert_path` returns absolute paths unchanged (`compress/round.py:295-297`), so any later reader gets a missing file. That is harmless for M4 (the headline path is relative).

**N6 — $\rho$ (angle-linearity flag) counts every exporter answer except `non_linear_angle:` as linear** (`loop.py:824-825`). `phase_not_in_K`, `unitary_gate`, `disallowed_gate`, `bad_layout` and `unsimulable` all give $\rho=0$. This is literally E3's definition. It does not affect the ranking: every $\rho=0$ entry in `robust.json` has `export_status "ok"`. For prompts/008: define $\rho=0$ only for `export_status == "ok"`.

## 5. Evidence: robust ranking (`results/compress/spinnet/robust.json`, evaluator `0bd7e7d9…`, spinnet code `7f5bb7f8…`)

| entry | robust key $(\mathrm{CX},\sum T,\rho,\sum\mathrm{depth}_{\rm CT},q)$ | $\bar T(10^{-6})$ | angle-linear | laptop key |
|---|---|---|---|---|
| `r02-F1-002` (headline) | (31, 21840, 0, 46024, 17) | 1092.0 | yes | (31, 1086, 2258, 17) |
| `r05-F2-005` | (31, 21840, 0, 46104, 17) | 1092.0 | yes | (31, 1086, 2262, 17) |
| `r04-F1-004` (laptop-key best) | (31, 21840, 1, 45876, 17) | 1092.0 | no ($\pi/4$ shift) | (31, 1062, 2173, 17) |
| `r03-F2-003` / `r03-F1-003` | (31, 21840, 1, 45882 / 46141, 17) | 1092.0 | no | (31, 1062, ·, 17) |
| `r05-F3-005` | (32, 16948, 0, 33225, 17) | 847.4 | yes | (32, 832, 1552, 17) |
| `r02-F5-002` | (34, 13312, 0, 23379, 17) | 665.6 | yes | (34, 658, 1116, 17) |
| `r00-seed-001` pairs9 | (34, 16948, 0, 33064, 19) | 847.4 | yes | (34, 832, 1597, 19) |
| `r00-seed-002` flags4 | (44, 11062, 0, 17227, 19) | 553.1 | yes | (44, 554, 869, 19) |
| `r01-F5-001` | (46, 9734, 1, 17840, 17) | 486.7 | no | (46, 491, 914, 17) |
| `r00-seed-000` general | (54, 11212, 0, 16945, 23) | 560.6 | yes | (54, 566, 861, 23) |

The three 31-CX $\pi/4$-shifted programs tie the headline exactly in $\sum T$ (21840). Their nominal-pair saving of 24 T is zero on the locked set, as the E3 analysis predicted.

## 6. What the result means
No silent physics error was found in M4. Every sign and convention is right (electric $j(j+1)=\tfrac34$, walk $R_z(2\beta k)$, order-1 Trotter product $U_BU_E$, route-B sign of $\beta$). Full-mode verdicts cover all 433 states. The headline circuit is exact with clean ancillas, and its Lean certificate really is the certificate of the archived headline program: re-exported identically at two angle pairs, rejected under ten kinds of tampering. The robust key and the stop rule were applied as E3 specifies. The open items are reporting defects (N1 must be fixed before Report 4 is rendered from the JSON), one hardening of the robust-key skeleton rule (N2), and binding and wording improvements (N3, N4).

## 7. For the consolidation plan prompts/008
1. N2: include the nominal (and alternate) circuits in the robust-key skeleton set. The rule should live in the shared registry version of `robust_metrics`, so rishon/fuzzy/LSH inherit it.
2. N6: $\rho=0$ only when the exporter returns a certificate (`"ok"`).
3. N3: put `entry_id` and `program_file_sha256` inside the certificate JSON; rename the gate-list hash to `gates_sha256`; add a "theorem literal equals fresh export of the headline" test to the shared gate tests.
4. N1: one helper for metric dicts that handles float and string $\varepsilon$ keys (or always JSON-round-trip). Show "–" for `depth_ct` when `measured` is False.
5. N5(c): relativise the three absolute `cert_path`s, or make `resolve_cert_path` fall back to `ROOT/results/<enc>/certs/<basename>`.
6. Documented env versions (numpy 2.5.4 vs 2.5.2) in `CLAUDE.md`.
7. If the robust T becomes the shared archive key (as 008 proposes), note that the 4th component (summed depth$_{\rm CT}$) is synthesis-word noise ($\le0.6\%$ between tied programs). Here it alone decided "no improvement" in round 5 (46104 vs 46024). A stop rule counted on it should treat depth-only changes as ties.

## 8. Verdict
**PASS WITH NOTES.** Blocking: none. Notes: N1 (fix before Report 4), N2–N6.

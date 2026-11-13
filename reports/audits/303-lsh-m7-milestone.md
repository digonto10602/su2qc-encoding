# Audit 303 — LSH milestone 7 (loop-string-hadron encoding, general one-Trotter-step circuit, Lean)

- Date: 2026-11-12 · Auditor: Claude Opus 5.5 (high) · Git: HEAD `7d06d8e` (branch `merge-desktop-tracks`); working tree has other agents' uncommitted `scripts/m4_results.py`, `tests/unit/test_spinnet_m4_results_unit.py` (not LSH, not audited).
- Commit range: `9fc4d93` (acceptance-v16, lock of `tests/acceptance/m7`) `..HEAD`, restricted to `src/su2plaq/lsh/`, `src/su2plaq/{circuits,encodings}/lsh.py`, `scripts/m7_results.py`, `lean/Su2Plaq/LSH/`, `lean/Su2PlaqCert/LSH/`, `lean/lakefile.toml`, `lean/Su2Plaq.lean`, `results/lsh/`, `tests/unit/test_lsh_*` (34 files, +4900 lines).
- Plan in force: `prompts/400-lsh-m7-plan.md` (LSH track, range 400–499); methods `docs/METHODS-lsh.md` L1–L11, `docs/METHODS.md` §2, §7, §11.
- Related: `reports/research/400-lsh-model.md`; tester reports `reports/tests/400`, `401`, `402`, `403`, `406`, `407` (gate full PASS, 178/178 acceptance, 934 unit).
- Numbering note: `next-num reports/audits` gave 303 (the folder's next free number); the track range in `notes/STATUS.md` says LSH = 400–499. Coordinator to decide; the file name was not changed by hand.

## 1. What was asked
Milestone-gate step 2 for M7: look for physics or numerics errors that the passing tests would miss. Specific points: the LSH model compared with Raychowdhury–Stryker (arXiv:1912.06133, Sec. V); the claim that the LSH plaquette operator equals the route-B 6j operator; the electric term $\tfrac34\sum_c N_n(c)$; the angle conventions of $U_B$; whether the transcoder is correct and leaves the ancillas clean; whether verification uses a target independent of the circuit; how CX, fixed T and $T(\varepsilon)$ are counted; whether Lean could certify a wrong circuit; provenance; and the defaults D1–D8.

Terms used below: *transcoder* = the project's per-site reversible circuit that rewrites LSH loop-number bits into spin-network bits; *route A* = the electric-basis construction with corner singlets; *route B* = the spin-network (6j-symbol) construction; *gauge* = a diagonal $\pm1$ sign change of basis vectors; *pin* = a SHA-256 fingerprint compiled into the Lean checker that fixes which states and target it accepts.

## 2. What I did
1. Read the plan, research 400, METHODS-lsh L1–L11, METHODS §2, the six tester reports, and every LSH source file in the diff. Used graphify first (`graphify query "LSH loop-string-hadron operators plaquette transcoder"`).
2. Derived each formula in the code by hand and compared it with METHODS-lsh, term by term: ladder dressing, vertex-matrix index contraction, raise/lower consistency across each link, transcoder truth table, walk-angle equation, electric phases, Laurent exponents of the exact targets.
3. Ran my own independent check, `scratchpad/audit_lsh.py`, through `tools/run-capped taskset -c 0-1`. It builds its own label-to-code map from $\ell_{12}=j_1+j_2-j_3$ (cyclic); it does not use `inner_code_of`. It applies the production `build_UB` / `build_step` circuits (d-only, 19 qubits) to all 47 inner codes with `qiskit.quantum_info.Statevector`. It compares the result with $e^{-i\beta K_{6j}}$, where $K_{6j}$ is the route-B `exact.spinnet.K_inner`, built from 6j symbols with no LSH code involved, and with the electric phases computed from the labels as $\sum j(j+1)$.
4. Checked that the generated Lean block and `Pins.lean` equal a fresh regeneration from production code. Checked that the global gauge-sign count is a basis invariant. Checked the provenance of the results and of the committed certificate.

## 3. Checklist

| Item | Verdict | Where / evidence |
|---|---|---|
| Model: point splitting, legs, loop numbers, fluxes ($N_1=\ell_{31}+\ell_{12}$, …) | OK | `lsh/operators.py:36-60`; METHODS-lsh L2; A1 brute force over $5^8$ |
| Ladder factors and dressing $(N_n+1)^{-1/2}\mathcal L(N_p+1)^{-1/2}$, $N_p$ on input, $N_n$ on output | OK | `operators.py:63-82`. Derived from $U_L=(N_L+1)^{-1/2}M_L$ and $U_R=M_R(N_R+1)^{-1/2}$ (RS20 Eqs. (24)–(25)); locked K1 checks it against the oscillator Fock space |
| Vertex matrices and the trace contraction $\mathrm{tr}(\mathcal V_0\mathcal V_1\mathcal V_2\mathcal V_3)$ | OK | `operators.py:28-33,175-186`: `VERTEX[c][idx[c]][idx[c+1]]`. On each link, the column index of corner $c$ and the row index of corner $c{+}1$ select the same raise/lower at both ends, so the Abelian Gauss law is preserved term by term (checked by hand for all 4 links) |
| $H_B=-(\mathrm{Tr}U_P+\mathrm{h.c.})$, $K=-(P+P^{\mathsf T})$, truncation by dropping invalid codes | OK | `operators.py:185,195-197`. $\max|K_{\rm LSH}-K_{6j}|=1.8\cdot10^{-15}$ (results/lsh `extra.physics`) |
| LSH plaquette = route-B 6j operator; route A related by a $\pm1$ gauge | OK | Locked K2 and C2 (1e-12 / 1e-10). Independent check (this audit): circuit vs $e^{-i\beta K_{6j}}$, error $\le3.7\cdot10^{-15}$, global phase exactly 1, at all 3 angle pairs |
| Electric term $\tfrac34\sum_cN_n(c)$; outer row $\tfrac34(2\ell_{12}+\ell_{2v}+\ell_{v1})$ | OK | `operators.py:219-230`, `circuits/lsh.py:20-38`, `walk.py:183-186`; $j(j+1)=\tfrac34$ is linear in $N\in\{0,1\}$ (METHODS §2) |
| Time-evolution sign and Trotter order ($U_1=U_BU_E$, electric layer first; $U_2=U_E(\tfrac\alpha2)U_BU_E(\tfrac\alpha2)$) | OK | `encodings/lsh.py:174-196`, `walk.py:46-59` (layer after the transcoder, before the frame; order 2 also after frame$^{-1}$) |
| Walk angles: $\sum_r\theta_r(-1)^{p_r}=2\beta k$, since `rz`$(\theta)=e^{-i\theta Z/2}$ | OK | `walk.py:134-144`, residual must be $\le10^{-9}$ (`walk.py:160-162`). Angles $(-\tfrac72,-1,3,\tfrac32)\beta$ = Lean `lshAngles` $[-7,-2,6,3]\cdot\beta/2$ |
| Transcoder truth table and `rccx` relative phase | OK | `walk.py:21-30`. By hand, for the 5 site codes: $x\to N_n$, $z\to N_v\bmod2$, $y\to[J=1]$. `rccx` is Hermitian (its own inverse); its $-i$ phase occurs only on site `010` and is the same for both members of every bright pair (numerically exact) |
| Ancillas clean, outer register never written | OK | Flags are a monomial unitary around a walk that is diagonal in the computational basis, so their phases cancel exactly. Locked B3, G1; independent check: leak $\le1.1\cdot10^{-15}$ |
| Qubit order / endianness | OK | Register order `d`, [`o`], `a`; `walk.build` `Q()` offset (`walk.py:166-169`); `wrap_spinnet` wire map (`circuits/lsh.py:84-87`). Qiskit little-endian is consistent with `code = Σ bit_i 2^i` |
| Decoding of codes that violate the Abelian Gauss law (Gauss check) | OK | `encodings/lsh.py:103-144`; locked C1 checks all 28 942 codes with the production `gauss_residuals_coo` (min $\ge 0.5$) |
| Truncation choice ($j\le\tfrac12$, $J\le1$) | OK (see N7) | Plan §1.1; 433 states (two independent counts: Python A1 and Lean `card_states_lsh`) |
| Verification against an independent target | OK (see N9) | The circuit angles and the target share $K_{\rm LSH}$, but $K_{\rm LSH}$ is tied to route B (1e-12) and route A (1e-10) by locked K2/C2; my direct route-B check closes the loop |
| Count conventions (CX, fixed T, $T(\varepsilon)$) | OK | `rccx` = 3 CX + 4 T (METHODS §7). $U_B$: $40+6+42+6=94$ CX, $32+56=88$ T. $T(10^{-6})$: (342−88)/4 = 63.5 per rotation, consistent with gridsynth at $10^{-6}$ |
| Precision | OK | float64 / complex128 everywhere; exact Laurent targets over $\mathbb Q(i,\sqrt2,\sqrt3)$ for Lean |
| Randomness / seeds | OK | Deterministic construction; `SEEDS` recorded in `results/lsh/*.json`; test seeds fixed (20261110) |
| Tests exercise the production path | OK (see N4) | B1/B2/S1/E1 call `circuits.lsh.*` and the shared `evaluate`; K1 checks `VERTEX` against independent oscillator products (`tests/acceptance/m7/_ref.py`) |
| No hard-coded answers in source | OK | Angles are solved, not typed; Lean tables generated, and the generated block equals a fresh `_table_block(LSH())` (checked) |
| Lean `decide` theorems state what METHODS L10 says | OK (see N1) | `Counts.lean:54-64`, `Circuit.lean:47-74`; no `native_decide`/`sorry`/`admit` |
| Lean certificate soundness (can a wrong circuit be certified?) | OK (see N2, N3) | `Su2PlaqCert/LSH/Check.lean:17-63`: states and target are SHA-pinned, register sizes and the 62-qubit cap are enforced, ancilla support is rejected; tester 406 tamper set 40/41 rejected (the one accept is a reorder of state records) |
| Provenance of results | OK | `results/lsh/{UE,UB,step}.json`: `3d99f68`, `git_dirty False`; tester 407 regenerated them bit for bit at HEAD |
| Provenance of the certificate | ISSUE (NON-BLOCKING, N2) | `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` records `4733370`, a commit where the exporter existed only in the working tree |

No BLOCKING issue.

## 4. Independent check (this audit)
Command: `PYTHONPATH=src PER_JOB_MEM=4G tools/run-capped taskset -c 0-1 python /tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/audit_lsh.py` (my own code-to-label map; the target is `exact.spinnet.K_inner` (6j) and $\sum_{\rm inner} j(j+1)$ from the labels).

| Circuit | $(\alpha,\beta)$ | $\max|M-cV|$ | leak (incl. dirty ancilla) | global phase $c$ |
|---|---|---|---|---|
| $U_B$ | (0.37, 0.61) / (0.91, 0.23) / (1.70, 1.00) | $2.6\cdot10^{-15}$ / $1.1\cdot10^{-15}$ / $3.7\cdot10^{-15}$ | $\le6.7\cdot10^{-16}$ | 1 |
| step order 1 | same | $2.6\cdot10^{-15}$ / $1.2\cdot10^{-15}$ / $3.7\cdot10^{-15}$ | $\le1.1\cdot10^{-15}$ | 1 |
| step order 2 | same | $2.6\cdot10^{-15}$ / $1.0\cdot10^{-15}$ / $3.7\cdot10^{-15}$ | $\le8.9\cdot10^{-16}$ | 1 |

So the production circuit implements $e^{-i\beta K_{6j}}$ and the Trotter steps exactly. Route B's own sign convention agrees, with no gauge needed. This confirms the claim "LSH plaquette = route-B 6j operator" at the circuit level, independently of `su2plaq.lsh.operators`.

Also checked: `lean_export._table_block(LSH())` appears verbatim in `lean/Su2Plaq/LSH/Circuit.lean` (True); `render_pins_lean(compute_pins())` equals `Pins.lean` (True). Gauge: of the 128 bright pairs, 64 have opposite signs in route A and LSH; the gauge vector has 64 minus signs, all on bright states, one per such pair.

## 5. Issues and notes (all NON-BLOCKING)

**N1 — Lean `Circuit.lean` tables are not tied to the LSH rules of `Counts.lean`.** `lean/Su2Plaq/LSH/Circuit.lean:27` (`lshInnerCodes`) is a list exported from Python. `Circuit.lean` does not import `Counts.lean`, and no theorem says the list equals $\{x<4096:\ \texttt{innerOK}\ x\}$. The theorems `transcode_into_spinnet` + `transcode_injective` + `table_lengths` only prove that the 47 listed numbers transcode one-to-one onto the 47 spin-network codes. A list holding an LSH-invalid code that happens to transcode onto a spin-network code would still pass. Python A1 does pin the list today, so nothing is wrong now; the gap is in what the kernel proves. Fix (one line, `decide`): import `Su2Plaq.LSH.Counts` and add `theorem inner_codes_from_rules : lshInnerCodes = (List.range 4096).filter innerOK := by decide`. METHODS L10 should then say the tables are tied to the counted rules. Also, `lshCoupling` is compared with the spin-network table, not derived from the LSH vertex factors in Lean. That matches D8 (the oscillator derivation stays numerical); Report 7 should say so in one sentence.

**N2 — Provenance of the committed certificate.** `results/lsh/certs/lsh-step-o1-ddc1571c27bd.json` has `provenance.git_commit = 4733370`. At that commit `export_certificate`/`certify` were uncommitted (`git diff 4733370 731da36 -- src/su2plaq/lsh/lean_export.py`: +352 lines), and the certificate schema has no `git_dirty` field. The certificate's validity does not depend on this, because the checker re-verifies it from its content. But the rule "every number traceable to commit + command" is not met for this file. Also, the L3 test rewrites the file on every run (tester 406/407 note). Fix: regenerate it once on a clean commit $\ge$ `731da36` and commit it. Through the planner/consolidation (shared `su2plaq.lean.certify` is on the do-not-edit list), add `git_dirty` to the certificate provenance and make the L3 test write to a temporary directory.

**N3 — The certified circuit is not the committed result circuit, and "certified" means two things.** The Lean certificate is for `build_step(0.37, 0.61, 1, with_outer=True)` (31 qubits). `results/lsh/step.qpy` is the d-only circuit (19 qubits; tester 406 certified that one too, but it is not committed). `results/lsh/*.json` contain `"certified": true` from the numerical evaluator, not from Lean, and have no link to the certificate. Fix for Report 7: name the certified circuit and the certificate path, and call the evaluator flag "evaluator-certified" or similar. Optionally add `extra.lean = {cert_path, circuit_id, status}` to `step.json` the next time results are regenerated.

**N4 — The negative control of locked L3 never reaches the checker.** `tests/acceptance/m7/test_lsh_lean.py` (L3): a $\beta(1+10^{-6})$ circuit gives `n_a` (`non_linear_angle`) in the Python exporter, so the Lean checker's rejection path is not exercised by the locked test. Tester 406 covered it by hand (o1 vs o2 targets, $-\beta$, $U_E$ vs $U_B$ target, 40 tampered files). Suggestion for the planner at the next lock (no change now): add one checker-level negative, e.g. the order-1 circuit against the order-2 target, which must be `rejected`.

**N5 — The synthesised outer electric row is not verified.** `scripts/m7_results.py:85-109`: the Clifford+T version of the 12 outer phases is recorded as `evaluable: False` (`writes_outer`), because synthesised $R_z$ words put Hadamards on outer qubits. Only the exact-angle outer row is verified ($7.7\cdot10^{-16}$); its $T(\varepsilon)$ cost is taken from the table. This is acceptable and honestly recorded. Report 7 should state it next to that row.

**N6 — Wording: "64 gauge minus signs".** The basis-independent statement is "64 of the 128 bright pairs have opposite matrix-element sign in route A and in LSH". Which member of a pair gets the minus is a choice made by `gauge_align`. Use the pair statement in Report 7.

**N7 — Defaults D1–D8 (for Digonto).** None is physically wrong. Remarks:
- D1: with the (inner | outer) pairing, the LSH loop basis is the spin-network intertwiner basis ($J_c$ = virtual spin) written in a different binary code. That is why the LSH circuit is exactly the spin-network circuit plus the transcoder (+40 CX, +32 T). The cost comparison therefore does not carry over to the uniform Raychowdhury–Stryker split used on periodic lattices (research 400 §6: 400 non-zeros, 18 qubits touched). Report 7 should state this limit.
- D3 is not a real choice: with both physical legs at $j\le\tfrac12$, the triangle rule already forces $J\le1$. Capping $J\le\tfrac12$ would be an extra truncation that is not Kogut–Susskind (256 states).
- D7: rejecting $-\beta$ pins a basis-sign convention, not physics (METHODS-lsh L5 says this correctly).
- D2, D4, D5, D6, D8: fine as stated.

**N8 — Known cosmetic items (confirmed).**
- `tests/unit` hygiene test does not scan `lean/Su2PlaqCert/LSH/*`; my grep found them clean.
- Tamper probe 40/41: the accepted case is a benign reorder of state records.
- New: the `Su2PlaqCert/LSH/Check.lean` docstring says targets are "at base $(4,4)$", but step order 2 uses $(8,4)$ (`Pins.lean`).

**N9 — How independent the verification is.** `circuits/lsh._table()` solves the circuit angles from `K_lsh`, and `LSH.target` is built from the same `K_lsh`. The evaluator check alone would therefore not catch an error in $K_{\rm LSH}$. Independence comes from the locked chain K2/C2 ($K_{\rm LSH}=K_{6j}$ to $10^{-12}$; target equals $D^\dagger V_AD$ to $10^{-10}$) and is now also confirmed directly (§4). No action needed; Report 7 should present the evidence as that chain.

## 6. What the result means
The M7 code implements the Raychowdhury–Stryker pure-gauge LSH Hamiltonian on the point-split plaquette correctly at $j_{\max}=\tfrac12$:
- Its plaquette operator equals the route-B 6j operator entry by entry, with no gauge.
- The electric phases are $\tfrac34$ per spin-$\tfrac12$ link.
- The circuits implement $U_B$ and both Trotter orders exactly, on every inner code, with clean ancillas and global phase 1.
- The counts follow the project's conventions.
- The Lean checker cannot accept a circuit that differs from the pinned target.

The notes are about provenance, the scope of what is kernel-proved, and wording in Report 7. None affects a number.

## 7. Verdict
**PASS WITH NOTES** — no blocking issue; notes N1–N9 above.

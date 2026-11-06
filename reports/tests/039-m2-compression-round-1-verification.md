# Tester report 039: M2 compression round 1 (twelve / step), second-engine verification of the 4 new archive entries

- Date: 2026-11-06
- Git commit: fca410c (working tree has untracked round-2 briefs/programs and a modified `compress/lean/structure.json`; none of them was touched by this run)
- Prompt in force: `prompts/006-lean-formal-verification-m2-addendum.md` (plan `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §5 row 2.7; `prompts/001` §4)
- Mode: step, compression-round verification (no source, no archive, no results of the loop and no program was edited)
- Entries checked: `r01-F1-001` (CX 146, T 754), `r01-F2-001` (CX 126, T 738, global best, Lean native-certified), `r01-F3-001` (CX 132, T 1130), `r01-F4-001` (CX 126, T 1254)
- Raw numbers: `results/tests/039-m2-compression-round-1-verification.json`; scripts: `scratch/tester-039/` (gitignored)
- `~/.claude/bin/acceptance-check`: PASS ("tests/acceptance matches acceptance-v7")

## Verdict: PASS (with one robustness WARN on F1, see section 6)

All four entries are confirmed by an engine that shares no simulation or lowering code with the project evaluator. No failing correctness check.

## 1. Method (what is independent and what is not)

| piece | independent of the project evaluator? |
|---|---|
| circuit | program file `build(spec)` run through the project's worker (`compress.evaluate._build_in_subprocess`, only to turn the file into a circuit); the file sha256 equals the archived `program_sha256` for all 4 programs |
| lowering to $\{cx,h,s,s^\dagger,t,t^\dagger,x,z,r_z\}$ | own hand-written tables (`indlib.py`) for ccx, rccx, ccz, ch, crz, crx, cp, swap, cz; each table checked against the Qiskit gate matrices (max deviation $\le 4.2\times10^{-16}$ up to a global phase) |
| engine A | own numpy sparse simulator (`indsim.py`), one input at a time, branching only at $H$, prune $|a|<10^{-15}$ with the dropped norm tallied (max total $1.7\times10^{-14}$) |
| engine B | Qiskit-Aer 0.17.2 statevector on the original (macro-containing) circuit with idle qubits removed (19 to 28 qubits) |
| target | project `Encoding.target('step', α, β)` AND an independent re-derivation: $U_E$ rebuilt from the data-qubit $q_j$ bits of my own copy of the 433 states ($E_k=\tfrac34\sum q_j$), $U_B = V U_E^\dagger$ unitary to $6.7\times10^{-16}$, spectrum of $-\arg(\mathrm{eig}\,U_B)/\beta$ is exactly $\{-2^{16},-1^{96},-\tfrac12^{16},0^{177},\tfrac12^{16},1^{96},2^{16}\}$ at all three angle pairs (the Lean-proved multiplicities) |
| physical states | project `physical_vectors()` (433 states, $\Psi^\dagger\Psi-\mathbb 1=7.3\times10^{-15}$, 33 425 terms, 10 897 distinct codes); same set as pinned in the Lean certificate (section 5) |
| Gauss | project `gauss_residuals_coo` applied to MY simulated output states (decoded to link labels) |
| error metric | residual matrix $R = O - e^{i\varphi}\Psi V$ over the whole 36-qubit key space, $\varphi=\arg\mathrm{tr}(V^\dagger\Psi^\dagger O)$; total error $=\|R\|_2$, block error $\|\Psi^\dagger O-e^{i\varphi}V\|_2$, ancilla leak $\|O_{\rm anc\neq0}\|_2$, span leak $\|O_{\rm anc=0}-\Psi\Psi^\dagger O\|_2$ (explicit residuals, no Gram-square-root floor) |

Verifier sanity (negative controls, circuit F2, nominal): $r_z[3]{+}10^{-6}$ gives total error $6.2\times10^{-7}$; $r_z[7]{+}10^{-3}$ gives $5.0\times10^{-4}$; dropping the last uncompute CX into an ancilla gives ancilla leak $1.0$; dropping a T gives $0.39$; the right circuit against the target at the wrong angles gives $1.18$. The verifier therefore resolves errors far below the $10^{-10}$ tolerance.

## 2. Correctness on all 433 physical states (engine A, all 4 entries x 3 angle pairs, 12 runs)

Tolerance (spec): op-norm error $\le 10^{-10}$, Gauss $\le 10^{-10}$, ancilla leak counted as amplitude.

| check | expected | got (max over 12 runs) | tolerance | result |
|---|---|---|---|---|
| total error $\|R\|_2$, nominal $(0.37,0.61)$: F1 / F2 / F3 / F4 | 0 | $9.6\times10^{-15}$ / $1.48\times10^{-14}$ / $8.2\times10^{-15}$ / $1.14\times10^{-14}$ | $10^{-10}$ | PASS |
| total error at $(0.91,0.23)$ and $(1.7,1.0)$ | 0 | $\le 1.49\times10^{-14}$ (F2 worst) | $10^{-10}$ | PASS |
| block error $\|\Psi^\dagger O-e^{i\varphi}V\|_2$ | 0 | $\le 2.12\times10^{-14}$ | $10^{-10}$ | PASS |
| ancilla clean (leak amplitude, operator norm and worst column) | 0 | exactly 0.0 in all 12 runs | $10^{-10}$ | PASS |
| span (out-of-physical-subspace) leak | 0 | $\le 1.51\times10^{-14}$ | $10^{-10}$ | PASS |
| Gauss residual of output, project operator on my states | 0 | $\le 2.24\times10^{-15}$ (invalid-code weight 0) | $10^{-10}$ | PASS |
| outer register untouched: ops other than a CX/rccx control on an outer qubit | 0 | 0 for all 4 circuits | 0 | PASS |
| outer register untouched: change of the outer-pattern marginal of each output column, new outer patterns | 0 | $\le 2.9\times10^{-14}$, 0 new patterns | $10^{-10}$ | PASS |
| column norm $|\,\|O_k\|-1\,|$ | 0 | $\le 1.9\times10^{-14}$ | $10^{-10}$ | PASS |
| simulator pruning (own) | small | dropped norm $\le 1.74\times10^{-14}$ (total over 433 inputs) | $10^{-12}$ rel. | PASS |

Outer qubits read: F1 and F4 the 8 outer $q_m$ bits (12, 14, ..., 26) as CX controls; F2 only outer $q_j$ bits 13 and 15; F3 no outer qubit at all (inner-only operator, valid by the block-diagonal structure; the project verdict method is `inner_span`, mine is the full 433-state test and it passes). Ancillas actually used equal ancillas allocated (8, 8, 7, 6).

Project verdicts for comparison (archive): `op_norm_error` $1.05\times10^{-13}$ (F1), $8.4\times10^{-14}$ (F2), $1.87\times10^{-13}$ (F3), $1.14\times10^{-13}$ (F4); the project figure includes the certified pruning bound, mine is the measured residual, so mine is at or below theirs in every case, as expected. Re-running the project evaluator on F1 reproduced the archived number bit for bit (1.0528275501162772e-13).

## 3. Second engine: Qiskit-Aer statevector

| entry | Aer qubits | coverage | max error vs exact target | ancilla norm | result |
|---|---|---|---|---|---|
| F3 | 19 (outer idle, 7 ancillas) | ALL 433 states, 3 angle pairs (625 basis columns per pair, then the same residual analysis as engine A) | total $7.8\times10^{-15}$, $7.5\times10^{-15}$, $7.6\times10^{-15}$; Gauss $\le 7.0\times10^{-16}$ | 0 | PASS |
| F2 (best) | 22 (2 outer, 8 anc) | 10 states at nominal (6 with bright-pair weight $>0.05$, 4 with none), 4 of them at each alternate pair; states 156, 209, 1, 20, 218, 94, 263, 53, 191, 277; seed 20261106 | $6.67\times10^{-15}$ | 0 | PASS |
| F4 | 26 (8 outer, 6 anc) | 6 states nominal (incl. the 1296-term state 432), 2 at each alternate pair | $6.59\times10^{-15}$ | 0 | PASS |
| F1 | 28 (8 outer, 8 anc) | 3 states nominal (incl. state 432), 1 at each alternate pair | $7.22\times10^{-15}$ | 0 | PASS |

Limits of this check (honest scope): Aer was run on all 433 states only for F3. For F1, F2, F4 the full 433 x 3 test is engine A (own sparse simulator), and Aer covers a seeded subset (28/22/26-qubit statevectors cost 200 s / 10 s per piece / 45 s per state on a machine at load average about 30). A 1050-column full Aer run for F2 was started and abandoned after 40 min under that load. The two engines agree on every state where both ran (both at $\le 2\times10^{-14}$ from the same exact target). Aer includes the circuit's global phase, so its fitted phase is $1+0i$ to $10^{-14}$ in all runs.

## 4. Metrics recount (own lowering vs Qiskit `transpile(optimization_level=0)` vs archive)

| entry | quantity | own | Qiskit count_ops/depth | archive | result |
|---|---|---|---|---|---|
| F1 | CX / T_fixed / N_rot / depth / qubits | 146 / 128 / 10 / 106 / 36 | 146 / 128 / 10 / 106 | 146 / 128 / 10 / 106 / 36 | PASS |
| F2 | same | 126 / 112 / 10 / 130 / 36 | 126 / 112 / 10 / 130 | 126 / 112 / 10 / 130 / 36 | PASS |
| F3 | same | 132 / 120 / 16 / 95 / 35 | 132 / 120 / 16 / 95 | 132 / 120 / 16 / 95 / 35 | PASS |
| F4 | same | 126 / 112 / 18 / 169 / 34 | 126 / 112 / 18 / 169 | 126 / 112 / 18 / 169 / 34 | PASS |

Gate-name histograms (h, s, sdg, t, tdg, x, z, rz, cx) are identical in all three columns for every entry.

T-count by pygridsynth 1.2.0 on the extracted rotation angles (own call, own word-error check $\le 4.9\times10^{-7}\le\varepsilon$):

| entry | $T(10^{-6})$ own | archive | $T(10^{-10})$ own | archive | $\mathrm{depth}_{\rm CT}$ own | archive |
|---|---|---|---|---|---|---|
| F1 | 754 | 754 | 1170 | 1170 | 1168 | 1168 |
| F2 | 738 | 738 | 1154 | 1154 | 1226 | 1226 |
| F3 | 1130 | 1130 | 1770 | 1770 | 2210 | 2210 |
| F4 | 1254 | 1254 | 1968 | 1968 | 2579 | 2579 |

All 12 values agree exactly. $\mathrm{depth}_{\rm CT}$ is convention dependent: it matches the archive when a synthesised word letter $X$ is expanded to $HSSH$ and $r_z(k\pi/4)$ to $S^{\lfloor k/2\rfloor}T^{k \bmod 2}$ (the project's convention); with $X$ as one gate my depths are 1153 / 1211 / 2177 / 2540. Not a defect, but the key's third component depends on that convention.

Clifford+T circuit itself simulated (rotations replaced by my own pygridsynth words at $\varepsilon=10^{-6}$, 433 states, nominal): T-count 754 / 738 / 1130 / 1254 (equal to the metric), total error $3.20\times10^{-6}$ / $2.74\times10^{-6}$ / $5.35\times10^{-6}$ / $4.54\times10^{-6}$ against the tolerance $N_{\rm rot}\varepsilon+10^{-9}$ = $1.0\times10^{-5}$ / $1.0\times10^{-5}$ / $1.6\times10^{-5}$ / $1.8\times10^{-5}$; Gauss $\le 1.33\times10^{-7}$; ancilla leak 0 except F3 $2.8\times10^{-6}$ (inside its tolerance, as it is the synthesis error of rotations on ancilla-entangled qubits). PASS for all four.

## 5. Angle linearity and Lean certificate

Linearity: the $r_z$/$p$ angles of each circuit built at the three pairs $(0.37,0.61),(0.91,0.23),(1.7,1.0)$ satisfy $\theta_i=a_i\alpha+b_i\beta$ (no constant) with least-squares residual $4.4\times10^{-16}$ in all four, and $a_i,b_i$ are rationals with denominator $\le 8$ (deviation $\le 1.1\times10^{-15}$): the 4 electric phases are $-\tfrac34\alpha$, the others pure multiples of $\beta$. For F2 (non-Clifford rotations): $(a,b)=(-\tfrac34,0)\times4$, then $b\in\{-\tfrac14,\tfrac34,-\tfrac34,-\tfrac34,\tfrac32,-\tfrac12\}$. PASS (all four).

Lean certificate of the global best `r01-F2-001` (`compress/lean/certs/step-o1-d8909cbbbc88.json`):

| check | expected | got | result |
|---|---|---|---|
| re-run checker `lean/.lake/build/bin/su2plaq_cert check <cert>` | ACCEPT | `ACCEPT`, 75 s wall (archive: 85 s) | PASS |
| checker binary sha256 | archive `befbd27e...bf5` | `befbd27e3ed4e8229f11320189441597e04c89c7bf7746cf93f1c55de261bfd5` | PASS |
| all `lean/Su2PlaqCert/*.lean` older than the binary (checker up to date); lean tree clean in git | yes | yes (only `Su2Plaq/Rewrites.lean`, not part of the checker, is newer) | PASS |
| `circuit_id` / `program_sha256` field = sha256 of the gate list | equal | `d8909cbbbc886...` equal; note this is the hash of the exported gate list, NOT of the program file | PASS |
| `Pins.lean` `statesSha256` vs recomputation (`pins.compute_pins`) | equal | equal | PASS |
| `Pins.lean` target pins UE:1, UB:1, step:1, step:2 vs recomputation | equal | all 4 equal | PASS |
| sha256 of the cert's 433 states under MY canonical writer vs Pins.lean | equal | `45be4cd3d73d5886...` equal | PASS |
| cert states vs my float physical vectors | same support, equal | 433 states, same support, max $|\Delta|=2.8\times10^{-16}$ | PASS |
| cert exact target blocks evaluated at nominal vs float $V$ | equal | $5.6\times10^{-16}$ (cert phase factor $=1$) | PASS |
| cert gate list vs MY lowering of the program's circuit, gate by gate | identical | 526 gates vs 526; names, qubits identical; the 10 angle gates $m_\alpha\alpha/d_\alpha+m_\beta\beta/d_\beta$ equal my angles to $0.0$ at all 3 pairs (`d_alpha=4`, `d_beta=8`) | PASS |
| program file sha256 | archive `37e6e5d9...` | `37e6e5d968dddeb58dcb1307bc0d923c9d03a6a63ae570e2e12ec0b96baadeb7` | PASS |
| Lean checker rejects broken certificates (4 mutants, hash field repaired) | REJECT | state coefficient changed: `REJECT state 5 is not normalised` (7 s); one $r_z$ exponent +2: `REJECT state 0 differs from the target` (10 s); one T deleted: same (9 s); one CX control/target swapped: same (8 s) | PASS |

Chain of evidence that the certificate is for exactly this program: program sha (file) matches the archive; the program rebuilt by me lowers to the identical 526-gate list as the certificate with identical angles at three pairs; the checker accepts the certificate, whose 433 input states and exact target are pinned by SHA-256 inside the binary and agree with my independent numbers. The archive does not store the program-file sha inside the certificate (only the gate-list hash); the link program to certificate is therefore my gate-by-gate comparison, not a field in the file (suggestion: store `program_sha256` of the source in the certificate provenance).

## 6. F1 evaluation wall time vs the 300 s budget: WARN (load dependent)

| measurement | value | budget |
|---|---|---|
| archived `wall_s` of F1 (build + nominal + 2 alternate verdicts + metrics, sequential) | 241.5 s (F4 168.9 s, F3 11.9 s, F2 6.6 s) | 300 s per nominal verdict, 120 s per alternate verdict (`evaluate_circuit`: `min(120, eval_budget_s)`) |
| implied per verdict from the archive | about 78 s | 300 / 120 s |
| my re-run via `_one_verdict`, machine at load average 38 on 12 cpus | `EvalTimeout` at 300 s (nominal) | 300 s |
| my re-run of `evaluator.evaluate` without a limit, same load | wall 373 s / 375 s / 293 s (nominal, alt1, alt2), CPU 127 / 126 / 127 s per verdict, $\text{op\_norm\_error}=1.0528\times10^{-13}$ (identical to the archive) | 300 / 120 / 120 s |

So F1 is valid and its numbers reproduce exactly, but it consumes 80 % of the 300 s budget in total and its alternate-angle verdicts need about 65 % of their 120 s cap on a quiet machine; it fails the caps (`eval_budget`) as soon as the machine is oversubscribed (the proposers running round 2 pushed the load to 30 to 38). This is not a correctness failure. Consequence for the loop: any re-evaluation of F1 (the pre-gate archive refresh under the final evaluator, or a re-run of round 1) must be done on a quiet machine, otherwise F1 will be rejected for a reason unrelated to the circuit. F4 (169 s) has the same exposure to a smaller degree. My own sparse simulator needs about 25 CPU-s per angle pair for F1, so the project's engine is about 5 times slower than necessary on these circuits (a speed note for the builder, not a correctness issue).

## 7. Summary table

| group | checks | passed | failed | pending |
|---|---|---|---|---|
| engine A, 4 entries x 3 pairs x 10 metrics | 120 | 120 | 0 | 0 |
| Aer second engine | 4 entries | 4 | 0 | 0 |
| counts / depth / T(1e-6, 1e-10) / depth_CT | 4 x 7 | 28 | 0 | 0 |
| Clifford+T circuit simulation | 4 | 4 | 0 | 0 |
| angle linearity | 4 | 4 | 0 | 0 |
| Lean certificate (F2) | 12 | 12 | 0 | 0 |
| F1 wall time | 1 | 0 | 0 | 1 WARN (load dependent, not a failure) |
| acceptance-check | 1 | 1 | 0 | 0 |

Not run (out of scope for this task, as briefed): the unit and acceptance suites (no source changed since the last tester report 038).

## 8. Commands (reproducible)

```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding   # scripts in scratch/tester-039/, run from a scratch dir
python build_all.py                          # build 3 circuits per program (nominal + 2 alternate pairs), compare program sha
python chk_tables.py; python counts.py       # own lowering tables vs Qiskit matrices; counts vs Qiskit transpile and archive
python target_chk.py                         # independent target / spectrum check
python verify.py r01-F1-001,r01-F2-001,r01-F3-001,r01-F4-001   # own sparse engine, 433 states x 3 pairs
python aer_chk.py col r01-F3-001; python aer_chk.py piece r01-F4-001; python aer_chk.py piece r01-F1-001 3 1; python aer_chk.py piece r01-F2-001 10 4 small
python synth_chk.py; python synth_sim.py     # pygridsynth T, linearity, depth_CT, Clifford+T simulation
python negctl.py; python lean_checks.py; python cert_vs_prog.py
lean/.lake/build/bin/su2plaq_cert check compress/lean/certs/step-o1-d8909cbbbc88.json     # ACCEPT
python f1_timing2.py                         # F1 verdict wall/CPU time
~/.claude/bin/acceptance-check
```
Seeds: Aer subset selection `numpy.random.default_rng(20261106)`; own simulator, Aer and pygridsynth are deterministic.

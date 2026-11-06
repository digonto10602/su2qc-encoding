# Tester report 040: M2 compression round 2 (twelve / step), second-engine verification of the 4 new archive entries

- Date: 2026-11-06
- Git commit: 418de65 (working tree: only untracked round-3 briefs under `compress/briefs/twelve/`; no source, archive, result of the loop or program was edited by this run)
- Prompt in force: `prompts/006-lean-formal-verification-m2-addendum.md` (plan `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §5 row 2.7; `prompts/001` §4)
- Mode: step, compression-round verification. Source unchanged since the last tester report (`git diff fca410c HEAD -- src tests lean` is empty), so unit and acceptance suites were not re-run; `~/.claude/bin/acceptance-check` was.
- Related: reports/tests/039 (round 1, same method; scripts copied from `scratch/tester-039/` to `scratch/tester-040/`, gitignored).
- Entries: `r02-F1-002` (CX 124, T 1114), `r02-F2-002` (CX 120, T 912, new global best, Lean native-certified), `r02-F3-002` (CX 124, T 1114), `r02-F4-002` (CX 121, T 738)
- Raw numbers: `results/tests/040-m2-compression-round-2-verification.json`
- `~/.claude/bin/acceptance-check`: PASS ("tests/acceptance matches acceptance-v7")

## Verdict: PASS (0 failures; 1 informational finding: F1-002 and F3-002 are near-duplicates)

All four entries are confirmed by an engine that shares no simulation or lowering code with the project evaluator, on all 433 physical states at three angle pairs. The global best $r02\text{-}F2\text{-}002$ was additionally run on Qiskit-Aer for all 433 states at all three pairs, and its Lean certificate is re-checked and tied gate by gate to the program.

## 1. Method (same as report 039)

| piece | independent of the project evaluator? |
|---|---|
| circuit | program file `build(spec)` through the project's worker (`compress.evaluate._build_in_subprocess`, only to get a circuit); sha256 of each program file equals the archived `program_sha256` (all 4 True) |
| lowering to $\{cx,h,s,s^\dagger,t,t^\dagger,x,z,r_z\}$ | own hand-written tables (`indlib.py`) for ccx, rccx, ccz, ch, crz, crx, cp, swap, cz; checked against Qiskit gate matrices (cx 0, p $1.2\times10^{-16}$, rz 0 up to global phase) |
| engine A | own numpy sparse simulator, one input at a time, prune $|a|<10^{-15}$ with the dropped norm tallied |
| engine B | Qiskit-Aer 0.17.2 statevector on the original (macro-containing) circuit, idle qubits removed, one run per distinct basis column (625 for F4, 1050 for the others; covers all 433 states) |
| target | project `Encoding.target('step',\alpha,\beta)` and an independent re-derivation: $U_B$ unitary to $6.7\times10^{-16}$ and spectrum of $-\arg\,\mathrm{eig}(U_B)/\beta$ is exactly $\{-2^{16},-1^{96},-\tfrac12^{16},0^{177},\tfrac12^{16},1^{96},2^{16}\}$ at all three pairs; $\Psi^\dagger\Psi-\mathbb 1=7.3\times10^{-15}$ (433 states, 33 425 terms) |
| error metric | residual $R=O-e^{i\varphi}\Psi V$ on the whole 35-qubit key space: total $\|R\|_2$, block $\|\Psi^\dagger O-e^{i\varphi}V\|_2$, ancilla leak $\|O_{\rm anc\ne0}\|_2$, span leak $\|O_{\rm anc=0}-\Psi\Psi^\dagger O\|_2$ |
| Gauss | project `gauss_residuals_coo` applied to my simulated output states (decoded to link labels) |

Verifier sanity (negative controls on the F2-002 circuit, nominal angles): $r_z[3]+10^{-6}$ gives total error $6.2\times10^{-7}$; $r_z[7]+10^{-3}$ gives $5.0\times10^{-4}$; dropping the last CX into an ancilla gives ancilla leak $1.0$; dropping one T gives $0.39$; the right circuit against the target of the wrong angles gives $1.18$. The verifier resolves errors well below the $10^{-10}$ tolerance.

Angle pairs $(\alpha,\beta)$: $(0.37,0.61)$ nominal, $(0.91,0.23)$, $(1.7,1.0)$. Tolerances (spec): op-norm error $\le10^{-10}$, Gauss $\le10^{-10}$, ancilla leak counted as amplitude.

## 2. Correctness on all 433 physical states, engine A (4 entries $\times$ 3 pairs = 12 runs)

| check | expected | got (max over the 12 runs; per entry in section 3) | tolerance | result |
|---|---|---|---|---|
| total error $\|R\|_2$ | 0 | $1.52\times10^{-14}$ (F4 nominal); F1 $\le1.44\times10^{-14}$, F2 $\le1.45\times10^{-14}$, F3 $\le1.44\times10^{-14}$, F4 $\le1.52\times10^{-14}$ | $10^{-10}$ | PASS |
| block error | 0 | $\le2.13\times10^{-14}$ | $10^{-10}$ | PASS |
| ancilla leak (operator norm and worst column) | 0 | exactly 0.0 in all 12 runs | $10^{-10}$ | PASS |
| span (out-of-physical-subspace) leak | 0 | $\le8.9\times10^{-15}$ | $10^{-10}$ | PASS |
| Gauss residual of the output | 0 | $\le1.68\times10^{-15}$ (weight on undecodable codes $\le5.5\times10^{-15}$, rounding level) | $10^{-10}$ | PASS |
| outer register untouched: ops that are not a CX/rccx control on an outer qubit | 0 | 0 for all 4 circuits | 0 | PASS |
| outer register untouched: change of the outer-pattern marginal of each output column, new outer patterns | 0 | $\le3.0\times10^{-14}$, 0 new patterns | $10^{-10}$ | PASS |
| column norm $|\,\|O_k\|-1\,|$ | 0 | $\le1.9\times10^{-14}$ | $10^{-10}$ | PASS |
| own simulator pruning (dropped $\ell_2$) | small | $\le3.0\times10^{-14}$ | $10^{-12}$ | PASS |

Outer qubits read (as CX controls only): F1, F2, F3 read outer $q_j$ bits 13 and 15; F4 reads none. Ancillas used: F1 7, F2 5, F3 7, F4 5 (qubits 28 to 34 / 28 to 32). Project verdicts for comparison (archive, certified, `physical` method): F2 nominal $9.98\times10^{-14}$; the project figure contains the certified pruning bound, mine is the measured residual, so mine is at or below it as expected.

## 3. Second engine: Qiskit-Aer statevector (all 433 states)

| entry | Aer qubits (outer read, ancillas) | pairs covered, all 433 states | total error | block | leak | span | Gauss | outer marg. | result |
|---|---|---|---|---|---|---|---|---|---|
| F4 | 17 (0, 5) | all 3 | $6.76$, $6.88$, $7.19\times10^{-15}$ | $\le1.75\times10^{-14}$ | 0 | $\le1.15\times10^{-14}$ | $\le1.49\times10^{-15}$ | $\le1.4\times10^{-14}$ | PASS |
| F2 (best) | 19 (2, 5) | all 3 | $6.21$, $5.94$, $8.19\times10^{-15}$ | $\le1.71\times10^{-14}$ | 0 | $\le1.19\times10^{-14}$ | $\le1.47\times10^{-15}$ | $\le1.1\times10^{-14}$ | PASS |
| F3 | 21 (2, 7) | (0.37,0.61), (0.91,0.23) (see note) | $6.07$, $6.47\times10^{-15}$ | $\le1.73\times10^{-14}$ | 0 | $\le1.17\times10^{-14}$ | $\le1.89\times10^{-15}$ | $\le1.2\times10^{-14}$ | PASS |
| F1 | 21 (2, 7) | (0.37,0.61), (0.91,0.23) (see note) | $6.26$, $6.41\times10^{-15}$ | $\le1.71\times10^{-14}$ | 0 | $\le1.16\times10^{-14}$ | $\le1.87\times10^{-15}$ | $\le1.2\times10^{-14}$ | PASS |

Note: for F1 and F3 the Aer column method costs about 45 min per pair (21 qubits, 1050 columns, 3000 s measured at nominal). The third pair $(1.7,1.0)$ for these two is covered by engine A only (total error $1.43\times10^{-14}$ and $1.41\times10^{-14}$); the Aer runs for it were stopped after about 55 min (not finished) at hand-off, so that pair has no second-engine confirmation (engine A passes it, and F1/F3 differ from each other by two CX only, while the other 2 pairs and the F2/F4 circuits agree between engines). The two engines agree on every state where both ran (both at $\le2\times10^{-14}$ from the same exact target). The column method uses one run per distinct (inner code, read outer bits) pair, so the 433-state test is exact, not a sample.

## 4. Metrics recount (own lowering vs Qiskit `transpile(optimization_level=0)` vs archive)

| entry | quantity | own | Qiskit | archive | result |
|---|---|---|---|---|---|
| F1 | CX / $T_{\rm fixed}$ / $N_{\rm rot}$ / depth / qubits | 124 / 104 / 16 / 142 / 35 | 124 / 104 / 16 / 142 | 124 / 104 / 16 / 142 / 35 | PASS |
| F2 | same | 120 / 104 / 13 / 142 / 33 | 120 / 104 / 13 / 142 | 120 / 104 / 13 / 142 / 33 | PASS |
| F3 | same | 124 / 104 / 16 / 142 / 35 | 124 / 104 / 16 / 142 | 124 / 104 / 16 / 142 / 35 | PASS |
| F4 | same | 121 / 112 / 10 / 165 / 33 | 121 / 112 / 10 / 165 | 121 / 112 / 10 / 165 / 33 | PASS |

T-count by pygridsynth 1.2.0 on the extracted rotation angles (own call; own word-error check $\le4.91\times10^{-7}\le\varepsilon=10^{-6}$ and $\le4.97\times10^{-11}\le10^{-10}$):

| entry | $T(10^{-6})$ own | archive | $T(10^{-10})$ own | archive | depth$_{\rm CT}$ own | archive |
|---|---|---|---|---|---|---|
| F1 | 1114 | 1114 | 1754 | 1754 | 2195 | 2195 |
| F2 | 912 | 912 | 1456 | 1456 | 1671 | 1671 |
| F3 | 1114 | 1114 | 1754 | 1754 | 2196 | 2196 |
| F4 | 738 | 738 | 1154 | 1154 | 1269 | 1269 |

All 12 values agree exactly (depth$_{\rm CT}$ with the project convention $X\to HSSH$, $r_z(k\pi/4)\to S^{\lfloor k/2\rfloor}T^{k\bmod 2}$; with $X$ as a single gate: 2162 / 1650 / 2163 / 1254).

Clifford+T circuit simulated (rotations replaced by my own pygridsynth words at $\varepsilon=10^{-6}$, 433 states, nominal angles, engine A):

| entry | T count | total error | tolerance $N_{\rm rot}\varepsilon+10^{-9}$ | ancilla leak | Gauss | result |
|---|---|---|---|---|---|---|
| F1 | 1114 | $4.39\times10^{-6}$ | $1.60\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |
| F2 | 912 | $3.53\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| F3 | 1114 | $4.44\times10^{-6}$ | $1.60\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |
| F4 | 738 | $3.10\times10^{-6}$ | $1.00\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |

(The project's own synthesised verdict for F2, `round-002.json`: error $4.71\times10^{-6}\le1.3001\times10^{-5}$, certified.)

## 5. Angle linearity and Lean certificate

Linearity: the $r_z$/$p$ angles of each circuit at the three pairs satisfy $\theta_i=a_i\alpha+b_i\beta$ (no constant) with least-squares residual $4.4\times10^{-16}$ in all four; $a_i,b_i$ are rationals with denominator $\le8$ (deviation $\le2.4\times10^{-15}$). Electric phases $(a,b)=(-\tfrac34,0)\times4$ in all four. Non-Clifford magnetic coefficients $b$: F2 $=\{-\tfrac12,\tfrac34,-\tfrac34,\tfrac34,-\tfrac14,\tfrac14,-\tfrac34,\tfrac34,-\tfrac14\}$; F4 $=\{-\tfrac14,\tfrac34,-\tfrac34,-\tfrac34,\tfrac32,-\tfrac12\}$; F1 and F3 $=\{-\tfrac58,\tfrac14,-\tfrac34,\tfrac38\,(\times4),-\tfrac34,-\tfrac34,\tfrac38\,(\times3)\}$ (per-gate list in the results JSON, key `synth`). PASS (all four).

Lean certificate of the new global best `r02-F2-002` (`compress/lean/certs/step-o1-c67fe2731d0e.json`):

| check | expected | got | result |
|---|---|---|---|
| re-run `lean/.lake/build/bin/su2plaq_cert check <cert>` | ACCEPT | `ACCEPT`, 74 s wall (archive: 78.8 s) | PASS |
| checker binary sha256 | archive `befbd27e...` | `befbd27e3ed4e8229f11320189441597e04c89c7bf7746cf93f1c55de261bfd5` | PASS |
| `Su2PlaqCert/*.lean` older than the binary; lean tree clean in git | yes | yes (only `Su2Plaq/Rewrites.lean`, not part of the checker, is newer) | PASS |
| `program_sha256` field = sha256 of the exported gate list; `circuit_id` suffix | equal | equal (`c67fe2731d0e...`) | PASS |
| `Pins.lean` `statesSha256` and targets UE:1, UB:1, step:1, step:2 vs recomputation (`pins.compute_pins`) | equal | all equal | PASS |
| sha256 of cert's 433 states under my canonical writer vs Pins.lean | equal | `45be4cd3d73d5886...` equal | PASS |
| cert states vs my float physical vectors | same support, equal | same support, max $|\Delta|=2.8\times10^{-16}$ | PASS |
| cert exact target at nominal vs float $V$ | equal | $5.6\times10^{-16}$ (cert phase factor 1) | PASS |
| exporter data mismatch (`_exporter_mismatch`) | none | None | PASS |
| cert gate list vs MY lowering of the program's circuit, gate by gate | identical | 511 gates vs 511; 0 name mismatches, 0 qubit mismatches; the 13 angle gates ($4p+9r_z$) $m_\alpha\alpha/d_\alpha+m_\beta\beta/d_\beta$ equal my angles to $1.6\times10^{-15}$, $5.9\times10^{-16}$, $2.6\times10^{-15}$ at the 3 pairs | PASS |
| program file sha256 | archive `9e5d9c55...` | `9e5d9c55ef7e60189bf896a2d4039c92946eb5d1794f38a3d3e07fe4b67cc26f` | PASS |
| Lean checker rejects broken certificates (5 mutants, hash field repaired) | REJECT | state coefficient $\tfrac12\to\tfrac34$: `REJECT state 5 is not normalised` (1 s); $r_z$ exponent $+2$: `REJECT state 0 differs from the target` (3 s); one T deleted: same (4 s); one CX control/target swapped: same (5 s); one CX deleted: same (3 s) | PASS |

Chain of evidence that the certificate is for exactly this program: the program-file sha matches the archive; the program rebuilt by me lowers to the identical 511-gate list as the certificate with identical angles at three pairs; the checker accepts the certificate, whose 433 input states and exact target are pinned by SHA-256 inside the binary and agree with my independent numbers. Same caveat as report 039: the certificate stores the gate-list hash, not the program-file sha, so the program-to-certificate link is my gate-by-gate comparison (STATUS known issue 2.L8).

## 6. F1-002 vs F3-002: genuinely different circuits, or duplicates?

| comparison | result |
|---|---|
| program file sha256 | different (`5c1e97cf15c1...` vs `86ff9c4bfa87...`) |
| program-level gate lists (302 gates each: 82 h, 66 cx, 32 x, 28 s, 28 sdg, 16 ch, 14 rccx, 12 rz, 8 t, 8 tdg, 4 p, 4 z) | equal in 300 of 302 positions; they differ only at positions 139 and 166, where F1 has `cx(5,11)` and F3 has `cx(8,11)` (the CX before and after the Walsh walk) |
| lowered 510-gate lists | not equal (same two CX); $r_z$ target qubits and the multiset of 16 angles are identical |
| metrics | identical CX 124, $T_{\rm fixed}$ 104, $N_{\rm rot}$ 16, depth 142, qubits 35, T(1e-6) 1114, T(1e-10) 1754; depth$_{\rm CT}$ 2195 vs 2196 |
| both correct | yes (sections 2, 3) |

Conclusion: not byte-identical, but a two-gate variant of the same circuit (the sandwiching CX has control 5 vs 8 onto qubit 11; the archive summaries describe this as multiplexer variable $t_1\oplus t_3$ vs $t_2\oplus t_3$, which I did not independently decode). Effectively one design counted twice in the archive; the second one adds no new cost point (it only loses the elite cell tie on depth$_{\rm CT}$). Informational, not a failure.

## 7. Summary table

| group | checks | passed | failed | pending |
|---|---|---|---|---|
| engine A, 4 entries $\times$ 3 pairs $\times$ 9 metrics | 108 | 108 | 0 | 0 |
| Aer second engine (entry $\times$ pair runs) | 10 (F2 3, F4 3, F1 2, F3 2) | 10 | 0 | F1/F3 pair (1.7,1.0) on Aer only (engine A PASS) |
| counts / depth / T(1e-6, 1e-10) / depth$_{\rm CT}$ | 4 $\times$ 7 | 28 | 0 | 0 |
| Clifford+T circuit simulation | 4 | 4 | 0 | 0 |
| angle linearity | 4 | 4 | 0 | 0 |
| Lean certificate (F2) | 13 | 13 | 0 | 0 |
| negative controls (verifier) | 5 | 5 | 0 | 0 |
| duplicate analysis F1/F3 | 1 | 1 (informational) | 0 | 0 |
| acceptance-check | 1 | 1 | 0 | 0 |

New failures vs report 039: none. The F1 wall-time warning of report 039 is gone: evaluation walls in `round-002.json` are 6.7 to 12.1 s per entry (none of the round-2 circuits reads 8 outer bits).

## 8. Commands (reproducible)

```
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd /home/digimonk/Projects/su2qc-encoding/scratch/tester-040      # scripts adapted from tester-039 (ids and cert path only)
python build_all.py                      # program sha vs archive, circuits at 3 pairs
python chk_tables.py; python counts.py   # own lowering tables vs Qiskit matrices; counts vs Qiskit transpile and archive
python target_chk.py                     # independent target / spectrum
python verify.py r02-F2-002,r02-F4-002,r02-F3-002,r02-F1-002     # engine A, 433 states x 3 pairs
python aer_chk.py col r02-F4-002; python aer_chk.py col r02-F2-002; python aer_chk.py col r02-F3-002; python aer_chk.py col r02-F1-002
python synth_chk.py; python synth_sim.py # pygridsynth T, linearity, depth_CT, Clifford+T simulation
python negctl.py; python lean_checks.py; python cert_vs_prog.py; python mut.py
(cd /home/digimonk/Projects/su2qc-encoding && lean/.lake/build/bin/su2plaq_cert check compress/lean/certs/step-o1-c67fe2731d0e.json)   # ACCEPT
~/.claude/bin/acceptance-check
```
No random seeds are involved (all engines and pygridsynth are deterministic; Aer column method is exhaustive).

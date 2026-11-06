# Tester report 041: M2 milestone gate (mode `full`), plus second-engine verification of the round-3, 4, 5 archive entries

- Date: 2026-11-06
- Git commit: 74598e7 (working tree before my run: clean. After the runs: `compress/lean/structure.json` modified by the acceptance tests (provenance only, see section 6) and untracked `results/compress/twelve/summary.json` (written by `report`); no source, test, archive or program file was edited by me)
- Prompt in force: `prompts/006-lean-formal-verification-m2-addendum.md` (plan `prompts/002-m0-m2-foundation-twelve-qubit-compression.md` §5; locked tests `acceptance-v7`)
- Mode: full (milestone gate M2). PENDING would count as FAIL; there was none.
- Related: reports/tests/039 and 040 (same verification method; their scripts were copied from `scratch/tester-040/` to `scratch/tester-m2gate/`, gitignored)
- Raw numbers: `results/tests/041-m2-gate-full.json` (per-entry engine-A, Aer, counts, synthesis, near-duplicate and Lean data; commit, angles and seeds recorded in it)

## Verdict: PASS (0 failures, 0 pending; 3 informational findings, none blocking)

## 1. Gate

Commands (env: `conda activate coding`, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`; the machine was shared, load average 6 to 28 while my verification jobs ran in parallel, so all wall times are inflated):

```
pytest --collect-only -q tests/acceptance
python tools/check_lock.py ; ~/.claude/bin/acceptance-check
pytest -n 6 tests/acceptance -p no:cacheprovider -q --durations=15     # m0, m1, m2, slow included
pytest -n 6 tests/unit        -p no:cacheprovider -q
cd lean && lake build
```

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| collect `tests/acceptance` | clean, all tests | 102 tests collected, 0.68 s, no errors | exact | PASS |
| `python tools/check_lock.py` | LOCK OK | `LOCK OK` | exact | PASS |
| `~/.claude/bin/acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v7` (run before the suite and again after all my runs) | exact | PASS |
| acceptance m0 + m1 + m2, all incl. slow, pending = fail | 102 pass | 102 passed, 0 failed, 0 skipped, 0 xfailed, 96 warnings; wall 543.65 s with `-n 6` (545 s measured outside) | 0 failures | PASS |
| `test_archive_best_valid_and_not_worse_than_seed` | pass | passed (50.8 s); archive best `r05-F2-005` has `evaluator_sha256` = current `code_hash()` = `0bd7e7d91d9d...` | exact | PASS |
| `test_archive_best_lean_status_recorded` | pass | passed; `r05-F2-005` lean status `certified`, checker sha256 `befbd27e...` | exact | PASS |
| unit suite `tests/unit` | all pass | 396 passed, 0 failed; wall 752 s (12 min 32 s) under heavy load | 0 failures | PASS |
| `lake build` | success, no sorry | `Build completed successfully (9095 jobs)`; 0 occurrences of "sorry" in build output; source grep for `sorry`/`axiom `: none (only a `native_decide` mention in a doc comment). Wall 13 s (incremental: modules replayed from the existing `.lake` cache; a clean rebuild was not repeated, last clean build in reports/tests/028: 379 s) | success | PASS |

Slowest acceptance tests (wall, `-n 6`, loaded machine): `test_lean_theorem_file_general` 309 s, `test_M1_P1_paulo_qpy_verifies` 291 s, `test_round_records_lean_certificate` 279 s, `test_seed_import_declared[paulo34]` 267 s, `test_M1_O1_outer_dont_care_table` 234 s, `test_report_table_from_results` 199 s.

## 2. Second-engine verification of the round-3, 4, 5 entries (9 entries)

Method identical to reports 039 and 040:

| piece | independent of the project evaluator? |
|---|---|
| circuit | program file `build(spec)` through the project's worker `compress.evaluate._build_in_subprocess` (only to obtain the circuit); sha256 of every program file equals the archived `program_sha256` (9 of 9 True) |
| lowering to $\{cx,h,s,s^\dagger,t,t^\dagger,x,z,r_z\}$ | own tables (`indlib.py`) for ccx, rccx, ccz, ch, crz, crx, cp, swap, cz |
| engine A | own numpy sparse simulator, one physical input at a time, prune $<10^{-15}$ with dropped norm tallied |
| engine B | Qiskit-Aer 0.17.2 statevector on the original macro-containing circuit, idle qubits removed, one run per distinct (inner code, read outer bits) pair, which covers all 433 states exactly |
| target | project `Encoding.target('step',\alpha,\beta)`; re-derived check below |
| metric | residual $R=O-e^{i\varphi}\Psi V$: total $\|R\|_2$, block, ancilla leak (operator norm), span leak, Gauss residual of the output, outer register untouched |

Target check (own script `target_chk.py`): $\Psi^\dagger\Psi-\mathbb 1=7.3\times10^{-15}$ (433 states, 33 425 terms, 10 897 distinct codes); $V^\dagger V-\mathbb 1\le6.7\times10^{-16}$ and $U_B$ unitarity $\le6.7\times10^{-16}$ at the 3 angle pairs; the spectrum of $-\arg\operatorname{eig}(U_B)/\beta$ is $\{-2^{16},-1^{96},-\tfrac12^{16},0^{177},\tfrac12^{16},1^{96},2^{16}\}$ at all three pairs.

Angle pairs $(\alpha,\beta)$: $(0.37,0.61)$, $(0.91,0.23)$, $(1.7,1.0)$. Tolerance in the spec: op-norm error $\le10^{-10}$, Gauss $\le10^{-10}$, ancilla leak counted as amplitude.

### 2a. Correctness on all 433 states, both engines, 3 angle pairs (9 entries x 3 pairs = 27 runs per engine)

| check | expected | engine A (max over 27 runs) | Aer (max over 27 runs) | tolerance | result |
|---|---|---|---|---|---|
| total error $\|R\|_2$ | 0 | $1.48\times10^{-14}$ | $8.19\times10^{-15}$ | $10^{-10}$ | PASS |
| block error | 0 | $2.10\times10^{-14}$ | $1.74\times10^{-14}$ | $10^{-10}$ | PASS |
| ancilla leak (operator norm, and worst column) | 0 | exactly 0.0 | exactly 0.0 | $10^{-10}$ | PASS |
| span (out of physical subspace) leak | 0 | $1.44\times10^{-14}$ | $1.23\times10^{-14}$ | $10^{-10}$ | PASS |
| Gauss residual of output | 0 | $1.7\times10^{-15}$ (weight on undecodable codes $\le5.6\times10^{-15}$) | $1.8\times10^{-15}$ | $10^{-10}$ | PASS |
| outer register untouched: ops that are not a control on an outer qubit | 0 | 0 in all 9 circuits | n/a | 0 | PASS |
| outer register untouched: change of the outer-pattern marginal, new outer patterns | 0 | $\le2.8\times10^{-14}$, 0 new patterns | $\le1.2\times10^{-14}$ | $10^{-10}$ | PASS |
| column norm deviation | 0 | $\le1.9\times10^{-14}$ | $\le9.0\times10^{-15}$ | $10^{-10}$ | PASS |
| own sparse simulator dropped $\ell_2$ | small | $\le3.0\times10^{-14}$ | n/a | $10^{-12}$ | PASS |

Per entry (maxima over the 3 pairs; Aer covers all 433 states at every pair; "read outer" = outer qubits that appear as CX/rccx controls):

| entry | CX / T(1e-6) | qubits (Aer simulated, read outer) | Aer runs | engine A total / block | Aer total / block | Gauss A / Aer |
|---|---|---|---|---|---|---|
| r03-F2-003 | 119 / 912 | 32 (18, 13 15) | 1050 | 1.47e-14 / 2.10e-14 | 8.19e-15 / 1.74e-14 | 1.1e-15 / 1.5e-15 |
| r03-F3-003 | 112 / 912 | 33 (19, 13 15) | 1050 | 1.31e-14 / 2.00e-14 | 6.03e-15 / 1.69e-14 | 1.2e-15 / 6.7e-16 |
| r03-F4-003 | 119 / 912 | 32 (16, none) | 625 | 1.48e-14 / 2.09e-14 | 6.77e-15 / 1.71e-14 | 1.4e-15 / 1.8e-15 |
| r04-F2-004 | 111 / 912 | 32 (18, 13 15) | 1050 | 1.33e-14 / 2.04e-14 | 6.03e-15 / 1.70e-14 | 1.2e-15 / 6.4e-16 |
| r04-F3-004 | 111 / 912 | 32 (18, 13 15) | 1050 | 1.33e-14 / 2.03e-14 | 6.38e-15 / 1.70e-14 | 1.2e-15 / 6.7e-16 |
| r04-F4-004 | 111 / 912 | 32 (16, none) | 625 | 1.33e-14 / 1.99e-14 | 6.47e-15 / 1.71e-14 | 1.7e-15 / 7.8e-16 |
| **r05-F2-005 (best)** | **111 / 912** | **31 (19, 13 15 21 23)** | **1764** | **1.21e-14 / 1.93e-14** | **6.26e-15 / 1.66e-14** | **1.6e-15 / 6.6e-16** |
| r05-F3-005 | 112 / 1112 | 31 (17, 13 15) | 1050 | 1.31e-14 / 2.00e-14 | 6.62e-15 / 1.68e-14 | 1.3e-15 / 7.0e-16 |
| r05-F4-005 | 111 / 912 | 32 (16, none) | 625 | 1.31e-14 / 2.00e-14 | 6.75e-15 / 1.70e-14 | 1.1e-15 / 8.0e-16 |

All 9 PASS. The best circuit reads 4 outer bits (13, 15, 21, 23), all as controls; the other entries 0 or 2. Ancillas: 3 (r05-F2-005, r05-F3-005), 4 or 5 for the others.

### 2b. Negative controls (verifier resolves small errors), on the global best `r05-F2-005`, nominal angles

| mutation | total error | note |
|---|---|---|
| $r_z[3]+10^{-6}$ | $6.2\times10^{-7}$ | resolved (tolerance $10^{-10}$) |
| $r_z[7]+10^{-3}$ | $5.0\times10^{-4}$ | resolved |
| last CX into an ancilla dropped | $1.41$ (ancilla leak $1.00$) | detected |
| one T gate dropped | $0.39$ | detected |
| right circuit against target of wrong angles | $1.18$ | detected |

### 2c. Metrics recount (own lowering vs Qiskit `transpile(optimization_level=0)` vs archive)

| entry | CX / $T_{\rm fixed}$ / $N_{\rm rot}$ / depth / qubits: own = Qiskit = archive | result |
|---|---|---|
| r03-F2-003 | 119 / 104 / 13 / 161 / 32 | PASS |
| r03-F3-003 | 112 / 104 / 13 / 129 / 33 | PASS |
| r03-F4-003 | 119 / 104 / 13 / 156 / 32 | PASS |
| r04-F2-004 | 111 / 104 / 13 / 149 / 32 | PASS |
| r04-F3-004 | 111 / 104 / 13 / 140 / 32 | PASS |
| r04-F4-004 | 111 / 104 / 13 / 153 / 32 | PASS |
| r05-F2-005 | 111 / 104 / 13 / 145 / 31 | PASS |
| r05-F3-005 | 112 / 96 / 16 / 135 / 31 | PASS |
| r05-F4-005 | 111 / 104 / 13 / 138 / 32 | PASS |

The gate multisets (cx, h, s, sdg, t, tdg, x, z, rz) also agree exactly between Qiskit and the archive for all 9.

T count by pygridsynth 1.2.0 on the extracted rotation angles (own call; own word-error check; archive values compared):

| entry | $T(10^{-6})$ own / archive | $T(10^{-10})$ own / archive | depth$_{\rm CT}$ own / archive | max word error at $10^{-6}$ | result |
|---|---|---|---|---|---|
| r03-F2-003 | 912 / 912 | 1456 / 1456 | 1678 / 1678 | $4.31\times10^{-7}$ | PASS |
| r03-F3-003 | 912 / 912 | 1456 / 1456 | 1648 / 1648 | $4.31\times10^{-7}$ | PASS |
| r03-F4-003 | 912 / 912 | 1456 / 1456 | 1716 / 1716 | $4.31\times10^{-7}$ | PASS |
| r04-F2-004 | 912 / 912 | 1456 / 1456 | 1664 / 1664 | $4.31\times10^{-7}$ | PASS |
| r04-F3-004 | 912 / 912 | 1456 / 1456 | 1664 / 1664 | $4.31\times10^{-7}$ | PASS |
| r04-F4-004 | 912 / 912 | 1456 / 1456 | 1694 / 1694 | $4.31\times10^{-7}$ | PASS |
| r05-F2-005 | 912 / 912 | 1456 / 1456 | 1663 / 1663 | $4.31\times10^{-7}$ | PASS |
| r05-F3-005 | 1112 / 1112 | 1760 / 1760 | 2177 / 2177 | $4.74\times10^{-7}$ | PASS |
| r05-F4-005 | 912 / 912 | 1456 / 1456 | 1672 / 1672 | $4.31\times10^{-7}$ | PASS |

(depth$_{\rm CT}$ uses the project convention $X\to HSSH$, $r_z(k\pi/4)\to S^{\lfloor k/2\rfloor}T^{k\bmod2}$; with $X$ as one gate the best is 1642.) All 27 values agree exactly.

Clifford+T circuit simulated (rotations replaced by my pygridsynth words at $\varepsilon=10^{-6}$, 433 states, nominal angles, engine A), tolerance $N_{\rm rot}\varepsilon+10^{-9}$:

| entry | T | total error | tolerance | ancilla leak | Gauss | result |
|---|---|---|---|---|---|---|
| r03-F2-003 | 912 | $2.63\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| r03-F3-003 | 912 | $3.40\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| r03-F4-003 | 912 | $3.31\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |
| r04-F2-004 | 912 | $2.74\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| r04-F3-004 | 912 | $2.75\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| r04-F4-004 | 912 | $2.68\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |
| r05-F2-005 | 912 | $2.74\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.8\times10^{-7}$ | PASS |
| r05-F3-005 | 1112 | $4.09\times10^{-6}$ | $1.60\times10^{-5}$ | 0 | $1.9\times10^{-7}$ | PASS |
| r05-F4-005 | 912 | $2.68\times10^{-6}$ | $1.30\times10^{-5}$ | 0 | $1.1\times10^{-7}$ | PASS |

Project's own synthesised verdict for the best (`round-005.json`): error $3.73\times10^{-6}\le1.3001\times10^{-5}$, certified (mine: $2.74\times10^{-6}$, same bound, both engines are valid lower-level estimates of the same quantity with different pruned sparse bookkeeping).

### 2d. Angle linearity

For all 9 entries the $r_z$/$p$ angles at the three pairs satisfy $\theta_i=a_i\alpha+b_i\beta$ with no constant: least-squares residual $4.4\times10^{-16}$ for every entry, $a_i,b_i$ rational with denominator $\le8$ (deviation $\le2.4\times10^{-15}$). Best circuit: four electric phases $(a,b)=(-\tfrac34,0)$; nine magnetic non-Clifford rotations with $b=\tfrac34,-\tfrac12,-\tfrac14,\tfrac14,-\tfrac14,\tfrac34,-\tfrac34,\tfrac34,-\tfrac34$ (all $a=0$). PASS (9 of 9).

## 3. Global best `r05-F2-005`: Lean certificate and gate-by-gate tie to the program

| check | expected | got | result |
|---|---|---|---|
| re-run `lean/.lake/build/bin/su2plaq_cert check compress/lean/certs/step-o1-ca5c0f1a907a.json` | ACCEPT | `ACCEPT`, 611 s wall (user 60 CPU-min; the archive recorded 352 s; machine was loaded by two other jobs and 6 pytest workers) | PASS |
| checker binary sha256 | archive `befbd27e...` | `befbd27e3ed4e8229f11320189441597e04c89c7bf7746cf93f1c55de261bfd5` | PASS |
| no `Su2PlaqCert/*.lean` newer than the binary; `git status lean` clean | yes | yes | PASS |
| program file sha256 vs archive | equal | `4f7fcb1eab11fc709a1e44eb0fdafe9a5f7cd9d48365aea6642cd280170cef92` both | PASS |
| `program_sha256` field = sha256 of the exported gate list; circuit id suffix | equal | equal (`ca5c0f1a907a...`) | PASS |
| `Pins.lean` `statesSha256` and targets UE:1, UB:1, step:1, step:2 vs my recomputation (`pins.compute_pins`) | equal | all equal | PASS |
| sha256 of the cert's 433 states under my own canonical writer vs `Pins.lean` | equal | `45be4cd3d73d5886...` equal | PASS |
| cert states vs float physical vectors | same support, equal | same support, $\max|\Delta|=2.8\times10^{-16}$ | PASS |
| cert exact target at nominal angles vs float $V$ | equal | $5.6\times10^{-16}$ | PASS |
| exporter data mismatch (`_exporter_mismatch`) | None | None | PASS |
| cert gate list vs MY lowering of the program's circuit, gate by gate, 3 angle pairs | identical | 432 cert gates (one program-level `cz(28,29)` kept native in the cert) expand to 434 = my 434 lowered gates; 0 name mismatches, 0 qubit mismatches; the 13 angle gates $m_\alpha\alpha/d_\alpha+m_\beta\beta/d_\beta$ equal my angles to $3.9\times10^{-16}$, $1.5\times10^{-16}$, $6.7\times10^{-16}$ | PASS |
| gate counts: cert (+ expanded cz) vs archive | cx 111, h 118, t 52, tdg 52, s 22, sdg 36, x 19, z 11, rz 13 | identical | PASS |
| Lean checker rejects 5 broken certificates (hash field repaired) | REJECT | state coefficient $\tfrac12\to\tfrac34$: `REJECT state 5 is not normalised`; $r_z$ exponent $+2$: `REJECT state 0 differs from the target`; one T deleted: same; one CX swapped: same; one CX deleted: `REJECT state 2 differs from the target` | PASS |

Lean certificates exist for the best of each round (`r01-F2-001`, `r02-F2-002`, `r03-F3-003`, `r04-F2-004`, `r05-F2-005`: status `certified`); the other round entries are `not_run` by design (the loop certifies only the new global best). Same caveat as 039/040: the cert stores the gate-list hash, not the program-file sha (STATUS known issue 2.L8); the program-to-certificate link is my gate-by-gate comparison above.

## 4. Near-duplicates (informational)

Comparison of the lowered gate lists (longest common subsequence, LCS, in gates) among the round-4/5 entries (lowered lengths 434 to 456):

| pair | LCS lowered / length | other | verdict |
|---|---|---|---|
| r04-F2-004 vs r04-F3-004 | 449 / 456 (98 %) | same 13-rotation multiset (qubits, angles); 28 positional differences; programs differ at 5 of 294 gates | **near-duplicate** (same circuit with the CX of some fold/frame steps differing) |
| r04-F2-004 vs r05-F3-005 | 410 / 456 | r05-F3-005 has 16 rotations (T 1112) | related, different cost |
| r04-F3-004 vs r05-F3-005 | 418 / 456 | same | related, different cost |
| r04-F4-004 vs r05-F4-005 | 322 / 456 | same CX and rotation multisets | same skeleton, reordered (about 70 %) |
| r05-F2-005 vs r04-F2-004 | 240 / 456 | same rotation multiset; r05 has 22 fewer gates, 31 vs 32 qubits | genuinely different CX network |
| r05-F2-005 vs r05-F4-005 | 84 / 456 | | distinct |
| r05-F2-005 vs r04-F4-004, r04-F3-004 | 125, 236 | | distinct |

Since the plateau is 111 CX / 912 T for five entries (r04-F2/F3/F4, r05-F2/F4), only `r04-F2-004` and `r04-F3-004` are essentially the same circuit; the others realise the same cost with different CX networks, qubit counts (31 vs 32) and depth$_{\rm CT}$ (1663, 1664, 1672, 1694). `r05-F2-005` is the only 31-qubit entry at 111 CX.

## 5. `results/compress/twelve/` and `compress/` consistency

| check | expected | got | result |
|---|---|---|---|
| archive entries vs `compress/attempts/twelve.jsonl` | one line per entry, same key/parent/program sha/round | 22 = 22, 0 differences, no orphans either way; all 22 valid; attempts per round 5, 4, 4, 3, 3, 3 | PASS |
| round JSONs `round-000 ... round-005` | present, `entries` all in the archive | 6 files, every entry id in the archive, candidate keys equal archive keys; `n_valid` 5, 4, 4, 3, 3, 3, `n_invalid` 0 | PASS |
| `feedback/<id>.json` for every entry | 22 | 22 files, one per archive entry | PASS |
| archive `key` = (CX, round T(1e-6), depth$_{\rm CT}$, qubits) from `metrics_raw` | equal | equal for all 22 | PASS |
| lineage parents known | each parent is `None` or an archive id | all known. Round-0 seeds and all round-1 entries have `parent None` (round-1 programs declared no PARENT; first stored parents are in round 2; cause not investigated); round 2: r02-F1 and r02-F2 descend from r01-F2, r02-F3 from r01-F3, r02-F4 from r01-F4; round 3: F2 from r02-F2, F3 from r02-F2 (migration), F4 from r02-F4; rounds 4 and 5 each from the same family of the previous round | PASS (informational: round-1 lineage is empty) |
| discoveries | `compress/discoveries/twelve.md` lines match each entry's `discoveries` field | 50 lines = 50 entries' discoveries, per entry equal, no orphan ids | PASS |
| `index.json` | best = lexicographic min key | best `r05-F2-005`, family bests F1 r02-F1-002, F2 r05-F2-005, F3 r04-F3-004, F4 r05-F4-005, seed r00-seed-001; 12 cell elites | PASS |
| `python -m su2plaq.compress.report --encoding twelve` (needs `PYTHONPATH=src`) | renders; numbers equal archive | table with 15 rows rendered; for the 12 rows that cite an archive entry (the 11 entry rows + global best) qubits, CX, $T_{\rm fixed}$, $N_{\rm rot}$, T(1e-6), T(1e-10), T_est (=104+3·13·log2(1e6)=881.33), depth$_{\rm CT}$, Lean status all equal the archive (0 mismatches); err column for 4 spot-checked rows equals `verdict_nominal.op_norm_error` (global best $1.00444\times10^{-13}$); the three non-entry rows (Qiskit L3 whole circuit, paulo34, spinnet15) match the round-0 `external` block; 6 "Clifford+T re-verification" lines match `synthesis_verification` of rounds 0 to 5 | PASS |

Global-best row of the table: 31 qubits, CX 111, $T_{\rm fixed}$ 104, $N_{\rm rot}$ 13, T(1e-6) 912, T(1e-10) 1456, depth$_{\rm CT}$ 1663, Lean certified, `r05-F2-005 @ d05f973`. Baselines in the same table: general 294 CX / 952 T, Qiskit L3 (windowed) 290/918, lean22_v2 seed 162/660, so the best is 2.65 x fewer CX than the general circuit and 1.46 x fewer than the best seed (T is 1.38 x higher than the seed's 660, by the cost ordering CX > T).

## 6. Informational findings (none changes the verdict)

1. **Stale evaluator hash on the five round-0 seeds.** `r00-seed-*` carry `evaluator_sha256 = 810e86f2640d...`; the other 17 entries carry the current `0bd7e7d91d9d...`. The gate test only needs the best to match, so it passes. The seed numbers (162/660 etc.) were independently verified in reports/tests/032. STATUS asked for a refresh of the seeds under the final evaluator; this has not been done. Guess: harmless cosmetic provenance, but anyone comparing "evaluator version" columns will see two values.
2. **Acceptance tests rewrite a tracked file.** After the suite, `compress/lean/structure.json` differs from HEAD only in `provenance.git_commit` (`4fa765b` to `74598e7`) and `structure_certificate.seconds` (53.4 to 39.3); content hashes of the structure data are unchanged. Guess: a locked test regenerates the file; restore with `git checkout` or commit it deliberately. I left it as is (not my file to edit).
3. **`report` writes a new untracked file** `results/compress/twelve/summary.json` on each run; I left it in the tree for the coordinator.
4. Timing: with the machine loaded (load average up to 28 from my own parallel jobs), the Lean checker run took 611 s instead of the recorded 352 s and 74 to 88 s in earlier quiet runs; no result depends on it, but the gate wall times above are upper bounds. The projected benchmark step should be run on a quiet machine.
5. The round-1 entries have no stored parent; the lineage of round 1 is therefore empty (cause not investigated).

## 7. Tally

- Gate tests: 102/102 acceptance (m0, m1, m2 incl. slow) PASS, 396/396 unit PASS, collect clean, `check_lock` OK, `acceptance-check` PASS (acceptance-v7), `lake build` OK (incremental).
- New second-engine checks: 9 entries x 3 angle pairs x 2 engines (own sparse, Aer), all 433 states, 54 runs: 54/54 PASS; recount 9/9; pygridsynth 9/9; Clifford+T simulation 9/9; linearity 9/9; best entry: Lean ACCEPT, 5/5 mutants rejected, gate tie PASS, 5/5 negative controls resolved.
- Failures: 0. Pending: 0. New failures vs report 040: 0.

Reproduction: scripts in `scratch/tester-m2gate/` (`build_all.py`, `verify.py`, `aer_chk.py col <id>`, `counts.py`, `synth_chk.py`, `synth_sim.py`, `negctl.py`, `lean_checks.py`, `cert_vs_prog.py`, `mut.py`, `dup.py`, `assemble2.py`); tool versions: python 3.12.14, numpy 2.5.2, scipy 1.18.0, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0; no random seeds (deterministic engines).

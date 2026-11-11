# Tester report 118 — M4 step 4.6 round 5 (loop stop) and steps 4.L1/4.L2/4.7, track S, mode `step`

- Date: 2026-11-10 (machine clock; it jumped by about 3 h across a usage-limit pause)
- Commits: round-5 verification at `f93eded` (round 5 evaluated; `d5d306b` is a STATUS-only commit on top). Step 4.L1/4.L2/4.7 verification at `d65d325` / HEAD `6d9bae8` (HEAD moved only by rishon and LSH commits; `git diff d65d325 HEAD` over `src/su2plaq/spinnet`, `src/su2plaq/compress`, `compress/archive/spinnet`, `compress/programs/spinnet`, `results/compress/spinnet`, `results/spinnet`, `tests/acceptance/m4`, `lean/Su2PlaqCert`, `lean/certs`, `scripts/m4_results.py` is empty). Code of 4.L1/4.L2/4.7: `b0d3db7`; results: `232bb5e`. Branch `merge-desktop-tracks`, host omnicommander, cores 0-1.
- Prompt in force: `prompts/104-spinnet-m4-plan.md` (row 4.6, §1 tester protocol, §11 errata E1-E3; rows 4.L1, 4.L2, 4.7)
- Related: `reports/tests/117-m4-round-004.md` (template), `reports/tests/116-m4-step-4-3b-headline.md`
- Raw numbers and scripts: `results/spinnet/tester/4_6_r5/` (`aer_r05-F*-005.json`, `keys_own.json`, `robust_depth_*.json`, `robust_cmp.json`, `probe_d.out`, `stop_rule.out`, `synth_aer_*.json`, `lean_r5.json`, `lean_certify.json`, `theorem_checks.json`, `artifacts_check.json`, `consistency_r5.out`, `m4_all_clean_f93eded.txt`, `m4_all_HEAD.txt`, `m3_m3x_notslow.txt`, `unit_*.txt`, the `.py` that produced each, `*.err` = my `tv.py` wall/RSS wrapper)

## Verdict: PASS

Round 5 (three entries) is valid on my own engine (Aer statevector, all 433 physical codes, 11 angle pairs each, error $\le 4.9\times10^{-15}$, ancillas clean, outer register untouched, no leak). All keys equal the archive exactly. Robust headline recomputed independently: **`r02-F1-002` stays the headline**, robust key $(31, 21840, 0, 46024, 17)$. Round 5 is the third consecutive round without a robust improvement: **stop-rule counter 3/3, the loop stops** (sessions 18/20). All three round-5 programs are now angle-linear and **Lean-certifiable** (certified by the compiled checker at two angle pairs each; the loop recorded `lean None` only because it certifies just the round's laptop-key best).

Steps 4.L1/4.L2/4.7: the whole m4 directory including slow is **19 passed, 0 failed** (L5 and R1 now green). The theorem file `lean/certs/spinnet-best-step.lean` elaborates with `[propext, Classical.choice, Quot.sound, spinnet_best._native.native_decide.ax_1_1]` and embeds, byte for byte, the headline's certificate. `write_theorem_file` refuses all 10 tampered inputs; hand-built theorem files from 4 tampered certificates fail to elaborate. `m4-compressed.json` numbers recomputed independently (31 CX, 17 rotations, $T=734/1086/1432/1784$, $\bar T=1092.0$, 54 and 34 CX of the comparison rows).

Non-green items, none mine: `acceptance-check` FAIL only because of an uncommitted new folder `tests/acceptance/m2c/` of another planner (see Tests). One finding for the coordinator (not a failure): the lean build tree must be rebuilt before the theorem file elaborates (N1).

## Commands (env `coding`, `PYTHONPATH=src`, one BLAS thread, `taskset -c 0-1`; heavy jobs through `tools/run-capped`; pytest through `tools/pytest-safe -n 2 -p no:cacheprovider`)
1. `graphify update .`
2. `python results/spinnet/tester/4_6_r5/aer_verify.py $PWD r05-F{1,2,3}-005` (three processes), `keys_own.py`, `probe_a.py`, `consistency_r5.py $PWD 9145258`
3. `robust_depth.py <id>` for `r05-F2-005`, `r05-F3-005`, `r05-F1-005`, `r02-F1-002`; `robust_cmp_r5.py`; `probe_d.py`; the stop-rule script (`stop_rule.out`); `python -m su2plaq.spinnet.loop headline`
4. `lean_r5.py` (export + compiled checker + 17 tamper probes + static scan), `lean_certify.py` (the loop's `lean_export.certify` path), `synth_aer.py`
5. `theorem_checks.py $PWD`; `cd lean && lake env lean certs/spinnet-best-step.lean`; `artifacts_check.py` (Aer on the shipped QPY and OpenQASM 3 files, own T / CX, rows of the before/after table)
6. `tools/pytest-safe -n 2 tests/acceptance/m4 -m "slow or not slow" -rA -q` twice: in a `git archive f93eded` copy (scratchpad; pre-4.7 state) and in the repository at `d65d325`; `tests/unit/test_spinnet_{lean_cert,m4_results,loop}_unit.py`; unit subset `test_compress_*`, `test_lean_round_unit`, `test_spinnet_*`; `tests/acceptance/m3 m3x -m "not slow"`
7. `python tools/check_lock.py`; `~/.claude/bin/acceptance-check`

## Method
As in report 117. Target $V=U_B(\beta)\,U_E(\alpha)$ from `su2plaq.exact.spinnet.h_magnetic_phys_6j` and `scipy.linalg.expm`; the circuit runs on Aer on each of the 433 codes; $M_{jk}=\langle y_j|C|y_k\rangle$; error $=\lVert M-e^{i\varphi}V\rVert_2$. Angle pairs for Aer: $(0.37,0.61),(0.91,0.23),(1.70,1.00)$, six draws of `random.Random(20261108)`, $(0,0)$, out-of-range $(4.5,2.7)$. Robust set: own `numpy.random.default_rng(20261107)` (20 alphas in $[0.05,2.0)$, 20 betas in $[0.05,1.2)$). $T_{10^{-6}}=T_{\rm fixed}+\sum_r T_r$ from `pygridsynth.gridsynth_gates`; depth$_{CT}$ from the lowered circuit with my own words (`X`$\to$`HSSH`, `W` dropped).

## 1. Validity and keys of the three round-5 entries

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| program SHA-256 on disk = archive (all 23 entries) | equal | equal | exact | PASS |
| angle set: own `default_rng(20261107)` pairs = `loop.ANGLE_SET` = cache; sha256 | equal | `769caec1...bb2e` equal in all three | exact | PASS |
| Aer block error, 11 pairs, `r05-F1-005` (18 qubits) | $\le10^{-10}$ | $1.57$ to $4.87\times10^{-15}$ (nominal $1.72$) | $10^{-10}$ | PASS |
| same, `r05-F2-005` (31 CX) | $\le10^{-10}$ | $1.03$ to $4.54\times10^{-15}$ (nominal $1.44$) | $10^{-10}$ | PASS |
| same, `r05-F3-005` | $\le10^{-10}$ | $1.81$ to $4.91\times10^{-15}$ (nominal $2.29$) | $10^{-10}$ | PASS |
| max per-input full residual (33 cases) | $\le10^{-10}$ | $4.79$ (F1), $4.48$ (F2), $4.74\times10^{-15}$ (F3) | $10^{-10}$ | PASS |
| ancilla weight (including both ancillas of F1), outer-changed weight, leak weight (33 cases) | 0 | exactly 0.0 | $10^{-14}$ | PASS |
| qubits seen by Aer | = key | 18, 17, 17 | exact | PASS |
| archive's own sparse-engine verdicts (nominal + 2 alt) | $\le10^{-10}$ | F1 $5.6,5.0,5.8$; F2 $5.0,5.8,5.9$; F3 $5.6,5.6,6.6\times10^{-15}$; Gauss $\le5.5\times10^{-16}$; skeleton equal, mode `full`, leak 0, dirty ancilla 0, outer bits read 0 | $10^{-10}$ | PASS |
| skeleton identical over 8 pairs; rotation angles affine $\theta=a\alpha+b\beta+c$, worst residual | $\sim10^{-15}$ | equal, $8.9\times10^{-16}$ (all three) | $10^{-12}$ | PASS |
| rotations with $c\neq0$ | 0 (angle-linear) | 0 of 13 / 17 / 13; slopes only $-\tfrac34\alpha$ (four electric) and $k\beta/4$, $k\beta/8$-type multiples | exact | PASS |
| outer register (qubits 8-15) only controls | none as target | none in all three | exact | PASS |
| static scan: evaluator `_scan_source` and own `ast` | accepted, no forbidden name | all accepted; imports F1 `fractions`, `builder`; F2 `itertools`, `numpy`, `builder`; F3 `dataclasses`, `numpy`, `from su2plaq.compress import oracle, builder` (the known false positive of `keys_own.py` on the module name `su2plaq.compress`, resolved by `lean_r5.py`: whitelisted name is `su2plaq.compress.oracle`) | exact | PASS |

### Keys recomputed (own CX via `transpile` to `{cx,u}`, own T, own depth$_{CT}$)

| program | CX own / key | $T_{\rm fixed}+\sum T_r=T$ own / key | depth$_{CT}$ own / key | qubits own / key | $N_{\rm rot}$ | verdict |
|---|---|---|---|---|---|---|
| F1 `r05-F1-005` | 32 / 32 | $24+810=834$ / 834 | 1565 / 1565 | 18 / 18 | 13 | PASS |
| F2 `r05-F2-005` | 31 / 31 | $16+1070=1086$ / 1086 | 2262 / 2262 | 17 / 17 | 17 | PASS |
| F3 `r05-F3-005` | 32 / 32 | $24+808=832$ / 832 | 1552 / 1552 | 17 / 17 | 13 | PASS |

(Own `t_from_exact_pi4_rotations` = 0: no rotation is a multiple of $\pi/4$.)

Index and archive (`consistency_r5.py`, 35 checks, base `9145258`, all PASS): 23 entries; `index.best` = `r04-F1-004` $(31,1062,2173,17)$, unique minimum; cells $(40,77)$ and $(40,80)$ elites unchanged (`r04-F3-004`, `r04-F1-004`; the new entries take none); family bests recomputed equal; `attempts` 23 lines, first 20 identical to base; feedback 23; `round-005.json`: round 5, 3 valid, 0 invalid, best key $(31,1062,2173,17)$, `synthesis_verification` null (best unchanged, so none run, as expected); discoveries file = 35 old + 8 new lines; older entries, feedback and `robust.json` entries unchanged; `evaluator_sha256`, `spinnet.code_sha256` equal to the current hashes; `summary.json`: 6 rounds, 23 candidates. Lineage: `r05-F1-005` from `r04-F1-004`, `r05-F2-005` from `r03-F2-003`, `r05-F3-005` from `r04-F3-004`. Note: `round-005.json` and the three entries say `git_commit 9145258`, `git_dirty True` (the new program files were uncommitted when they were evaluated, as in report 117).

### Synthesised verification (extra)
Own synthesis of each program at $\varepsilon=10^{-6}$ with my own `pygridsynth` words, Aer on a seeded 60-code subset, nominal angles, bound $N_{\rm rot}\varepsilon+10^{-9}$ against block error plus leak amplitude:

| entry | T gates in synthesised circuit | block error | leak amplitude | sum | bound | verdict |
|---|---|---|---|---|---|---|
| `r05-F1-005` | 834 | $2.36\times10^{-6}$ | $6.19\times10^{-6}$ | $8.5\times10^{-6}$ | $1.30\times10^{-5}$ | PASS |
| `r05-F2-005` | 1086 | $3.43\times10^{-6}$ | $4.50\times10^{-6}$ | $7.9\times10^{-6}$ | $1.70\times10^{-5}$ | PASS |
| `r05-F3-005` | 832 | $2.57\times10^{-6}$ | $3.70\times10^{-6}$ | $6.3\times10^{-6}$ | $1.30\times10^{-5}$ | PASS |

## 2. Robust headline, ranking, stop rule

Own $\sum_{20}T$ for all nine competitors equals the cache at every one of the 20 pairs (max per-pair difference 0), own $\sum$depth equal to the cache, own $\rho=0$ (strict angle fit) for the three new entries.

| entry | own CX | own $\sum_{20}T$ / cache | own $\sum$depth / cache | own $\rho$ | robust key |
|---|---|---|---|---|---|
| `r02-F1-002` (headline) | 31 | 21840 / 21840 | 46024 / 46024 | 0 | $(31,21840,0,46024,17)$ |
| **`r05-F2-005`** | 31 | 21840 / 21840 | 46104 / 46104 | 0 | $(31,21840,0,46104,17)$ |
| `r04-F1-004` | 31 | 21840 | 45876 | 1 | $(31,21840,1,45876,17)$ |
| `r03-F2-003`, `r03-F1-003` | 31 | 21840 | 45882 / 46141 | 1 | not better |
| **`r05-F3-005`** | 32 | 16948 / 16948 | 33225 / 33225 | 0 | $(32,16948,0,33225,17)$ |
| **`r05-F1-005`** | 32 | 16950 / 16950 | 33213 / 33213 | 0 | $(32,16950,0,33213,18)$ |

Own ranking of the 31-CX entries: `r02-F1-002` < `r05-F2-005` ($\rho=0$, $+80$ depth, $+0.17\%$) < `r04-F1-004` ($\rho=1$) < `r03-F2-003` < `r03-F1-003`; every other valid entry has CX $\ge32$. `loop headline` returns `r02-F1-002`, key $(31,21840,0,46024,17)$, $\bar T=1092.0$, Lean `certified`, `archive_best` = `r04-F1-004`; its full ranking equals my sort of the cache for all 23 entries (`probe_d.out`); `robust.json` sha256 unchanged by the call.

Per-pair differences over the 20 pairs (mean $\pm$ s.e.; counts of $<0/=0/>0$):

| difference | mean $\pm$ s.e. | min / max | $<0/=0/>0$ |
|---|---|---|---|
| $T(\text{r05-F2-005})-T(\text{r02-F1-002})$ (headline) | $0.00\pm0.00$ | 0 / 0 | 0 / 20 / 0 |
| $T(\text{r05-F2-005})-T(\text{r03-F2-003})$ (parent) | $0.00\pm3.67$ | $-32$ / $+32$ | 9 / 3 / 8 |
| $T(\text{r05-F3-005})-T(\text{r04-F3-004})$ (parent) | $-0.30\pm1.83$ | $-11$ / $+15$ | 11 / 0 / 9 |
| $T(\text{r05-F3-005})-T(\text{r03-F3-003})$ | $0.00\pm0.00$ | 0 / 0 | 0 / 20 / 0 |
| $T(\text{r05-F1-005})-T(\text{r04-F1-004})$ | $-244.5\pm2.9$ | $-264$ / $-220$ | 20 / 0 / 0 |
| $T(\text{r05-F3-005})-T(\text{r02-F1-002})$ | $-244.6\pm1.4$ | $-256$ / $-230$ | 20 / 0 / 0 |

Statement. `r05-F2-005` is the same T as the headline at every pair (identical rotation count and angle slopes; the F2 design differs in the walk but has the same 17 rotations); only its $\sum$depth is larger. It is an independent angle-linear 31-CX rebuild, not an improvement. `r05-F3-005` equals its previous angle-linear ancestors in $\sum T$ ($16948$) and only removes $\rho$; `r05-F1-005` is $+2$ T (sum $16950$) with 18 qubits.

**Stop rule** (rounds $\ge3$ counted on $k_{\rm rob}$; script `stop_rule.out` from the cache): global robust best before each round and round minimum:

| round | round-minimum $k_{\rm rob}$ (entry) | global best before | improved | counter |
|---|---|---|---|---|
| 2 | $(31,21840,0,46024,17)$ (`r02-F1-002`) | `r01-F1-001` | yes | - |
| 3 | $(31,21840,1,45882,17)$ (`r03-F2-003`) | `r02-F1-002` | no | 1 |
| 4 | $(31,21840,1,45876,17)$ (`r04-F1-004`) | `r02-F1-002` | no | 2 |
| 5 | $(31,21840,0,46104,17)$ (`r05-F2-005`) | `r02-F1-002` | no | **3** |

Counter 3 of 3: **the loop stops by the 3-round rule** (the round-8 limit is not reached). Sessions: 15 before round 5 plus 3 (F1, F2, F3) = **18/20** (archive evidence: three round-5 entries; the earlier 15 are the STATUS count, not re-derivable from the archive because round 4 had one unsubmitted F2 session).

### Proposers' claims (sanity level, not re-derived)
Search logs exist under `scratch/proposer/f1r5/` (about 100 files: `sup12.log`, `z4*.log`, `wkc_*.txt`, C sources `walk5.c`, `wkc.c`, `ms.c`), `f2r5/` (`dir2_L12.log`, `dir3_L6cz1.log`, `dir3_L7_*.log`, `lin2_L12.log`, `anneal_host*.log`, `c/` annealer sources and inputs) and `f3r5/` (`run4_nor.log`, `run5_7.log`, `search.py`, `gen.py`, `milp2.py`). Spot checks of quoted counts against logs: F1 "4546 designs" in `z4b.log` ("kept 4546"); F2 "840 designs" (`dir2_L12.log`), "2016 designs" (`lin2_L12.log`), "7104 designs" (`dir3_L7_1.log`, `dir3_L6cz1.log`), "3439" in `prog005.py`. Not found in the logs by a plain search: F1's "118 three-AND atom sets" (the script that produced it may be a scratch file I did not search; sanity gap, not a failure). The claims are explicitly scoped to the enumerated design spaces: F1 "(complete for (i),(ii); partial for (iii))" and "32 CX is the floor of **this design**"; F2 "no 30-CX walk for [list]", "the 31-CX floor of **all-linear two-flag walks** keeps 13 walk rotations"; F3 "none fixes ... (exhaustive over [list])", "the design costs $\ge32$ CX". None claims a global 31-CX or 30-CX bound. PASS at this level.

## 3. Lean for the round-5 entries (new information)

| check | expected | got | verdict |
|---|---|---|---|
| archive `lean` of the three | `None` (loop certifies only the round's laptop-key best) | `None` | as recorded |
| own `export_certificate` at $(0.37,0.61)$, compiled checker, 3 entries | ACCEPT | F1: 108 gates, 18 qubits, `ACCEPT`; F2: 96 gates, 17 qubits, `ACCEPT`; F3: 118 gates (31 CX + 1 CZ), 17 qubits, `ACCEPT`; 433 states each | PASS |
| `lean_export.certify` (the loop's path) at $(0.37,0.61)$ and $(1.70,1.00)$ | `certified` | `certified` for all three at both pairs (0.4-3.6 s) | PASS |
| tamper, 17 circuit-changing probes per entry (drop middle / last gate, reverse first / last / retarget last `cx`, `rz` / last `rz` / `p` $+$ unit, `tdg`$\to$`t`, `s`$\to$`sdg`, phase $+1$, drop state, insert `x`, remove first `tdg`, `x` on outer qubit 8, `x` on ancilla 16) | REJECT | 17 of 17 REJECT for each of the three | PASS |
| harmless change (`program_sha256`) | ACCEPT | ACCEPT | PASS |
| non-commuting adjacent `cx` swaps | REJECT | F2: 1 probe REJECT; F1 and F3: none exist (0 probes, not tested) | PASS / n.a. |

Consequence: `r05-F2-005` is Lean-certifiable, so the headline rule is not affected (it ranks second among the 31-CX entries), and the `best_family_F2`, `best_family_F3` rows of `m4-before-after.md` show `not_run` although `certified` is the true status. Informational; the archive is not mine to edit.

## 4. Steps 4.L1 / 4.L2 / 4.7 (code `b0d3db7`, results `232bb5e`)

### Theorem file `lean/certs/spinnet-best-step.lean`

| check | expected | got | verdict |
|---|---|---|---|
| `lake env lean certs/spinnet-best-step.lean` (after the build tree is current, see N1) | return 0, standard axioms + one `native_decide` axiom | return 0 in 0.97 s; `'spinnet_best' depends on axioms: [propext, Classical.choice, Quot.sound, spinnet_best._native.native_decide.ax_1_1]`; no `sorryAx` | PASS |
| statement | `Su2PlaqCert.SpinNet.checkJsonString certJson = true := by native_decide` | as printed in the file | PASS |
| embedded JSON (own unescape) = `results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json` | byte-identical | identical; sha256 `1445a52a...a1e3` equals the sha in the file header | PASS |
| compiled checker on the embedded text | `ACCEPT` | `ACCEPT` (87 gates, 17 qubits, 433 states) | PASS |
| names the headline | `r02-F1-002` / program sha | first line `-- entry r02-F1-002, program sha256 750151e9...c650` = archive sha | PASS |
| own re-export of the archived headline program at $(0.37,0.61)$ | same circuit | same `circuit_id spinnet-step-o1-ec21654efa8e`; all fields except `provenance` equal | PASS |
| `write_theorem_file` on the real certificate | reproduces the committed file | byte-identical to the committed file | PASS |
| `write_theorem_file` refusals | refuse | REFUSED: state term code flipped; one state dropped; duplicate state index; target entry indices changed; target block entry dropped; name too long; name `a b:=by sorry --`; empty name; comment containing a newline; wrong schema. 10 of 10 refused, no file written | PASS |
| hand-built theorem file (writer bypassed) from tampered certificates | elaboration error | gate 40 dropped, `rz` $+2$ units, one state term code flipped, one target entry index changed: all four fail with ``Tactic `native_decide` evaluated that the proposition ... = true`` to false (return 1); the checker CLI says REJECT (state 0 differs / states differ from the pinned states / target differs from the pinned target). Untampered control: return 0, same axiom list | PASS |
| trust statement (comment in the file) | compiler trust named | "trust: Lean compiler + checker source"; the one `native_decide` axiom is the compiler-trust axiom; no kernel proof of the circuit semantics is claimed (same as `twelve-general-step.lean`) | PASS |

The checker binary (`su2plaq_cert_spinnet`) sha256 is `ec00aa45...3de5` before and after everything, equal to the value recorded in the archive entry and in `m4-compressed.json`; the certificate file is unchanged (sha256 above).

### `results/spinnet/m4-compressed.json` independently recomputed (`artifacts_check.py`)

| quantity | claimed | own | verdict |
|---|---|---|---|
| headline entry | `r02-F1-002`, robust key $(31,21840,0,46024,17)$, `git_dirty` False, commit `b0d3db7` | key as in §2 (own); provenance as stated | PASS |
| CX, $N_{\rm rot}$, $T_{\rm fixed}$, qubits | 31, 17, 16, 17 | 31, 17, 16, 17 | PASS |
| $T(10^{-4}),T(10^{-6}),T(10^{-8}),T(10^{-10})$ at $(0.37,0.61)$ | 734, 1086, 1432, 1784 | 734, 1086, 1432, 1784 (own `pygridsynth`) | PASS |
| $\bar T$ over 20 pairs | 1092.0 | 21840/20 = 1092.0 | PASS |
| verification block | ok, error $5.13\times10^{-15}$, leak 0, Gauss $5.3\times10^{-16}$ | own Aer: $1.39\times10^{-15}$ on the shipped QPY and on the shipped OpenQASM 3 (both: ancilla 0, leak 0, 17 qubits) | PASS |
| shipped files | `files.sha256` = QPY sha | equal; QPY and QASM3 both reload and are exact on Aer | PASS |
| general row `r00-seed-000` | 54 CX, 56 $T_{\rm fixed}$, 8 rot, 23 qubits, $T=566$ ($10^{-6}$), 884 ($10^{-10}$) | 54, 56, 8, 23, 566, 884 | PASS |
| pairs9 row `r00-seed-001` | 34 CX, 24, 13 rot, 19 qubits, 832, 1376 | 34, 24, 13, 19, 832, 1376 | PASS |
| F2 / F3 / global-best rows | `r05-F2-005` (31, 16, 17, 17, 1086, 1784), `r05-F3-005` (32, 24, 13, 17, 832, 1376), `r04-F1-004` (31, 24, 17, 17, 1062, 1752) | all equal | PASS |
| CX saving of the headline | vs general 54, vs pairs9 34 | $54-31=23$ CX ($-42.6\%$), $34-31=3$ CX ($-8.8\%$) | PASS |

Honest framing for Report 4 (not a failure): the compression buys CX and qubits, not T. $T(10^{-6})=1086$ and $\bar T=1092.0$ for the headline against $566/560.6$ (general, 23 qubits) and $832/847.4$ (pairs9, 19 qubits): the headline needs $+92\%$ and $+29\%$ more T than those rows. The 32-CX angle-linear `r05-F3-005` has $\bar T=847.4$ at 17 qubits (CX $+1$, $\bar T$ $-22\%$ against the headline; same as pairs9). The headline rule ranks CX first, so it is the headline by the locked rule; which of the two is "better" depends on the relative cost of CX and T.

### Stale absolute `cert_path` (archive entries `r00-seed-000`, `r00-seed-001`, `r01-F1-001`, path `/home/digonto/Projects/su2qc-spinnet/results/spinnet/certs/...`)
Judgement: **does not matter for the gate.** (1) `/home/digonto` does not exist here, but the three certificate files are tracked under `results/spinnet/certs/` with the same basenames (`spinnet-step-o1-b0a415d9322f`, `...066f66922ff8`, `...47a41f2305b0`); I ran the compiled checker on all three: `ACCEPT` (164 / 97 / 98 gates). (2) The only consumers of an entry's `cert_path` are `round._certify` (for a fresh certificate), `scripts/m4_results.py` (the headline only, whose path is relative and resolves) and the acceptance test L1 (which re-certifies; it passes). `resolve_cert_path` returns old absolute paths unchanged, so a later reader of those three entries would see a missing file. Recommendation (optional, for the coordinator): relativise those three `cert_path` strings (the file contents are untouched) after the milestone or leave a note in the report.

## 5. Tests

| test | expected | got | verdict |
|---|---|---|---|
| m4 whole directory incl. slow, repository at `f93eded` (clean `git archive` copy, pre-4.7) | 17 pass, L5 and R1 pending 4.7 | 17 passed, 2 failed (R1, L5: missing 4.7 outputs) in 140 s | PASS (as expected then) |
| m4 whole directory incl. slow, repository at `d65d325` | 19 pass | **19 passed in 65 s** (S0-S9, G1-G3, L1-L5, R1) | PASS |
| `tests/unit/test_spinnet_{lean_cert,m4_results,loop}_unit.py` | pass | 64 passed in 35 s | PASS |
| unit subset `test_compress_*`, `test_lean_round_unit`, `test_spinnet_*` (shared code changed: `lean_export.py`, `loop.py`) | pass | 306 passed in 326 s | PASS |
| m3 + m3x acceptance `-m "not slow"` (regression) | pass | 27 passed in 28 s | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | PASS |
| `~/.claude/bin/acceptance-check` | PASS | **FAIL** against acceptance-v17: only "Untracked: `tests/acceptance/m2c/test_consolidation_{evaluator,gate,registry}.py`" (a new folder of another planner, not committed). No m0-m4 file differs | NOT MINE |

Counts: acceptance m4 19 passed, 0 pending, 0 failed; m3/m3x 27 passed; unit 64 + 306 passed; numeric checks all pass; new failures vs report 117: none.

## Notes (no failures)
- **N1 (info, for the coordinator).** `lean/.lake` is untracked. When I first ran `lake env lean certs/spinnet-best-step.lean` (at about HEAD `d5d306b`, before my m4 run) it failed with ``Unknown identifier `Su2PlaqCert.SpinNet.checkJsonString` `` because `.lake/build/lib/lean/Su2PlaqCert/SpinNet/Check.olean` was older than the committed `Check.lean`. The m4 test run (L-tests call lake) rebuilt it; after that the elaboration is green (0.97 s) and the checker binary sha is unchanged. A fresh clone must `lake build Su2PlaqCert su2plaq_cert_spinnet` before L5; the milestone gate should keep that in its recipe.
- **N2 (info).** `lean` of `r05-F2-005` and `r05-F3-005` in the before/after table reads `not_run` although both are `certified` by my run (section 3). Consequence of the loop certifying only the laptop-key best; no impact on the headline.
- **N3 (info).** `r05-F2-005` has exactly the headline's T at all 20 pairs, as did the older 31-CX entries (data-level tie, reports 116-117).
- **N4 (side effects).** The m4 acceptance run rewrote five tracked cert files (`results/spinnet/certs/spinnet-UB-o1-33d95284ebb7`, `...UB-o1-458a39365261`, `...UE-o1-df0c79b22d3f`, `...step-o1-066f66922ff8`, `...step-o1-b0a415d9322f`; provenance field only); I restored them with `git checkout -- results/spinnet/certs/`. The headline certificate and the checker are unchanged (sha256 before = after). Files my runs leave: `results/spinnet/tester/4_6_r5/` (new, mine; it contains `theorem/` and `certs*/` scratch) and this report; the scratchpad copy `.../scratchpad/clone_f93eded` is outside the repository. `lean/Su2Plaq.lean` is modified by the LSH track, not by me. Temporary `lean/certs/_tester118_*.lean` files were deleted.
- **N5 (concurrency).** During the first half of this session another agent worked in the tree (uncommitted `src/su2plaq/spinnet/lean_export.py`, `loop.py`; certificate and archive rewrites at that time). Round-5 numbers above come from `compress/archive/spinnet` and `results/compress/spinnet` at `f93eded` (`git diff f93eded d65d325` over those paths and over the round-5 programs changes only the entries `r02-F1-002.json`, `r04-F1-004.json` and `index.json` (`written_utc`) by the 4.7 `certify_best`: cert path relativised, `program_file_sha256` added, timing fields); the m4 test at `f93eded` ran in a clean archive copy for that reason.
- What is not independent: target and gauge come from `su2plaq.exact.spinnet` (shared with the evaluator; cross-checked in earlier reports); the ranking rule and angle-set definition are the spec's; the Lean checker's pinned states and targets are the project's (the writer's exact-data comparison and the checker's SHA pins are tested adversarially above). Independent here: Aer, the build path (in-process `exec`), CX/T/depth counts and every per-pair $T$ and depth, $\rho$, ranking, stop rule from the cache, own synthesis plus Aer, certificate re-export, the tamper sets, the theorem-file unescape and byte comparison, QPY/QASM3 re-simulation.
- Resources (wall / peak RSS): Aer verification 380 s / 0.24 GB (F1, 18 qubits, shared cores), 245 s / 0.24 GB (F2), 230 s / 0.29 GB (F3); `keys_own.py` 13 s / 0.24 GB; Lean exports and checks about 15 s; theorem file elaboration 1 s; m4 whole directory 65 s and 140 s; unit subset 326 s. Seeds: robust angle set `numpy.random.default_rng(20261107)`; Aer extra pairs `random.Random(20261108)`; affine fit `random.Random(20261107)`; synthesised subset `random.Random(20261110)`. Aer statevector is deterministic.

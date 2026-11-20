# Report 445: tester, LSH milestone-8 gate step 1, mode full (prompts/401 row 8.10)

- Date: 2026-11-20. Mode: full. Commit under test: `2b0a311` at launch (`git rev-parse --short HEAD`); at the end HEAD was `e8f6212`. The two commits in between (`e729f15`, `e8f6212`) change only `docs/METHODS-lsh.md`, `docs/report-8-lsh-compression.md`, `notes/STATUS.md` (`git diff --stat 2b0a311..HEAD`); `src/`, `tests/`, `results/` are identical.
- Plan in force: `prompts/401` on `prompts/400`. Related reports: 436 to 444 (LSH steps and rounds), 435 (rishon gate, the model of this report), 428 (frozen hashes).
- Raw numbers: `results/tester/445-gate-full.json`, `results/tester/445/` (`recount.py/.json/.log`, `headline_check.py/.json`, `depth_ct.py/.json`, `depth_tiebreak.json`, `aer_headline.py/.json`, `hashes.py/.json`, `outer_roles.json`, `lean.log`, `raw/*.xml|log`, `summary.txt`, `run_streams.sh`, `rerun.sh`). Machine: omnicommander, `taskset -c 0-7`, `tools/pytest-safe -n 4`, threads 1. Seeds: none of my own; acceptance tests fix theirs; the angle set (seed 20261107) is read from the file and regenerated; the Aer states use seed 20261121 (as in 444).

## Verdict: FAIL

One genuine red: acceptance `M8_G2_best_and_headline_second_engine_aer` (m8) fails on the committed headline `r05-F3-005`, because the headline reads two outer qubits as CX controls and the locked helper refuses any gate that touches the outer register. `prompts/401` itself names this case ("the archive best or headline touches the outer register ... M8-G2 fails by design" and D11), so it is a plan-level gap and not a physics error: the headline is verified correct by three engines including a 24-qubit Aer run. Everything else is green or explained (three load/memory artefacts that pass on a quiet rerun, listed below), and the only other red is the expected `M11_T2` PENDING. The acceptance lock is intact. No new failure of physics.

## Plain-English summary

I ran every locked test of every milestone (including the slow ones), the unit tests, and the lock checks. All pass except one test in the LSH milestone: it checks the best circuit with a second simulator (Qiskit Aer), but only on the 12 inner links plus helper qubits, and it stops with an error if the circuit touches the outer-link register at all. The final best circuit does read two outer-link qubits (as controls; it never changes them). That is allowed by the project's rule, so the locked test cannot judge this circuit. I ran the check the test intended, but on the full 24 qubits, myself: the circuit matches the exact one-step operator to $2.4\times10^{-15}$. I then recounted every number in the LSH result files independently. They all agree, and the Lean theorem file elaborates with the expected axioms. The planner has to decide how M8-G2 is amended (or accepted as a known red) before the gate can close.

## Commands run

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
results/tester/445/run_streams.sh m6 m8 m9 m10 m11 m2c            # stream B   (each: taskset -c 0-7 tools/pytest-safe -n 4 tests/acceptance/<m> -q -rfEs --junitxml=...)
results/tester/445/run_streams.sh m0 m1 m2 m3 m3x m4 m5x m7 m5 unit   # stream A (unit = tests/unit)
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python results/tester/445/hashes.py
python results/tester/445/headline_check.py ; python results/tester/445/recount.py ; python results/tester/445/depth_ct.py
PER_JOB_MEM=8G taskset -c 0-3 tools/run-capped python results/tester/445/aer_headline.py
cd lean && PER_JOB_MEM=6G taskset -c 0-3 ../tools/run-capped lake env lean certs/lsh-best-step.lean
results/tester/445/rerun.sh     # quiet reruns: m2 whole, unit Lean files, m9 test_fuzzy_codec_gauss.py
```

## Results: test suites

| # | suite | expected | got (first pass) | wall | after quiet rerun | result |
|---|---|---|---|---|---|---|
| 1 | acceptance m0 | green | 34 passed | 27 s | | PASS |
| 2 | acceptance m1 | green | 22 passed | 162 s | | PASS |
| 3 | acceptance m2 | green | 45 passed, 1 failed (`test_lean_formal.py::test_program_lemma_file_checked`, call = 120.11 s, the test's own 120 s Lean timeout) | 271 s | rerun of the whole m2 alone: 46 passed in 129 s; that test alone 3.1 s | PASS (load timeout, see O1) |
| 4 | acceptance m2c | green | 28 passed | 27 s | | PASS |
| 5 | acceptance m3 | green | 24 passed | 19 s | | PASS |
| 6 | acceptance m3x | green | 4 passed | 6 s | | PASS |
| 7 | acceptance m4 | green | 19 passed | 33 s | | PASS |
| 8 | acceptance m5 | green | 56 passed | 1005 s | | PASS |
| 9 | acceptance m5x | green | 8 passed | 7 s | | PASS |
| 10 | acceptance m6 | green | 33 passed (slowest `M6_E4_full_mode_general_step`) | 1958 s | | PASS |
| 11 | acceptance m7 | green | 29 passed | 10 s | | PASS |
| 12 | acceptance m8 | green | 32 passed, **1 failed: `test_M8_G2_best_and_headline_second_engine_aer`** (deterministic, see below) | 152 s | not rerun (not load related) | **FAIL** |
| 13 | acceptance m9 | green | 27 passed, 1 failed: worker `gw2` crashed ("node down: Not properly terminated") during `test_M9_C1_seeded_physical_states_and_gauss`; journal: `su2qc.slice: The kernel OOM killer killed some processes in this unit` at 03:43:36 | 1085 s (`M9_T1[step]` alone 1010 s) | `test_fuzzy_codec_gauss.py` rerun alone: 3 passed in 371 s (C1 370 s) | PASS (OOM kill from my own parallel streams, see O2) |
| 14 | acceptance m10 | green | 10 passed | 72 s | | PASS |
| 15 | acceptance m11 | only `M11_T2` PENDING | 32 passed, 1 failed = `M11_T2` | 53 s | | PASS (expected) |
| 16 | unit suite `tests/unit` | green | 1221 passed, 3 failed: `test_lean_project_unit.py::test_program_lemma_files`, `::test_lemma_files_with_side_effects_or_no_theorem`, `test_lean_round_unit.py::test_round_lean_default_records_certificate_and_lemma_check` (120 s Lean lemma-check timeouts under load) | 1021 s | those two files rerun alone: 13 passed in 58 s | PASS (load timeouts, see O1) |
| 17 | `pytest --collect-only -q tests/acceptance` | clean | 407 tests collected, no error (start and end) | 0.3 s | | PASS |
| 18 | `python tools/check_lock.py`; `~/.claude/bin/acceptance-check` | OK | `LOCK OK`; `PASS: tests/acceptance matches acceptance-v22` (start and end) | | | PASS |
| 19 | six frozen hashes (nine keys, `results/tester/434-hashes.json`) | equal | provenance and twelve `99663fa6…3e37`, lsh `88e0d76b…c1ca`, spinnet `10f5727f…e15c`, fuzzy_ub = fuzzy_link `b4bd20fe…87f9`, rishon = `rishon.compress.code_hash` `5f5decfa…ef23`, `spinnet.loop.code_hash` `f1314a01…63d4`: all 9 equal (start and end) | exact | | PASS |

Acceptance total 407 collected = 405 passed + 1 red (M8_G2) + 1 PENDING (M11_T2), counting the quiet reruns for the three load/OOM artefacts. Unit 1224 tests, all passed after rerun of the 3.

### The M8-G2 red (the real one)

```
tests/acceptance/m8/test_lsh_m8_gate.py:191: res = aer_inner_check(qc, enc, *NOMINAL)
tests/acceptance/m8/test_lsh_m8_gate.py:118: AssertionError: gate cx touches the outer register: the reduced check does not apply (planner decision)
  assert not ({0, 14} & {12, 13, 14, 15, 16, 17, ...})
```

Cause (a guess, supported by numbers below): since round 3 the F3 line reads outer qubits 13 and 14 as controls (own scan of the lowered headline gate list: qubit 13: 3 `cx` controls; qubit 14: 5 `cx` controls; nothing writes an outer qubit; JSON `verification.outer_bits_read` = 2). The locked helper `aer_inner_check` asserts that no gate touches the outer register. `prompts/401` (stop rule, line 220: "the archive best or headline touches the outer register ... M8-G2 fails by design") and D11 say this case goes back to the planner. The test needs a planner erratum (e.g. a full 24-qubit Aer fallback when the circuit reads outer bits, as I did and as tester 444 did for `r06-F3-006`), or the red is recorded as accepted.

Independent substitute for the intended second-engine check (not a replacement of the locked test): `results/tester/445/aer_headline.py`, Aer statevector on the full 24-qubit register, headline circuit loaded from `results/lsh/m8-headline-step.qpy` (nominal pair) and rebuilt from the program (two other pairs), 12 seeded states per pair (2 pure in each $(b_{13}, b_{14})$ sector, 4 random mixtures; sector sizes 190 / 92 / 92 / 59 states), own 24-bit codes and own expm target.

| pair $(\alpha,\beta)$ | max error vs exact target (after one global phase) | max leak outside the 433 codes | max change of outer-register weight | max Gauss weight |
|---|---|---|---|---|
| (0.37, 0.61) | $2.24\times10^{-15}$ | $4.2\times10^{-15}$ | $4.2\times10^{-16}$ | 0 |
| (0.91, 0.23) | $1.50\times10^{-15}$ | $3.2\times10^{-15}$ | $2.9\times10^{-16}$ | 0 |
| (1.70, 1.00) | $2.44\times10^{-15}$ | $4.9\times10^{-15}$ | $4.7\times10^{-16}$ | 0 |

tolerance $10^{-10}$ (error), $10^{-10}$ (weights): all PASS.

## Results: headline `r05-F3-005` rebuilt from its qpy, own engine (`headline_check.py`, 22 of 22)

Engine = tester-444 own sparse gate-walk, own 24-bit codes, own `expm` of the 6j magnetic block times the diagonal electric phase, all 433 physical states.

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `m8-headline-step.qpy` sha256 | equals `files.sha256` in the JSON (`19f2d533…7647f`) | equal | exact | PASS |
| qubits; native gate set | 24; cx 68, h 50, s 26, sdg 25, rz 18, t 12, tdg 12, p 4 | 24; identical (lowering is the identity) | exact | PASS |
| own CX / $T_{\rm fixed}$ / $N_{\rm rot}$ | 68 / 24 / 22 | 68 / 24 / 22 | exact | PASS |
| own pygridsynth $T$ at $\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$ | 956 / 1396 / 1828 / 2312 (JSON `t_table`) | 956 / 1396 / 1828 / 2312 | exact | PASS |
| op-norm error vs target, 433 states, native and lowered | $<10^{-10}$ (JSON $1.44\times10^{-14}$) | $6.26\times10^{-15}$ both | $10^{-10}$ | PASS |
| leak outside 433 codes; dirty ancilla; outer register changed; Abelian Gauss weight | 0 | 0, 0, 0, 0 | $10^{-20}$ | PASS |
| unitarity defect of the 433 block | small | $1.2\times10^{-14}$ | $10^{-10}$ | PASS |
| wrong-sign target (-beta) distinguishable | error $>0.1$ | $1.88$ | – | PASS (test has power) |
| program file sha256 `5b00e6e7…e8c07` equals archive entry; qpy gate list equals program-built gate list | equal | equal | exact | PASS |
| outer roles | controls only | q13: 3 cx controls, q14: 5 cx controls, nothing else | exact | PASS (basis of the M8-G2 red) |
| certificate gate multiset (`results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json`, 215 gates, 433 states) | equals the qpy gate set | cx 68, p 4, sdg 25, h 50, t 12, s 26, tdg 12, rz 18 | exact | PASS |

## Results: recount of `results/lsh/m8-compressed.json` and `m8-before-after.md` (`recount.py`, 195 of 196 checks agree; the one non-agreement is the documentation observation O3)

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| provenance | `git_commit` `b422e78` (ancestor of HEAD), `git_dirty` false, `command` `python scripts/m8_results.py`, `quick` false; file last committed `2b0a311` | all as stated | exact | PASS |
| archive `compress/archive/lsh/entries` | 29 entries, all valid, all `evaluator_sha256` = frozen lsh hash `88e0d76b…c1ca` | equal | exact | PASS |
| headline id and archive key | `r05-F3-005`, $(68, 1396, 3210, 24)$ (CX, $T$, depth$_{CT}$, qubits) | archive minimum by key is `r05-F3-005`, key equal | exact | PASS |
| robust key $(68, 28348, 0, 63378, 24)$: CX, $\sum T(10^{-6})$ over the 20 angle pairs | CX 68; $\sum T = 28348$; mean $1417.4$ | own pygridsynth on the program built at each of the 20 pairs: $\sum T = 28348$ (per pair 1316 to 1468), mean $1417.4$; structure (68, 24, 22, 24) at every pair | exact | PASS |
| angle set | sha256 `769caec1c2738356`, seed 20261107, 20 pairs | `numpy.default_rng(20261107)`, all 20 alphas first then 20 betas, reproduces the pairs; sha256 of `repr(tuple)` = `769caec1…` | exact | PASS |
| robust depth sum 63378 and depth$_{CT}$ 3210 | JSON values | own Clifford+T depth (pygridsynth word per rotation, Qiskit depth): 3207 nominal and 62910 over 20 pairs, i.e. a constant offset of about 3 per circuit; same ordering of the three tied 68-CX entries (3207 < 3217 < 3218 vs archive 3210 < 3220 < 3221) | ordering | PASS (see O4: my depth definition differs slightly; tie-break order unchanged) |
| $T(\varepsilon)$ rows | 956 / 1396 / 1828 / 2312 | own = JSON | exact | PASS |
| before/after table: 19 rows | each row's CX, $T_{\rm fixed}$, $N_{\rm rot}$, qubits, key, $T(10^{-6})$, $T(10^{-10})$, depth$_{CT}$ equal to the archive entry; markdown row equals JSON row | all equal; general 94 / 88 / 8 / 598; wrap_sn_headline 71 / 48 / 17 / 1118; best_family_F1 71 / 40 / 17 / 1110; headline = global_best = 68 / 24 / 22 / 1396 (T_avg 1417.4); seed T_avg 592.6; `step.json` (M7) 94 / 88 / 8 | exact | PASS |
| `native_gain_cx` | $71-68=3$ | 3 | exact | PASS |
| `overhead_cx` | $68-31=37$ | 37 | exact | PASS |
| transcoder | 40 CX, 32 $T_{\rm fixed}$ | $71-31=40$ CX and $48-16=32$ $T_{\rm fixed}$ from the lsh seed-005 and spinnet `r02-F1-002` archive entries; $1118=1086+32$; own recount of the wrapped circuit 71 / 48 / 17 / 1118; JSON `transcoder` equal | exact | PASS |
| T_avg differences | $-293.4$, $+325.4$, $1092.0\to1124.0$ | equal | $10^{-9}$ | PASS |
| ranking | 28 ranked, leader `r05-F3-005`, sorted by robust key, `r00-seed-qiskit_l3` unrankable | equal | exact | PASS |
| Pareto front CX vs $T_{\rm avg}$ | 7 points (68, 1417.4), (70, 1354.3), (71, 1116.0), (72, 879.4), (74, 697.6), (82, 641.1), (84, 585.1) | recomputed from the ranking: identical | exact | PASS |
| stop record | `stop` true, `max_sessions`, streak 2, sessions 20; parameters `max_sessions` 20, `no_gain_rounds` 3 | equal in JSON, in `results/compress/lsh/stop.json` and in the md; streak recomputed from the `improved` flags (T, F, T, T, T, F, F) = 2 | exact | PASS |
| round files `round-000…006.json` | best keys (71,1118,2276,25), same, (71,1110,2291,25), (70,1338,3047,24), (68,1396,3221,24), (68,1396,3210,24), (68,1396,3210,24); 29 candidates, 29 valid | equal to JSON `rounds`; candidate counts 10+5+5+2+3+3+1 = 29 | exact | PASS |
| `results/compress/lsh/summary.json` | global best `r05-F3-005`, 29 candidates | equal; file unchanged by the M8-G3 run (not dirty) | exact | PASS |
| lineage | 29 rows, parents equal to the archive, `parent_known` all true | equal; headline chain `r05-F3-005 ← r04-F3-004 ← r03-F3-003 ← r01-F3-001`; root `r01-F3-001` has `PARENT = None` (a from-scratch F3 program, not a seed) | exact | PASS (O5) |
| Lean block | `certified`, `native-certified`, `angle_linear` true, `theorem_file_status` `elaborated`, binding `entry_id` `r05-F3-005`, `program_file_sha256` = archive, `git_dirty` false, `matches_headline` true | equal; `cert_sha256` `b05ef21d…ebef44` recomputed; `theorem_file_sha256` `dae606e5…079447` recomputed; first line of the theorem file names `r05-F3-005` and sha `5b00e6e7…e8c07` | exact | PASS |
| embedded certificate string in the theorem file | byte-equal to `results/lsh/certs/lsh-step-o1-dd63c8bf6fad.json` | equal (146 955 bytes) | exact | PASS |
| qasm3 file | 68 `cx` lines | 68 | exact | PASS |
| synthesis verification of the headline at $10^{-6}$ | ok, $N_{\rm rot}=22$, $T=1396$ | in JSON: ok, op-norm $8.1\times10^{-6}\le2.2\times10^{-5}$ | | PASS (read from file) |

### Lean theorem file, re-elaborated by me

`cd lean && PER_JOB_MEM=6G taskset -c 0-3 ../tools/run-capped lake env lean certs/lsh-best-step.lean` (file sha256 `dae606e5…079447`, last committed `b422e78`): rc 0, 4 s wall, output

```
'lsh_best' depends on axioms: [propext, Classical.choice, Quot.sound, lsh_best._native.native_decide.ax_1_1]
```

= 3 standard axioms + exactly 1 native (`native_decide`). PASS. As in earlier reports this is "native-certified" (compiled checker plus Lean compiler as trust root), not kernel-checked.

## Observations

- **O1 (load timeouts).** The Lean lemma-file tests (`check_program_lemmas(..., timeout=120)`) need a free Lean session; with my two parallel streams and other Lean work running they used the whole 120 s and failed (m2: one test; unit: three tests). Run alone, the same m2 test takes 3.1 s; the whole m2 reruns green in 129 s; the unit Lean files rerun green in 58 s. Not a code defect. For the gate on this machine, run m2 and the Lean unit files without another Lean job in parallel.
- **O2 (OOM kill).** `systemctl --user status su2qc.slice` reports `Memory max: 11G` (drop-in `~/.config/systemd/user.control/su2qc.slice.d/50-MemoryMax.conf`), not the 24G written in project `CLAUDE.md`; peak 20.8G. At 03:43:36 the kernel OOM killer killed the `M9_C1` worker while my other stream and unit Lean jobs were running. The test passes alone (371 s). Two parallel `-n 4` streams exceed the 11G slice; use one stream, or document the real cap.
- **O3 (documentation, not numbers).** `m8-before-after.md` says of the Pareto table "the first row is the headline (smallest CX)". The first row is `r04-F3-004`, the headline is `r05-F3-005`. Both (and `r05-F5-005`) have CX 68 and $T_{\rm avg}$ 1417.4; `pareto_front` sorts ties by id and keeps the first. The headline is not dominated (no entry with CX $\le$ 68 and smaller $T_{\rm avg}$), so only the sentence is imprecise. Cosmetic, for Report 8 wording.
- **O4 (depth).** My own Clifford+T depth differs from the archive by a constant 3 (3207 vs 3210, sum over 20 pairs 62910 vs 63378); the ordering of the tied entries is the same. I do not know the exact word convention of the project's `synth.depth()`; not a gate item.
- **O5 (lineage).** The headline descends from `r01-F3-001`, a from-scratch F3 program, not from a seed; worth one sentence in Report 8 ("the best circuit did not derive from the wrapped spin-network seed").
- **O6 (Report 8 draft).** `docs/report-8-lsh-compression.md` (commit `e8f6212`, after my launch) has gate placeholders; every number I verified above may replace them, with the M8-G2 status stated.
- **O7 (T-estimate).** `t_est` in `t_table` (900.99 / 1339.48 / 2216.47 at $\varepsilon=10^{-4},10^{-6},10^{-10}$) is the project's Ross-Selinger-style estimate; I did not recompute it (the measured $T$ are the gate numbers).

## Byproducts and files left (I restored nothing)

`git status --short` at the end:

```
 M results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json
 M results/spinnet/certs/spinnet-UB-o1-458a39365261.json
 M results/spinnet/certs/spinnet-UE-o1-df0c79b22d3f.json
 M results/spinnet/certs/spinnet-step-o1-066f66922ff8.json
 M results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json
?? results/tester/445/        (mine)
```

The five tracked spinnet certificates are rewritten by the unit and acceptance runs (one line each: the provenance block); same byproduct as in report 435 O3. `M8_G3` did not change `results/compress/lsh/summary.json` (clean). A stray untracked `lean/Lemma_1411693_73344785.lean` was visible for a while during the contended m2 phase and was gone at the end (created and removed by a Lean lemma test). `results/tester/445-gate-full.json` is also mine (untracked, not shown above only because it is created last; check `git status`).

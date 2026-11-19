# Report 435: tester, rishon milestone-6 gate, mode full (prompts/204 step C6 = prompts/203 row 6.8)

- Date: 2026-11-19. Mode: full. Commit under test: `fcd61dd`/`1c6c6c2` source state (`git rev-parse --short HEAD` was `1c6c6c2` at the start and `9761c72` at the end; the commits in between, `acdc461 … 9761c72`, change only `notes/STATUS.md`, `docs/report-6-…`, `docs/report-11-…`; `src/` and `tests/` are identical).
- Plan in force: `prompts/205` on `prompts/204` on `prompts/203`. Related: reports/tests/428 (frozen hashes), 433, 434.
- Raw numbers: `results/tester/435-gate-full.json`, `results/tester/435/recount.json` (+ `recount.py`, `hashes.json`). Machine: omnicommander, `taskset -c 0-8`, `tools/pytest-safe -n 4`, OMP/OPENBLAS/MKL threads 1. No random seeds of my own (acceptance tests fix theirs; the recount is deterministic).

## Verdict: PASS

Every acceptance test of m0, m1, m2, m5, m5x, m6 (slow included) is green, the unit suite is green, the lock checks pass, the six frozen hashes are unchanged, and `results/rishon/m6-compressed.json` is reproduced by an independent recount (74 of 74 recount checks). No red except the expected `M11_T2` (stale gate table, PENDING).

## Plain-English summary

I ran every locked test of the milestones 0, 1, 2, 5, 5x and 6, including the slow ones, plus the unit tests. All passed. Then I rebuilt the numbers of the final results file by myself from the archive, the round files and the three-layer file, and re-counted the gates and the T gates of the headline circuit directly from its saved circuit file. They agree with the file. Finally I let Lean check the theorem file of the best circuit and printed the axioms it uses: the three standard ones plus one native-decide axiom.

## Commands run

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 0-8 tools/pytest-safe -n 4 -m "not slow or slow" tests/acceptance/<m0|m1|m2|m5|m5x|m6> -p no:cacheprovider -q -rfEs --junitxml=...
taskset -c 0-8 tools/pytest-safe -n 4 -m "not slow" tests/acceptance/m2c ; same for m11
taskset -c 0-8 tools/pytest-safe -n 4 tests/unit
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python results/tester/435/recount.py                      # independent recount (core 8)
cd lean && PER_JOB_MEM=6G taskset -c 8 ../tools/run-capped lake env lean certs/rishon-best-step.lean
```

## Results

| # | check | expected | got | tolerance | result |
|---|---|---|---|---|---|
| 1 | acceptance m0 (slow incl.) | all green | 34 passed, 0 failed, 15 s | exact | PASS |
| 2 | acceptance m1 | all green | 22 passed, 0 failed, 67 s | exact | PASS |
| 3 | acceptance m2 | all green | 46 passed, 0 failed, 118 s | exact | PASS |
| 4 | acceptance m5 | all green | 56 passed, 0 failed, 812 s | exact | PASS |
| 5 | acceptance m5x | all green | 8 passed, 0 failed, 7 s | exact | PASS |
| 6 | acceptance m6 (G1–G6, H1–H4, L1–L9, K*, R*, S*, E*) | all 33 green | 33 passed, 0 failed, 0 pending, 1540 s (slowest: `M6_E4_full_mode_general_step` 1458 s, then `H2` 150 s, `R2` 84 s, `H4` 80 s, `E3` 80 s, `G1` 60 s) | exact | PASS |
| 7 | m2c not-slow (cross-track) | green | 18 passed, 35 s | exact | PASS |
| 8 | m11 not-slow (cross-track) | only `M11_T2` PENDING | 23 passed, 1 failed = `M11_T2` PENDING "rows not final" (stale `results/crosscheck/gate-table.json`; same text as report 428 5d) | expected red | PASS (expected) |
| 9 | unit suite `tests/unit` | green | 1201 passed, 0 failed, 710 s | exact | PASS |
| 10 | `pytest --collect-only -q tests/acceptance` | clean | 407 tests collected, no error | – | PASS |
| 11 | `python tools/check_lock.py` / `acceptance-check` | OK | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v22` | – | PASS |
| 12 | nine frozen hashes (reports/tests/428; file `results/tester/434-hashes.json`) | equal | provenance and twelve `99663fa6…3e37`, lsh `88e0d76b…c1ca`, spinnet `10f5727f…e15c`, fuzzy_ub = fuzzy_link `b4bd20fe…87f9`, rishon = `rishon.compress.code_hash` `5f5decfa…ef23`, `spinnet.loop.code_hash` `f1314a01…63d4`: all equal | exact | PASS |
| 13 | `m6-compressed.json` provenance | `git_dirty` false, circuit `r06-F3-006` | `git_dirty` False, `git_commit` `fcd61dd`, `circuit_id` `r06-F3-006`, `command` `python scripts/m6_results.py`, `quick` False | – | PASS |
| 14 | archive entries (recount from `compress/archive/rishon/entries/*.json`) | general 10102 / 20650; cheapest seed `r00-seed-001` 6874 / 17694; headline 216 / 832 | equal (all three `valid`; round-000 `best_key` = (6874, 17694, 31954, 58)) | exact | PASS |
| 15 | round files `round-000…006.json` best keys | monotone to the headline | (6874,17694,31954,58) → (256,1020,1714,58) → (252,1120,2023,54) → (232,1090,2037,53) → (228,846,1417,53) → (220,840,1389,53) → (216,832,1350,52) | – | PASS |
| 16 | general step files `results/rishon/step.json`, `step3.json` | unit 10102 / 20650; +det 10134 / 21146 | 10102 / 20650 and 10134 / 21146 | exact | PASS |
| 17 | general + det and cheapest + det additivity | $10102+32=10134$, $20650+496=21146$, $6874+32=6906$, $17694+496=18190$ | equal in `m6-compressed.json`, `m6-before-after.md` and `UD.json` (32 CX, 496 T) | exact | PASS |
| 18 | headline from its own circuit (`results/rishon/m6-compressed.qpy`, sha256 `f6e5f8a3…bd29e` equals the JSON) | 216 CX, 52 qubits, $T_{\rm fixed}=196$, 10 rotations, $T$ = 832 | I lowered the circuit myself (qiskit `transpile`, level 0): 216 CX, 52 qubits, 98 T + 98 Tdg = 196, 10 rotations (4 `p` at $-\tfrac34\alpha$, 6 `rz`); I ran pygridsynth at $\varepsilon=10^{-6}$ on each angle: $\sum T_r=636$, total $196+636=832$ | exact | PASS |
| 19 | headline mean $T$, depth, qubits | 829.8 / 1350 / 52 | `robust.json` `t_sum`=16596, $16596/20=829.8$; $\mathrm{depth}_{CT}$ 1350; 52 qubits; in JSON and md | $10^{-9}$ | PASS |
| 20 | det layer | 32 CX / 496 T / mean 500.8 | `three-layer.json` `det_key` (32, 496, 326, 48); `t_sum` 10016, $10016/20=500.8$ | exact | PASS |
| 21 | three-layer | 248 / 1328 / mean 1330.6 / depth 1676 / 52 qubits | `three_layer_key` (248, 1328, 1676, 52); additivity $216+32$, $832+496$, $1350+326$, $\max(52,48)$; means $829.8+500.8=1330.6$ | exact | PASS |
| 22 | `three-layer.json` | clean, same program | `git_dirty` False (commit `086c0fd`), program sha equals archive sha, `ok` True, 3 triples, all verdicts `ok` and `certified` | – | PASS |
| 23 | program file sha256 | equal to archive and to the JSON | `compress/programs/rishon/F3/006-closed-mark-in-restore.py` sha256 `78c86d8d…abadd` equals archive entry, `m6-compressed.json`, `three-layer.json` and the theorem-file first line | exact | PASS |
| 24 | rows of `results/rishon/m6-before-after.md` (and `before_after` in the JSON) | the ten rows quoted above | md and JSON agree on all of: general 10102 / 20650; general+det 10134 / 21146; cheapest 6874 / 17694; cheapest+det 6906 / 18190; headline 216 / 832 (mean 829.8, depth 1350, 52 q); det 32 / 496 (500.8, 326); headline+det and global_best+det 248 / 1328 (1330.6, 1676) | exact | PASS |
| 25 | ratios implied by the table (general / headline) | – | CX $10102/216=46.8\times$, $T$ $20650/832=24.8\times$; cheapest seed / headline: CX $31.8\times$, $T$ $21.3\times$; three-layer general+det / headline+det: CX $40.9\times$, $T$ $15.9\times$ | – | recorded |
| 26 | Lean theorem file `lean/certs/rishon-best-step.lean` (369 403 bytes, last committed `1c6c6c2`) | elaborates; 3 std axioms + 1 native | `lake env lean` rc 0, 48 s wall: `'rishon_best_step' depends on axioms: [propext, Classical.choice, Quot.sound, rishon_best_step._native.native_decide.ax_1_1]` | – | PASS |
| 27 | first line of the theorem file | names entry and sha | `-- entry r06-F3-006, program sha256 78c86d8d1dddca4ed31e36d328ab381ad19c849a19275af016f3c54e780abadd` = archive sha | exact | PASS |
| 28 | embedded certificate | equals the certificate file | the string literal `certJson`, decoded, is byte-equal to `compress/lean/certs/step-o1-24d16bdd9c45.json` (286 054 bytes, sha256 `ef70932c…82987`, the value in header, `m6-compressed.json` and archive; exporter commit `fcd61dd`) | exact | PASS |

All of 13 to 24 are executed by `results/tester/435/recount.py` (74 of 74 checks `ok`; one first-run FAIL was my own key-name typo, `t_avg` vs `t_avg_1e-6`, fixed in the script and rerun).

## Observations (no failure)

- O1: the working tree was not quiet. A second agent (LSH builder, steps 8.2–8.4 and tester 436) edited `src/su2plaq/lsh/loop.py`, `tests/unit/test_lsh_loop_unit.py` and created `compress/programs/lsh/`, `compress/specs/lsh-step.md`, `tests/unit/test_lsh_stop_state_tester436.py` and `results/tester/436-*`, `tests/independent/lsh_m8_436/` while my runs were going (first seen 12:04). These are not mine and I did not touch them. `lsh/loop.py` is in no hash list (nine hashes equal). The rishon, m0 to m6 and m2c results do not read it; my unit run (1201 passed) did include their in-flight edit of `test_lsh_loop_unit.py`, so the unit count 1201 is not the committed-tree count (report 434: 1169 + later additions).
- O2: no pytest worker was killed by the memory limit (no OOM message in any log).
- O3: the unit/acceptance runs rewrote the provenance line of one tracked certificate, `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json`; restored with `git checkout --`. Nothing else tracked was changed by me.
- O4: `M6_E4_full_mode_general_step` alone costs 1458 s of the 1540 s m6 wall time (general step full evaluation; one worker, the others idle). On a busier machine it can approach any time limit; not a failure.
- O5: qubit counts: `results/rishon/UD.json` and `step.json` report 16 and 26 logical qubits (inner register view), while the archive / compress keys use 48 / 58 / 52 (register incl. outer links and ancillas). The two conventions are both internal and consistent (compress key used everywhere in the gate files); worth one sentence in Report 6 so the reader does not mix them.
- O6: the Report 6 and Report 11 drafts committed during my run contain `[GATE]` placeholders; the numbers I verified (the list above) can replace them.

## Restored / left files

`git status --short` at the end: my files `reports/tests/435-…md`, `results/tester/435/` (recount.py, recount.json, hashes.json), `results/tester/435-gate-full.json`; the rest belongs to the parallel LSH agent / tester 436 (`src/su2plaq/lsh/loop.py`, `tests/unit/test_lsh_loop_unit.py`, `compress/programs/lsh/`, `compress/specs/lsh-step.md`, `results/tester/436-*`, `tests/independent/lsh_m8_436/`, `tests/unit/test_lsh_stop_state_tester436.py`). Restored by me: `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json`.

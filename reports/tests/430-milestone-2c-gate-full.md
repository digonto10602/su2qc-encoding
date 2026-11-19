# Report 430: tester, milestone-2c gate (prompts/008 step C5, part 1), mode full

- Date: 2026-11-19. Commit: `9483896` (clean tree at start). Plan in force: `prompts/008` Phase C, row C5 (with `prompts/010`, `prompts/204/205`, `prompts/401` for the PENDING items). Acceptance tag `acceptance-v22`.
- Related: reports/tests/426, 427, 428, 429 (C1 to H.3). The previous gate reports are 404 (m4) and 407 (m7); there is no earlier gate report that covered m5, m6, m9, m10, m11 together, so counts below are compared with 428/429 (the not-slow sweeps).
- Raw numbers: `results/tester/430-gate-full.json`. Logs: scratchpad `acc-m*.log`, `unit.log`.
- Resources: `taskset -c 0-8`, `tools/pytest-safe -n 4 -p no:cacheprovider -rfEs -q` per milestone directory (sequential), load average 1 to 5 (quiet machine). No worker was OOM-killed (grep of all logs for "crashed"/"OOM": none), so no re-run was needed.

## Commands

```
source .../conda.sh && conda activate coding; export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
for d in m0 m1 m2 m2c m3 m3x m4 m5 m5x m6 m7 m8 m9 m10 m11; do taskset -c 0-8 tools/pytest-safe -n 4 -p no:cacheprovider -rfEs -q tests/acceptance/$d; done
taskset -c 0-8 tools/pytest-safe -n 4 -p no:cacheprovider -rfEs -q tests/unit
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python <scratchpad>/hashes.py     # su2plaq.compress.provenance.code_hash_for(enc), spinnet.loop.code_hash(), rishon.compress.code_hash()
```

## Verdict: PASS (no real failure; every red is a PENDING stub of work outside prompts/008)

Acceptance: 407 collected, 331 passed, 26 red; all 26 reds are `PENDING:` messages or the M8_E2 `NotImplementedError` pointing at a not-yet-built LSH step. Unit: 1145 passed, 0 failed.

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| m0 (34) | all pass | 34 passed, 14 s | - | PASS |
| m1 (22, incl. slow) | all pass | 22 passed, 65 s | - | PASS |
| m2 (46, incl. slow) | all pass | 46 passed, 118 s | - | PASS |
| **m2c (28)** | all pass | **28 passed**, 27 s | - | PASS |
| m3 (24) / m3x (4) | all pass | 24 passed 8 s / 4 passed 5 s | - | PASS |
| m4 (19) | all pass | 19 passed, 28 s | - | PASS |
| m5 (56, incl. slow) | all pass | 56 passed, 773 s | - | PASS |
| m5x (8) | all pass | 8 passed, 6 s | - | PASS |
| m6 (33) | 4 PENDING (L2, L3, L9, G6) | 25 passed, 8 PENDING (L2, L3, L9, G6 + slow L4, L5, L6, L7), 1203 s | - | PASS (see O1) |
| m7 (29) | all pass | 29 passed, 8 s | - | PASS |
| m8 (33) | 8 PENDING (E2, S0, S2, S3, S4, S5, H1, L2) | 17 passed, 16 PENDING (the 8 + slow G1, G2, G3, G4, L1, L5, R1, H2), 7 s | - | PASS (see O2) |
| m9 (28, incl. slow) | all pass | 28 passed, 1024 s (M9_S1, M9_C1 included, no worker killed) | - | PASS |
| m10 (10) | all pass | 10 passed, 72 s | - | PASS |
| m11 (33) | 1 PENDING (T2) | 31 passed, 2 PENDING (T2, slow K4[lsh-twelve]), 58 s | - | PASS (see O3) |
| `tests/unit` | all pass | 1145 passed, 0 failed, 360 s (6 min) | - | PASS (429: 1145/0) |
| `pytest --collect-only -q tests/acceptance` | clean | 407 tests collected, no errors | - | PASS |
| `python tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `acceptance-check` | PASS | `PASS: tests/acceptance matches acceptance-v22` | - | PASS |
| six frozen hashes | equal to 428 | provenance/twelve `99663fa6cd2550d9...b02e3e37`, lsh `88e0d76bce7b3af6...526ec1ca`, spinnet `10f5727f5379cb44...35e15c`, fuzzy_ub = fuzzy_link `b4bd20fe811e5c99...e287f9`, rishon `5f5decfa34f53069...31324ef23`, spinnet loop `f1314a01d7716b7a...74663d4` (full values in the JSON) | exact | PASS |
| tracked files after the run | clean | 5 `results/spinnet/certs/*.json` rewritten (provenance line only); no `compress/` or `results/compress/` file changed (consistent with the atomic robust.py write); restored one by one | - | PASS |

Wall times: acceptance total about 3 400 s (57 min; m6 1203 s, m9 1024 s, m5 773 s dominate), unit 360 s.

## The 26 reds (all PENDING, none a real failure)

| test | exact message | class |
|---|---|---|
| m6 L2, L3, L4, L5, L6, L7 | `PENDING: lean/Su2PlaqCert/Rishon/Laurent3.lean missing (step 6.L2)` | PENDING, rishon prompts/204 C3 (Lean layer) |
| m6 L9 | `PENDING: su2plaq.rishon.lean_cert has no attribute recognise_angle_single` | PENDING, rishon prompts/204 C3 to C4 |
| m6 G6 | `PENDING: results/compress/rishon/three-layer.json missing (prompts/204 step C5)` | PENDING, rishon prompts/204 C5 |
| m8 S0, L2, E2 | `NotImplementedError: su2plaq.lsh.loop.render_spec: prompts/401 step 8.2 (needs the registry ... 8.R)` (E2 shows it as the stderr of a subprocess inside an `assert 1 == 0`) | PENDING, LSH M8 |
| m8 S2, S5, H1 | `NotImplementedError: su2plaq.lsh.loop.general_program_path: ... step 8.2` | PENDING, LSH M8 |
| m8 S3, S4, H2 | `NotImplementedError: su2plaq.lsh.loop.seed_round: ... step 8.3` | PENDING, LSH M8 |
| m8 L1 | `NotImplementedError: su2plaq.lsh.loop.lean_certify: ... step 8.4` | PENDING, LSH M8 |
| m8 G1, G2, G3, G4, L5, R1 | `PENDING: compress/archive/lsh missing (prompts/401 step 8.6: round 0)` | PENDING, LSH M8 |
| m11 K4[lsh-twelve] | `PENDING: no cached headline of the lsh archive (results/compress/lsh/robust.json; prompts/008 Phase C, for lsh the M8 loop of prompts/401)` | PENDING, LSH M8 |
| m11 T2 | `PENDING: rows not final: {...}` (twelve, spinnet, rishon, fuzzy rows say "no cache file / stale"; lsh waits for M8) | PENDING, stale committed gate table (step 11.8), plus three-layer.json and LSH |

## Observations (not failures)

- O1. m6 has 8 reds, not the 4 you listed: L4, L5, L6, L7 are `slow`, so the "not slow" sweeps of 427/428 never ran them. They are PENDING on the same missing file as L2/L3 (`Laurent3.lean`, rishon Lean layer of prompts/204), so the same work closes them. They should be added to the "expected PENDING" list for the gate.
- O2. m8 has 16 reds, not 8: eight more are `slow` (G1, G2, G3, G4, L1, L5, R1, H2) and are PENDING on the LSH round-0 archive or step 8.3/8.4 stubs. Same cause (LSH M8 not started). M8_E2 is the only one printed as an assertion failure, but its stderr is the same step-8.2 `NotImplementedError`, so it is a stub, not a bug.
- O3. m11 K4[lsh-twelve] is a ninth PENDING (slow), also waiting for the LSH headline. T2 text is the stale committed `results/crosscheck/gate-table.json` (as in 428 check 5d); its rows for twelve, spinnet, fuzzy, rishon will change when step 11.8 regenerates it. After the regeneration T2 will still wait for `three-layer.json` (C5 of prompts/204) and the LSH loop.
- O4. The five rewritten `results/spinnet/certs/*.json` differ from HEAD only on the first line (provenance field), as in report 407; restored with `git checkout -- <file>` for each: `spinnet-UB-o1-33d95284ebb7`, `spinnet-UB-o1-458a39365261`, `spinnet-UE-o1-df0c79b22d3f`, `spinnet-step-o1-066f66922ff8`, `spinnet-step-o1-b0a415d9322f`. `git status --short` is empty apart from this report and `results/tester/430-gate-full.json`.
- O5. For the milestone-2c definition (m0 to m5x, m7, m9, m10 and all 28 m2c green incl. slow): met. No OOM kill occurred this time (m9 M9_S1 and M9_C1 passed in the full parallel run).
- Not done here (outside this part): auditor on `pre-consolidation-008..HEAD`, benchmark vs reports/benchmarks/003, `git tag milestone-2c`.

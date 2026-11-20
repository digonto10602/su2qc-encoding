# Report 446: tester, LSH milestone-8 gate step 1, second attempt (mode full, narrow re-run after erratum prompts/402)

- Date: 2026-11-20. Commit under test: `4177db4` (`git rev-parse --short HEAD`; working tree clean at start and end except my untracked `results/tester/446/`).
- Plan in force: `prompts/402` (G2 erratum) on `prompts/401` on `prompts/400`. Acceptance tag: `acceptance-v23` (commit b94a6f9). Related reports: 445 (the run that went red only on M8-G2), 444, 441.
- Nothing in `src/` or `scripts/` changed since 445 (`git diff 2b0a311 HEAD --stat -- src scripts` is empty); `git diff 2b0a311 HEAD --stat -- src tests scripts` lists only `tests/acceptance/LOCK.json` and `tests/acceptance/m8/test_lsh_m8_gate.py`.
- Raw numbers and scripts: `results/tester/446/` (`raw2/*.log|xml`, `memwall.py`, `g2_table.py/.json`, `mutants_copy.py`, `mutants-rerun.json`, `mutants_programs/`, `hashes.py/.json`, `review/old.py,new.py`, `run_seq.sh`). Machine omnicommander, `taskset -c 0-7`, one pytest stream at a time, 1 BLAS thread. Seeds: the test's own `G2_SEED = 20261120` (10 states), plus the tests' own fixed seeds; I used no seed of my own.

## Verdict: PASS

## Plain-English summary

I ran only the pieces that the erratum could affect: every locked LSH milestone-8 test (including the slow ones), the milestone-7 tests, the LSH unit tests, and the lock checks. All pass, including M8-G2, which was the only red in report 445. Then I checked the new G2 test itself in four ways. (a) The part that handles circuits that never touch the outer-link qubits is byte-for-byte the old code. (b) I re-ran the planner's 17 test circuits (the real headline, 5 that write an outer qubit, 9 wrong circuits, 2 ancilla cases): all 17 get the expected pass or fail. (c) The numbers for the headline circuit `r05-F3-005` reproduce the table in `prompts/402` section 7 to the printed digits. G2 takes about 114 s and 1.64 GiB, inside the 2.2 GB budget.

## Commands run

```
source /home/digimonk/miniforge3/etc/profile.d/conda.sh && conda activate coding
cd /home/digimonk/Projects/su2qc-encoding; export PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance      # start and end
results/tester/446/run_seq.sh    # = taskset -c 0-7 tools/pytest-safe -n 2 tests/acceptance/m8 -m "slow or not slow" ; same for tests/acceptance/m7 ; tests/unit -k "lsh or m8"
taskset -c 0-7 python results/tester/446/memwall.py tools/pytest-safe -n 1 tests/acceptance/m8/test_lsh_m8_gate.py -k G2 -m "slow or not slow"   # G2 alone: wall + peak memory of the process tree
taskset -c 0-7 python results/tester/446/memwall.py tools/run-capped python scratch/tester/446/m402/mutants.py     # copy of the planner's mutants.py (see below)
taskset -c 0-7 python results/tester/446/memwall.py tools/run-capped python results/tester/446/g2_table.py        # per-pair table, helpers of the LOCKED test
python results/tester/446/hashes.py                                                                              # frozen hashes
```
Copy of the planner's script: `scratch/planner/402` -> `scratch/tester/446/m402`; three edits only: `ROOT` hard-set, the module under test = the real locked file `tests/acceptance/m8/test_lsh_m8_gate.py` instead of the planner's scratch copy (same sha256 `522c1f71...6843`, checked), output json path.

## Results

| # | check | expected | got | tolerance | result |
|---|---|---|---|---|---|
| 1 | `tests/acceptance/m8` incl. slow | all green | 33 passed, 0 failed, 114.8 s (`-n 2`); G2 112.1 s in that run | | PASS |
| 2 | M8-G2 `test_M8_G2_best_and_headline_second_engine_aer`, alone | green, <= 2.2 GB | 1 passed, 113.6 s pytest / 114.0 s wall; peak summed RSS of the process tree 1.636 GiB (PSS 1.608 GiB), sampled every 0.2 s | 2.2 GB | PASS |
| 3 | `tests/acceptance/m7` | green | 29 passed, 12.1 s | | PASS |
| 4 | `tests/unit -k "lsh or m8"` | green | 125 passed, 32.2 s | | PASS |
| 5 | `pytest --collect-only -q tests/acceptance` | clean | 407 tests collected, no errors (start and end) | | PASS |
| 6 | `python tools/check_lock.py` / `~/.claude/bin/acceptance-check` | OK / matches acceptance-v23 | `LOCK OK` / `PASS: tests/acceptance matches acceptance-v23` (start and end) | | PASS |
| 7 | frozen hashes (9 keys vs `results/tester/434-hashes.json`) | equal | all 9 equal: provenance and twelve `99663fa6...3e37`, spinnet `10f5727f...e15c`, fuzzy_ub = fuzzy_link `b4bd20fe...87f9`, rishon = `rishon.compress.code_hash` `5f5decfa...ef23`, lsh `88e0d76b...c1ca`, `spinnet.loop.code_hash` `f1314a01...63d4` | exact | PASS |
| 8 | (a) old vs new test file | `aer_inner_check` and all other pre-existing helpers unchanged | AST source of `aer_inner_check` identical (sha256 prefix `91de6e2a2c3a4583` both); all 15 other top-level functions of the old file identical except `test_M8_G2_...`; 5 new functions (`outer_reads`, `aer_outer_read_check`, `g2_states`, `aer_full_register_check`, `g2_second_engine`); the empty-read branch of `g2_second_engine` has the three old lines verbatim (`aer_inner_check(qc, enc, *NOMINAL)`, `error <= TOL`, `ancilla_weight <= 1e-20 and leak_weight <= 1e-20`). File sha256 old `8aa27c35...ba15`, new `522c1f71...6843` = value quoted in prompts/402 section 6. | byte-identical | PASS |
| 9 | (b) static scan on writers (planner mutants W1-W5) | `AssertionError` "writes the outer qubit" | W1 cx(0->13) x2, W2 x(13) x2, W3 h(14) x2, W4 swap(13,14) x2, W5 cx(0->13) once: all 5 rejected at the static scan in 0.5 s (including the net-identity pairs, which a pure state test would miss) | exact zeros | PASS |
| 10 | (b) 17 outcomes of `mutants.py` | 17 as expected | 17 `OK`, 0 `BAD`, final line `ALL AS EXPECTED`; real headline pass; C1 walk sign (error 0.152), C2 wrong outer qubit (error 2.0), C3 dropped cx (2.0), C4 -beta (1.878), C5 rz shift 1e-8 (error 5.0e-9, fail), C6 rz shift 1e-13 (error 5.1e-14, pass), C7 rz(0.3) on q13 (0.195), C8 cz(13,14) (2.0), C9 x(0) (1.0, leak 1.0): fail; A1 dirty ancilla (ancilla weight 1.0): fail; A2 clean ancilla at 25 qubits: fails with the 24-qubit-limit message (by design) | verdict per row | PASS |
| 11 | extra rows of `mutants.py` | dynamic parts alone see writes; full-register alone catches wrong circuits | W5/W6 with the static scan bypassed: reduced check outer_weight 1.0 / 0.5 (error 1.0 / 1.71); full-register alone: C1 error 0.120, C5 3.9e-9 (fail), C6 3.9e-14 (pass), C7 0.146, W5 and W7 (cx onto an outer qubit never read) error 0.557, outer-pattern probability change 0.0144; 9 round-0 seeds: old 47-code vs new 433-column routine agree, errors 3.0e-15 to 5.3e-15, differences <= 1.1e-16 | | PASS |
| 12 | (c) 433-code block, `r05-F3-005`, 3 pairs (63 runs, 14 qubits) | error <= 1e-10; weights <= 1e-20 | error 2.98e-15 / 2.59e-15 / 3.10e-15 for (0.37,0.61) / (0.91,0.23) / (1.70,1.00); ancilla, leak, outer weights 0, 0, 0 (table section 7 of prompts/402: 2.98 / 2.59 / 3.10e-15, 0,0,0) | 1e-10, 1e-20 | PASS |
| 13 | (c) 10 seeded states on the 24-qubit register, same pairs | error <= 1e-10; weights <= 1e-20; outer-pattern probability change <= 1e-10 | error 1.80e-15 / 1.46e-15 / 2.20e-15; ancilla and leak weight 0, 0; probability change 7.8e-17 / 6.1e-17 / 8.0e-17 (prompts/402: identical to the digits) | 1e-10, 1e-20, 1e-10 | PASS |
| 14 | read set and shape | q13: 3, q14: 5 reads; 24 qubits, 0 ancilla; best = headline | read set {13: 3, 14: 5} at all three pairs; 24 qubits, 0 ancillas; archive best = headline = `r05-F3-005`; sector sizes (190, 92, 92, 59) with smallest per-state sector weight 0.422, 0.179, 0.183, 0.112 (every state has weight in every sector) | exact | PASS |

Tolerance margins: the largest G2 error is $3.1\times10^{-15}$ against $10^{-10}$ (margin $3\times10^{4}$); the largest probability change is $8.0\times10^{-17}$ against $10^{-10}$.

## Review of the G2 amendment against prompts/402 section 3

- Section 3.0 branch: `outer_reads(qc, enc)` first; empty read set -> old path, verbatim (row 8). Verified.
- Section 3.1 static scan: matches the text (gate matrix, exact-zero entries between the two values of the bit; qubit position p = bit p). Rejects writers independent of whether the net effect is the identity (W1-W5). Passes diagonal gates (C7, C8), which section 3.2 and 3.3 then catch (errors 0.195, 2.0 and 0.146).
- Sections 3.2/3.3: run counts (63 per pair for the headline), thresholds, one global phase for the whole matrix/all states, 10 states, seed 20261120: as written. Both blocks catch the walk-sign, wrong-outer-qubit, dropped-gate and -beta mutants; the full-register block also catches the cx writes that the static scan would block, so the two guards are independent.
- A circuit that reads outer qubits and has ancillas is refused at 25 qubits (A2), as written in section 5 (planner decision; it is not exercised by the archive: best = headline has 0 ancillas). Note for the auditor: this is a limit by memory, not by physics; a future circuit of that type goes back to the planner.

## Observations (not failures)

- O1: tolerance-edge behaviour is as designed: a $10^{-8}$ rz shift is rejected (error $5.0\times10^{-9}$, i.e. the test resolves errors $\ge 10^{-10}$), a $10^{-13}$ shift is accepted (error $5.1\times10^{-14}$).
- O2: G2 now dominates the m8 wall time (112 s of 115 s) and is the largest memory user of the file (1.64 GiB, 74 % of the 2.2 GB acceptance budget). Running it next to other heavy tests in the 11 GB slice is fine (`-n 2` m8 run: no OOM).
- O3: the first launch of my sequence script (`results/tester/446/raw/`) failed on a missing `/usr/bin/time` before pytest started m8; its `m7.log/.xml` there is from that aborted launch (m7 29 passed) and its `m8.log` is empty. All numbers above come from `raw2/`. The `raw/` directory is a harmless byproduct (I did not delete it).

## Byproducts and tracked files

- `git status --short` after all runs: only `?? results/tester/446/` (untracked, mine). No tracked file was rewritten by the test runs (in particular `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` is not modified now). `scratch/tester/446/` (gitignored): copy of the planner's mutants and the rerun json. `graphify update .` run at the start (graphify-out is gitignored).
- Peak memory numbers are sums of RSS over the pytest process tree (sampled every 0.2 s), not cgroup peaks; PSS (which splits shared pages) agrees within 2 %.

## Failures

None.

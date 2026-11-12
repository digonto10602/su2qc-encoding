# Tester report 408: verification of the audit-note N1 fix (scripts/m4_results.py)

Date: 2026-11-12. Git commit: b0c51a1 (+ uncommitted scripts/m4_results.py and tests/unit/test_spinnet_m4_results_unit.py).
Prompt in force: spinnet track (audit report reports/audits/302-spinnet-m4-milestone.md). Mode: step (small scope). Cores 14-17.
Related: reports/audits/302-spinnet-m4-milestone.md, reports/tests/407.

## Commands
- `PYTHONPATH=src taskset -c 14-17 tools/run-capped python scripts/m4_results.py --quick --out $S/out` ($S = scratchpad)
- same with HEAD's script (`git show HEAD:scripts/m4_results.py`, copied next to the other scripts in $S/head2/scripts), `--root` = repo, `--out $S/outhead`
- `tools/pytest-safe -n 0 -q` on the new unit tests (fixed script) and on a copy of the test file whose SCRIPT points to the HEAD script copy
- `tools/pytest-safe -n 4 -q tests/acceptance/m4`; `pytest --collect-only -q tests/acceptance`; `python tools/check_lock.py`; `~/.claude/bin/acceptance-check`

## Results
| check | expected | got | PASS/FAIL |
|---|---|---|---|
| (1) paulo15 $T(10^{-6})$ | 316 (results/compress/spinnet/round-000.json) | 316 | PASS |
| (1) paulo15 $T(10^{-10})$ | 478 | 478 (est. $T(10^{-6})$ = 303.2) | PASS |
| (1) qiskit_l3_whole depth_CT | "-" | "-" (JSON null; HEAD gave 67 = uncompiled depth) | PASS |
| (2) all other rows vs committed m4-before-after.md / m4-compressed.json | identical | only `before_after` entries [3] qiskit_l3_whole and [8] paulo15 differ; remaining JSON diffs are provenance/timing/paths and --quick-only content (eps grid (1e-4,) in t_table, no lean block) | PASS |
| (2b) fixed vs HEAD script, same --quick config | differ only in the two external rows | `diff` of the before-after tables: exactly lines 12 and 17 | PASS |
| (3) 2 new unit tests on HEAD script | fail | 2 failed, 1 passed (`(None, None, None) != (316, 478, 303.2)`) | PASS |
| (3) new unit tests on the fixed script | pass | 3 passed (whole file) | PASS |
| (4) spinnet.loop.code_hash() | 7f5bb7f8... | 7f5bb7f8e65f39c89eca59abae352c3f36433e00523ae3321f9b6e59e54d0ed5 | PASS |
| (4) compress.provenance.code_hash() | 0bd7e7d9... | 0bd7e7d91d9d7bcfc78641d1a14bb87f0f82f932c41c601fb991d30de13a0582 | PASS |
| (5) tests/acceptance/m4 | all green | 19 passed in 44.5 s | PASS |
| (5) collect-only | clean | 341 tests collected, no collection errors | PASS |
| (5) check_lock / acceptance-check | OK | LOCK OK; PASS (matches acceptance-v18) | PASS |

## Observations
- Side effect of the fix (consistent with it): the qiskit_l3_whole row now shows $T_{est}(10^{-6}) = 534.4$ (its counts-only estimate was dropped before by the same string-key bug); measured $T$ cells stay "-". The committed before-after table (full run, commit b0d3db7) still has the old cells (paulo15 "-", qiskit_l3_whole depth 67); it changes when the coordinator regenerates with a full (non --quick) run, which I did not do.
- Files touched by my runs: results/spinnet/certs/*.json (5 files, restored with `git checkout`); other outputs in the scratchpad. results/lsh/certs unchanged. Final `git status`: only the two builder files modified.

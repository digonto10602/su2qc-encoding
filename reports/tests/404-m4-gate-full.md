# Tester report 404 — M4 milestone gate, mode `full`, spinnet track

- Date: 2026-11-11 (machine clock)
- Git: tests started at `5d5d502`; HEAD moved to `0dfe4ae` during the run (other agents' commits; rishon work uncommitted in the tree, not mine)
- Prompt in force: `prompts/104-spinnet-m4-plan.md` (§11 errata E1–E3) on `prompts/103`; acceptance lock `acceptance-v18`
- Related: `reports/tests/117-m4-round-004.md`, `reports/tests/118-*.md` (round 5, loop stop, 4.L1/4.L2/4.7)
- Raw outputs: `results/spinnet/tester/m4_gate/{acceptance.out,unit.out,lake_build.out,summary.json}`

## Verdict: PASS

All 149 acceptance tests of m0, m1, m2, m3, m3x, m4 (slow ones included) pass; all 932 unit tests pass; collection is clean; lock check and `acceptance-check` pass; the Lean build is up to date and the headline theorem elaborates.

## Commands (env `coding`, BLAS threads 1, `taskset -c 0-5`)
1. `graphify update .`
2. `cd lean && PER_JOB_MEM=12G ../tools/run-capped taskset -c 0-5 lake build Su2PlaqCert su2plaq_cert_spinnet`
3. `PYTEST_MEM_MAX=14G taskset -c 0-5 tools/pytest-safe -n 6 -p no:cacheprovider -rA --durations=15 tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m2 tests/acceptance/m3 tests/acceptance/m3x tests/acceptance/m4`
4. `PYTEST_MEM_MAX=14G taskset -c 0-5 tools/pytest-safe -n 6 -p no:cacheprovider -q --durations=10 tests/unit`
5. `pytest --collect-only -q tests/acceptance`; `python tools/check_lock.py`; `~/.claude/bin/acceptance-check` (before and after the runs)
6. `cd lean && lake env lean certs/spinnet-best-step.lean` (same resource wrapper)
7. Provenance read of `results/spinnet/m4-compressed.json`; `git diff b0d3db7 HEAD` over the spinnet code, archive, script and cert file.

## Results
| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| acceptance m0 | all pass | 34 / 34 | – | PASS |
| acceptance m1 | all pass | 22 / 22 | – | PASS |
| acceptance m2 | all pass | 46 / 46 | – | PASS |
| acceptance m3 | all pass | 24 / 24 | – | PASS |
| acceptance m3x | all pass | 4 / 4 | – | PASS |
| acceptance m4 (incl. slow, L5, R1) | all pass | 19 / 19 | – | PASS |
| acceptance total | 149 pass, 0 fail, 0 skip, 0 xfail, 0 pending | 149 passed, 0 others, 445 s | – | PASS |
| unit suite `tests/unit` | all pass | 932 passed, 0 failed, 644 s | – | PASS |
| `pytest --collect-only -q tests/acceptance` | clean | 341 collected (m0 34, m1 22, m2 46, m2c 28, m3 24, m3x 4, m4 19, m5 56, m5x 8, m6 33, m7 29, m9 28, m10 10), no errors | – | PASS |
| `tools/check_lock.py` | LOCK OK | LOCK OK | – | PASS |
| `acceptance-check` | PASS vs latest tag | PASS: matches acceptance-v18 (before and after the runs) | – | PASS |
| `lake build Su2PlaqCert su2plaq_cert_spinnet` | success | "Build completed successfully (43 jobs)" (oleans were already current; replay only, <1 s) | – | PASS |
| `lean/certs/spinnet-best-step.lean` elaborates | no error | elaborates; `'spinnet_best' depends on axioms: [propext, Classical.choice, Quot.sound, spinnet_best._native.native_decide.ax_1_1]` (the native-certified label, as in report 118) | – | PASS |
| theorem file belongs to headline | `r02-F1-002`, sha256 `750151e9…c650` | header "entry r02-F1-002, program sha256 750151e9ad41…c650"; same id and sha in `m4-compressed.json` `extra.headline` | exact | PASS |
| headline numbers in `m4-compressed.json` | valid, certified | ok true, op-norm error $5.1\times10^{-15}$, 433 inputs, Gauss residual $5.3\times10^{-16}$, leak 0, ancilla dirty 0, 31 CX, 17 qubits, engine `sparse`, `certified` true, Lean "certified" | $10^{-10}$ | PASS |
| results produced on a clean commit | `git_dirty` False | `provenance.git_commit` = `b0d3db7`, `git_dirty` = false, command `python scripts/m4_results.py`, seeds angle_set 20261107 / transpiler 20261104 / clifford_t 12345; committed afterwards as `232bb5e` | exact | PASS |

Note on the commit id: the brief names `232bb5e`. That is the commit that stored the results; the code state they were produced from is its parent `b0d3db7` (`git log -1 232bb5e^` = `b0d3db7`), which is what the provenance block records. `git diff b0d3db7 HEAD` over `src/su2plaq/spinnet`, `src/su2plaq/compress`, `compress/archive/spinnet`, `scripts/m4_results.py` shows no source change; the only difference in that set is `lean/certs/spinnet-best-step.lean` (+13 lines, the theorem part added by the step-4.7 commit).

Slowest tests (acceptance): `m1 test_M1_O1_outer_dont_care_table` 354 s, `m2 test_round_records_lean_certificate` 135 s, `m2 test_round_dry_run_end_to_end` 121 s (6 workers on a loaded machine; load average about 19–21 from other agents). No test was killed by the memory cap.

## Pending / skipped
None. No test raised `NotImplementedError`; no skip or xfail.

## Byproducts and clean-up
- Restored with `git checkout -- results/spinnet/certs` (the tests rewrote 5 tracked cert JSONs, provenance only): done, tree clean for `results/spinnet` except my new untracked `results/spinnet/tester/m4_gate/`.
- Tracked files touched by the test runs and left alone (not restored; they are shared byproducts or belong to other agents): `compress/lean/structure.json` (m2 structure tests), `results/compress/fuzzy_ub/summary.json` and `results/compress/rishon/robust.json` (could be my m2 runs or the fuzzy/rishon agents; not separable). `lean/lakefile.toml`, `lean/Su2PlaqCert/LSH/`, fuzzy round-004 files and rishon sources are other agents' work.
- The unit count (932) includes the uncommitted rishon det-term unit tests in the tree; they pass.

## Problems / assumptions
- None blocking. Deprecation warnings only (mpmath `bitcount`, 116 warnings, in m0 and m3x).
- The Lean build step was effectively a no-op (everything already built); my earlier first attempt of the command failed only because `/usr/bin/time` does not exist here, not because of Lean.

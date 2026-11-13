# Tester report 411: rishon milestone-5d gate step 1 (mode `full`), det term $\lambda_D$

- Date: 2026-11-13 (run 11:22 to 12:03 EST, plus spot checks), host omnicommander, cores 14-19 (`taskset -c 14-19`, `-n 6`)
- Git commit: `1cd9bf9` (tree: `docs/METHODS-rishon.md` modified and `prompts/205-...md` untracked = planner drafts, ignored as instructed; `compress/programs/fuzzy_ub/F3/009-...py` appeared during the run, belongs to a round-9 proposer, not touched)
- Prompt in force: `prompts/204-rishon-det-term-amendment.md` (step D7 gate), locked tests acceptance-v19
- Related: `reports/tests/410` (C1), `405` (D3-D6), `222` (D1-D2), `reports/tests/204`, `215`, `216`, `221` (milestone-5 numbers). The earlier broken run (exit 127, no environment) is not used.
- Raw logs: `results/rishon/tester-411-*` (logs, junit XML, `B-failures.json`, `spotcheck.json/.py`, `tcount-check.json/.py`, `exits.txt`)

## Commands (driver script began with conda activate coding, cd to project, OMP/OPENBLAS/MKL threads = 1; a smoke run of `tests/unit/test_rishon_det_unit.py` gave 29 passed, exit 0, before the long runs)

```
P="taskset -c 14-19 tools/pytest-safe -n 6 -q -p no:cacheprovider"
A: $P tests/acceptance/m5 tests/acceptance/m5x                                  # incl. slow
B: $P -m "not slow" tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m6,m7,m8,m9,m10}
C: $P tests/unit
D: pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
spot: python results/rishon/tester-411-spotcheck.py ; taskset -c 14-19 python results/rishon/tester-411-tcount-check.py
```

## Result table

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| A: m5 + m5x incl. slow (64 tests) | all pass | 64 passed, 0 skipped, 1027 s (slowest: M5_T1[step] 865 s, M5_T1[UB] 641 s, DT4 three-layer 153 s / 151 s) | - | PASS |
| B: m0, m1, m2, m3, m3x, m4, m7, m9, m10 not slow | all pass | 33, 21, 40, 23, 4, 12, 28, 24, 7 passed | - | PASS |
| B: m6 not slow | only G5/G6/L2/L3/L9 pending | 19 passed, 5 failed = exactly M6_G5 (`replay-204.json` missing, step C2), M6_G6 (`three-layer.json` missing, step C5), M6_L2, M6_L3 (`Laurent3.lean` missing, step 6.L2), M6_L9 (`recognise_angle_single` missing) | - | PENDING only (expected) |
| B: m8 not slow | only registry ids pending (prompts/401) | 13 passed, 9 failed, all `PENDING: cannot import su2plaq.encodings.registry`: S0, S2, S3, S4, S5, H1, L2, E1, E2 | - | PENDING only (expected) |
| B: m2c not slow (not named in the task) | - | 18 failed, all labelled `PENDING` (registry missing 8, `su2plaq.compress.replay` missing 6, `Verdict.span_leak` / `evaluate(prune_fraction=)` missing 4): consolidation plan `prompts/008` Phase B, matches STATUS "28 m2c tests PENDING" | - | PENDING only (listed separately, see Notes) |
| B: failures not labelled PENDING | 0 | 0 of 32 | - | PASS |
| C: unit suite | all pass | 961 passed, 463 s | - | PASS |
| D1: `pytest --collect-only -q tests/acceptance` | clean | 374 tests collected, no errors | - | PASS |
| D2: `python tools/check_lock.py` | LOCK OK | LOCK OK | - | PASS |
| D3: `acceptance-check` | PASS | PASS: tests/acceptance matches acceptance-v19 | - | PASS |

Totals over the whole gate run: passed = 64 + 224 + 961 = 1249 (B: 224 passed); failed (non-pending) = 0; pending = 32 (9 m8 + 5 m6 + 18 m2c). New failures against report 410: none.

## Physics spot checks of the det-term results (`results/rishon/{UD,step3,step3_order2}.json`, generated at clean commit 6fea036, `git_dirty` False, `python scripts/m5_det_results.py --jobs 4`, seed 20261104, $(\alpha,\beta,\eta)=(0.37,0.61,0.29)$)

Exact-angle verdicts (method `inner_block`, engine sparse, 1296 inner codes, tolerance `tol_err` = `tol_gauss` = $10^{-10}$, dropped cap $0.1\times10^{-10}$):

| circuit | ok / certified | op-norm error | block | leak | dropped | Gauss residual (273 states) |
|---|---|---|---|---|---|---|
| $U_D$ (UD) | True / True | $2.76\times10^{-15}$ | $1.48\times10^{-15}$ | 0 | $1.28\times10^{-15}$ | $2.15\times10^{-16}$ |
| step3 order 1 | True / True | $4.98\times10^{-13}$ | $4.74\times10^{-14}$ | 0 | $4.51\times10^{-13}$ | $3.62\times10^{-15}$ |
| step3 order 2 | True / True | $4.75\times10^{-13}$ | $4.86\times10^{-14}$ | 0 | $4.26\times10^{-13}$ | $2.36\times10^{-15}$ |

All errors are at least $2\times10^{2}$ below $10^{-10}$; all dropped values are $\le 4.5\times10^{-13}$ against the cap $10^{-11}$.

Counts and Clifford+T ($T$ at $\varepsilon$ per rotation, pygridsynth), against milestone 5 (reports 204/215/216/221, same $U_E$, $U_B$, step JSONs untouched at commit b4c1917):

| quantity | milestone 5 (no det) | with det | check |
|---|---|---|---|
| $U_D$ CX / rotations / depth | - | 32 / 8 / 10, no ancilla, 16 qubits, $T_{\rm fixed}$ 0 | plan: 8 CX + 2 rz per link on 4 links: PASS |
| $U_E$ | 8 CX, $T(10^{-6})$ 256 | unchanged JSON | PASS |
| $U_B$ | 10094 CX, $T_{\rm fixed}$ 10218, 162 rot, $T(10^{-6})$ 20394 | unchanged JSON | PASS (matches report 204) |
| step order 1 | 10102 CX, 166 rot, $T(10^{-6})$ 20650 | step3: 10134 CX, 174 rot, $T$ 21146 | $10102+32$, $166+8$, $20650+496$: PASS |
| step order 2 | 10110 CX, 170 rot, $T(10^{-6})$ 20922 | step3_order2: 10174 CX, 186 rot, $T$ 21946 | $10110+64$, $170+16$; $21946-20922=1024=2\times512$ at $\eta/2$: PASS |
| $T(\varepsilon)$ of UD at $10^{-4}, 10^{-6}, 10^{-8}, 10^{-10}$ | - | 352, **496**, 688, 816 | independent pygridsynth recount of $8\times {\rm rz}(0.58)$: 44, 62, 86, 102 per rotation, i.e. 352, 496, 688, 816: PASS |
| step3 $T(10^{-4}, 10^{-6}, 10^{-8}, 10^{-10})$ | 17326, 20650, 24282, 27482 | 17678, **21146**, 24970, 28298 | builder report values (496, 21146) reproduced: PASS |
| unchanged $U_E$/$U_B$/step verification numbers | step op-norm $4.125\times10^{-13}$, dropped $3.676\times10^{-13}$, Gauss $2.66\times10^{-15}$ (report 216) | `step.json` identical to those digits | PASS |

Synthesised (Clifford+T) verification at the four $\varepsilon$ (all `t_matches_table` True). At $\varepsilon\in\{10^{-6},10^{-8},10^{-10}\}$ every circuit is ok / certified on the sparse engine and the measured error is below the budget $N_{\rm rot}\varepsilon+10^{-9}$ (for example step3 at $10^{-6}$: $2.05\times10^{-5}\le1.74\times10^{-4}$; UD at $10^{-6}$: $3.84\times10^{-6}\le8.0\times10^{-6}$; step3_order2 at $10^{-6}$: $2.25\times10^{-5}\le1.86\times10^{-4}$). **Exception, see Notes: $\varepsilon=10^{-4}$ of step3 and step3_order2.**

Outer det row (`UD_outer_row_certified.json`, method `outer_det_gadgets`, 12 links): CX 96, 24 rotations, 14 gates per link; per-link error $3.33\times10^{-16}$ each, bound $=12\times3.331\times10^{-16}=3.997\times10^{-15}$ (recomputed), $\le10^{-10}$: PASS (expected $\approx4.0\times10^{-15}$). Phase $1-6.4\times10^{-17}i$. The DT7 result-file tests and observables test in m5 all passed in run A.

## Notes (no blocking failure)

1. **step3 and step3_order2 at $\varepsilon=10^{-4}$: synthesised verdict `ok False`, reason `leak`** (engine `aer_mps`, not sparse; synth wall 52 070 s and 52 332 s). Values: step3 op-norm $2.14\times10^{-2}$ vs budget $1.74\times10^{-2}$ (block $2.07\times10^{-3}$, leak amplitude bound $1.93\times10^{-2}$, per-input max leak $3.7\times10^{-4}$); order 2: $2.29\times10^{-2}$ vs $1.86\times10^{-2}$. For comparison the det-free `step` at the same $\varepsilon$ is ok on the sparse engine (leak $2.2\times10^{-3}$, block $1.9\times10^{-3}$). The block error ($2\times10^{-3}$) is far inside the budget; the failure is the combined leak bound from the MPS path, which is pessimistic. No locked test asks for this row (DT7 checks only the exact-angle verdict and the 4-row table length), so it is not a gate failure. It is a cosmetic gap in the results file, since the `t_table` for these two rows contains a non-ok synth verdict. Guess: the sparse engine's cap was exceeded at this $\varepsilon$ and the fallback bound $\sqrt{\cdot}$-pessimism of Aer MPS exceeds the budget. Suggest a one-line wording in the Report 5 addendum, or a planner decision on whether to rerun with a sparse-capable engine; I did not change anything.
2. m2c (prompts/008 consolidation) contributes 18 PENDING failures; the task text listed only m8 and m6 as expected. They are all `PENDING:`-labelled and consistent with STATUS (Phase B not started). If the gate wants zero PENDING outside m6/m8 these count against it; otherwise nothing is red.
3. M6 pending ids are exactly the five named; none of them belongs to the det-term D1-D7 milestone-5d ids.
4. `M5_T1[step]` took 865 s in this run (plan quoted 581-671 s in a single process; it was one of six parallel workers). Not a failure; it is `slow`-marked by design.

## Files touched

- New (all under `results/rishon/`): `tester-411-*` (logs, XML, spotcheck, tcount check, exits, git-status-before, start) and the two scripts. Report: `reports/tests/411-rishon-milestone-5d-full.md`.
- Test byproducts, restored with `git checkout --` afterwards: `results/compress/fuzzy_link/summary.json`, `results/compress/rishon/robust.json` (only the `evaluator_sha256` line changed), `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `spinnet-UB-o1-458a39365261.json`, `spinnet-UE-o1-df0c79b22d3f.json`, `spinnet-step-o1-b0a415d9322f.json`. After the restore `git status` shows only the pre-existing `docs/METHODS-rishon.md` and `prompts/205`, plus the proposer's `compress/programs/fuzzy_ub/F3/009-...py` and my `tester-411-*` files.
- No source, test, lock or tolerance was edited; no commit made.

## Verdict

**PASS** for milestone-5d gate step 1 (mode full): 1249 passed, 0 failed, 32 pending (9 m8 + 5 m6 + 18 m2c, all `PENDING`-labelled), 0 new failures relative to report 410, lock/collect/acceptance-check all PASS.

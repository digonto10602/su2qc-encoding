# Tester report 116 — M4 step 4.3b "headline rule" (erratum E3), track S, mode `step`

- Date: 2026-11-07/08 (machine clock; the run was interrupted once by the API usage limit and resumed)
- Commit: `d806bf5` (HEAD, contains acceptance-v13 `fd60843`) plus the uncommitted builder work: `src/su2plaq/spinnet/loop.py`, `tests/unit/test_spinnet_loop_unit.py`, new `results/compress/spinnet/robust.json`. Branch `m3-spin-network`.
- Prompt in force: `prompts/104-spinnet-m4-plan.md` (§11 erratum E3, "Interface additions")
- Related: `reports/tests/115-m4-round-003.md` (the nominal-angle finding that triggered E3)
- Raw numbers and scripts: `results/spinnet/tester/4_3b/` (`probe_a.py`, `probe_b.py` + `sens_T_b.py`, `probe_c2.py`, `probe_d.py`, `probe_e.py`, `spec_diff.txt`, `headline_cli.json`, `certify_best.json`, `m4_all.txt`, `s8s9.txt`, `unit.txt`, `*.err` = `/usr/bin/time -v`)

## Verdict: PASS

All checks asked for pass. The only red items are the two expected ones: `test_M4_L5` and `test_M4_R1` (missing step-4.7 artefacts), and the unit test `test_committed_spec_file_is_current`, whose diff is exactly the new headline section (4 added lines, 0 removed).

## Commands (env `su2qc-coding`, `PYTHONPATH=src`, one thread per BLAS, `taskset -c 0-9`, `-p no:cacheprovider`, `PATH` with `~/.elan/bin`; at most 4 jobs at a time)
1. `graphify update .`; `graphify affected robust_metrics` / `headline` (callers: `headline`, `certify_best`, `report_table`, `main`, tests S8/S9, all covered below).
2. `pytest -q tests/acceptance/m4 -k "S8 or S9" -m "slow or not slow" -rA`
3. `pytest -n 3 -q tests/acceptance/m4 -m "slow or not slow" -rA` (all 19 m4 tests)
4. `pytest -n 1 -q tests/unit`
5. `python tools/check_lock.py`; `~/.claude/bin/acceptance-check`
6. Probes (a) to (g) below; `python -m su2plaq.spinnet.loop headline`; `python -m su2plaq.spinnet.loop certify-best --root <tmp copy>`.

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| m4 S8 (angle set, robust_metrics) | pass | passed | - | PASS |
| m4 S9 (headline selection, slow) | pass | passed (S8+S9 together 67 s) | - | PASS |
| m4 S0 to S7 | pass | 8/8 passed | - | PASS |
| m4 G1, G2, G3 | pass | 3/3 passed | - | PASS |
| m4 L1 to L4 | pass | 4/4 passed | - | PASS |
| m4 L5 | fails only for the missing theorem file | all headline-lean assertions passed; fails at `assert f.exists()` "write_theorem_file for the headline circuit (step 4.7)" | - | expected |
| m4 R1 | fails only for the missing results file | fails at `assert f.exists()` "run scripts/m4_results.py" | - | expected |
| m4 total | 17 pass + 2 expected | 17 passed, 2 failed in 125 s | - | PASS |
| tests/unit | green except spec-file test | 550 passed, 1 failed (`test_committed_spec_file_is_current`) in 660 s | - | PASS |
| spec file diff | only the new section | `render_spec()` vs `compress/specs/spinnet-step.md`: 0 lines removed, 4 added (blank, `## Headline rule (track S)`, blank, the paragraph); added text equals `HEADLINE_RULE_SECTION` and the plan's Decision 2 text (ASCII `+-pi/4`, `pi/2`) | exact | PASS |
| `tools/check_lock.py` | LOCK OK | `LOCK OK` | - | PASS |
| `acceptance-check` | PASS (v13) | `PASS: tests/acceptance matches acceptance-v13` | - | PASS |

### Independent probes
- **(a) angle set.** My own `default_rng(20261107)`: 20 alphas $\in[0.05,2.0)$ first, then 20 betas $\in[0.05,1.2)$, pairs as Python floats. Equal to `loop.ANGLE_SET` exactly; sha256 (of `repr` of the tuple of pairs) own = loop = cache = `769caec1c2738356f2e5a4f51adc1d286ce3bb585c034c7a98950df701e3cbb2`; cache holds seed 20261107, n = 20 and the same pairs. PASS. (The sha definition is the spec's, so the sha check is only as independent as that definition.)
- **(b) $\sum T$ over the 20 pairs.** My own `transpile` (basis cx,h,s,sdg,t,tdg,rz,p,x,z,cz, level 0) + `pygridsynth` at $\varepsilon=10^{-6}$ on my regenerated pairs (script derived from the report-115 tester script, not the loop code). Per-pair T equal to `robust.json::t_eps` at all 20 pairs for all three entries (max $|d|=0$):

| entry | own $\sum T$ | cache $\sum T$ | own CX | cache CX |
|---|---|---|---|---|
| r02-F1-002 | 21840 | 21840 | 31 | 31 |
| r03-F1-003 | 21840 | 21840 | 31 | 31 |
| r02-F2-002 | 16948 | 16948 | 32 | 32 |

  PASS (the three 31-CX programs tie exactly at $\bar T=1092.0$, as the plan table says; the round-3 saving is zero on this set).
- **(c) $\rho$ (angle-linearity) by my own fit.** For every rotation (rz/p after lowering) fitted $\theta=c_\alpha\alpha+c_\beta\beta+c_0$ over 6 pairs; linear iff residual $<10^{-9}$ and $c_0\equiv0 \pmod{2\pi}$. All 18 archive entries agree with the cache `angle_linear`: r02-F1-002 linear (17 rotations, 0 bad); r03-F1-003 and r03-F2-003 not (8 rotations with $c_0=\pi/4$, slope $\pm3/4$); r03-F3-003 / r02-F3-002 not ($c_0=\pm\pi/2$, 4 rotations); r01-F5-001 not (one `rz`, $c_0=-\pi/4$); the rest linear. Note: with a lenient criterion ($c_0\equiv0 \pmod{\pi/2}$) the F3 programs would count as linear; the exporter (and so the rule) counts an embedded $\pi/2$ offset as non-linear, which is what the plan says ("multiples of $\pi/2$ belong in separate `s`/`sdg`/`z` gates"). PASS.
- **(d) ranking and tie-break.** Independent sort of `robust.json` (key recomputed from the raw `t_eps`, `depth_ct` lists, $\rho$ from `export_status`) by (CX, $\sum T$, $\rho$, $\sum$depth, qubits, laptop key, id): identical to `loop headline` ranking (18 = 18 valid entries, none unrankable). The full tie among r00-seed-000/010/011 (54, 11212, 0, 16945, 23) is resolved by id; the $\rho$ rule orders r02-F1-002 ($\rho=0$) before r03-F2-003 and r03-F1-003 ($\rho=1$), which then order by depth (45882 < 46141). PASS.
- **(e) cache invalidation** (tmp copy of `compress/` and `results/compress/`, counting stub for `robust_metrics`): warm cache 0 recomputed; cached `program_sha256` of one entry altered: 1 recomputed; cached angle-set sha altered: 18; cached evaluator sha altered: 18; `refresh=True`: 18; warm again: 0. Archive entry sha altered (program file no longer matches): `RuntimeError: program file of r02-F1-002 ... differs from the archived sha256` (never uses a stale program). PASS. Cache file is current: `loop headline` on the real tree took 1.7 s, did not rewrite `robust.json` (byte-identical to the builder's file).
- **(f) headline.** `loop headline`: `r02-F1-002`, robust key $(31, 21840, 0, 46024, 17)$, $\bar T=1092.0$, Lean `certified`; `archive_best` = `r03-F1-003` with robust key $(31, 21840, 1, 46141, 17)$. Equals the expected value. PASS.
- **(g) laptop-owned files.** `git diff --name-only HEAD` after cleanup: only `src/su2plaq/spinnet/loop.py` and `tests/unit/test_spinnet_loop_unit.py` (+ untracked `robust.json`). `evaluate.py` (`ALLOWED_IMPORTS`), the sandbox and all laptop files untouched; `SPINNET_CODE_FILES` do not include `loop.py`, so the code hash recorded in rounds is unchanged. S2/S5/S7 (sandbox, rejections, twelve untouched) pass. PASS.

### Extra checks
- `make_brief(5, F1)` on the tmp copy: exactly one `## Output` and one `## Headline rule (track S)`, in that order; the section is the last one. PASS.
- `certify-best` on the tmp copy: archive best `r03-F1-003` gets `n_a non_linear_angle:p:1.0628981633974481` (unchanged); the headline `r02-F1-002` is re-certified through the same path: `certified` (2.7 s). The cert JSON it writes lands in the real `results/spinnet/certs/` (laptop code ignores `--root` for certs); the content is identical up to a timing field and I restored it. PASS.
- `report_table` (run by the m4 tests on the real tree) wrote `summary.json` with `headline` = `{id: r02-F1-002, robust_key: [31,21840,0,46024,17], t_mean: 1092.0, angle_set_sha256: 769c...}`, 18 `t_avg` values, and `t_avg` per lineage item (copy kept in `summary_after_tests.json`). PASS.

## Cost
Wall times: S8+S9 67 s; full m4 125 s (`-n 3`); unit 660 s (`-n 1`); cached `headline` 1.7 s; one `sens_T_b` run 7 to 9 s per entry. Peak RSS of a single process: unit 6.8 GB (largest), m4 0.83 GB, others $\le 0.3$ GB; never above the 10 GB cap. Estimated cold cost of `headline`: about 10 s per entry (per plan), not re-measured.

## Notes (no failures)
- N1. The cache key includes `spinnet_code_sha256` and the evaluator sha: any edit of a `SPINNET_CODE_FILES` entry or a laptop evaluator file recomputes all 18 entries (about 3 min). `loop.py` itself is not in that hash. The committed `robust.json` is valid for the tree as tested.
- N2. The test runs rewrote or created `results/compress/spinnet/summary.json`, five tracked cert JSONs and `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`; I restored (`git checkout`) or removed them. Left in the tree: the three builder files plus `results/spinnet/tester/4_3b/`.
- N3. For the coordinator: the committed `compress/specs/spinnet-step.md` must be regenerated once the round-4 proposers are done, which turns the one red unit test green.

## Failures
None. Expected non-green: m4 L5 and R1 (step 4.7), unit `test_committed_spec_file_is_current` (spec file deliberately not regenerated).

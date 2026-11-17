# Report 423: tester, milestone M11 steps 11.6 and 11.7 (result files and tables: `crosscheck/report.py`, `scripts/m11_results.py`)

- Date: 2026-11-17. Mode: step. Commit under test: `7d0a99c` plus the uncommitted builder files (`src/su2plaq/crosscheck/{report,limits,ks}.py`, `scripts/m11_results.py`, `tests/unit/test_crosscheck_{report,limits}_unit.py`, untracked `results/crosscheck/{spectra.json,gate-table.json,tradeoff.pdf,tables.md}`).
- Plan in force: `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` §5.4, §7 rows 11.6 and 11.7, §8. Related: reports/tests/421, 422.
- Raw numbers: `results/tester/423-m11-s6-7.json`. Scratch scripts and the two re-run trees are under the session scratchpad.
- Resources: `taskset -c 0-8`, `-n 3`, inside `tools/pytest-safe` / `tools/run-capped`. The other builder's `compress/*` diffs were ignored.

## Commands

```
taskset -c 0-8 tools/pytest-safe -n 3 -m "not slow" tests/acceptance/m11 -q -rA
taskset -c 0-8 tools/run-capped python scripts/m11_results.py --root <scratch rootA2>   # twice (A2, B2), roots = symlinks to results/*, compress/, lean, docs, refs
python (own recompute of Table 1 / Table 2 general cells from results/<enc>/step*.json); own recompute of spectra.json entries
mv results/crosscheck results/crosscheck.moved_by_tester; taskset -c 0-8 tools/pytest-safe -n 3 tests/unit/test_crosscheck_{ks,embed,limits,report}_unit.py tests/unit/test_m9_results_script_unit.py -q; mv back
python hashes.py ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; pytest --collect-only -q tests/acceptance
```

## Verdict: PASS

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| m11 not-slow | R1, T1 green, T2 PENDING "rows not final", rest as in 422 | 23 passed, 1 failed. T2 fails with `PENDING: rows not final: {...}` (all five rows pending). R1 and T1 pass. All of 421/422's greens still pass (K1 K2 K3 E1 E1_det F3 E2 E3[1.0] F1 F2); H1 passed, not judged | exact | PASS |
| collect-only | 407 | 407 | exact | PASS |
| tracked results files unchanged | none rewritten | sha256 of all tracked `results/` files equal before and after (no restore needed) | exact | PASS |
| unit tests without `results/crosscheck` | pass | 50 passed in 64 s (ks, embed, limits, report, m9 script) with the directory moved away; no `results/crosscheck` was created by them; directory put back with its four files | exact | PASS |
| six hashes vs report 420 | equal | provenance `99663fa6…e37`, lsh `88e0d76b…1ca`, spinnet `10f5727f…15c`, fuzzy_ub = fuzzy_link `b4bd20fe…7f9`, rishon `5f5decfa…f23`, spinnet loop `f1314a01…3d4`: all equal | exact | PASS |
| `acceptance-check`, `check_lock.py` | pass | "PASS: tests/acceptance matches acceptance-v22", "LOCK OK" | exact | PASS |

### Table 1 and general columns of Table 2 recomputed from the source files

Every filled cell is a general-circuit cell (all headline cells are pending, see below). I read `metrics.logical` and the `t_table` row with $\varepsilon=10^{-6}$ (`t_total`, and checked $=t_{\rm fixed}+t_{\rm rot}$) directly from the files named in the cells, and the `provenance` commit and dirty flag for the source string.

| row | file | qubits | CX | n_rot | T fixed | T(1e-6) | source string | state count | result |
|---|---|---|---|---|---|---|---|---|---|
| twelve (A) | results/twelve/step.json @ a9702e5 | 34 | 294 | 10 | 312 | 952 | equal | 433 | PASS |
| spinnet (A) | results/spinnet/step.json @ d82a472 | 15 | 54 | 8 | 56 | 566 | equal | 433 | PASS |
| lsh (A) | results/lsh/step.json @ 76fd221 | 19 | 94 | 8 | 88 | 598 | equal | 433 | PASS |
| rishon (B) | results/rishon/step3.json @ 6fea036 | 26 | 10134 | 174 | 10218 | 21146 | equal | 38 432 | PASS |
| rishon two-layer | results/rishon/step.json @ b4c1917 | 26 | 10102 | 166 | 10218 | 20650 | equal | | PASS |
| fuzzy (C) | results/fuzzy/step.json @ 8e71c38 (dirty) | 23 | 1862 | 56 | 1826 | 5398 | equal | 101 197 218 | PASS |

No wrong number or source path. The state counts 433 and 38 432 are the physical-basis dimensions used elsewhere; 101 197 218 matches `docs/METHODS-fuzzy.md` and `compress/specs/fuzzy-structure.json` (Lean `count_fixed_far_end`). `tables.md` Table 1 and Table 2 show the same numbers (294/952, 54/566, 94/598, 10134/21146, 1862/5398; rishon two-layer CX 10102 in the note). The block labels A, A, A, B, C and `comparable_with` lists are as in the plan.

### Pending cells: is each reason true?

| row | reason in the file | what I found | true? |
|---|---|---|---|
| twelve | no cache file `results/compress/twelve/robust.json` | file absent (`results/compress/twelve/` has only round files and feedback) | yes |
| spinnet | `robust.json` present but stale for the current code hash | `robust.json` has `evaluator_sha256` `0bd7e7d9…0582` (the B0 hash); current stamp hash is `99663fa6…`; `_load_cache` returns {} on that mismatch | yes |
| lsh | the lsh archive has no ranked valid entry | no `compress/archive/lsh`, no `results/compress/lsh` at all; headline returns id None. True, though the wording understates it: there is no archive yet | yes (wording note) |
| rishon | stale `robust.json`; `three-layer.json` missing | `evaluator_sha256` `ddb440ad…` vs current `5f5decfa…`; `results/compress/rishon/three-layer.json` absent | yes |
| fuzzy | no cache for `fuzzy_ub`, `fuzzy_link`; units pending | `results/compress/fuzzy_ub/` and `fuzzy_link/` have round files but no `robust.json`; `results/fuzzy/compressed_step_headline.json` absent (only the older `compressed_step.json` exists) | yes |

"Waits for" targets (Phase C replay, prompts/204-205, M8 phases 1-2, prompts/010 H.2/H.3) are the right ones per STATUS and the prompts.

Because every row is pending, the headline, T-first, Pareto, fuzzy-composition and `headline_with_det` code paths are not exercised by the real files. I exercised them with a synthetic ranking (monkeypatching `_cached_headline`, same functions otherwise): headline picked the smallest robust key (b: CX 17, T 1000), T-first the smallest $\bar T$ (c: $\bar T=486.7$), Pareto points (b, d, c) correct and the dominated entry dropped, fuzzy composition CX $=17+4\times17=85$, $\bar T=1000+4\times1000=5000$ (T-first $486.7\times5=2433.5$), `headline_with_det` read from `three_layer_key` ([260, 1342] gives CX 260, T 1342), status "final" for the three KS rows and pending (missing file) for rishon and fuzzy. A `three-layer.json` without `three_layer_key` raises `KeyError('three_layer_key')` out of `gate_table` (propagates, no catch).

### Reruns and diff

`scripts/m11_results.py --root <scratch>` twice: 62 s and 68 s, exit 0. Differences between the two runs: `provenance.command` (root path), `provenance.timestamp_utc`, and `seconds` of the three cross-verdicts. Nothing else (gate-table.json differs only in command and timestamp; `tables.md` and `tradeoff.pdf` byte-identical). Against the builder's files in `results/crosscheck`: the same plus `provenance.git_commit` (`7d0a99c` vs the builder's `cdef450`, HEAD has moved). `tables.md` and `tradeoff.pdf` are byte-identical to the builder's. The figure shows six empty panels "pending: no cached headline" (twelve, spinnet, lsh, rishon, fuzzy_ub, fuzzy_link), as expected.

### spectra.json against reports 421 and 422

| quantity | spectra.json | my earlier number | result |
|---|---|---|---|
| largest level difference of the 3 encodings, $g^2=0.5,1,2$ (with outer electric) | 2.7534e-14, 1.1990e-14, 2.6645e-14 | 421: 2.75e-14 (0.5), 1.20e-14 (1), 2.66e-14 (2) | PASS (identical) |
| `transported_target_max` | 3.0373e-15 | 421: 3.04e-15 | PASS |
| $H_B$ multiplicities | 16, 96, 16, 177, 16, 96, 16 in all three | same | PASS |
| cross-verdict total errors (twelve/lsh, spinnet/twelve, lsh/spinnet) | 2.7214e-13, 1.1050e-14, 1.6484e-14; all ok, certified, 0 outer bits | 421: same to all digits | PASS |
| mutant ($\beta+10^{-6}$) block error | 2.0000000012e-6, 2.0000000018e-6, 2.0000000034e-6, `ok` False | 421: identical | PASS (window $[1.9,2.1]\times10^{-6}$) |
| squared leaks U | 0.5, 0.5, 0.5, 0.5, 1, 1 | exact 1/2, 1 | PASS |
| squared leaks plaquette | 15, 15, 4.125, 4.125, 4, 4 (15 - 2.7e-14; 4.125 - 7e-15; 4 - 2.7e-15) | exact 15, 33/8, 4 | PASS |
| embedding residuals | all $\le4.7\times10^{-16}$, $[P,L],[P,R]$ 0.0, phase $(1,0)$ and $(0,1)$ for rishon_minus | 421 | PASS |
| rishon blocks | 305, largest 4352 | 422 | PASS |
| rishon full-space limit, 433 levels, $g^2=0.5$/1/2, $L=64$,128 | $L\cdot$dev 7.0814/7.0947, 2.1988/2.1972, 0.7487/0.7465; gaps 246.48/502.47, 248.75/504.74, 246.41/502.40 | 422: 0.11065, 0.055427 etc. (L dev 7.0814, 7.0947, ...) agree to $3\times10^{-15}$ | PASS |
| rishon closed-sector rows (21), predicted coefficients | predicted coefficient exactly $-\tfrac{13}{4g^4}w_k$ (difference 0 from my own formula); deviations equal my recomputation of the 17 x 17 R13 formula to $6.5\times10^{-9}$ in $L\cdot$dev (rounding of $c_E\sim 10^3$ cancellations), at $g^2=2$, $L=1024$: $L\cdot$dev $=-0.74454$ vs predicted $-0.74427$ | 422 E2 | PASS |
| fuzzy flavour sectors | 16 sectors, dims 2 (x2: (+,+,-,-), (-,-,+,+)), 4 (x2), 3 (x12); KS distance $\le1.8\times10^{-15}$ for the two, $\ge0.6076$ for the other 14 | 422 | PASS |
| fuzzy isolated | splitting $\le5\times10^{-15}$, third level 7.810/3.600/0.8446, slopes 7.00044 ($K_2$) and 7.02865 ($r=1$), $E_1-E_0$ over $2g^2$ at 16: 0.99995529 / 0.99999729 | 422 | PASS |
| $\mathcal K_2$ on embeddings | $[-4,2,2,2,2]$, $[4,-2,-2,-2,-2]$ | F3 | PASS |
| closed-sector table (KS 2, rishon 17 at $\lambda_D=0,0.2,0.5$, fuzzy 9 and 12 levels, three $g^2$) | recomputed from `rishon.operators.closed_block_full`, `fuzzy.observables.closed_sector`, the KS 2 x 2 block | max difference $1.4\times10^{-14}$ | PASS |
| `not_comparable` rishon step distance to KS step | 1.9904120121517077 | `results/rishon/ks_projection.json` value read by me: 1.9904120121517077 | PASS |
| dropped images record | HB: 0 images outside the code, weight 0.0, 0 code entries below 1e-14, 6428 zeroed entries, max $4.72\times10^{-16}$; HD: 0 images outside, 38 448 zeroed, max $2.08\times10^{-16}$ | requested: 0 outside-code images, zeroed entries at most $5\times10^{-16}$; consistent with `det_sector_structure` leaving weight $1.6\times10^{-25}$ (422 O1) | PASS |

### Code review

| item | finding | result |
|---|---|---|
| numbers come from files | cross-verdicts, levels, embeddings, closed-sector table, general cells, headlines, `not_comparable` are computed or read. Typed constants are parameters or definitions: $g^2$ list, $L$ lists, angle pairs, the KS 2 x 2 block formula, the per-row `n_physical_states` (433, 433, 433, 38 432, 101 197 218) and block labels (the plan fixes these as facts; not read from a file, noted) | PASS (note) |
| silent exceptions | no `try`/`except` in `report.py`, `limits.py`, `ks.py`, `scripts/m11_results.py`; the `three_layer_key` `KeyError` propagates (tested above) | PASS |
| read-only caches | `_rishon_phys_ops` (sparse arrays, labels), `_fuzzy_isolated_blocks`, `_flavour_blocks` are now frozen: item assignment on each raises `ValueError: assignment destination is read-only`. This closes the 422 observation | PASS |
| `step_circuit(..., root=)` added | default behaviour unchanged (root defaults to the checkout); acceptance K3 and the cross-verdicts are unchanged | PASS |
| `git_dirty: true` in the files | present in both files (builder's tree is dirty); expected until 11.8 regenerates them on a clean commit | note only |
| hashed files / acceptance | `git diff --stat`: only crosscheck package, `scripts/m11_results.py`, the unit tests, plus the other builder's `compress/*`; no hashed file, nothing under `tests/acceptance` | PASS |

## Observations (not failures)

- O1: the LSH pending reason reads "no ranked valid entry" while the real situation is "no LSH archive exists yet"; the text is true but could say so.
- O2: `spectra.json` and `gate-table.json` carry `git_commit` `cdef450` and `git_dirty: true`; 11.8 must regenerate them from a clean commit (T2 also checks clean provenance).
- O3: the closed-sector rows $L\cdot$dev at $L=1024$ reproduce to $6.5\times10^{-9}$ only, because $c_E\approx-2700$ and the levels are shifted by $8L$; R1's recomputation tolerance ($10^{-6}$) leaves a factor 150.
- O4: my own scratch run created a stray directory `./$S/` in the project root (an unexpanded variable in a heredoc); it contained only symlinks and one test file, and I removed it. `git status` shows no trace of it.

## Counts

passed: 23 acceptance (not slow) + 50 unit; failed: 0; pending: 1 (T2, "rows not final", as expected before Phase C, M8 and prompts/010 H.3). R1 and T1 newly green. H1 passed, not judged. New failures versus report 422: none.

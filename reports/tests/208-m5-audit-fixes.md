# Report 208 — M5 audit fixes N4, N5, N7, N8 (tester, mode `step`, desktop track R)

- Date: 2026-11-06
- Commit: `b2e258f` (HEAD) plus the builder's uncommitted working tree (`git status`: 5 modified src/docs files, 2 modified unit-test files)
- Prompt in force: `prompts/200-rishon-m5-plan.md` (+ one-off test fix `prompts/201`); acceptance tag `acceptance-v8`
- Related: `reports/tests/207` (gate full PASS), `reports/audits/200-m5-rishon-audit.md` (notes N4, N5, N7, N8)
- Raw files: `results/rishon/tester-208-*` (logs, junit XML, `.time`, scripts, JSON)

## Commands (env `su2qc-coding`, `OMP/OPENBLAS/MKL_NUM_THREADS=1`, all under `taskset -c 10-19`, `pytest -n 10`)
```
results/rishon/tester-208-run.sh      # pytest tests/unit; tests/acceptance/m0; m1; m5 (incl. slow T1); acceptance-check; tools/check_lock.py
python results/rishon/tester-208-closed-block.py        # own 17-state closed block (own global-JW operators), item 2
python results/rishon/tester-208-adversarial.py         # copy of tester-203 adversarial verify suite, item 3
PYTHONPATH=src python results/rishon/tester-208-observables-regen.py   # item 5
python results/rishon/tester-208-rebuild-circuits.py    # item 5 (UE, UB vs committed .qpy)
```
No source, test, prompt or tolerance file was edited.

## Results

| check | expected | got | tolerance | verdict |
|---|---|---|---|---|
| `tests/unit` | all pass | 312 passed (308 + the 4 new tests), 119 s, peak RSS 6.8 GB | exact | PASS |
| `tests/acceptance/m0` | all pass | 34 passed, 13 s | exact | PASS |
| `tests/acceptance/m1` | all pass | 22 passed, 104 s | exact | PASS |
| `tests/acceptance/m5` incl. slow T1 | all pass | 34 passed, 0 failed/skipped, 840.6 s, peak RSS 6.8 GB | exact | PASS |
| `acceptance-check` / `tools/check_lock.py` | PASS | "PASS: tests/acceptance matches acceptance-v8", exit 0 / "LOCK OK" | — | PASS |
| acceptance m5 pending | none | 0 pending | — | PASS |
| 17-basis states of `closed_block_full` | 16 vacuum codes + loop | own build: 16 codes with every link A (`0b0011`) or B (`0b1100`) = exactly the 16 inner codes with $H_E=0$ (set equality); loop = $W\lvert{\rm vac}_A\rangle/4$ (norm 4, support 16 codes, overlap with vacuum codes 0.0); Gram deviation $\lVert BB^T-1\rVert_\infty=0.0$ | 1e-12 | PASS |
| span invariance under $H$ (own 1296-dim operators) | residual 0 | $\lVert HB^T-B^T(BHB^T)\rVert_\infty=0.0$ at g² = 0.5, 1, 2 | 1e-10 | PASS |
| $W$ and $W^\dagger$ on the 16 vacuum codes | only vac_A, vac_B couple to the loop | $\lVert W\lvert{\rm vac}\rangle\rVert$ = 4 for exactly one code, $\lVert W^\dagger\lvert{\rm vac}\rangle\rVert$ = 4 for exactly one code, 0 for the other 14 | exact | PASS |
| `closed_block_full(g²)` vs own 17×17 block | identical | max entry difference 0.0 at g² ∈ {0.5, 1, 2} | 1e-12 | PASS |
| `closed_spectra()` eigenvalues vs own | ≤ 1e-12, mult 1, 15, 1 | diffs 5.0e-16 / 8.8e-17 / 2.3e-16; multiplicities [1, 15, 1] at all three g² | 1e-12 | PASS |
| committed `observables.json` `closed_spectra` vs own | ≤ 1e-12, mult 1, 15, 1 | diffs 5.0e-16 / 8.8e-17 / 2.3e-16; multiplicities [1, 15, 1] | 1e-12 | PASS |
| closed form $\tfrac34 g^2\pm\sqrt{\tfrac{9}{16}g^4+32/g^4}$ and 0 | match | max diff 1.8e-15 (g² = 0.5, 1), 2.5e-16 (g² = 2) | 1e-12 | PASS |
| invariance check fires (monkeypatched $H_B^{\rm in}$ + 1e-3 coupling) | `ValueError` | raised for: vac code k=5 ↔ outside code, a loop-support code ↔ outside code, vac_A ↔ outside code ("not invariant under H"); an in-sector coupling vac_1 ↔ vac_2 (0.5) does not raise and shows up as block entry 0.5 | — | PASS |
| verify adversarial suite (36 circuits) vs tester-203 | identical | 36/36 cases: same `ok`, same `reason`, same numbers (max numeric diff 0 at 1e-12); 0 false accepts, 0 exceptions (so the new `RuntimeError` never fired); reasons: 12 outer_read_unsupported, 10 error, 5 ok, 4 disallowed_gate, 3 writes_outer, 1 dirty_ancilla, 1 bad_layout | exact | PASS |
| classify path on valid circuits | no raise | `classify_outer_gates` on committed UE (16 q), UB, step, step_order2 (26 q): no raise, 0 outer qubits read; `verify` of a valid circuit has no `classify_error` key (unit test) | — | PASS |
| docs: outer electric row | code = text | `outer_electric_check`: codes from `physical_vectors("sample")` = 17 closed + 256 seeded (`n_sample=256`, seed `SEED = 20261104`), subsampled to ≤ `n_codes` (4000 in `scripts/m5_results.py` `SAMPLES["outer"]`), target $e^{-\frac34 i\alpha\#Q}$ up to one fitted global phase; `results/rishon/UE_outer_row.json`: `sampled: true`, `certified: false`, `n_codes` 3515 (< 4000, so the cap did not bind), `max_error` 1.4e-16, seed 20261104 | — | PASS |
| docs: ccx wording | matches `build_UB` | `_pair_ops` uses `ccx` chain + `crx`; no `rccx` anywhere in `circuits/rishon.py` executable code; `UB.qasm3` has 1402 `ccx`, 0 `rccx`; reports/tests/204 N1 is the cited rejection | — | PASS |
| rebuild vs committed circuits | equal | `build_UE(0.37)` and `build_UB(0.61)` equal to committed `.qpy` (12 and 4277 ops), stored sha256 matches files | exact | PASS |
| observables regeneration with current tree vs committed `observables.json` | 0 diffs | `repr`-identical floats, 0 differences (max numeric diff 0.0), incl. `closed_spectra` (exact same eigenvalue repr, mult [1, 15, 1]) | exact | PASS |

## Item 3 detail (verify.py)
Old: `except ValueError: read = set()` swallowed the classify error and relied on `evaluate`. New: error text stored in `extra["classify_error"]`; after `evaluate`, if `classify_error` is set and `iv.ok` or `iv.reason` is not in {`bad_layout`, `writes_outer`, `disallowed_gate`}, a `RuntimeError` is raised. Both code paths see the same exceptions (`evaluate` re-runs `layout_of`, `_translate`, `_outer_reads` on the same circuit), so a valid circuit cannot reach the error path; the only way is an inconsistency between `classify_outer_gates` and `evaluate`, which is what the assert is for (unit test with a monkeypatched `classify_outer_gates` raises `RuntimeError`). The only `except` left in `verify.py` is `ss.SimCapExceeded` (reported as `unsimulable`, unchanged); the diff removes the only bare-`ValueError` swallow. Side note (no action): the committed `UE_outer_row.qpy` raises `OuterWriteError` in `classify_outer_gates` (CX onto the outer qubits, restored); it is by design not sent through `verify` but through `outer_electric_check`; if it were sent through `verify` the result would still be `writes_outer` with the message now recorded.

## Item 5: regeneration needed?
No. The changes since `b4c1917` (the commit the committed `results/rishon/*.json` were generated at, `git_dirty: false`) in code that results use: `closed_spectra` (now computed, not typed-in zeros) and `verify` extra key (only added on error). Measured: observables table byte-for-byte equal in float `repr`; UE and UB rebuilt equal the committed `.qpy`; `circuits/rishon.py` diff is docstring only. Stored provenance (`git_commit` b4c1917) stays true for every number. A regeneration would only change the recorded commit, not any value.

## Notes
- None blocking. Peak RSS of the largest single pytest run 6.8 GB (< 10 GB).
- Open items from STATUS (METHODS R6 wording, N1 γ=0, etc.) were not part of this step and are unchanged.

## Verdict
PASS. Counts: 312 unit + 34 m0 + 22 m1 + 34 m5 = 402 passed, 0 failed, 0 pending in these suites; acceptance-check PASS.

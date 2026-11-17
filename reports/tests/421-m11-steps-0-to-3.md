# Report 421: tester, milestone M11 steps 11.0 to 11.3 (crosscheck package: stubs, `ks.py`, `embed.py`)

- Date: 2026-11-17. Mode: step. Commit under test: `a9009ac` plus uncommitted builder files (`src/su2plaq/crosscheck/`, `src/su2plaq/fuzzy/headline_step.py`, `scripts/m11_results.py`, two unit-test files).
- Plan in force: `prompts/009-final-cross-encoding-report-spectra-crosscheck.md` §5.1, §5.2, §7 rows 11.0 to 11.3 (and prompts/010 only for the stub). Conventions: `docs/METHODS.md` §13.
- Related: reports/tests/420 (hash reference), reports/research/006 (planner prototype numbers).
- Raw numbers: `results/tester/421-m11-s0-3.json`. Independent script (scratch, not committed): `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/c0852fe6-e8f0-4e38-bdd5-b42d861ef247/scratchpad/indep.py`.
- Resources: cores 0-8 (`taskset -c 0-8`), at most `-n 3`, everything inside `tools/pytest-safe` / `tools/run-capped`. Ignored by instruction: the other builder's diffs in `compress/{robust,report,replay}.py` and their tests; I did not run the whole unit suite.

## Commands

```
pytest --collect-only -q tests/acceptance
taskset -c 0-8 tools/pytest-safe -n 3 -m "not slow" tests/acceptance/m11 -q -rA
taskset -c 0-8 tools/pytest-safe -n 3 tests/unit/test_crosscheck_ks_unit.py tests/unit/test_crosscheck_embed_unit.py -q
taskset -c 0-8 tools/run-capped python -I <scratchpad>/indep.py <scratchpad>/indep.json     # independent checks, 20 s
taskset -c 0-8 tools/run-capped python <scratchpad>/mem.py                                  # serial pytest, peak RSS
python <scratchpad>/hashes.py ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check ; git diff --stat
```

## Verdict: PASS

## Results

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| collect-only, all acceptance | clean, 407 tests | 407 tests collected, no error | exact | PASS |
| m11 not-slow, green set (K1 x3, K1_spectra_agree, K2, K3 x3, E1 x6, E1_det, F3) | 17 pass | 17 passed (plus H1, see below) | exact | PASS |
| m11 not-slow, all other failures are PENDING | 7 failures, all `PENDING:` | 7 failed, every one `PENDING:` (E2, E3[1.0], F1, F2: `limits.*` not built; R1, T1, T2: results files missing) | exact | PASS |
| H1 | not judged (needs their `angle_offsets`) | it passed in this tree (the other builder's `robust.py` edit is already in the working tree) | not judged | informational |
| unit tests (ks 8, embed 6 functions, 19 cases) | all pass | 19 passed in 3.8 s | exact | PASS |
| `acceptance-check`, `check_lock.py` | PASS | "PASS: tests/acceptance matches acceptance-v22", "LOCK OK" | exact | PASS |
| six hashes vs report 420 | equal | all six equal (below) | exact | PASS |
| `git diff --stat` | no hashed file, nothing under `tests/acceptance` changed | only `compress/{replay,report,robust}.py` and three unit tests (the other builder). `evaluate/`, `encodings/`, `rishon/`, `fuzzy/`, `tests/acceptance/` untouched | exact | PASS |

Hashes (computed with `hashes.py`, same code as 420): provenance `99663fa6…e37`, lsh `88e0d76b…1ca`, spinnet `10f5727f…15c`, fuzzy_ub = fuzzy_link `b4bd20fe…7f9`, rishon `5f5decfa…f23`, spinnet loop `f1314a01…3d4`. All six full strings equal 420 line 48.

### Independent checks (my own code path, not through `crosscheck.cross_verdict`)

Common setup: encodings from `compress.spec.get_encoding`; the three H_B matrices read from each encoding's own attributes (twelve: `exact.operators.h_magnetic_phys`; spinnet/lsh: `_HB`); signs from `Encoding.gauge`.

**11.1 spectra and targets** (433 levels, `eigvalsh` of $\tfrac{g^2}{2}\mathrm{diag}(h_E)+H_B/g^2$, all three pairs):

| quantity | planner prototype (research 006) | got | locked tolerance | result |
|---|---|---|---|---|
| largest spectrum mismatch, max over $g^2\in\{0.5,1,2\}$, with and without outer electric | $2.8\times10^{-14}$ | $2.75\times10^{-14}$ (outer, $g^2=0.5$); per case: 2.75e-14, 1.11e-14, 1.20e-14, 5.2e-15, 2.66e-14, 7.1e-15 | $10^{-10}$ | PASS |
| matrix level: $\max|H_B^{\rm twelve}-D H_B^{\rm enc} D|$ | not stated | spinnet $2.7\times10^{-15}$, lsh $8.9\times10^{-16}$ | $10^{-10}$ | PASS |
| $H_E$ diagonals differ between encodings | 0 | 0.0 (inner and all) | $10^{-12}$ | PASS |
| $H_B$ Hermiticity | 0 | 0.0 for the three | $10^{-12}$ | PASS |
| $H_B$ multiplicities of $-2,-1,-\tfrac12,0,\tfrac12,1,2$ | 16, 96, 16, 177, 16, 96, 16 | exactly that, in each of the 3 encodings (sum 433) | counts exact | PASS |
| gauge signs of twelve | all $+1$ | all $+1$ (0 minus signs); spinnet and lsh each have 64 minus signs, all $\pm1$ | exact | PASS |
| transported target $\|D_sD_dV_sD_dD_s-V_d\|_2$, 6 ordered pairs, 3 angle pairs (18 values) | $3.0\times10^{-15}$ | max $3.04\times10^{-15}$ (angles (1.70, 1.00)); at nominal max $1.5\times10^{-15}$; order 2 max $1.6\times10^{-15}$ | $10^{-10}$ | PASS |

**11.2 cross-verdicts** (circuit `circuits.<enc>.build_step(0.37, 0.61, 1)`, target = foreign encoding's own `target('step')` conjugated with my own `np.outer(sg, sg)`, direct `evaluator.evaluate`; 433 inputs, certified):

| circuit vs target | ok | total_error | block_error | Gauss residual | seconds |
|---|---|---|---|---|---|
| twelve vs lsh | True | $2.72\times10^{-13}$ | $1.22\times10^{-13}$ | $3.9\times10^{-15}$ | 4.9 |
| spinnet vs twelve | True | $1.10\times10^{-14}$ | $3.7\times10^{-15}$ | $5.5\times10^{-16}$ | 0.2 |
| lsh vs spinnet | True | $1.65\times10^{-14}$ | $5.6\times10^{-15}$ | $5.4\times10^{-16}$ | 0.2 |

Largest $2.7\times10^{-13}$ against locked $10^{-10}$ (prototype range $4.8\times10^{-15}$ to $2.7\times10^{-13}$): PASS. Every `max_leak` is 0.0 and `outer_bits_read` is 0.

Mutants, all rejected (`reason` = "error"):

| mutant | twelve | spinnet | lsh | expected |
|---|---|---|---|---|
| target at $\beta+10^{-6}$ | block error $2.0000000012\times10^{-6}$ | $2.0000000018\times10^{-6}$ | $2.0000000034\times10^{-6}$ | rejected, in $[1.9,2.1]\times10^{-6}$ |
| wrong gate order, instruction list reversed | rejected, total error 0.9897 | rejected, 0.9897 | rejected, 0.9897 | rejected |
| wrong gate order, layers swapped ($U_E$ after $U_B$, i.e. $U_EU_B$ instead of $U_BU_E$) | rejected, block error 0.9897 | rejected, 0.9897 | not built (no separate layer API in the LSH wrapper) | rejected |

The two extra gate-order mutants (the one the plan asked for) are rejected with error 0.99, not near the tolerance, so the evaluator is sensitive to the order.

**11.3 link isometry by an independent route.** For each of the six models I rebuilt $V$ without using `link_isometry`: the quartet block comes from the intertwiner (Schur) equations $L_aW=WL^{\rm KS}_a$, $R_aW=WR^{\rm KS}_a$ on the $j=\tfrac12$ block, solved as a null-space problem (dimension 1 for the rishon link, 2 for the fuzzy link, where the copy is then fixed by $W|ab\rangle=\sqrt2U_{ab}s/c$); the singlet $s$ is checked to lie in the null space of all $L_a,R_a$ (distance $\le2.2\times10^{-16}$). Operators $U,L,R$ come from the models' own modules (as in the plan).

| model | $\max|V_{\rm mine}-V_{\rm module}|$ | $V^\dagger UV-cU^{\rm KS}$ | $V^\dagger LV-L^{\rm KS}$ | $V^\dagger RV-R^{\rm KS}$ | $V^\dagger H_EV-\mathrm{Casimir}$ | $V^\dagger V-1$ |
|---|---|---|---|---|---|---|
| rishon_plus | $1.9\times10^{-14}$ | $2.6\times10^{-15}$ | $3.2\times10^{-15}$ | $3.2\times10^{-15}$ | $4.9\times10^{-15}$ | $6.4\times10^{-15}$ |
| rishon_minus ($c=i$) | $1.9\times10^{-14}$ | $2.6\times10^{-15}$ | $3.2\times10^{-15}$ | $3.2\times10^{-15}$ | $4.9\times10^{-15}$ | $6.4\times10^{-15}$ |
| fuzzy_one | $5.6\times10^{-16}$ | $4.4\times10^{-16}$ | $3.9\times10^{-16}$ | $3.9\times10^{-16}$ | $6.7\times10^{-16}$ | $7.8\times10^{-16}$ |
| fuzzy_gamma5 | $5.6\times10^{-16}$ | $4.4\times10^{-16}$ | $3.9\times10^{-16}$ | $3.9\times10^{-16}$ | $6.7\times10^{-16}$ | $7.8\times10^{-16}$ |
| fuzzy_fplus | $7.8\times10^{-16}$ | $8.9\times10^{-16}$ | $1.0\times10^{-15}$ | $1.0\times10^{-15}$ | $1.6\times10^{-15}$ | $2.0\times10^{-15}$ |
| fuzzy_fminus | $2.2\times10^{-16}$ | $5.6\times10^{-16}$ | $4.4\times10^{-16}$ | $4.4\times10^{-16}$ | $6.7\times10^{-16}$ | $8.9\times10^{-16}$ |

All residuals are $\le 2\times10^{-14}$ against the locked $10^{-12}$ (prototype: $\le 4.7\times10^{-16}$; the slightly larger rishon numbers, $10^{-14}$, come from the null-space solve in my route, not from the module: the module's own residuals are $\le 4.4\times10^{-16}$ for all six). The phase $c$ from the module is $1$ (five models) and $i$ (rishon_minus), as in the plan.

Compression of the KS link operator, module numbers (`link_compression`, max over entries): isometry, $U$, $L$, $R$, $H_E$ all $\le 4.4\times10^{-16}$; $[P,L_a],[P,R_a]$ exactly 0.0; plaquette $V^{\otimes4\dagger}WV^{\otimes4}-W^{\rm KS}$ (`plaquette_W(cg)`, 625 x 625): $\le 4.7\times10^{-16}$, and my own `kron` of four 5 x 5 factors gives the same $\le 4.7\times10^{-16}$.

**Isometry leaks** (squared 2-norms; exact values in the plan are 1/2, 1/2, 1 and 15, 33/8, 4):

| model | $\max\|(1-P)U_{ab}V\|^2$ module / mine | exact | $\|(1-P^{\otimes4})WV^{\otimes4}\|^2$ module | exact |
|---|---|---|---|---|
| rishon (both) | 0.4999999999999998 / 0.5000000000000024 | 0.5 | 14.999999999999973 | 15 |
| fuzzy_one, fuzzy_gamma5 | 0.4999999999999999 / 0.5000000000000001 | 0.5 | 4.124999999999993 | 33/8 = 4.125 |
| fuzzy_fplus, fuzzy_fminus | 0.9999999999999996 / 0.9999999999999991 | 1 | 3.9999999999999973 to 3.9999999999999982 | 4 |

Largest deviation from the exact value: $2.7\times10^{-14}$ (plaquette leak, rishon), against the locked $10^{-6}$ on the squared plaquette leak and $10^{-12}$ on the link leak: PASS.

**Memory.** The independent script (all of the above, including the 625 x 625 Gram matrices) peaked at 778 MB RSS. A serial pytest process running K1 to K3, E1, E1_det, F3 and both unit files peaked at 765 MB RSS (limit 2 GB). No 65536 x 625 array is formed: `compressed_plaquette` builds only `kron` of 5 x 5 factors, and the largest array is 625 x 625 (code read; the measured peak agrees).

### Code review

| item | finding | result |
|---|---|---|
| hard-coded expected numbers in src | none (no 15, 33/8, 2.0e-6, 1e-12 anywhere in `crosscheck/`; only definitions: $c=i$ for rishon_minus, the singlet vectors of §3.2, shapes 16, 5, 433, 625) | PASS |
| silently caught exceptions | no `try`/`except` in `crosscheck/`, `headline_step.py` or the script | PASS |
| dtype | all constructed arrays `complex128`/`float64` (`np.zeros(..., dtype=np.complex128)`, `.astype(np.complex128)`); no lower precision | PASS |
| error handling | unknown encoding, unknown model, `which` not in {general, headline}, `headline` with `order=2` all raise `ValueError`; no cached headline raises `FileNotFoundError` (checked on the real tree: all three encodings, no write) | PASS |
| stubs | all 11 public stub names (`limits.*` x5, `report.*` x4, `headline_step`, `write_headline_step`) raise `NotImplementedError` through `su2plaq._stub.todo` ("... is not built yet"); `scripts/m11_results.main` also uses `todo` | PASS |
| `fuzzy/headline_step.py` not hashed | `registry._FUZZY_FILES` = verify, targets, circuits/fuzzy, units, compress_hook only | PASS |
| crosscheck package in no hash list | not named in `encodings/registry.py` or any `*_FILES`; hashes unchanged | PASS |

## Observations (not failures)

- O1: a tracked file `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json` was rewritten during my runs (provenance `git_commit` field only, `d5d306b` to `a9009ac`). It is the cert re-export of the existing spinnet lean exporter, known from report 420. I restored it with `git checkout --`; `git status` shows no `results/` change now.
- O2: the LSH wrapper has no separate U_E/U_B layer API, so the "layers swapped" mutant was built only for twelve and spinnet; the reversed-instruction mutant covers all three.
- O3: `link_compression` leak keys are the plain (non-squared) norms (`leak_U`, `leak_plaquette`); the plan's JSON schema (§5.4) wants `leak_U_sq`, `leak_plaquette_sq`. That is a conversion for step 11.6, not a defect of 11.3 (the locked E1 test squares them itself).
- O4: while this report was being written `HEAD` moved from `66a32eb` to `a9009ac`; the hashes were recomputed after that and are equal to 420.

## Counts

passed: 17 acceptance (m11, not slow) + 19 unit; failed: 0; pending: 7 (E2, E3[g2=1.0], F1, F2 pending on steps 11.4/11.5; R1, T1, T2 pending on steps 11.6 to 11.8). H1 passed but was not judged. New failures versus the last report (420): none. Slow m11 tests (K4 x3, E3 x2, E3_levels, H2 x2, H3) not run in step mode.

# Report 414: tester, consolidation 008 step B2 (evaluator: span leak, `Verdict` fields, reason order, `prune_fraction`, `inner_target`)

- Date: 2026-11-14. Commit: `5fe990f` plus the builder's uncommitted B2 changes (`src/su2plaq/evaluate/evaluator.py`, `results/store.py`, `compress/{round,report,run_candidate}.py`, `rishon/compress/evaluate.py`; new `tests/unit/test_evaluator_span_leak_unit.py`).
- Plan in force: `prompts/008` §5, §8, §10 row B2 (METHODS §6 "span leak as an exact operator norm"). Lock: acceptance-v20. Mode: step. Machine: omnicommander, cores 14-19, `tools/pytest-safe`, `tools/run-capped`.
- Related: reports/tests/413 (B1 baseline). Raw numbers: `results/tester/008-b2-evaluator.json`. My scripts: `/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/57b28677-d814-4f58-bc95-52ae378eb01f/scratchpad/b2t/` (`ref.py` dense reference, `t1.py`, `t2.py`, `t4.py`, `t5.py`, `t6.py`, `fulleval.py`, `timing.py`).

## Verdict: PASS

All checks pass. Red tests: exactly the 26 that are red because of a later step or the §8 list (B1 had 30; E1, E3, E4, E6 turned green; nothing turned red). Two non-blocking observations (rishon early verdicts give `total_error = NaN`; timing increases that are planned in §12).

## Commands
1. `tools/pytest-safe -n 3 -m "not slow" -rfEs -q tests/acceptance/{m0,m1,m2,m2c,m3,m3x,m4,m5,m5x,m6,m8,m9,m10}` (cores 15-17): 264 passed, 26 failed, 1523 s.
2. `tools/pytest-safe -n 3 -m slow -rfEs -q tests/acceptance/{m0,m1,m3}` (cores 18,19,14): 3 passed (`M0_C6_jmax1_count_slow`, `M1_P1_paulo_qpy_verifies`, `M3_L3_native_certificate_general_step`), 130 s. (Only these three tests carry the `slow` mark in m0/m1/m3; M0-E5 `aer_mps`, M1-V1 prune and M1-T1 are not marked slow and are inside run 1, all green.)
3. `tools/pytest-safe -n 3 -q tests/unit` (separately, cores 17-19): 1012 passed, 898 s (B1 baseline 998; +14 = the new span-leak unit tests).
4. `HEAD` reference tree: `git archive 5fe990f | tar -x -C ../su2qc-head-5fe990f-tester-b2` (no git metadata touched), moved afterwards to `should-be-deleted/su2qc-head-5fe990f-tester-b2`.
5. Own scripts listed above (all under `tools/run-capped`, `taskset`).
6. `python tools/check_lock.py`, `~/.claude/bin/acceptance-check`, `pytest --collect-only -q tests/acceptance`.

## (1) Span-leak definition against my own dense reference

Reference (`ref.py`, independent of the project's simulator and evaluator): the columns $U|d,\text{anc}=0\rangle$ for every valid data code $d$ from `qiskit.quantum_info.Operator` (data-only circuits) or `Statevector` (circuits with ancillas, $\le 20$ qubits), the physical states from `enc.physical_vectors()`, $A=\Psi^\dagger U\Psi$, residual $R=U\Psi-\Psi A$ per outer pattern, $S$ = rows of $R$ on valid data codes with ancillas $0$, $X$ = all other rows. $S$ is formed directly (no Gram trick; my first version used a Gram sandwich and showed the expected $10^{-8}$ floor on exact circuits, which I discarded). $\lVert S\rVert_2=\sqrt{\lambda_{\max}(S^\dagger S)}$.

| case (evaluator `sparse`, `gauss=False`) | expected (dense reference) | got | tolerance | result |
|---|---|---|---|---|
| spinnet general step, exact | $0$ | evaluator $0.0$, reference $0.0$ | $10^{-12}$ | PASS |
| spinnet UE + $R_y(\theta)$ on qubit 0, $\theta=0.02,0.3,1.0$ | $\sin(\theta/2)=9.99983333\cdot10^{-3},\ 0.149438132,\ 0.479425539$ | evaluator equals $\sin(\theta/2)$ and reference to $\le1.1\cdot10^{-16}$ | $10^{-14}$ | PASS |
| spinnet step + $R_x(\theta)$ on qubit 3, $\theta=0.02,0.3,1.0$ (ancilla circuit, 15 qubits) | reference | $|\Delta|\le2.8\cdot10^{-17}$, $3.9\cdot10^{-16}$, $1.6\cdot10^{-15}$ | $10^{-14}$ | PASS |
| same, trial mode (64 seeded states) | reference on the same states | $|\Delta|\le2.6\cdot10^{-17}$, $3.9\cdot10^{-16}$, $1.2\cdot10^{-15}$ | $10^{-14}$ | PASS |
| twelve UE exact (data register, 12 qubits) | $\approx 3\cdot10^{-15}$ | evaluator $3.33\cdot10^{-15}$, reference $3.15\cdot10^{-15}$ | $10^{-12}$ | PASS |
| twelve UE + $R_y$, $\theta=0.02,0.3$ | $\sin(\theta/2)$, reference | $|\Delta|\le5.6\cdot10^{-17}$ | $10^{-14}$ | PASS |
| twelve UE + $R_x,\mathrm{CX},R_y,H,\mathrm{CX}$ ($\theta=0.02,0.3$; span leak $0.99996$, $0.99019$), full and 64-state trial | reference | $|\Delta|\le6.7\cdot10^{-16}$ (full), $1.1\cdot10^{-16}$ (trial) | $10^{-14}$ | PASS |
| `extra["span_leak_max_state"]` | largest column norm of $S$ | equals the reference to $\le1.2\cdot10^{-15}$ in every case above; always $\le$ `span_leak` | $10^{-14}$ | PASS |
| `total_error` $-$ (`op_norm_error` $+$ `span_leak`) | 0 | $0.0$ in all 17 cases | $10^{-15}$ | PASS |
| `leak_amplitude` (`sparse`) vs reference $\lVert X\rVert_2$ | equal | $|\Delta|\le1.1\cdot10^{-15}$ | $10^{-14}$ | PASS |
| twelve general step (the real 50-qubit seed) | $\le10^{-12}$ | span leak $3.32\cdot10^{-15}$ (nominal), $3.82\cdot10^{-15}$, $5.37\cdot10^{-15}$ (alternate angles); `span_leak_max_state` $3.28\cdot10^{-15}$ | $10^{-12}$ | PASS |

Trial subset never exceeds the full value (nested random subsets of sizes 1, 2, 5, 16, 64, 200, 433 from one permutation, seed 7; evaluator vs reference):

| circuit | full | subsets $m=1\ldots433$ | non-decreasing, $\le$ full, $|\Delta_{\rm ref}|\le$ | result |
|---|---|---|---|---|
| spinnet step + $R_x(0.3)$ | 0.1494381325 | 0.14943813 for all $m$ | yes, yes, $4.4\cdot10^{-16}$ | PASS |
| spinnet UB + $R_y,\mathrm{CX},R_y$ | $0.9999999999999979$ | 0.341, 0.341, 0.570, 0.570, 0.9994, $1-3\cdot10^{-15}$, full | yes, yes, $2.4\cdot10^{-15}$ | PASS |
| spinnet UE + $H,R_y$ | 0.7071067812 | 0.70710678 for all $m$ | yes, yes, $2.2\cdot10^{-16}$ | PASS |

## (2) `aer_mps` engine path (the builder did not test it)

`evaluate(..., engine="aer_mps", tol_err=1e-3)` forced; compared with `engine="sparse"` and with the dense reference (`t2.py`). The same code path `span_leak` is used on the MPS block $M$.

| case | sparse | aer_mps | dense ref | $|\Delta|$ aer vs sparse | result |
|---|---|---|---|---|---|
| spinnet step + $R_x(0.02)$ | 0.009999833334166649 | 0.009999833334166961 | 0.009999833334166677 | $3.1\cdot10^{-16}$ | PASS |
| same, 64-state trial | 0.009999833334166642 | 0.009999833334166958 | 0.009999833334166668 | $3.2\cdot10^{-16}$ | PASS |
| spinnet step + $R_x(0.3)$ | 0.149438132473599 | 0.149438132473601 | 0.149438132473599 | $1.5\cdot10^{-15}$ | PASS |
| same, 64-state trial | 0.14943813247359886 | 0.14943813247360044 | 0.14943813247359922 | $1.6\cdot10^{-15}$ | PASS |
| twelve UE + $R_x,\mathrm{CX},R_y,H,\mathrm{CX}$, 8-state trial (seed 5) | 0.9901895263527993 | 0.9901895263527989 | 0.990189526352799 | $4\cdot10^{-16}$ | PASS |
| spinnet exact step | 0.0 | $8.6\cdot10^{-16}$ | 0.0 | $\le10^{-12}$ | PASS |
| spinnet step reading the 8 outer qubits + $R_x(0.1)$ (no dense reference possible) | 0.04997916927067826 | 0.04997916927067928 | n/a | $1.0\cdot10^{-15}$ | PASS |
| spinnet step reading the outer qubits, exact | 0.0 | $2.7\cdot10^{-15}$ | n/a | $\le10^{-12}$ | PASS |

`aer_mps` reports `engine="aer_mps"`, `certified=True` (tol 1e-3). Note: with `aer_mps` `leak_amplitude` is the certified pessimistic bound (METHODS §6, e.g. $0.0346$ vs exact $0.0100$), hence `total_error` is larger there; that is the documented engine behaviour, not a B2 effect. A full 625-input twelve `aer_mps` call was abandoned after 17 CPU minutes (not a result; the cost of the existing 12-qubit invalid-code contraction, unrelated to span leak).

## (3) `twelve` unchanged

`evaluate_program(compress/programs/twelve/seed/000-general.py, default_spec("twelve","step"), "full", cache=False)` in the working tree vs the `5fe990f` archive tree (`fulleval.py`), and against the committed entry `compress/archive/twelve/entries/r00-seed-000.json`:

| check | expected | got | tolerance | result |
|---|---|---|---|---|
| key (CX, T, depth_CT, qubits) | (294, 952, 1421, 50) | (294, 952, 1421, 50), valid, `ok` | exact | PASS |
| `op_norm_error` nominal | `2.68813143571731e-13` (HEAD and archive) | `2.68813143571731e-13` (bit-identical); alt angles `2.694656317437985e-13`, `2.669600012558199e-13` equal HEAD | bitwise | PASS |
| every other leaf of `ProgramResult` and `Entry` (272 vs 248 leaves) | equal except timings, provenance | new keys only (24): `span_leak`, `total_error`, `extra.span_leak_max_state`, `extra.gauss` for 3 verdicts, in `result` and `entry`. Differing values: `evaluator_sha256` and `encoding_sha256` (`1b38431d…` → `c4e357e9…`), `git_commit`, `git_dirty`, `seconds`, `wall_s`, `written_utc`. Nothing else | exact | PASS |
| `spec.sha256()` | `ee3ce506…caaa5d` | identical | exact | PASS |
| new fields on this circuit | span $\le10^{-12}$ | span $3.32\cdot10^{-15}$, total $2.7214\cdot10^{-13}$, `extra["gauss"]="checked"` | | PASS |

## (4) Reason order, `prune_fraction`, `inner_target`

Perturbed spinnet step ($R_x(0.02)$ on qubit 3): `op_norm_error` $=0.0199998$, `span_leak` $=0.0099998$ $(=\sin 0.01)$, `total_error` $=0.0299996$, Gauss residual $0.0199997$, `leak_amplitude` $0.0099998$.

| check | expected | got | result |
|---|---|---|---|
| `tol_err` between `op_norm_error` and `total_error`, Gauss tolerance loose | `span_leak` | `span_leak`, `failing_inputs=[("span_leak",…),("total_error",…)]` | PASS |
| `tol_err` just above `total_error` ($1+10^{-6}$) | `ok` | `ok` | PASS |
| same `tol_err`, Gauss tolerance $=g/2$ | `gauss` (older reason first) | `gauss` | PASS |
| `tol_err` $\in({\rm leak},{\rm op\_norm\_error})$ | `error` | `error` | PASS |
| `tol_err` $=\text{leak}/2$ | `leak` / `dirty_ancilla` | `leak` | PASS |
| `prune_fraction=1e-30` with every other check failing | `pruning_bound` first | `pruning_bound` | PASS |
| `prune_fraction` $\in\{0,\,0.0,\,-0.1,\,1.0000001,\,2,\,\mathrm{NaN},\,+\infty,\,-\infty\}$ | `ValueError` | `ValueError` for all 8 | PASS |
| `prune_fraction` $\in\{\text{None},1.0,0.5\}$ | accepted | accepted (`ok`) | PASS |
| twelve trial circuit, `dropped_total` $=1.467\cdot10^{-13}$, cap $=f\cdot10^{-10}$: $f=0.01$ (default), 1.0 | `ok` | `ok` (default constant `PRUNE_FRACTION`=0.01 unchanged) | PASS |
| same, $f=0.9\,d/10^{-10}$ ($=1.32\cdot10^{-3}$), $0.5\,d/10^{-10}$ | `pruning_bound` | `pruning_bound` | PASS |
| same, $f=1.1\,d/10^{-10}$ ($=1.61\cdot10^{-3}$) | `ok` | `ok` (the exact boundary `dropped_total > f*tol_err` is honoured) | PASS |
| `extra["gauss"]` with `gauss=False` / `True` | `not_checked`, residual NaN / `checked`, finite | `('not_checked', nan)` / `('checked', 0.02)` | PASS |
| `inner_target` twelve | (625,625) built-in | (625,625) | PASS |
| `inner_target` for an object with its own method | its method's result | returned `eye(3)*(1+2+3)` | PASS |
| `inner_target` for an object without the method, not named `twelve` | `NotImplementedError` | `NotImplementedError` | PASS |
| `inner_target(SpinNet())` | n/a | returns (SpinNet defines its own `inner_target`; so the m2c-E6 "encoding without it" case is a synthetic one) | note |

(In my first run I wrote the `ok`/`pruning_bound` expectations for the three $f$ near the boundary the wrong way round; the evaluator's answers are the correct ones: `pruning_bound` iff $d>f\cdot10^{-10}$.)

## (5) Regression set

| set | expected | got | result |
|---|---|---|---|
| `tests/unit` | all green | 1012 / 1012 | PASS |
| `-m slow` m0 m1 m3 | green | 3 / 3 | PASS |
| `-m "not slow"` m0 m1 m2 m3 m3x m4 m5 m5x m6 m9 m10 (+ m2c, m8) | green except §8 / PENDING | 264 passed, 26 failed (all listed below) | PASS |
| m2c E1, E3, E4, E6 | newly green | all four PASS (2.3 s, 2.8 s, 12.8 s, 0.7 s) | PASS |
| m2c E2 | red only on its `fuzzy_link` line | `ValueError: unknown encoding 'fuzzy_link'; known: ['twelve', 'lsh']` raised at `test_consolidation_evaluator.py:130`, after the spinnet and twelve checks (full and 64-state trial) passed | PASS |
| `collect-only`, `check_lock`, `acceptance-check` | clean | 374 collected; `LOCK OK`; `PASS: tests/acceptance matches acceptance-v20` | PASS |

All 26 red ids (identical set to the B1 report 413 minus E1, E3, E4, E6; none new):

- m2c E2 (fuzzy_link, B4); E5: `unknown encoding 'fuzzy_link'` (B4).
- m2c Y1 and G1 x5: `PENDING: cannot import su2plaq.compress.replay` (B7; §8 expected red).
- m2c R1, R3, P1, P2, R2: registry lacks spinnet / fuzzy / rishon; facades still patch (B3-B5).
- m6 G5 (`replay-204.json missing`), G6 (`three-layer.json missing`): §8 expected red.
- m6 L2, L3 (`Laurent3.lean missing`), L9 (`recognise_angle_single`): PENDING before B1 too.
- m8 E2, S0, S2, S3, S5, L2 (`NotImplementedError su2plaq.lsh.loop.<hook>`), S4, H1 (`No module named su2plaq.compress.robust`): later LSH/B6 steps.

## (6) Evaluator time overhead (full evaluation of the first seed per encoding, `cache=False`, 3 repetitions, one core each, new tree vs the `5fe990f` copy)

Cores are not equal on this host: core 16 is about 2.2 times slower than core 15, so I ran each tree on both cores and compare on the same core only. Sums of `verdict.seconds` over the three verdicts (nominal + 2 alternate angles); the first repetition is cold (module imports, cache), repetitions 2-3 are warm.

| encoding | core | new, warm (s) | HEAD, warm (s) | $\Delta$ per verdict | wall ratio (warm, median) |
|---|---|---|---|---|---|
| twelve step | 15 | 3.43, 3.46 | 2.52, 2.54 | $+0.30$ s | 1.30 |
| twelve step | 16 | 8.75, 8.57 | 6.50, 6.38 | $+0.72$ s | 1.28 |
| spinnet step | 15 | 0.67, 0.62 | 0.52, 0.57 | $+0.03$ s | 1.10 ($+0.1$ s) |
| spinnet step | 16 | 1.58, 1.54 | 1.38, 1.34 | $+0.06$ s | 1.15 |
| rishon step | 15 | 20.88, 19.60 | 20.02, 18.81 | $+0.3$ s | 1.02-1.04 |
| rishon step | 16 | 33.92, 33.84 | 34.58, 33.59 | $\approx0$ | 0.98-1.00 |

All `op_norm_error` values in these runs are bit-identical between the trees (twelve, spinnet and rishon, three verdicts each). The plan (§12) states the span-leak cost as $+0.4$ to $1.5$ s per twelve verdict, $+0.05$ s spinnet, $0$ rishon/fuzzy and calls it a planned change of the benchmark "evaluator time per circuit", not a regression; measured $+0.3$ s (fast core) / $+0.7$ s (slow core) per twelve verdict, $+0.03$-$0.06$ s spinnet, rishon $0$-$+4\,\%$ (noise level of this host). The relative increase of the whole twelve evaluation exceeds the generic 10 % threshold (1.28-1.31), spinnet 1.10-1.15; both are inside the §12 statement. Flag for the benchmark gate step.

## (7) Hashes (recomputed with my own sha256 loop over the file lists, not through `provenance.py`)

| quantity | expected | got | result |
|---|---|---|---|
| `provenance.code_hash()` | `c4e357e9…` | `c4e357e91fcb8043e02750d92e97c1e2e11fd8c4d9f921e14fabce2a9c6b3f6d`; my loop identical | PASS |
| `code_hash_for("lsh")` | `35c0667f…` | `35c0667f0fa62b5b554274c5e7e19156aa4556f3dbee8c4ee71d543a0163361c`; own loop identical | PASS |
| `spinnet.loop.code_hash()` | `914e5711…` | `914e571147f064a73975c7af9d53c2264afed2f2144c1d5765f8590fa7273767`; own loop identical | PASS |
| `rishon.compress.code_hash()` | `64f364f2…` | `64f364f2816db3c039ffdf501399a59e93e85d2de101a1bcea50483c7fc248fe`; own loop identical | PASS |

These replace the B1 values (`1b38431d…`, `bcdd4e4e…`, `f61b82b2…`, `2b6fbaa2…`) because `evaluate/evaluator.py` is in the shared hashed list; the stored `evaluator_sha256` in the twelve entry I re-evaluated is `c4e357e9…`.

## Observations (non-blocking, not failures)

1. `rishon/compress/evaluate.py::to_verdict` gives `total_error = NaN` for verdicts whose inner verdict is an early one (`unsimulable`, `bad_layout`, ...): `iv.span_leak` is NaN and `rv.op_norm_error = inf`, so `inf + nan = nan` (checked with `cap=10` and a 3-qubit circuit: `to_verdict: unsimulable nan nan`). The evaluator's own early verdicts use the dataclass default `total_error = inf`, and the plan text ("`to_verdict` copies `span_leak` ... and sets `total_error`") does not say which. Consequence: none for validity (`ok` is False); JSON gets NaN instead of Infinity (non-strict either way); `report._verdict` already falls back to `op_norm_error` when `total_error` is not finite. A one-line `inf if not finite` would make both paths equal.
2. `SpinNet` defines its own `inner_target`, so the m2c-E6 "encoding without `inner_target`" branch is exercised with a synthetic object only; behaviour as specified.
3. The sparse engine returns span leak exactly `0.0` on basis encodings (spinnet) because each $P_o$ has unit-vector columns, so $B_o$ is a set of unit vectors and $C_o=\Omega_o-B_oB_o^\dagger\Omega_o$ cancels exactly; the dense reference gives $0.0$ too. `aer_mps` gives $10^{-15}$ there. Not a defect.
4. The four slow expected-red ids of report 413 (`m2` archive best, `m4` G1, `m10` G1 x2) were not re-run; they are stale-stamp tests that depend on the archives, not on B2.

## Byproducts and files touched
- Tracked byproducts written by test runs and restored with `git checkout --`: `results/compress/fuzzy_link/summary.json`, `results/compress/rishon/robust.json`, `results/spinnet/certs/spinnet-UB-o1-33d95284ebb7.json`, `results/spinnet/certs/spinnet-UB-o1-458a39365261.json`, `results/spinnet/certs/spinnet-UE-o1-df0c79b22d3f.json`, `results/spinnet/certs/spinnet-step-o1-b0a415d9322f.json`. `git status` afterwards shows only the builder's six modified source files, the builder's new unit test, and my new `results/tester/008-b2-evaluator.json`.
- New by me: `reports/tests/414-consolidation-008-b2.md`, `results/tester/008-b2-evaluator.json` (commit `5fe990f` + uncommitted B2, seeds recorded). No source, test or acceptance file edited. HEAD reference copy moved to `should-be-deleted/su2qc-head-5fe990f-tester-b2`.

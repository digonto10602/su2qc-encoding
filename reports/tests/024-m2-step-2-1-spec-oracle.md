# Tester report 024 - M2 step 2.1 (TaskSpec + oracle), mode `step`

- Date: 2026-11-05. Commit: `fb0678d` + uncommitted working tree (spec.py, oracle.py, compress/specs/*, tests/unit/test_compress_spec_oracle_unit.py).
- Plan in force: `prompts/002` + addenda 003, 004, 005, 006 (acceptance-v6). Previous report: `reports/tests/023` (not re-read; this one is independent).
- Raw numbers: `results/tester_m2_step21_oracle.json`. Scripts (scratchpad, not in repo): `indep1.py` (oracle), `indep2.py` (spec text, sha256).
- Ignored by instruction: Lean step 2.L1 (`lean/`, `src/su2plaq/lean/`).

## Commands
```
pytest -n auto tests/acceptance/m2 -q --junitxml=...         # classification of every failure by message
pytest -n auto -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q
pytest -n auto tests/unit -q
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
python indep1.py ; python indep2.py ; PYTHONHASHSEED={0,1,random,12345} python -c "default_spec().sha256()"
python -m su2plaq.compress.oracle --encoding twelve {--target ub --column 3 | --target ue --element 5 5 | --codec --state 5 | --block 0 | --order 2 ...}
```

## Summary table
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| `m2::test_oracle_matches_exact_step` | PASS | PASS | - | PASS |
| `m2::test_macro_costs_match_lowering`, `test_lean_project_present_and_builds_checker` | PASS | PASS | - | PASS |
| other m2 tests (43) | PENDING / not built | 43 fail, all "not built" (list below) | - | PENDING (0 unexpected) |
| m0 + m1 non-slow | all green | 54 passed (196 s) | - | PASS |
| unit | all green | 202 passed (112 s; includes the parallel Lean unit tests) | - | PASS |
| collect | 102 | 102 collected, clean | - | PASS |
| `tools/check_lock.py`, `acceptance-check` | OK | `LOCK OK`, `PASS: tests/acceptance matches acceptance-v6` | - | PASS |
| (1) oracle vs independent `scipy.linalg.expm(-i beta H_B)`, `diag(exp(-i alpha H_E))` | equal | max abs diff over 16 cases (UE, UB, step order 1 and 2; angle pairs (0.37,0.61), (0.91,0.23), (1.70,1.00), (0.123,2.5)) = 0 (same float64 recipe) ; $\max\lvert V^\dagger V-1\rvert=8.9\times10^{-16}$ | 1e-12 | PASS |
| column(top=1e6) re-assembled == column of reference, all 16 cases, columns {0,5,200,432}; sorted by $\lvert v\rvert$ descending; element(i,j) (int and label-tuple) | equal | max diff $\le10^{-13}$, sorted, equal | 1e-13 | PASS |
| `block(spec,0)` vs $\exp(-i\beta H_B^{\rm cl})\,\mathrm{diag}(1,e^{-i\alpha H_E^{\rm cl}})$ from the M0-X7 closed block (indices 0, 352; $H_E^{\rm cl}=(0,3)$, $H_B^{\rm cl}=-2\sigma_x$) | equal | 0.0 | 1e-12 | PASS |
| `block(spec,0)` vs analytic $(\cos2\beta+i\sin2\beta\,\sigma_x)\,\mathrm{diag}(1,e^{-3i\alpha})$ | equal | $2.2\times10^{-16}$ | 1e-12 | PASS |
| `block(spec,o)` for 40 random admissible keys (of the 3153) + 0 vs independent selection (decode base-5 digits with `LinkSpace`) | equal, unitary, no support outside the block | 41/41 equal, max leak outside block $<10^{-13}$, unitarity $<10^{-10}$ | 1e-10 | PASS |
| unsupported outer keys | rejected | $5^8$, $5^8+3$, $-1$ -> `ValueError`; keys 1, 2, 4, 5, 25 (single half-integer outer link, no gauge-invariant state) -> `ValueError`; 1.5, "a" -> `ValueError`, None -> `TypeError` | - | PASS (see note N1) |
| (2) rendered text == `compress/specs/twelve-step.md` on disk | identical | identical | exact | PASS |
| `tol_leak` anywhere (render, on-disk spec, TEMPLATE, spec.py, oracle.py, `to_dict`, `hasattr`) | absent | absent | - | PASS |
| section order | Task, Registers, Circuit model, Correctness, Cost, Proved structure (Lean), Tools | exactly this | - | PASS (see note N2) |
| numbers traceable (118 numeric tokens; 14 groups below, ~30 distinct values) | each from spec/describe/MACRO_COST | all traced (table below) | - | PASS |
| MACRO_COST vs `docs/METHODS.md` line 67 (9 macros, regex parsed) | equal | 9/9 equal | exact | PASS |
| BASIS / MACROS vs prompts/002 §5 | equal | `x z h s sdg t tdg rz p cx cz` / `ccx rccx ccz swap ch crz crx cp` | exact | PASS |
| codec text vs actual `physical_vectors().codes` (all 433 states; inner code table 0->000, ++->111, +-->110, -+->101, --->100; outer q_m/q_j; near ends `R R L R L L R L`) | support sets equal | 433/433 equal, 0 mismatches | exact | PASS |
| Lean section with a realistic `structure.json` (schema of prompts/006 §4) | decide/native facts listed, numerical skipped | `card_physical`, `spectrum_multiplicities` listed with theorem/certificate; `x` (numerical) skipped; "pending" text when file missing | - | PASS |
| (3) sha256 stable across processes (`PYTHONHASHSEED` 0, 1, random, 12345) | same | `ee3ce506...aa5d` identical all 4; also identical to sha of `json.dumps(to_dict(), sort_keys=True)` | exact | PASS |
| sha256 sensitive to each of 15 fields | changes | 14 of 14 non-identity variations changed it (kind, alpha, beta, order, alt_angles, tol_err, tol_gauss, eps, eval_budget_s, support_cap, max_qubits, cell_k, trial_inputs, trial_seed); `encoding` changes too ("other" vs "twelve", checked separately; my first table row used "twelve" again) | - | PASS |
| sha256 sensitive to 1 ulp in alpha | changes | changes | - | PASS |
| `with_angles(alpha, beta)` same angles -> same sha; list-of-lists `alt_angles` normalised | same | same | - | PASS |

## Rendered-number traceability (all 118 tokens, grouped)
| text | source | verified |
|---|---|---|
| 433 physical states | `len(enc.basis.labels)` | 433 |
| 12-qubit, 12 data + 16 outer | `enc.n_data`, `enc.n_outer` | yes |
| (0.37,0.61), (0.91, 0.23), (1.7, 1) | `spec.alpha/beta`, `alt_angles` (`:g` formatting) | yes |
| 625 valid inner codes, 5^4 | `len(enc.inner_codes())` | 625 |
| code table 000/111/110/101/100, unused 001/010/011 | `LINK_CODE`, checked against codes of all 433 states | yes |
| qubits (3l,3l+1,3l+2), o_k = (12+2k, 13+2k), near ends | `describe()` loops; independent decode of keys | yes |
| ccx (6,7,0) ... cz (1,0,0), 9 costs | `MACRO_COST`, METHODS line 67 | yes |
| gate/macro lists | `BASIS`, `MACROS` | yes |
| at most 60 qubits | `peak_qubit_cap()` = 12+16+32, METHODS line 76 | yes |
| 1e-10 (error), 1e-10 (Gauss) | `tol_err`, `tol_gauss` (prompts/003, 004) | yes |
| 300 s, 5000000 amplitudes | `eval_budget_s`, `support_cap` | yes |
| $\varepsilon=$1e-06, cells with 8 | `eps`, `cell_k` | yes |
| 64 physical inputs | `trial_inputs` | yes |
| "leak amplitude", "(+ certified simulator pruning bound)" | prompts/004 Eq. for `op_norm_error` = block + dropped_total + leak amplitude | yes |

## Failing m2 tests - all classified (43 fail / 3 pass)
40 fail with `PENDING: NotImplementedError: <X> is not built yet` (X = Builder, general_circuit, gridsynth_T, evaluate_circuit, Archive.load, code_hash, import_seed, qiskit_l3, general_program_path, lean.certify.*, lean.structure.*).
3 fail with a message that is NOT the `PENDING:` prefix but are consequences of the Lean skeleton (step 2.L1, parallel tester; not 2.1): 
- `test_lean_generic_theorems_standard_axioms`: `unknown theorems: [Su2Plaq.norm_sum_sq_of_pairwise_orth, ...26 names]` (theorems not yet written; 2.L2/2.L3);
- `test_lean_theorem_file_general`: `lean/certs/twelve-general-step.lean` does not exist (2.L5);
- `test_lean_counts_kernel_checked`: `theorem card_physical` not in `Counts.lean` skeleton (2.L3).
None touches spec.py/oracle.py. Nothing outside "not built" occurs.

## Notes (non-blocking)
- N1 (design): `oracle.block` decodes base-5 digits as "0 -> j=0, 1..4 -> j=1/2" and selects states by outer SPINS, so it also accepts keys that are not in `s_o_dims` (e.g. 45927, digits not admissible local indices) and returns the same block as the admissible key with the same spins. Harmless (block is correct for those spins), but "unsupported keys rejected" holds only for keys with no physical state or not a valid key.
- N2 (judgement): the section order follows prompts/002 §5 hand-text (Task, Registers, Circuit model, Correctness, Cost, [Lean], Tools). Extended Data Fig. 1 (refs line 935-990) shows only a three-part spec (Task / Interface / Model) plus the Objective/API/Discoveries lines in (b); there is no section list to match exactly. Task -> Registers/Interface -> Circuit model/Model is the same relative order.
- N3: the rendered Correctness text states the combined bound, `tol_gauss` and identical skeleton, but not (a) the synthesised-circuit tolerance rule $N_{\rm rot}\varepsilon+10^{-9}$ (prompts/003) nor (b) the prune cap $10^{-2}\cdot{\rm tol\_err}$ ($=10^{-12}$ for exact circuits, prompts/005). Only "(+ certified simulator pruning bound)" is said. Not required by prompts/004 line 104, which the text satisfies.
- N4: `sha256` is type-sensitive: `eval_budget_s=300` (int) hashes differently from `300.0` (json `300` vs `300.0`); only matters if someone builds a spec with ints (cache-key churn, no false hit).
- N5: every column of the step target has at most 2 non-zero entries (177 columns with 1, 256 with 2): `column(spec, j)` returns <= 2 rows regardless of `top`.

## Verdict
PASS. 0 failed (in scope), 0 unexpected, 43 pending/not built (40 explicit PENDING + 3 Lean-skeleton), 3 m2 passed. No new failures versus the last report; acceptance-check PASS.

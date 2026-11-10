# Report 206 — M5 steps 5.L1–5.L3 (Lean: rishon counts, JW facts, H_B structure certificate)

- Date: 2026-11-06
- Git commit: `b4c1917` plus the uncommitted builder changes (lean/Su2Plaq/Rishon/{Counts,JW}.lean, lean/Su2Plaq.lean (+2 imports), lean/Su2PlaqCert/Rishon/{HB,HBData}.lean, lean/certs/rishon-hb-structure.lean, src/su2plaq/rishon/lean_export.py, tests/unit/test_rishon_lean_export_unit.py, tests/unit/test_rishon_stubs_unit.py)
- Prompt in force: `prompts/200-rishon-m5-plan.md` (+ `prompts/201`); acceptance-v8
- Mode: step. Related: `reports/tests/205-m5-step-5-9-5-10-results.md`
- Machine: desktop, `taskset -c 10-19`, 1 BLAS/OMP thread, a 6 GB results job running concurrently (wall times are contended).
- Raw numbers: `results/rishon/tester-206-summary.json`, `tester-206-hb-tamper.json`, `tester-206-hb-independent.py`, logs `tester-206-{unit,acc,l3-test}.log`.

## Verdict: PASS for 5.L1–5.L3 (one unrelated unit failure flagged, see F1)

## Commands
```
pytest tests/acceptance/m5/test_rishon_lean.py -k "L1 or L2"      # 2 passed, 28.7 s wall, peak RSS 6.8 GB
pytest tests/acceptance/m5/test_rishon_lean.py -k L3              # 1 passed, 10.1 s, 0.82 GB
pytest tests/unit -n 4                                            # 307 passed, 1 failed, 322 s
pytest tests/acceptance -m "not slow" -n 3                        # 94 passed, 33 failed (all 33 = PENDING, laptop M2), 2514 s
~/.claude/bin/acceptance-check                                    # PASS: matches acceptance-v8
lake build --no-build Su2Plaq                                     # "All targets up-to-date"; Structure.Counts only "Replayed", never rebuilt
lake env lean <file>   (Counts, JW, HB, HBData, own #print axioms, own mutants, 17 own tampered certificates)
python results/rishon/tester-206-hb-independent.py                # independent checks of the certificate
```

## Results
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| M5-L1 `test_M5_L1_counts_kernel_checked` | pass | pass | exact | PASS |
| M5-L2 `test_M5_L2_jw_facts_kernel_checked` | pass | pass | exact | PASS |
| M5-L3 `test_M5_L3_hb_structure_certificate` | pass | pass (9.2 s) | exact | PASS |
| `acceptance-check` | PASS | PASS acceptance-v8 | — | PASS |
| `native_decide` / `sorry` / `admit` under `lean/Su2Plaq/` | none | none (only the word "admits" in a Structure/Counts comment) | — | PASS |
| `native_decide` under `lean/Su2PlaqCert/` | none | none (only in `lean/certs/` file) | — | PASS |
| axioms card_rishon_physical / closed | standard only | `[propext]` each | — | PASS |
| axioms car_4, car_8, bilinear_string_free_8, sector_card, det_u_sector, end_bilinear_local | standard only | none (no axioms) | — | PASS |
| axioms u_ladder | standard only | `[propext, Quot.sound]` | — | PASS |
| axioms rishon_hb_structure | std + exactly 1 native | test: exactly one native axiom (`Lean.ofReduceBool`-type) | — | PASS |
| Counts values | 38 432 / 4 352 | `#check` shows `rishonTotal = 38432`; `rishonTotal := sumOver (fun n => patternCount n * 2^zeros n) 4096`; theorems proved by `decide +kernel` (kernel evaluation, not by definition) | exact | PASS |
| Counts build | ≤ 600 s, ≤ 15 GB | `lake env lean Counts.lean`: 31.8 s, 8.3 GB RSS (contended) | | PASS |
| JW build | within limits | `lake env lean JW.lean`: 264.8 s, 7.1 GB RSS (contended with the unit run); no errors or warnings | | PASS |
| HB.lean / HBData.lean compile | — | 2.5 s / 2.6 s, 0.82 GB | | PASS |
| unit suite | all pass | 307 pass, 1 fail (F1) | | see F1 |
| m0+m1 regression | 54/54 | 54/54 | | PASS |
| m5 non-slow | all | 31/31 pass + L3 (slow) pass | | PASS |
| m2 (laptop, not a completed milestone here) | — | 9 pass, 33 PENDING (`... is not built yet`: general_circuit, gridsynth_T, import_seed, Archive.load, lean.certify.*, lean.structure.*, qiskit_l3, code_hash, evaluate_circuit, general_program_path) | | PENDING, unrelated |

### Statement review (point 2)
Each theorem is a genuine statement quantified over finite ranges, proved by kernel evaluation; none is a restated definition.
- `card_rishon_physical : rishonTotal = 38432`, `card_rishon_closed : rishonClosed = 4352`. The numbers come out of a kernel computation of $\sum_{n<4096}\text{patternCount}(n)\,2^{\text{zeros}(n)}$ (and $n<16$ for the closed sector) built on the laptop's `cornerCount`/`patternCount`; the same two numbers are found by Python's three routes (reports 201). This is a fourth route, with a different weighting (singlet multiplicity $2$ for $j=0$, $1$ for the quartet). PASS.
- `car_4`, `car_8`: $\forall k,l$: $\{c_k,c_l^\dagger\}=\delta_{kl}$, $\{c_k,c_l\}=\{c_k^\dagger,c_l^\dagger\}=0$ on 4 and 8 modes, JW operators defined in the file as sparse signed partial permutations.
- `bilinear_string_free_8`: for all $d_1,d_2\in\{c,c^\dagger\}$ and all mode pairs of one link, the 8-mode product equals the 4-mode product embedded at qubits 4–7 (and 0–3). Stronger than the plan (all four dag combinations, both links).
- `sector_card`: weight-2 strings of 4 bits are exactly `[3,5,6,9,10,12]` (length 6).
- `u_ladder`: $U_{ij}$ maps $A$ to one $Q$ state with sign $\pm1$, $Q\to B$ or 0, $B\to0$, and the four images of $A$ are distinct.
- `det_u_sector`: $\det U = 2U_{11}U_{22}$ gives $A\mapsto 2B$ (coefficient $+2$) and every other sector state $\mapsto0$.
- `end_bilinear_local`: every product of two modes of one link end acts only on that end's two qubits.

Deviations judged:
1. `Nat` with explicit bounds `s < 2^n` instead of `Fin (2^n)`: equivalent (every quantifier is bounded; operators are guarded `k < n`). Acceptable.
2. Sparse `SOp` (lists of (image, coefficient)) instead of the monomial `FOp`: needed because $\{c,c^\dagger\}$ and the embedded sums are not monomials; `FOp` is retained for $c$, $c^\dagger$. Equality is `OpEq` on all $s<2^n$ after normalising (merge equal images, drop zeros, sort). Acceptable; strictly more general.
3. "six" vs "seven": the plan's own code block (lines ~152–158) lists seven names (`car_4, car_8, bilinear_string_free_8, sector_card, u_ladder, det_u_sector, end_bilinear_local`) and the locked test names seven; "six" in the step table is a miscount. No change of meaning.

Sensitivity (my own mutants of a trimmed copy of JW.lean, `scratch/t206/jw_mut_*.lean`): JW sign string removed (`jwSign := 1`) -> `car_4` rejected; creation sign := 1 -> `car_4` and `det_u_sector` rejected; $\det$ coefficient 2 -> 3 -> `det_u_sector` rejected; sector weight 2 -> 1 -> `sector_card` rejected. The unmutated trimmed file compiles with no errors. So the theorems are not vacuous.

### L3 certificate soundness (point 3)
`checkHB` recomputes $W=\sum_{abcd}U_{ab}\otimes U_{bc}\otimes U^\dagger_{dc}\otimes U^\dagger_{ad}$ from the eight $6\times6$ link matrices, then checks (parts `shape, kappa, dark, ortho, identity`):
$16(W+W^T)=\sum_p\kappa_p\big[(4u_p)(4v_p)^T+(4v_p)(4u_p)^T\big]$ entrywise in $\mathbb Z[\sqrt2]$; the Gram matrix of the 162 vectors $=16\,\mathbb 1$; $\kappa$ multiset $\{1{:}32,2{:}48,4\sqrt2{:}1\}$ and 81 pairs; 990 codes outside the support; indices $<1296$, `nCodes = 1296`, 8 link ops with entries in $6\times6$. All exact integer-pair arithmetic.

Independent confirmation (own code, `tester-206-hb-independent.py`):
| check | expected | got |
|---|---|---|
| cert link ops vs my own 4-mode JW $c_k=Z^{\otimes k}\sigma^-_k$ on the sector $[3,5,6,9,10,12]$ ($U_{ij}=c_{L_i}c^\dagger_{R_j}$, $U^\dagger$ as transpose) | equal | max deviation 0.0 |
| my own $W$ (numpy kron) from the cert link ops vs production `plaquette_W_inner` | equal | 0.0 |
| $\|16(W+W^T)-\sum\kappa(\dots)\|_\infty$ (floating, cert $\mathbb Z[\sqrt2]$ values) | 0 | 3.6e-15 |
| Gram of the 162 vectors minus $16\,\mathbb1$ | 0 | 3.6e-15 |
| support / dark codes | 306 / 990 | 306 / 990 |
| spectrum of $-(W+W^T)$ | $\pm4\sqrt2(1),\pm2(48),\pm1(32),0(1134)$ | identical |
| $2U_{00}U_{11}$ on the sector $=2|B\rangle\langle A|$ | 0 | 0.0 |

Because the vectors are orthonormal and the identity holds, the spectrum follows exactly; the 990 "dark" codes are outside every vector's support so $H_B$ vanishes on them; the 144 remaining zero modes lie inside bright components (990+144=1134). The statement is the plan's.

Tampered certificates (each through `check_hb`, native Lean; times 2.6–4.4 s each; JSON `tester-206-hb-tamper.json`):
| tamper | status |
|---|---|
| swap a $\kappa=1$ with a $\kappa=2$ (multiset unchanged) | rejected (only `identity` fails) |
| one $\kappa$ 2 -> 1 | rejected |
| $\kappa=4\sqrt2 \to 5$ | rejected |
| one vector entry +1 | rejected |
| one vector index shifted | rejected (`dark`, `ortho`, `identity` fail) |
| drop a pair (middle / last) | rejected (`kappa`, `dark`, `identity` fail) |
| duplicate a pair (82 pairs) | rejected (`kappa`, `ortho`, `identity` fail) |
| index 1296 (out of range) | rejected (`shape`) |
| `n_codes` = 1295 | rejected |
| a link-matrix entry sign flipped (U) / (Ud) / an entry dropped | rejected / rejected / rejected |
| $\kappa\to-\kappa$ on one pair; $u\to-u$ only | rejected / rejected |
| control: swap $u\leftrightarrow v$ of one pair (valid, $H$ symmetric); extra zero-valued entry | certified / certified (as they should) |
The per-part booleans (`#eval checkHBParts`) show each of `kappa`, `dark`, `ortho`, `identity`, `shape` can fail individually, i.e. no part is vacuous.

`HBData.lean` and `lean/certs/rishon-hb-structure.lean` regenerated by `write_hb_lean` into scratch are byte-identical to the repo files (`True, True`); also checked by the builder's unit test `test_repo_generated_files_match_code` (passes).

`Su2PlaqCert.Rishon.HB` is not imported by `lean/Su2PlaqCert.lean`: this does not affect the tests, because `check_hb` explicitly runs `lake build +Su2PlaqCert.Rishon.HB` (and `+...HBData` if imported) before `lake env lean`. Consequence: a plain `lake build` does not compile the checker, so it could rot unnoticed outside the tests (N2).

### The edit in `tests/unit/test_rishon_stubs_unit.py` (point 1)
Legitimate. The test asserted that `export_hb_certificate`, `write_hb_lean`, `check_hb` raise `NotImplementedError`; they are now implemented, so the assertion is obsolete. `PENDING` is emptied and the parametrisation falls back to one sentinel that returns (a vacuous test, harmless). The functions are now covered by real tests in `test_rishon_lean_export_unit.py` (export values vs numerical bright pairs, exact Python mirror, accept/reject, regeneration identity, three real Lean tampering runs). No tolerance, no skip/xfail, no acceptance test touched.

## Failures / flags
- **F1 (unrelated to this diff, flagged):** `tests/unit/test_results_unit.py::test_render_is_deterministic_and_contains_only_json_numbers` fails with `assert 'c1' not in t_noq` because the rendered provenance line contains the git hash `b4c1917*`, which contains the substring `c1`; the test uses circuit ids `c0`, `c1`. Guess: a laptop-inherited test that is hash-dependent; it passed at the previous commit and will pass again whenever the HEAD hash has no `c1` (about 98 % of hashes). It is not caused by the Lean changes. I did not edit it (rule: tests are not mine to change); the coordinator should have a planner/builder make it hash-independent.
- N1 (design note, non-blocking): the eight link matrices in `HBData.lean` are certificate data; the Lean checker recomputes $W$ from them but does not itself tie them to the `Uop` of `JW.lean` (nor check $U^\dagger=U^T$). I checked this outside Lean: they equal my own JW matrices exactly (deviation 0.0), and sign flips of any entry are rejected by the identity check. If the audit wants a closed formal chain, a Lean lemma connecting `Uop` restricted to the sector to `linkOps` is the missing piece.
- N2: add `import Su2PlaqCert.Rishon.HB` to `lean/Su2PlaqCert.lean`, or run `lake build +Su2PlaqCert.Rishon.HB` in CI, so the default build covers the checker.
- N3: build times for JW (265 s) and Counts (32 s) were measured from source via `lake env lean` while other jobs ran; the cached `lake build` of the targets is instantaneous. The limits in the plan (Counts ≤ 600 s / 15 GB) hold with a wide margin (8.3 GB).
- N4: `lake build Su2Plaq` did not rebuild `Structure.Counts` (only "Replayed").

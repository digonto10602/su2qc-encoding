# Report 107 — M3x (prompts/102 W0–W4): exact Lean recoupling, gate semantics, spectrum, bridge — tester, mode `step`

- Date: 2026-11-06 · Git: `d55fa94` + uncommitted (branch `m3-spin-network`; the brief said c655475, HEAD is the later docs-only commit d55fa94)
- Prompt in force: `prompts/102-spinnet-m3-wait-lean-structure.md` (+ `prompts/103-spinnet-m3x-test-fixes.md`), acceptance-v9
- Related: `reports/tests/105` (L1/L2 trust caveats this step closes), `reports/audits/100` (§2.3, N4), `reports/research/101`
- Under test (uncommitted): `lean/Su2Plaq/SpinNet/{Recoupling,Semantics,Spectrum,Bridge}.lean`, one appended line in `lean/Su2Plaq.lean`, `src/su2plaq/spinnet/lean_export.py` (W0–W2 functions), `tests/unit/test_spinnet_lean_exact_unit.py`
- Raw data and scripts: `results/spinnet/tester/m3x_*` (listed at the end)

**VERDICT: PASS** (no failures, no pending in the m3x/m3 scope other than the known M3-L3 that waits for the laptop's checker).

## 1. What was asked
Independent verification of the builder's W0–W4: do the new Lean theorems state and prove what plan 102 §1–§2 claims, do they hold on trusted axioms only, are they tied to the real Python/Qiskit objects, and do they actually fail when the model is wrong (mutation tests).

## 2. Commands run (all from `~/Projects/su2qc-spinnet`, env `su2qc-coding`, `taskset -c 0-9`, 1 BLAS thread)
```
taskset -c 0-9 pytest -n 1  tests/acceptance/m3x -q
taskset -c 0-9 pytest -n 10 tests/unit -q
taskset -c 0-9 pytest -n 10 tests/unit/test_spinnet_lean_exact_unit.py -q
taskset -c 0-9 pytest -n 10 tests/acceptance/m3 -q -k "not M3_L"
taskset -c 0-9 pytest -n 1  tests/acceptance/m3 -q -k "M3_L"
taskset -c 0-9 pytest -n 10 -m "not slow" tests/acceptance/m0 tests/acceptance/m1 -q
pytest --collect-only -q tests/acceptance ; python tools/check_lock.py ; ~/.claude/bin/acceptance-check
cd lean && taskset -c 0-9 lake build Su2Plaq          # incremental
lake env lean /tmp/.../Ax.lean                           # #print axioms of the 12 theorems
python results/spinnet/tester/m3x_independent_checks.py  # C1-C5, independent numeric/exact cross-checks
python results/spinnet/tester/m3x_mutate.py <scratch> 3  # 24 mutants (scratch copy outside the repo)
python results/spinnet/tester/m3x_mutate_py_tie.py <scratch>
```

## 3. Gate checks
| check | expected | got | tolerance | result |
|---|---|---|---|---|
| m3x acceptance (W1, W2, W3, L) | 4/4 pass | 4 passed, 16.5 s | — | PASS |
| unit suite | all green | 309 passed (new file: 14 passed) | — | PASS |
| m3 acceptance, non-Lean | green | 21 passed | — | PASS |
| m3 L1, L2 | pass | 2 passed | — | PASS |
| m3 L3 (native certificate) | PENDING (laptop checker) | `PENDING: Su2PlaqCert checker not yet delivered` | — | PENDING (expected) |
| m0 + m1, `-m "not slow"` | green | 54 passed (130.6 s) | — | PASS |
| collection | 130 tests | 130 | exact | PASS |
| `tools/check_lock.py` | LOCK OK | LOCK OK | — | PASS |
| `acceptance-check` | PASS acceptance-v9 | PASS: matches acceptance-v9 | — | PASS |
| `lake build Su2Plaq` incremental | green, `Structure/Counts` not rebuilt | "Build completed successfully (9064 jobs)", 2.95 s, `Structure.Counts` shown as *Replayed*; `Counts.olean` mtime 2026-11-05 23:54:26.3018 before and after | identical mtime | PASS |
| per-file elaboration (plan limits ≤ 60/60/90 s, ≤ 3 GB) | within | Recoupling 7.6 s / 0.82 GB; Semantics 4.5 s / 0.90 GB; Spectrum 11.5 s / 1.10 GB; Bridge 2.8 s / 6.8 GB (Mathlib import) | plan 102 §4 | PASS |
| ownership | only the listed files | `git status`: M `lean/Su2Plaq.lean` (+1 line `import Su2Plaq.SpinNet.Bridge`), M `lean_export.py` (+202/−1: the `-1` is the `CIRCUIT_LEAN` line re-expressed through `_SPINNET_LEAN`, same value), untracked 4 Lean files + 1 unit test; `Circuit.lean`, `Counts.lean`, laptop-owned dirs untouched | exact | PASS |

## 4. Trust: axioms and source scan
`#print axioms` (one Mathlib-importing `lake env lean`, 4.2 s, 6.8 GB):

| theorem | axioms |
|---|---|
| `valid_codes_from_codec`, `ub_h_count`, `card_states_exact`, `blocks_cover` | `[propext]` |
| `k_matching`, `coupling_from_6j`, `k_from_6j_full`, `ub_exact_all_codes`, `eig_blocks`, `eig_count`, `eig_mult` | `[propext, Classical.choice, Quot.sound]` |
| `tables_agree` | none |

All are in the allowed standard set. Note (not a failure): plan 102's prose says "at most `propext`", but seven theorems also list `Classical.choice`, `Quot.sound` (they enter through the `List.all` / `Int` decidability lemmas used by `decide`; the evaluation itself is still the kernel's). The locked test allows the three. `grep` for `sorry|admit|native_decide|axiom ` in the four new files: no hits. No `Rat`, `Nat.sqrt`.

## 5. Do the statements say what plan 102 §1–§2 claims?
Read line by line (`Recoupling.lean`, `Semantics.lean`, `Spectrum.lean`, `Bridge.lean`).

1. **K derived in Lean from 6j/F-symbols, not copied.** `sixj` is Racah's sum in exact `Nat`/`Int` arithmetic (`q·√r`), `fsym` is Edmonds 6.1.5, `pAmp`/`kEntry?`/`twoK?` build $K=-(P+P^{\mathsf T})$ from the codec (`Jc`, `cornerP/N`, `validCode`). The exported tables enter only through `coupling_from_6j` and `k_from_6j_full` as the *right-hand side* of an equation with the 6j-computed value (all $47\times47=2209$ entries, symmetric, zero off the four-link flip). `tables_agree` (Mathlib side) ties the same two lists to M3's `validInnerCodes`/`couplingTable`. Independent confirmation (C1): my own exact sympy computation of $K$ (sympy `wigner_6j`, formula re-transcribed from METHODS §5) equals Lean's `kEntry?` in 2209/2209 entries (0 mismatches, none irrational), equals the exported $2K$ on all 47 codes, takes values $\{-4,-1,0,2\}$ for $2K$, and agrees with the production float `K_codes` to $1.8\cdot10^{-15}$.
2. **`ub_exact_all_codes`.** Statement: for every valid code $y$ (ancillas 0) `runGates ubGates [(y,1)] == target y (twoK? y)`, where $\text{target}=(z^{m}+z^{-m})|y\rangle-(z^{m}-z^{-m})|y\oplus15\rangle$ (dark: $2|y\rangle$), $m=2\cdot(2K)$ computed from 6j, coefficients in $\mathbb Z[i][z^{\pm1}]$ stored canonically (sorted, no zero terms), so list equality is an identity of Laurent polynomials in $z=e^{i\beta/4}$, hence true for every $\beta$. Equality of the *whole* sparse vector also forces clean ancillas and zero leak (no basis index $\ge256$ appears). With `ub_h_count = 2` the true output is $\tfrac12\times$ this, i.e. $e^{-i\beta K}|y\rangle$; I re-derived $z^{m}=e^{i\beta K}$ and the sign of the off-diagonal term. Numeric check (C3): Lean's exact output evaluated at $z=e^{i\beta/4}$, $\beta\in\{0.61,1,0.05,2.3,-0.7,3.9\}$, equals Qiskit `Statevector` of `build_UB(β)` on all 47 codes to $9.9\cdot10^{-15}$ and equals $\exp(-i\beta K_{\rm prod})$ to $7.2\cdot10^{-15}$; the Qiskit output has amplitude exactly 0.0 outside the data indices. Scope limit: inputs are the 47 valid codes with clean ancillas (the physical subspace); invalid codes are not covered.
3. **Gate list tied to the real circuit.** `ubGates` is a generated block (`write_lean_exact_tables`); regenerating into scratch copies reproduces both `Recoupling.lean` and `Semantics.lean` byte for byte. My own parser of the `.lean` literal (not `gate_ints`) equals the `qc.data` list of `build_UB(β)` for $\beta\in\{1,0.61,0.05,2.3,-0.7\}$: 48 gates (cx 12, h 2, x 16, rccx 14, rz 4), identical. The Lean model has 15 wires (ancillas on 8..14); the shipped circuit `build_UB(β, with_outer=True)` has 23 wires: its gate list is *exactly* the 15-wire list with ancilla wires relabelled $8..14\to16..22$ and no gate touches the outer wires 8..15 (checked structurally), so the model is the shipped circuit.
4. **Lean gate matrices vs Qiskit (incl. RCCX phases).** C4: `lean_gate_images` vs `Operator` for 26 cases on 3 qubits (x ×3, cx all 6 orientations, rccx all 6 wirings, h ×3, rz with $a\in\{-7,-2,3,6\}$ on 2 qubits) at $\beta=0.61$: max deviation $2.2\cdot10^{-16}$. Mutants that change the RCCX relative phases survive the Lean theorems (see §7) but their 8×8 matrix differs from Qiskit's `rccx` by 2.0, so the W2 matrix tie is what pins them, as plan 102 says.
5. **`eig_*`.** `hb2` = route-B definition ($\delta_{oo'}K[y\oplus15,y]$ from the exported $2K$, tied to 6j by §5.1). `eig_blocks` checks $(2H_Bv)_t=2\lambda\,v_t$ for every candidate vector and every row of its block; `eig_count` = 433; `eig_mult` = `[16,96,16,177,16,96,16]` for $2\lambda\in\{-4,-2,-1,0,1,2,4\}$. Independent check (C5), using the Lean eigenvector list (433 triples $(o,y,\sigma,2\lambda)$ from `#eval`) embedded in the encoding's 433-state order: $\max|H_B^{\rm prod}V-V\Lambda|=1.8\cdot10^{-15}$ with $H_B^{\rm prod}=$ `SpinNet().h_magnetic()` (production route B), Gram matrix off-diagonal max 0.0 (exactly orthogonal), diagonal min 1.0 (all vectors nonzero, norms² 1 or 2), rank 433, sorted Lean eigenvalues vs `eigvalsh(H_B)` max dev $1.8\cdot10^{-15}$, multiplicities (16,96,16,177,16,96,16) reproduced; Lean's own dense `hb2/2` over all $433^2$ pairs equals `h_magnetic()` to $1.8\cdot10^{-15}$ (256 non-zero entries = the 256 bright states; cross-block zeros confirmed numerically).

## 6. What remains unproved (stated as such)
- **Orthogonality / linear independence / completeness of the 433 eigenvectors is not a Lean theorem.** Lean proves the eigen-equations and the counts; "433 orthogonal vectors ⇒ the multiset of eigenvalues is the spectrum" is standard linear algebra, not re-proved (checked numerically: Gram off-diagonal 0.0, rank 433). `eig_blocks`+`eig_count` alone would accept duplicated vectors; only `eig_mult` happens to reject that (mutant S2).
- **$H_B=\bigoplus_o K$ is route B's definition** in Lean; it is not derived from the Hamiltonian. Route A ↔ route B agreement stays numerical (M0-X4–X6, M3-K1). Lean's `hb2` vs production `h_magnetic` is checked here numerically (above).
- **The F-symbol product formula** (argument order, corner assignment, phase) is a transcription; my sympy check re-transcribes the *same* METHODS §5 formula, so it guards against Racah/arithmetic/codec mistakes, not against a formula error shared with METHODS (that is covered by the numerical route-A comparison).
- **Lean gate semantics ↔ Qiskit** is numeric (26 matrices, $\le2.2\cdot10^{-16}$) plus the generated-literal tie, not a proof. Relative phases of RCCX cancel in the compute/uncompute sandwich, so the Lean theorems do not detect them.
- `angleTable`/the rz integers are chosen by Python; their correctness for the 6j-computed $K$ is exactly what `ub_exact_all_codes` proves.
- Inputs limited to valid inner codes with clean ancillas; outer register not modelled (shown untouched structurally, §5.3).
- Axioms include `Classical.choice`, `Quot.sound` (standard).

## 7. Mutation tests (scratch copies of the three Mathlib-free files concatenated outside the repo, bare `lean`, 15–29 s, 1.1 GB each)
Control (unmutated concatenation): all 11 theorems pass. `lean` reports a failing `decide` as an error at the theorem.

| id | mutation | theorems that FAIL |
|---|---|---|
| B1 (builder) | `rz` sign flipped in `applyBasis` | `ub_exact_all_codes` |
| B2 (builder) | one `ubGates` angle `.rz 0 (-7)` → `(-6)` | `ub_exact_all_codes` |
| B3 (builder) | eigenvalue signs swapped in `eigsOf` | `eig_blocks` |
| T2b (mine) | one F-symbol value negated, $(J,j_p,j_n)=(\tfrac12,0,\tfrac12)$ | `coupling_from_6j`, `k_from_6j_full`, `ub_exact_all_codes` |
| T2c (mine) | one F-symbol value negated, $J=0$, $j_p=j_n=\tfrac12$ | same three |
| T3 (mine) | F phase exponent loses the $J$ term | same three |
| T4 (mine) | F factor $\sqrt{(2j_{12}+1)(2j_{23}+1)}$ → $\sqrt{2j_{12}+1}$ | same three |
| T6 (mine) | $K=+(P+P^{\mathsf T})$ | same three |
| T5 (mine) | codec: corner 0 visits $(r,b)$ instead of $(l,b)$ | `valid_codes_from_codec`, `coupling_from_6j`, `k_from_6j_full`, `ub_exact_all_codes`, `card_states_exact`, `blocks_cover`, `eig_count`, `eig_mult` |
| G1 (mine) | gate qubit index `.cx 14 0` → `.cx 14 1` | `ub_exact_all_codes` |
| G2 (mine) | `.rccx 6 7 9` → `.rccx 6 7 10` | `ub_exact_all_codes` |
| G3 (mine) | last gate `.cx 1 3` dropped | `ub_exact_all_codes` |
| G4 (mine) | one uncompute `.rccx 4 5 8` dropped | `ub_exact_all_codes` |
| G5 (mine) | $H$: sign of the $|1\rangle$ branch dropped | `ub_exact_all_codes` |
| G8 (mine) | target off-diagonal sign flipped | `ub_exact_all_codes` |
| S1 (mine) | expected multiplicities 16→15, 177→178 | `eig_mult` |
| S2 (mine) | both partners get the $+$ vector (duplicated vectors) | `eig_mult` only |
| S3 (mine) | $\mathrm{fuse}(\tfrac12,\tfrac12)=\{0,\tfrac12\}$ | `card_states_exact`, `blocks_cover`, `eig_count`, `eig_mult` |

Mutants that survive all Lean theorems, and what catches them instead:

| id | mutation | Lean | why / who catches |
|---|---|---|---|
| G6 | RCCX relative phases conjugated ($i\leftrightarrow-i$) | all pass | correct physics: compute/uncompute sandwich cancels the phases (plan 102 §1). Lean `rccx` 8×8 matrix differs from Qiskit's by **2.0** → caught by the W2 matrix tie |
| G7 | RCCX as plain Toffoli (all relative phases 1) | all pass | same; matrix deviation **2.0** from Qiskit |
| T1 | Racah alternating sign $(-1)^z$ removed | all pass | $K$ of these 47 codes is unchanged (equivalent for $K$); Lean `sixj` then differs from sympy on **18 of 729** tuples, max dev 1.414 → caught by the W1 acceptance test (sympy/`six_j` comparison) |
| T2 | F value negated for $J=1$ corners | all pass | equivalent mutant for $K$: $J_c=1$ corners occur only in the 31 dark codes where $K=0$ (the flip leaves the valid set); the 6j table itself is unchanged (max dev 0.0 vs sympy) |
| S4 | `hb2` ignores the outer-block condition | all pass | equivalent for the checks: `eig_blocks` only queries same-block pairs; cross-block zeros are route B's definition, confirmed numerically (Lean `hb2` vs `h_magnetic`, $1.8\cdot10^{-15}$) |

All three builder mutations (B1–B3) reproduced: they fail exactly `ub_exact_all_codes` / `ub_exact_all_codes` / `eig_blocks`, as plan 102 §4 requires ("decide reports is false"). Fifteen of my 20 own mutants (plus the 3 builder ones) are caught by Lean theorems; the survivors are either caught by the locked Python ties (G6, G7, T1) or are equivalent for the statement (T2, S4).

## 8. Failures
None. Observations (not failures): (i) HEAD in the brief (c655475) is d55fa94 (docs-only successor). (ii) `Classical.choice`/`Quot.sound` appear although plan 102 said "at most propext". (iii) the `graphify update .` did not re-index the Lean files (code-graph topology unchanged).

## 9. Raw data (`results/spinnet/tester/`, commit d55fa94 + uncommitted; no random seeds — all computations deterministic)
- `m3x_independent_checks.py`, `m3x_independent.json` — C1–C5
- `m3x_mutate.py`, `m3x_mutation_results.json` (24 mutants incl. control, with wall time / peak RSS), `m3x_mutate_py_tie.py`, `m3x_mutation_pytie.json`
- `m3x_counts_olean_mtime_before.txt`, `m3x_counts_olean_mtime_after.txt`

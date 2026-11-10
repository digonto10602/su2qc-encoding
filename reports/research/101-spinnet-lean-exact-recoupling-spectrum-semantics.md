# Research 101 — Kernel-checked exact structure of the spin-network encoding: 6j/recoupling over square-root-free rationals, the $H_B$ eigenbasis on 433 states, exact gate semantics of the general circuit (feasibility prototype)

- Date: 2026-11-06 · Author: planner (Claude Fable 5.1) · Git commit: `5a03f98` (branch `m3-spin-network`, tag `milestone-3`)
- Prompt in force: `prompts/100` (M3, done) → this research feeds `prompts/102-spinnet-m3-wait-lean-structure.md`
- Related: `reports/tests/105` (trust judgement), `reports/audits/100` §2.3 + N4, `docs/report-3-spinnet-general-circuit.md` §3.5, `prompts/006` (trust levels, do-not-retry list), `reports/research/004` (Lean prototypes P1–P6), `reports/research/100` §6
- Prototype: `scratch/planner/lean/SpinNetExact.lean` (one Mathlib-free file, 11 theorems, all `by decide`); runner `scratch/planner/lean/run_guarded.sh` (polls RSS, kills at 9 GB); variants `vA/vB/vC.lean`, mutations `mut_*.lean`. Command: `cd lean && source ~/.elan/env && taskset -c 0-9 lake env lean ../scratch/planner/lean/SpinNetExact.lean`. Lean v4.35.0 toolchain of the project; no Mathlib import.

## 1. What was asked
Choose ≤ 3 wait-time work items (START_HERE §6) that close the most important Lean caveats of M3 without the laptop's checker and without `native_decide`, and prototype their feasibility (Lean time/memory) before choosing.

## 2. Sources used (opened and read)
- Racah's closed formula for the 6j symbol and the recoupling coefficient: A. R. Edmonds, *Angular Momentum in Quantum Mechanics* (Princeton, 1957), Eqs. 6.3.7 and 6.1.5 — the same equations the project's `su2plaq/su2/wigner.py` implements (verified against sympy in `reports/tests/003`, 570 symbols, $8.9\cdot10^{-16}$). Also D. A. Varshalovich, A. N. Moskalev, V. K. Khersonskii, *Quantum Theory of Angular Momentum* (World Scientific 1988) §9.2 (Racah formula, symmetries) for the special values $\{0\,b\,c;\,d\,e\,f\}=\delta_{bc}\delta_{ef}(-1)^{b+e+d}/\sqrt{(2b+1)(2e+1)}$ used to hand-check the prototype.
- Route-B plaquette operator in the spin-network basis: T. V. Zache, D. González-Cuadra, P. Zoller, *Quantum and classical spin-network algorithms for q-deformed Kogut–Susskind gauge theories*, Phys. Rev. Lett. 131, 171902 (2023), arXiv:2304.02527, Eq. 2 (product of F-moves around the plaquette) — as cited in `docs/METHODS.md` §5 and `docs/METHODS-spinnet.md` §2.
- Qiskit gate matrices: `qiskit.circuit.library.RCCXGate` (relative-phase Toffoli; matrix printed from `RCCXGate().to_matrix()` in this run, qiskit 2.5.2), `RZGate` ($\mathrm{diag}(e^{-i\theta/2},e^{i\theta/2})$), `HGate`; the project's `sparse_sim.SIM_BASIS` conventions (prompts/006 §1 M4).
- Lean kernel evaluation: Lean 4 reference, `decide` tactic and kernel `Nat` acceleration (GMP for `Nat.add/mul/div/mod/gcd/beq/ble/land/lor/xor/shiftLeft/shiftRight/pow`), https://lean-lang.org/doc/reference/latest/ (section "Tactic proofs → decide" and "Natural numbers → kernel reduction"); the project's prompts/006 §9 ("kernel `decide` for anything with `Rat`: stuck at `Rat.mul`") which motivated the custom fraction type.

## 3. Prototype results (all numbers from `run_guarded.sh`, cores 0–4 or 3–6 of the i7-12700KF, other track active on cores 10–19)
### 3.1 Design
- **Arithmetic**: `Frac` = unnormalised `(num : Int, den : Nat)`, equality by cross-multiplication; `SR` = $q\sqrt r$ with `q r : Frac`; `SR.toFrac?` reduces $r$ with `Nat.gcd` and takes exact integer square roots by bounded search (`List.range 512`; the largest reduced denominator met is $4096$, square root $64$ — a first attempt with range 64 failed exactly on the alternating pair $0101\leftrightarrow1010$, whose $r=1/4096$).
- **6j**: Racah sum on doubled spins; `fsym` with the project's phase convention (integer division of the doubled sum, as `wigner.f_symbol`); `pAmp y' y` = product over the four corners of $F^{J_c\,j_p\,j_n}_{\frac12\,j'_n\,j'_p}$ when the four link bits are flipped and all $J_c$ agree; `kEntry? y' y = -(P[y',y]+P[y,y'])`; `twoK? y` = the integer $2K[y\oplus15,y]$.
- **States**: `validCode` (corner bit only at a corner with both inner links $\tfrac12$) → 47 codes; `stateOK y o` with `fuseN` → 433 states in 128 non-empty outer blocks (sizes: 41×2, 52×3, 8×4, 22×5, 4×9, 1×17; $\sum n_o^3=12\,823$, computed in Python from `SpinNet().labels()`).
- **Eigenbasis**: per block, vectors $e_s\pm e_{s'}$ (sign by bit 0 of the code) and $e_s$ for dark codes; `hb2` = block-diagonal matching with the table's $2K$; dense check $(2H_Bv)_t=2\lambda v_t$ over all rows $t$ of the block.
- **Semantics**: `Lau` = sorted `(exponent, re, im)` lists (Gaussian-integer Laurent polynomials in $z=e^{i\beta/4}$), `Vec` = sorted `(index, Lau)`; gates `x, cx, rccx, h, rz q a` with Qiskit matrices (`rz` angle $a\beta/2\Rightarrow\mathrm{diag}(z^{-a},z^{a})$; `h` unnormalised with the $1/\sqrt2$ counted by `hCount`); `ubGates` = the 48 gates of `build_UB(0.61)` read off `qc.data` in this run; `target y twoK` = $2e^{-i\beta K}|y\rangle$.

### 3.2 Kernel cost (wall / peak RSS; `lake env lean`, no Mathlib)
| Variant | Theorems | Wall | Peak RSS | Result |
|---|---|---|---|---|
| A | `valid_codes_eq`, `coupling_from_6j`, `k_matching`, `k_from_6j_full` (47×47) | 8.2 s | 1.49 GB | all proved |
| B (first version: dense 433×433 through the 6j-valued `hb`) | `eig_vectors` | killed at 133 s | 9.05 GB | **too heavy** (kernel whnf cache) |
| B (per outer block, integer `hb2`) | `card_states`, `blocks_cover`, `eig_blocks`, `eig_count`, `eig_mult` | 11.2 s | 1.89 GB | all proved |
| C | `h_count_two`, `ub_exact_all` (47 codes × 48 gates) | 4.1 s | 1.65 GB | all proved |
| full file | all 11 | 22.4 s | 1.91 GB | all proved |
| first attempt (all three, dense B, `Nat.sqrt`-free but range-64 sqrt) | — | killed at 161 s | 12.6 GB | abandoned → split and restructured |

### 3.3 Mutation tests (each a one-line change; "FALSE" = `decide` reports the proposition is false)
| Mutation | Theorem | Result | Reading |
|---|---|---|---|
| `rz` convention flipped ($\mathrm{diag}(z^{a},z^{-a})$) | `ub_exact_all` | FALSE | sign/exponent convention $e^{-i\beta K}$ is checked |
| first angle $-7\to-6$ | `ub_exact_all` | FALSE | angle table checked |
| target off-diagonal sign flipped ($e^{+i\beta K}$) | `ub_exact_all` | FALSE | as above |
| one uncompute `x 4` dropped | `ub_exact_all` | FALSE | uncompute half checked |
| Hadamard sign on the wrong branch | `ub_exact_all` | FALSE | Hadamards checked |
| RCCX phases $i\leftrightarrow-i$ | `ub_exact_all` | proved | the compute/uncompute sandwich cancels the relative phases for either convention — expected; the Lean gate matrices are therefore tied to Qiskit by a separate numerical test (W2) |
| RCCX replaced by a plain Toffoli | `ub_exact_all` | proved | same reason (Report 3's "Toffoli semantics" reading was correct; now the cancellation is kernel-checked) |
| F-symbol phase $(-1)^{j_1+j_2+j_3+J}$ dropped | `coupling_from_6j` | FALSE | — |
| corner wiring changed (`cornerP`) | `coupling_from_6j` | FALSE | — |
| dimension factor $\sqrt{(2j_{12}+1)(2j_{23}+1)}$ dropped | `coupling_from_6j` | FALSE | — |
| Racah sign $(-1)^z$ dropped | `coupling_from_6j` | proved | every sum here has one term ($z$ range of length 1), so all 6j symbols flip sign together and the four-corner product is unchanged — a genuine degeneracy at $j_{\max}=\tfrac12$ |
| eigenvalue signs swapped in `eigsOf` | `eig_blocks` | FALSE | — |
| multiplicity list $177\to176$, $16\to17$ | `eig_mult` | FALSE | — |
| `fuseN` wrong (always $\{0,1\}$ for equal spins) | `card_states`, `blocks_cover`, `eig_count`, `eig_mult` | FALSE | — |
| `hb2` made non-symmetric | `eig_blocks` | FALSE | symmetry of $K$ on pairs is checked |

### 3.4 Hand-checked values (Varshalovich §9 special cases) agreeing with the prototype's `#eval`
$\{0\,0\,0;\tfrac12\tfrac12\tfrac12\}=-1/\sqrt2$, $\{0\,\tfrac12\,\tfrac12;\tfrac12\,0\,0\}=-1/\sqrt2$, $\{\tfrac12\,0\,\tfrac12;\tfrac12\,0\,\tfrac12\}=-\tfrac12$, $\{\tfrac12\,\tfrac12\,0;\tfrac12\,\tfrac12\,0\}=-\tfrac12$; corner amplitudes $F=+1$ for $(0,0)\leftrightarrow(\tfrac12,\tfrac12)$ at $J=0$, $F=+1$ for $(0,\tfrac12)\to(\tfrac12,0)$ and $F=-\tfrac12$ for $(\tfrac12,0)\to(0,\tfrac12)$ at $J=\tfrac12$; hence $P=1$ (vacuum pair, $K=-2$), $P=\tfrac14$ (alternating, $K=-\tfrac12$), $P=-\tfrac12$ (the six others, $K=+1$). Every corner amplitude is rational at $j_{\max}=\tfrac12$ (the $\sqrt2$ of the 6j cancels against the dimension factor), which is why the square-root-free representation closes.

## 4. Candidate comparison and choice
| Item | Closes | Trust level | Cost (kernel) | Duplicates the laptop? | Chosen |
|---|---|---|---|---|---|
| (a) $K$ from 6j in Lean | tables copied; $K$ numerical | kernel | 8 s / 1.5 GB | no (laptop's structure certificate is native and over $\mathbb Q(i,\sqrt2,\sqrt3)$ for the 12-qubit basis) | **W1** |
| (c) exact circuit semantics | rccx phases, Hadamards, sign convention, whole gate semantics; audit N4 | kernel | 4 s / 1.7 GB | no (one specialised 15-qubit theorem, no JSON, no general checker; M3-L3 stays pending) | **W2** |
| (b) spectrum on 433 states | pair-class-only multiplicities | kernel (explicit orthogonal eigenbasis; not Mathlib's `charpoly`) | 11 s / 1.9 GB | no | **W3** |
| Mathlib `Matrix.charpoly` of the $433\times433$ matrix | same as (b) with a stronger "spectrum" word | kernel, Mathlib | days of proof work, unclear feasibility | — | rejected (prompts/006 §9 spirit: no SU(2)/spectral theory in Mathlib) |
| $U_E$/step semantics with a second variable $z_\alpha$ | nothing numerical-only remains for $U_E$ (4 phase gates) | kernel | small | no | deferred (optional later step) |

Order of value: W1 > W2 > W3 (W2's theorem depends on W1's $K$ definition through `twoK?`, so W1 comes first).

## 5. Open points for the plan
- Memory: a file importing `Circuit.lean` loads Mathlib (≈ 8 GB RSS); the heavy `decide`s must live in Mathlib-free files, with a trivial `Bridge.lean` tying the exported literals to the m3 tables (`tables_agree`).
- `#eval` cross-checks (Lean 6j vs Python `six_j` on 729 tuples; Lean `states` vs the codec; Lean gate images vs Qiskit matrices) are the only ties between the Lean definitions and the shipped Python/Qiskit objects; they are numerical ($10^{-12}$) and labelled so.
- `List.range 512` in `isqrt?` costs ≤ 512 steps per call; called ≈ 200 times in W1 — negligible (measured inside the 8 s).

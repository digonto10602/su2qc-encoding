# Audit 201 — M5x (rishon wait-time Lean / robustness work): physics and numerics review

- Date: 2026-11-06 · Auditor: Claude Opus 5.5 (high) · Git commit reviewed: `34724fb` (branch `m5-rishon`, clone `~/Projects/su2qc-rishon`)
- Commit range: `milestone-5` (a8f051e) .. `34724fb` (`git diff milestone-5..HEAD`; 85 files, of which the reviewed source is 4 new Lean files, `src/su2plaq/rishon/{lean_export,results}.py`, `scripts/m5x_outer_row.py`, `docs/METHODS-rishon.md`, 2 locked test files, 3 unit-test files)
- Plan in force: `prompts/202-rishon-m5x-wait-robustness.md` (locked as acceptance-v9). Methods: `docs/METHODS-rishon.md` R6, R9. Research: `reports/research/201-rishon-m5x-wait-robustness.md`.
- Related reports: tester `reports/tests/209` (W0+W1), `210` (W2+W3), `211` (O1+W4), `212` (full gate, PASS); previous audit `reports/audits/200-m5-rishon-audit.md` (its N5, N6 are what M5x set out to close); `reports/tests/206` N1.
- Auditor scratch and raw numbers: `scratch/auditor201/outer_bound.py` → `results/rishon/auditor-201-outer-bound.{json,log}`; `scratch/auditor201/GadgetAllLinks.lean` (Lean probe); `scratch/auditor201/UESem_copy.lean` (regeneration check). Nothing in `src/`, `tests/`, `lean/`, `docs/`, `prompts/` was changed.

**VERDICT: PASS WITH NOTES** — no blocking issue. Six non-blocking notes (N1–N6), two of which (N1, N2) are documentation that should be fixed before the `milestone-5x` tag.

## 0. What was asked, what I did

Asked: check that the 11 new Lean theorems state what METHODS-rishon R9 and the plan say, and that they close audit 200 N5/N6a/N6b/N6c and tester 206 N1; say exactly what is still numerical. Check that the conventions match M5. Check that `outer_electric_certify` is sound (is it a valid operator-norm bound, up to one global phase, on the physical subspace of all 48 qubits, and is "certified" an honest word for a float computation?). Look for silent errors.

Actions (environment as in the brief, `taskset -c 10-19`, threads 1):
1. Read the four Lean files line by line against `JW.lean`, `HB.lean` (the checker), `HBData.lean`, METHODS-rishon R1/R2/R6/R9 and plan §1–§5. Read the Python diff (`results.py:156-221`, `lean_export.py:254-390`, `scripts/m5x_outer_row.py`) and both locked m5x test files.
2. My own soundness test of the outer-row bound (`scratch/auditor201/outer_bound.py`, seed 20261106, 339 s, 0.20 GB). I built 30 random 48-qubit mutants of the shipped row, each with perturbations ($R_x,R_y,R_z,P$, angle magnitude $10^{-6}$ to $10^{-2}$) on 3 random links. For each I computed the **true** operator-norm error on the product of the three link sectors ($216$ dimensions; the other 9 links are exact and add only a phase). I did this both at the certificate's own phase and at the optimal global phase, and compared with `error_bound`. I also ran four structural probes.
3. A Lean probe (`scratch/auditor201/GadgetAllLinks.lean`, `lake env lean`, 0.60 s, 0.82 GB) of the per-link gadget statement for all 12 link positions.
4. A check that the generated gate block of `UESemantics.lean` regenerates byte for byte (`write_lean_ue_gates` into a copy, `cmp`). A check of `qc.global_phase` of `build_UE`.

## 1. Checklist

| Item | Verdict | Where / evidence |
|---|---|---|
| Equations vs METHODS-rishon term by term | OK | $U_{ij}=c_{L,i}c^\dagger_{R,j}$ (`JW.lean:127`); `Udop i j` $=c_{R,j}c^\dagger_{L,i}=(c_{L,i}c^\dagger_{R,j})^\dagger$ (`HBLink.lean:40`); $\det U=U_{11}U_{22}-U_{12}U_{21}$ with 0-based `Uop 0 0`, `Uop 1 1`, `Uop 0 1`, `Uop 1 0` and `detU := smul 2 (comp (Uop 0 0) (Uop 1 1))` (`HBLink.lean:57-59`, `JW.lean:144`); $2G^z=\sum_e(n_{e,1}-n_{e,2})$, $G^+=\sum_ec^\dagger_{e,1}c_{e,2}$, $G^-=\sum_ec^\dagger_{e,2}c_{e,1}$ (`CornerKernel.lean:38-41`). The quartet Casimir: $H_E=\tfrac12\sum_a(L_a^2+R_a^2)=\tfrac12(\tfrac34+\tfrac34)=\tfrac34$ on $Q$, $0$ on $A,B$ (R1), so $U_E=e^{-i\frac34\alpha}$ on $Q$, i.e. $z^{-3}$ with $z=e^{i\alpha/4}$ (`UESemantics.lean:90-92`, `results.py:199`) |
| Time-evolution sign and ordering | OK | Lean `.p q a` multiplies by $z^{a}$ when bit $q=1$ (`UESemantics.lean:62`) = Qiskit `PhaseGate(θ)=diag(1,e^{iθ})` with $θ=a\alpha/4$. The locked W3 test ties the Lean images of `x`, `cx` (both orientations) and `p` to Qiskit `Operator` to $10^{-12}$. `build_UE` uses `p(-0.75 α)` (`circuits/rishon.py:12`) → $a=-3$. `comp A B` applies $B$ first. `runGates` folds in program order. Per-link program order is kept in `outer_electric_certify` (`results.py:186-192`). Reordering gates of *different* links is exact, because they act on disjoint qubits. `qc.global_phase` = 0 for `build_UE` at $\alpha\in\{0.37,1,2.9\}$ (checked) |
| Basis / index conventions | OK | Little-endian, bit $k$ = mode $k$; link $\ell$ = qubits $4\ell..4\ell+3=(L_1,L_2,R_1,R_2)$. Certificate triples are (row = output position, col = input position). Example: `U00` entry `(2,0,1)` is $A=3\mapsto 6$ (sector position 2), which is what `HB.lean` `opColumns` (column = input) and $W[r,c]=\langle r|W|c\rangle$ expect. Corner ends on qubits $(2e,2e+1)$ = (colour 1, colour 2), the same as R2 and `end_generator`. JW sign of $c^\dagger_{2e}c_{2e+1}$ is $+1$ for every $e$ (adjacent modes), and the kernel would not depend on it anyway. Register order: permuting the `d`/`o` registers leaves the certificate unchanged (probe: certified, bound 0.0). Both registers are multiples of 4 qubits and the target is the same on every link, so a link-preserving relabelling cannot fool it |
| Near/far end of outer links in `outer_electric_certify` | OK | The target depends only on "$Q$ or not". $A\leftrightarrow B$ under $L\leftrightarrow R$, and $Q\to Q$. So the near/far orientation of an outer link (R2) cannot change $T_\ell$. The anchor code $A=3$ has target phase 1, the same as $B$. The locked O1 test checks the target against the encoding's own `decode(...).count("Q")` on 40 seeded physical codes ($10^{-12}$) |
| Truncation | N/A | No truncation in M5x (rishon number 2 per link is the model, R1) |
| Normalisation; real/unit quantities | OK | $T_\ell$ and $V_\ell$ restricted to the sector are isometries. `phase` has modulus 1 (asserted in the test). The bound is for unit-norm $\Psi$ |
| Precision | OK, note N3 | float64/complex128 throughout. The Lean parts are exact (integers, $\mathbb Z[i][z^{\pm1}]$) |
| Randomness / seeds | OK | `outer_electric_certify` is deterministic. The sample seed 20261104 is recorded in `provenance.seeds`. Auditor seed 20261106 |
| Tests exercise the production path | OK | O1 calls the production `outer_electric_certify` and `build_UE`. W1 compares the exported certificate with the test's own numpy JW. W2 compares Lean `kerDim` (via `#eval`) with the production `physical.corner_kernel` and the test's own singlet count. W3 checks the generated literals verbatim against `build_UE`. No duplicate implementation stands in for production |
| Tolerances justified | OK | $10^{-10}$ = the METHODS §6 exact-angle `tol_err`; $10^{-14}$/$10^{-12}$ cross-checks are justified in plan §5. The $10^{-7}$ mutant is $10^3\times$ above the tolerance |
| Hard-coded expected numbers in source | OK, note N4 | None found. `n_links` comes from the encoding, the sector from `RishonLink`. 1296/81/12 appear only inside Lean *statements*. The Casimir $\tfrac34$ is a typed literal in the target (N4) |
| Silent exception catches | OK | The only catch is `except QiskitError` (`results.py:208`). It returns `reason="error"` with `detail`, never certified. Other exceptions propagate |
| Generated Lean data come from the code | OK | `write_lean_ue_gates` reproduces `UESemantics.lean` byte for byte (`cmp`: IDENTICAL). `linkOpsData := rishonHBCert.linkOps` is the very constant used by `lean/certs/rishon-hb-structure.lean` |
| Provenance | OK | `results/rishon/UE_outer_row_certified.json`: `git_commit 59e863d`, `git_dirty false`, command and seeds recorded. `git diff --stat 59e863d..HEAD -- src scripts lean tests` is empty, so the file is current |
| Lean statements = R9 / plan §1 and closure of the open items | OK, note N1 | §2 below |
| Report 5 consistency (W4 deliverable) | ISSUE (doc), N2 | §4 N2 |

## 2. The 11 Lean theorems: what they prove, what they close, what stays numerical

| Theorem (file:line) | States | Matches R9 / plan §1? | Closes |
|---|---|---|---|
| `hb_link_ops_from_jw` (`HBLink.lean:46`) | for $i,j<2$: certificate list $2i+j$ = `sectorEntries (Uop i j)`, list $4+2i+j$ = `sectorEntries (Udop i j)` and = transpose of list $2i+j$, and both operators keep the sector | yes. `sameSet` (equal length + mutual containment) is a correct set equality here: `sectorEntries` of a signed partial permutation has no duplicate entries, so equal length + mutual containment forces the certificate list to be duplicate-free and equal as a multiset | tester 206 N1, audit 200 N6c. The formal chain is now JW definitions → `rishonHBCert.linkOps` (kernel) → `checkHB` (native) |
| `hb_link_ops_count` (`:54`) | 8 lists | yes | — |
| `det_u_identity` (`:57`) | $U_{11}U_{22}-U_{12}U_{21}=2U_{11}U_{22}$ on all 16 link states (`OpEq 4`) | yes; proved from the definitions, so no normalisation convention is assumed | audit 200 N6b |
| `u_commute` (`:62`) | $[U_{ij},U_{kl}]=0$, all 16 index tuples | yes | R1 "measured exact" → proved |
| `corner_kernel_dims` (`CornerKernel.lean:90`) | for all 81 end configurations: $G^z,G^\pm$ keep `cornerBasis m`, and $D-\mathrm{rank}_{\mathbb Q}[2G^z;G^+;G^-]$ = `cornerCountR` of the end spins | yes. Fraction-free elimination gives the rank over $\mathbb Q$ = rank over $\mathbb C$. The joint kernel of $G^z,G^\pm$ equals that of $G^{x,y,z}$. `add` normalises (merges equal images, `JW.lean:79`), so `matRow`'s `find?` reads the full matrix element | audit 200 N6a, the decidable half |
| `card_inner_codes` (`UESemantics.lean:87`) | 1296 inner codes | yes | — |
| `ue_gadget_sector` (`:90`) | gadget **0** on each bare 4-bit sector code: eigenvector, phase $z^{-3}$ exactly on $Q$ | yes as stated in R9, but only for link position 0 (N1) | — |
| `ue_gates_structure`, `ue_outer_gates_structure` (`:94-95`) | rendered lists = 4 / 12 consecutive gadgets | yes | — |
| `ue_exact_all_codes` (`:98`) | the rendered 12-gate inner list maps each of the 1296 codes to $z^{-3\#Q(y)}\lvert y\rangle$ as a Laurent polynomial, i.e. for every $\alpha$ | yes. The output equals a single basis term with a unit-modulus coefficient, so block exactness, zero leak and the sign are all in one equality | `build_UE` inner exactness (was numerical M5-E1) |
| `corner_count_agree` (`Bridge.lean:21`) | `cornerCountR = cornerCount` on all 16 Boolean inputs | yes. It is an extensional equality of functions, so the Bool meaning ("true = spin ½") carries over automatically | ties W2 to the laptop's `cornerCount` used in `patternCount`/`rishonTotal` |

Axioms (tester 212, re-read in its log): the four large `decide` theorems use $\{$`propext`, `Classical.choice`, `Quot.sound`$\}$; the other seven use none. There is no `native_decide` or `sorry` in the four files.

**Audit 200 N5 (outer row only sampled): closed** by O1 (§3). Its Lean counterpart is only structural (N1).

**What remains a documented argument or a numerical check (not Lean):**
1. *Corner kernel → physical-state count.* Lean proves the per-corner kernel dimensions (`corner_kernel_dims`). It proves `kerDim m = cornerCountR … = cornerCount …` via `corner_kernel_dims` + `corner_count_agree`; `cornerCountR` is a definition-for-definition copy, not derived from `kerDim`. Lean also proves the arithmetic $\sum_n\text{patternCount}(n)2^{\text{zeros}(n)}=38\,432$ (M5). Three steps between these are not in Lean: (a) for a fixed type assignment the Gauss kernel of the 12-link space is $\bigotimes_c\ker G_c$ with dimension $\prod_c$ `kerDim` (tensor factorisation over corners; the $G^a_c$ act on disjoint end qubits); (b) grouping the $3^{12}$ type patterns by spin pattern with weight $2^{\#\{j=0\}}$; (c) the outer far-end fixing (R2, a model choice). These are stated in R9 and checked numerically by three routes (reports/tests/201). The locked W2 test additionally ties Lean `kerDim` to the production `corner_kernel` on all 81 configurations.
2. *Outer-row phase semantics.* In Lean only `ueOuterGates = (List.range 12).flatMap gadget` and the gadget-0 eigen-statement are proved (N1). The action on 48-bit codes is certified numerically by O1 (float64).
3. *`build_UB`*: not modelled (plan §0, kernel cost about $3\times10^4$ s). Still `Lean: n_a`.
4. *`checkHB`* remains `native_decide` (one native axiom, M5 L3). M5x only removed the data gap in front of it.

## 3. `outer_electric_certify` soundness

**Bound.** Let $P$ be the projector on the 6 sector codes of one link. For a circuit whose gates each act inside one link, $U=\bigotimes_{\ell}V_\ell$; gates on different links commute, so program order inside each link is all that matters. Write $A_\ell=V_\ell P$ and $B_\ell=e^{i\varphi_\ell}T_\ell P$ (both $16\times6$ isometries). Then
$$\bigotimes_\ell A_\ell-\bigotimes_\ell B_\ell=\sum_{k}\Big(\bigotimes_{\ell<k}B_\ell\Big)\otimes(A_k-B_k)\otimes\Big(\bigotimes_{\ell>k}A_\ell\Big)\;\Rightarrow\;\Big\|\bigotimes_\ell A_\ell-\bigotimes_\ell B_\ell\Big\|_2\le\sum_\ell\|A_\ell-B_\ell\|_2=\sum_\ell\epsilon_\ell .$$
This is the standard telescoping estimate for products of operators of norm $\le1$ (Nielsen & Chuang, *Quantum Computation and Quantum Information*, Eq. 4.69, applied factorwise; the laptop's `prod_sub_prod_le`, METHODS §11). It holds for *any* choice of the $\varphi_\ell$, so the type-A anchored phase (`results.py:200-205`) gives a valid bound. The resulting single global phase $e^{i\sum\varphi_\ell}$ is admissible because verification is up to one global phase. Every physical state lies in $\bigotimes_\ell\mathrm{range}(P)$ (the valid 48-bit codes, $6^4\cdot4^8$ of them, R2, are a subset of the $6^{12}$ sector-product codes). So `error_bound` bounds $\|(U-e^{i\Phi}U_E^{\rm target})\Psi\|$ for every unit-norm physical $\Psi$ of the whole 48-qubit register (inner and outer links together). $\epsilon_\ell$ uses the full $16\times6$ block, so leakage out of the sector is included.

**Independent check** (`results/rishon/auditor-201-outer-bound.log`): 30 random 3-link mutants, bounds $2.1\times10^{-5}$ to $7.7\times10^{-3}$. Results:
- Soundness violations: **0**.
- True error at the certificate's phase divided by the bound: $0.506$ to $0.9999999$, so the bound is tight to within $2\times$.
- True error at the optimal global phase divided by the bound: $0.46$ to $0.998$.
- No mutant certified.

Probes:
- outer register first: certified, bound 0.0 (correct);
- one outer gadget with reversed CX (link 5): rejected, bound 0.548;
- `qc.global_phase = 0.3`: certified, 0.0 (correct, free global phase);
- circuit at $\alpha=0.37$ certified at $\alpha=0.38$: rejected, bound 0.090.

This agrees with tester 211 §3–§4. I agree with tester 211 that the anchored phase is never more than $2\times$ pessimistic and is not always stricter than the plan's sum-fit phase. Both are valid; this is already recorded, so I do not re-report it.

**Is "certified" honest for float operators?** Yes in substance, with N3. The 16×16 operators are products of exact permutations and one float phase gate, so Qiskit's `Operator` reproduces $\mathrm{fl}(e^{i\theta})$ bit for bit, and the target uses the same float argument. That is why `error_bound` is exactly 0.0. The true error of the circuit as defined (float angle) against the mathematically exact target $e^{-i\frac34\alpha}$ is at most about one rounding of the exponential and the angle per link. That is $\lesssim3\times10^{-16}$ per link and $\lesssim4\times10^{-15}$ for 12 links, five orders of magnitude below `tol_err` $=10^{-10}$. The word matches the project's existing convention: the laptop's float evaluator also certifies when the engine accuracy is far below the tolerance. It is not a rigorous interval-arithmetic certificate, and the JSON does not say so (N3).

## 4. Notes (all NON-BLOCKING)

### N1. METHODS-rishon R6 overstates the Lean coverage of the outer row (doc)
`docs/METHODS-rishon.md:70` (R6, certified bullet) says: "The same fact for the rendered gate list, for all $\alpha$ symbolically, is the kernel theorem `ue_gadget_sector` + `ue_outer_gates_structure` (R9)". But `ue_gadget_sector` (`UESemantics.lean:90`) is about `gadget 0` acting on a bare 4-bit code $s<16$. Two steps are not in Lean: (i) `gadget l` acts on bits $4\ell..4\ell+3$ of a 48-bit index exactly like gadget 0 acts on the 4-bit field, as the identity on all other bits; (ii) the composition over the 12 links. Tester 210 N3 says the same. My probe shows (i) costs nothing: for all $\ell<12$ and all sector codes $s$, `runGates (gadget l) [(s·16^l, one)]` and the same with all other 11 links in code 5 are kernel-checked, 0.60 s / 0.82 GB, axioms standard (`scratch/auditor201/GadgetAllLinks.lean`).
Fix: reword to "…is the kernel theorem `ue_gadget_sector` + `ue_outer_gates_structure` plus the (unproved, elementary) locality of each gadget and the tensor composition; the 48-bit action itself is certified numerically by O1". Optionally add the per-link probe as a 12th theorem in a later plan (it changes `RISHON_M5X_THEOREMS`, a locked name list, so it needs the planner).

### N2. Report 5 was not updated with the M5x results (W4 deliverable, doc)
Plan §4 W4 asks for Report 5 addendum paragraphs for §3.3 (certified outer row) and §3.6 (Lean column, items closed by prompts/202). `docs/report-5-rishon-general-circuit.md` was last changed in `eeee99b` (before M5x) and now contradicts the M5x state:
- line 19: "The outer electric row … is checked **separately by sampling** (labelled `sampled: true, certified: false`)";
- line 107: $\det U=2U_{11}U_{22}$ identity "numerical";
- line 108: "The 8 link matrices are certificate data from Python, not tied in Lean to `JW.lean`";
- line 121: "The outer electric row is verified by sampling only … not certified".

Report 5 is a document that leaves the project. Fix before the `milestone-5x` tag: add the addendum (certified row: `results/rishon/UE_outer_row_certified.json`, commit 59e863d, `error_bound` 0.0 ≤ $10^{-10}$ at $\alpha=0.37$, 12 links; Lean rows for the 11 theorems with the scope of §2 above). Do not edit the M5 numbers.

### N3. The certificate does not state its float character
`results.py:213-219` / the JSON give `error_bound: 0.0` and `certified: true` without saying that this is a float64 evaluation with no rounding allowance. The estimate in §3 shows the omission cannot change the verdict (allowance $\lesssim4\times10^{-15}$ against $10^{-10}$). Suggested minimal change, at the next planner run (the result keys are locked by the plan interface): add one sentence to R6 ("float64 per-link operators; exact up to rounding $\lesssim10^{-15}$, not included in `error_bound`"). Optionally add a `"arithmetic": "float64"` key or a fixed allowance term `12·n_gates·2^{-52}`.

### N4. The target's Casimir $\tfrac34$ is a typed literal shared by circuit, certificate and test
`circuits/rishon.py:12` (`p(-0.75*alpha)`), `results.py:199` (`np.exp(-0.75j*alpha*…)`) and the locked test `_own_link_errors` all type $\tfrac34$. A common-mode error in this number would pass all three. It is tied to the operator $H_E$ only indirectly, through the M5 inner-row test (M5-E1, `build_UE` vs $e^{-i\alpha H_E^{\rm in}}$ built from $L_a,R_a$) and the measured Casimirs $(0,\tfrac34,\tfrac34,\tfrac34,\tfrac34,0)$ (R1). The value is right: $H_E=\tfrac12\sum_a(L_a^2+R_a^2)=j(j+1)=\tfrac34$ for $j=\tfrac12$ (R1; BCW hep-th/9704106 Sec. 2). Suggested hardening (later): build $T_\ell$ from the diagonal of the link operator $\tfrac12\sum_a(L_a^2+R_a^2)$ computed by `RishonLink.end_generator` on the sector instead of the literal.

### N5. "Exhaustive over all $6^{12}$ valid codes" clashes with R2's definition of "valid" (wording)
`docs/METHODS-rishon.md:70` and plan §1 O1: R2 defines the valid 48-bit codes as $6^4\cdot4^8$ (the far end of each outer link is fixed). The certificate covers the larger product of full link sectors, $6^{12}$. The claim is therefore stronger than needed and correct, but the word "valid" is used in two senses. Suggested wording: "all $6^{12}$ sector-product codes (which contain the $6^4\cdot4^8$ valid codes of R2)".

### N6. Small interface remarks (already partly known)
- `reason == "error"` is used both for a bound above tolerance and for an instruction without an operator (`results.py:208-210`, `:219`). It is distinguishable by the presence of `detail`, but a separate `"tolerance"` reason would read better. This complements the known `ancilla_register` label note (tester 211 N2).
- `lean_corner_kernel_dims` parses the first `[...]` group of the Lean stdout with a greedy regex (`lean_export.py`, `re.search(r"\[(.*)\]", out, re.S)`). It is safe today because the 81-element length is checked. It would break noisily, not silently, if Lean printed a warning containing brackets.

## 5. Items in the brief I checked and do not re-report
- Tester 210 N1–N4, tester 211 notes (sum-fit vs anchored phase in plan §1 and in the locked helper; `ancilla_register` label), the pending prompts/202 §7 change, the $\gamma=0$ approval. I agree with all of them. On the phase rule: the anchored phase is sound (§3); the plan text should be corrected by the planner, not the code.
- The SU(2) generator form at R ends: `CornerKernel.lean` uses the same form $c^\dagger T_a c$ for every end, as R1 does for $L_a$ and $R_a$. Even under a conjugate-representation convention for one end type, the singlet count (and hence the kernel dimension) is unchanged, because the fundamental of SU(2) is pseudo-real. The W2 test against the production `corner_kernel` confirms equality on all 81 configurations.

## 6. Reproduction
```
cd ~/Projects/su2qc-rishon && source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 && source ~/.elan/env
PYTHONPATH=src taskset -c 10-19 python scratch/auditor201/outer_bound.py results/rishon/auditor-201-outer-bound.json   # 339 s, 0.20 GB
cd lean && taskset -c 10-19 lake env lean ../scratch/auditor201/GadgetAllLinks.lean                                   # 0.60 s, 0.82 GB
cp lean/Su2Plaq/Rishon/UESemantics.lean scratch/auditor201/UESem_copy.lean   # then write_lean_ue_gates(copy); cmp → IDENTICAL
```

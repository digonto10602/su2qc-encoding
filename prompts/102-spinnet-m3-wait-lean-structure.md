# 102 — M3 wait-time plan (track S): kernel-checked $K$ from 6j symbols, exact gate semantics of the general circuit, and the $H_B$ eigenbasis on the 433 states (Lean 4, `decide`, standard axioms)

- Date: 2026-11-06 · Author: planner (Claude Fable 5.1) · Git commit at writing: `5a03f98` (branch `m3-spin-network`, tag `milestone-3`)
- Plan in force: `prompts/100` (+ erratum `101`) for M3 is **done**; this file governs the wait-time work until the laptop's `milestone-2` bundle arrives (START_HERE §6). M4 (compression) is not started here. Nothing in `prompts/100` changes.
- Trigger: M4 waits for the laptop's compression machinery and per-circuit checker (`Su2PlaqCert`, prompts/006 2.L4+). START_HERE §6: "Lean structure proofs, extra Lean certificates, and benchmark and robustness checks that do not need the machinery". The open Lean caveats to close: `reports/tests/105` (trust judgement items 1–4), `reports/audits/100` §2.3 and N4, `docs/report-3-spinnet-general-circuit.md` §3.5.
- Research and prototype numbers: `reports/research/101-spinnet-lean-exact-recoupling-spectrum-semantics.md`, `scratch/planner/lean/SpinNetExact.lean` (all 11 prototype theorems kernel-checked in 22.4 s wall, 1.91 GB peak RSS, Mathlib-free). Methods: `docs/METHODS-spinnet.md` §9 (new).
- Acceptance tests: **new folder `tests/acceptance/m3x/`** ("M3 extension"; m3 is locked as acceptance-v7 and m4 belongs to the compression milestone). One file, four tests (§5). Lock: `python tools/lock.py m3x` then `~/.claude/bin/acceptance-lock "prompts/102-spinnet-m3-wait-lean-structure.md"` (coordinator).

Jargon, once: *kernel-checked* = the proof is re-verified by Lean's small trusted kernel by evaluating the definitions (`decide`), with at most the standard axiom `propext`; *native-certified* = decided by compiled code (`native_decide` or the laptop's checker executable), adds compiler trust — **not used here**; *Mathlib-free* = the file imports nothing from Mathlib, so elaboration needs ≈ 2 GB instead of ≈ 8 GB; *Racah formula* = the closed-form sum for the Wigner 6j symbol; *F-symbol* = the recoupling coefficient between the two ways of coupling three spins; *Laurent polynomial* = polynomial with negative powers allowed, used here in $z=e^{i\beta/4}$ so that every circuit amplitude is exact for all $\beta$ at once; *outer block* = the set of physical states sharing the 8 outer spins.

## 0. Diagnosis — what is only numerical today, and which item closes it
| Caveat (reports/tests/105, audit 100, Report 3 §3.5) | Closed by |
|---|---|
| (1) `validInnerCodes`, `couplingTable` are copied from Python; Lean proves only self-consistency with the walk; "$K$'s entries $-2,-\tfrac12,+1$ are numerical (6j in float)" | **W1**: Lean computes the 6j symbols (Racah), the F-symbols, the route-B amplitude and $K$ from the codec, exactly, and proves the exported tables equal them (all $47\times47$ entries) |
| (3) `rccx` read with Toffoli semantics; relative-phase cancellation, the uncompute half, the Hadamards, the sign/exponent convention $e^{-i\beta K}$ are numerical only | **W2**: exact gate semantics with Qiskit's matrices over $\mathbb Z[i][z^{\pm1}]$; kernel-checked: the 48-gate `build_UB` equals $e^{-i\beta K}$ on all 47 valid codes with clean ancillas, for all $\beta$; the gate list is rendered from the Qiskit circuit and the Lean gate matrices are cross-checked against Qiskit (audit N4 closed inside the suite) |
| (4) $16/96/16$ are pair-class counts; the spectrum $16/96/16/177/16/96/16$ is not a Lean theorem | **W3**: explicit eigenbasis $e_s\pm e_{s'}$ of $H_B$ on the 433 states, eigen-equations checked densely inside every outer block, multiplicities as a kernel-checked list |
| (2) Lean circuit model tied to `GENERAL7` only outside the suite (audit N4) | already generated from `GENERAL7` (d82a472) + unit test; W2 adds the stronger gate-for-gate tie to the shipped Qiskit circuit, in a locked test |
| `angleTable` copied from Python | stays "chosen by Python"; `walk_table_exact` (M3-L2) + W1 prove it is *a correct* angle table for the 6j-computed $K$, and W2 proves the circuit built from it is exact — nothing numerical remains in the chain |

Not in scope (and why): the native per-circuit certificate M3-L3 stays PENDING on the laptop's checker (we do not duplicate `Su2PlaqCert`; W2 is a hand-specialised *kernel* theorem for one 15-qubit circuit, not a general checker); route A ↔ route B agreement (the physical content of Paulo's Fig. 2 claim) stays numerical (M0-X4–X6, M3-K1) — in Lean, $H_B=\bigoplus_oK|_{S_o}$ is route B's *definition*; the $U_E$/step circuits (4 phase gates, trivially diagonal) are not modelled; benchmarks are unchanged (no production numerics change).

## 1. Method (equations and conventions; sources; details in `docs/METHODS-spinnet.md` §9)
**Doubled spins.** Every spin is stored as $2j\in\mathbb N$; a corner label $J_c\in\{0,\tfrac12,1\}$ as $0,1,2$.

**Racah's formula** (Edmonds, *Angular Momentum in Quantum Mechanics*, Eq. 6.3.7; identical to `su2plaq.su2.wigner._six_j_2x`):
$$\begin{Bmatrix}a&b&c\\d&e&f\end{Bmatrix}=\Delta(abc)\Delta(aef)\Delta(dbf)\Delta(dec)\sum_{z}\frac{(-1)^z(z+1)!}{(z-t_1)!(z-t_2)!(z-t_3)!(z-t_4)!(q_1-z)!(q_2-z)!(q_3-z)!},$$
$t_1=a+b+c,\ t_2=a+e+f,\ t_3=d+b+f,\ t_4=d+e+c,\ q_1=a+b+d+e,\ q_2=a+c+d+f,\ q_3=b+c+e+f$, $\max t_i\le z\le\min q_j$, $\Delta(abc)=\sqrt{\frac{(a+b-c)!\,(a-b+c)!\,(-a+b+c)!}{(a+b+c+1)!}}$; zero unless the four triads $(abc),(aef),(dbf),(dec)$ satisfy the triangle rule with integer sum.

**Square-root-free exact arithmetic.** Every 6j symbol is $q\sqrt r$ with $q,r\in\mathbb Q$, $r=\Delta^2(abc)\Delta^2(aef)\Delta^2(dbf)\Delta^2(dec)>0$ (a product of rationals) and $q$ the Racah sum. Products of such numbers stay of the form $q\sqrt r$. A value is rational iff $r$ is a rational square, $r=(m/n)^2$ with $m,n\in\mathbb N$ found by an exact integer square root of the reduced numerator and denominator (bounded search; all numbers here are $<10^5$). Rationals are stored unnormalised as `(num : Int, den : Nat)` and compared by cross-multiplication; **`Rat` is not used** (prompts/006 §9: kernel `decide` gets stuck on `Rat.mul`). All operations are `Nat`/`Int` arithmetic, which the kernel evaluates with GMP.

**F-symbol** (Edmonds Eq. 6.1.5; `su2plaq.su2.wigner.f_symbol`, argument order and the integer-division phase as in the code):
$$F^{j_1j_2j_{12}}_{j_3Jj_{23}}=(-1)^{j_1+j_2+j_3+J}\sqrt{(2j_{12}+1)(2j_{23}+1)}\begin{Bmatrix}j_1&j_2&j_{12}\\j_3&J&j_{23}\end{Bmatrix}.$$

**Codec** (METHODS-spinnet §1): inner code $y\in[0,256)$, bits $0..3$ = $2j$ of links $b,r,t,l$, bit $4+c$ = $[J_c=1]$; corner $c$ visits inner links $(p(c),n(c))=(l,b),(b,r),(r,t),(t,l)$; $J_c(y)=1$ if bit $4+c$ is set, else $\tfrac12$ if $j_{p}\ne j_{n}$, else $0$; a code is valid iff every set corner bit sits at a corner with $j_p=j_n=\tfrac12$ (47 codes).

**Route-B plaquette** (METHODS §5, METHODS-spinnet §2; `su2plaq.exact.spinnet.plaquette_P`): $P[y',y]=\prod_{c}F^{J_c\,j_{p(c)}\,j_{n(c)}}_{\frac12\,j'_{n(c)}\,j'_{p(c)}}$ when every inner link is shifted by $\pm\tfrac12$ (at $j_{\max}=\tfrac12$: $y'$ has the four link bits flipped) and $J_c(y')=J_c(y)$ for all $c$; $0$ otherwise. $K=-(P+P^{\mathsf T})$ on the 47 codes; on the 433 states $H_B[(y',o'),(y,o)]=\delta_{oo'}K[y',y]$ (the outer spins enter only through admissibility). Expected (kernel-checked in W1): $2K[y\oplus15,y]$ equals `couplingTable` ($-4$ on $0000/1111$, $-1$ on $0101/1010$, $+2$ on the twelve other bright codes, $0$ on the 31 dark codes), $K$ symmetric, zero off the flip.

**States and eigenbasis** (W3). $\mathrm{fuse}(a,b)=\{0,1\}$ (coded $[0,2]$) if $a=b=\tfrac12$, $\{0\}$ if $a=b=0$, $\{\tfrac12\}$ otherwise; $(y,o)$ is a state iff $y$ valid and $J_c(y)\in\mathrm{fuse}(o_{2c},o_{2c+1})$ for all $c$ (433 states in 128 non-empty outer blocks, sizes 2–17, $\sum_on_o^3=12\,823$). For a bright $y$ with partner $y'=y\oplus15$ and $k=K[y',y]$: $H_B(e_{(y,o)}\pm e_{(y',o)})=\pm k\,(e_{(y,o)}\pm e_{(y',o)})$; dark: $H_Be_{(y,o)}=0$. One vector per state ($+$ for bit $0$ of $y$ clear, $-$ for set, dark alone) gives 433 pairwise-orthogonal eigenvectors, hence an orthogonal eigenbasis, hence the spectrum. The kernel checks $(2H_Bv)_t=2\lambda\,v_t$ for every vector $v$ of a block and every row $t$ of that block (dense inside the block), using the integer $2K$ of the exported table (tied to the 6j symbols by W1's `k_from_6j_full`); the cross-block zeros are route B's definition. Multiplicities of $2\lambda\in\{-4,-2,-1,0,1,2,4\}$: $16,96,16,177,16,96,16$.

**Exact gate semantics** (W2). Qubits little-endian, basis index $i=\sum_q b_q2^q$, 15 wires (data $0..7$, ancillas $8..14$; the outer register is never touched by `build_UB` — checked by the evaluator, M3-B2). Coefficient ring $\mathbb Z[i][z,z^{-1}]$ with $z=e^{i\beta/4}$, stored as sorted lists $(m,\Re,\Im)$; the two Hadamards contribute a global $(1/\sqrt2)^2=\tfrac12$ that is kept as a count $h$ (`ub_h_count : hCount ubGates = 2`). Gate matrices = Qiskit's (`SIM_BASIS`): $X$, $CX$ permutations; $H=\tfrac1{\sqrt2}\begin{pmatrix}1&1\\1&-1\end{pmatrix}$; $R_z(\theta)=\mathrm{diag}(e^{-i\theta/2},e^{i\theta/2})$ with $\theta=a\beta/2$, $a\in\mathbb Z$ (`angleTable`), i.e. $\mathrm{diag}(z^{-a},z^{a})$; `rccx`$(a,b,t)$ = Qiskit `RCCXGate` (relative-phase Toffoli): $|a{=}1,b{=}1,t\rangle\mapsto i^{\pm1}|a,b,\neg t\rangle$ ($+i$ for $t:0\to1$, $-i$ for $1\to0$), $|a{=}1,b{=}0,t{=}1\rangle\mapsto-|{\cdot}\rangle$, all other basis states fixed (`RCCXGate().to_matrix()`, index $a+2b+4t$). Target, with $4k=2\cdot(2K[y',y])\in\{-8,-2,4\}$ an integer:
$$2\,e^{-i\beta K}|y\rangle=(z^{4k}+z^{-4k})|y\rangle-(z^{4k}-z^{-4k})|y'\rangle,\qquad 2\,e^{-i\beta K}|y_{\rm dark}\rangle=2|y_{\rm dark}\rangle,$$
since $e^{-i\beta K}=\cos(\beta k)\mathbb 1-i\sin(\beta k)\sigma_x$ on the pair and $z^{4k}=e^{i\beta k}$. The theorem `ub_exact_all_codes`: for every valid code $y$ (ancillas $0$), `run ubGates |y⟩` (unnormalised by $\sqrt2^{\,h}$) equals this target *exactly* — this single equality gives block exactness, zero leak, clean ancillas and the sign convention for all $\beta$ (same logic as prompts/006 M4). Prototype: 4.1 s, 1.65 GB. Mutation tests (research §3): fails on flipped $R_z$ convention, a changed angle, flipped target sign, a dropped uncompute gate, a wrong Hadamard sign; passes with the RCCX phases conjugated and with plain-Toffoli semantics — correct physics (the compute/uncompute sandwich cancels the relative phases), which is why the test ties the Lean gate matrices to Qiskit's separately (§5, W2).

## 2. Lean layout (track-owned `lean/Su2Plaq/SpinNet/`; names LOCKED by `tests/acceptance/m3x/test_spinnet_lean_exact.py`)
All in `namespace Su2Plaq.SpinNet`. Files W1–W3 are **Mathlib-free** (no `import` except each other), so each heavy `decide` elaborates in ≈ 2 GB. Avoid name clashes with `Circuit.lean`/`Counts.lean` (`bt`, `fuse`, `step`, `run`, `Op` exist there): use `bitOf`, `fuseN`, `runGates`, `Gate`.
```
Recoupling.lean   (no imports)  Frac, SR, fact, isqrt?, tri, delta2, racahSum, sixj, fsym, bitOf, cornerP, cornerN, Jc,
                                validCode, validCodes, pAmp, kEntry?, twoK?, fuseN, stateOK, states, blockCodes
                                -- BEGIN generated exact … -- END generated exact :  exportedCodes : List Nat, exportedTwoK : List Int
                                theorem valid_codes_from_codec : validCodes = exportedCodes
                                theorem k_matching : validCodes.all (fun y => validCodes.all (fun y' => if y' == y ^^^ 15 then kEntry? y' y == kEntry? y y' else (pAmp y' y).q.isZero)) = true
                                theorem coupling_from_6j : (List.range 47).all (fun i => twoK? (exportedCodes.getD i 0) == some (exportedTwoK.getD i 0)) = true
                                theorem k_from_6j_full : validCodes.all (fun y => validCodes.all (fun y' => <2·kEntry? y' y  ==  if y' == y ^^^ 15 then twoKlit y else 0, as Frac.beq; none ↦ false>)) = true
Semantics.lean    (import Recoupling)  Lau, Vec, Gate (x | cx | rccx | h | rz q a), applyBasis, applyGate, runGates, hCount, target
                                -- BEGIN generated exact … -- END generated exact :  ubGates : List Gate   (rendered from build_UB(1.0))
                                theorem ub_h_count : hCount ubGates = 2
                                theorem ub_exact_all_codes : validCodes.all (fun y => runGates ubGates [(y, [(0, 1, 0)])] == target y ((twoK? y).getD 999)) = true
Spectrum.lean     (import Recoupling)  twoKlit (from exportedCodes/exportedTwoK), hb2, blocks, eigsOf, vecAt, hvAt
                                theorem card_states_exact : states.length = 433
                                theorem blocks_cover : (blocks.map (fun ob => ob.2.length)).sum = 433
                                theorem eig_blocks : blocks.all (fun ob => (eigsOf ob.2).all (fun e => (e.2.1 == 0 || ob.2.contains (e.1 ^^^ 15)) && ob.2.all (fun t => hvAt ob.1 e t == e.2.2 * vecAt e t))) = true
                                theorem eig_count : (blocks.map (fun ob => (eigsOf ob.2).length)).sum = 433
                                theorem eig_mult : [-4, -2, -1, 0, 1, 2, 4].map (fun l => …count of e.2.2 == l…) = [16, 96, 16, 177, 16, 96, 16]
Bridge.lean       (import Su2Plaq.SpinNet.Circuit, Semantics, Spectrum)   -- the only file that loads Mathlib (through Circuit → Counts); trivial decide
                                theorem tables_agree : exportedCodes = validInnerCodes ∧ exportedTwoK = couplingTable
lean/Su2Plaq.lean gains one line: import Su2Plaq.SpinNet.Bridge      (shared-file append → notes/merge-notes-spinnet.md)
```
Definitions are those of `scratch/planner/lean/SpinNetExact.lean` (sections A, B, C) — **copy, rename as above, do not re-derive**. `set_option maxRecDepth 100000` and `maxHeartbeats 0` as in the existing files. Every proof is `by decide`; no `native_decide`, no `sorry`, no `Rat`, no `Nat.sqrt`, no `~~~` on `Nat`.

## 3. Interface (Python, track-owned `src/su2plaq/spinnet/lean_export.py`; builder creates stubs raising `NotImplementedError` first)
```python
RECOUPLING_LEAN, SEMANTICS_LEAN, SPECTRUM_LEAN, BRIDGE_LEAN: pathlib.Path    # lean/Su2Plaq/SpinNet/{Recoupling,Semantics,Spectrum,Bridge}.lean
GATE_NAMES = ("x", "cx", "rccx", "h", "rz")
def gate_ints(qc) -> list[tuple]        # program order: ("x", q) | ("cx", c, t) | ("rccx", a, b, t) | ("h", q) | ("rz", q, a); q = qc.find_bit(.).index;
                                        # a = angle / (beta/2) with beta = qc.metadata["beta"], integer within 1e-9 (ValueError otherwise);
                                        # ValueError for a gate outside GATE_NAMES or qc.num_qubits != 15 (the outer register is not modelled)
def gate_literal(qc) -> str             # "[.cx 1 3, .cx 0 1, …, .rz 0 (-7), …]"  (negative integers in parentheses) — verbatim in Semantics.lean
def write_lean_exact_tables(recoupling_path=None, semantics_path=None) -> tuple[pathlib.Path, pathlib.Path]
                                        # regenerates the two "-- BEGIN generated exact" / "-- END generated exact" blocks:
                                        # Recoupling.lean: exportedCodes := lean_literals(enc)["codes"], exportedTwoK := lean_literals(enc)["coupling"];
                                        # Semantics.lean: ubGates := gate_literal(build_UB(1.0)); ValueError if markers are missing
def lean_eval(body: str, imports: tuple[str, ...] = ("Su2Plaq.SpinNet.Recoupling",), timeout: float = 300.0) -> str
                                        # writes <imports> + body to a temporary .lean file, runs project.lake(["env", "lean", <abs path>]) (cwd lean/),
                                        # returns stdout; RuntimeError with stdout+stderr on non-zero exit; the modules must be built (`lake build Su2Plaq`)
def lean_sixj_table() -> dict[tuple[int, int, int, int, int, int], float]   # all (a,b,c,d,e,f) ∈ {0,1,2}^6 (doubled) ↦ float(q·√r) of Su2Plaq.SpinNet.sixj
def lean_valid_codes() -> list[int]      # #eval validCodes
def lean_states() -> list[int]           # #eval states as y + 256·o, in Lean order
def lean_gate_images(gate: tuple, n_qubits: int, beta: float) -> np.ndarray
                                        # complex (2^n, 2^n): column i = applyBasis gate i [(0,1,0)] evaluated at z = e^{iβ/4}; "h" columns × 1/√2
```
`#eval` output is parsed from Lean's `Repr` of `List (… × Int …)` (or a custom `toString`; builder's choice, documented). Unit tests (builder, `tests/unit/test_spinnet_lean_exact_unit.py`): drift of either generated block vs `GENERAL7`/`build_UB` fails; `gate_ints` rejects a non-integer angle and a `with_outer` circuit; `lean_eval` raises on a Lean error.

## 4. Steps (one builder call each; the tester verifies the listed ids with `taskset -c 0-9 pytest -n 1 tests/acceptance/m3x -k <id>`)
| Step | Builds | Done-check | Acceptance ids that must turn green |
|---|---|---|---|
| W0 | stubs for §3 (`NotImplementedError`); `tests/unit/test_spinnet_lean_exact_unit.py` skeleton | `pytest --collect-only -q tests/acceptance` clean (130); `pytest tests/acceptance/m3x` fails only `PENDING:`; unit suite green | — |
| W1 | `Recoupling.lean` (copy prototype §A + states; generated block; 4 theorems); `write_lean_exact_tables` (Recoupling half), `lean_eval`, `lean_sixj_table`, `lean_valid_codes`, `lean_states` | `cd lean && taskset -c 0-9 lake build Su2Plaq.SpinNet.Recoupling` green in ≤ 60 s, Lean peak RSS ≤ 3 GB (prototype 8.2 s, 1.49 GB); W1 green; never rebuilds `Structure/Counts.lean` | `test_spinnet_lean_exact.py::test_M3X_W1_recoupling_matches_wigner_and_codec` |
| W2 | `Semantics.lean` (prototype §C; generated gate block; `ub_h_count`, `ub_exact_all_codes` with the target from `twoK?`); `gate_ints`, `gate_literal`, `write_lean_exact_tables` (Semantics half), `lean_gate_images` | `lake build Su2Plaq.SpinNet.Semantics` green ≤ 60 s, ≤ 3 GB (prototype 4.1 s, 1.65 GB); W2 green; **mutation check by the tester**: flipping the `rz` sign in `applyBasis` or one angle in `ubGates` must make `ub_exact_all_codes` fail (`decide` reports "is false") | `::test_M3X_W2_semantics_gate_list_and_qiskit_matrices` |
| W3 | `Spectrum.lean` (prototype §B; 5 theorems) | `lake build Su2Plaq.SpinNet.Spectrum` green ≤ 90 s, ≤ 3 GB (prototype 11.2 s, 1.89 GB); W3 green; tester mutation: swapping the eigenvalue signs in `eigsOf` must fail `eig_blocks` | `::test_M3X_W3_spectrum_states_and_multiplicities` |
| W4 | `Bridge.lean` (`tables_agree`), import line in `lean/Su2Plaq.lean` (+ merge note), METHODS-spinnet §9 measured numbers (build times, RSS), `graphify update .`, Report 3 §3.5 addendum paragraph "closed by prompts/102" (coordinator may delegate to the builder) | `taskset -c 0-9 lake build Su2Plaq` green (incremental; `Structure/Counts.lean` untouched — check its `.olean` mtime); L green; `python tools/check_lock.py` and `~/.claude/bin/acceptance-check` PASS after the lock | `::test_M3X_L_exact_theorems_kernel_checked` |
| Gate | tester mode `full` on m0+m1+m3+m3x (m2 Lean/compress PENDING allowed, M3-L3 PENDING allowed) → auditor (physics/numerics review of the Lean definitions vs METHODS §5/§9: F-symbol argument order, codec, RCCX matrix) → commit, tag `milestone-3x` (no benchmark: no numerical production code changed; `lake build` wall is recorded in METHODS §9 instead) | — | all m3x |

Builder briefs must include: graphify-first rule; "copy `scratch/planner/lean/SpinNetExact.lean`, rename per §2, do not re-derive"; `source ~/.elan/env`; `taskset -c 0-9`; ≤ 10 GB; never `lake build` the whole default target set while `Structure/Counts.lean` would rebuild (it will not unless its source or `Su2Plaq.Structure` changes — do not touch them); never edit laptop-owned files (`lean/Su2Plaq/Structure/`, `lean/Su2PlaqCert/`, `src/su2plaq/lean/`, `.gitignore`); no `native_decide`, no `sorry`; the m3 tests must stay green (`Circuit.lean`'s generated block is unchanged).

## 5. Acceptance tests (locked with this plan) and their limits
File `tests/acceptance/m3x/test_spinnet_lean_exact.py` (imports the project only through `tests/acceptance/_api.py::api`; missing Lean files → `PENDING:`). Collection checked: `pytest --collect-only -q tests/acceptance` → 130 tests; `pytest tests/acceptance/m3x` → 4 `PENDING` failures, nothing else.

| Test id | Checks | Limit | Justification |
|---|---|---|---|
| `test_M3X_W1_recoupling_matches_wigner_and_codec` | file exists, Mathlib-free, 4 theorem statements, no native/sorry, exported tables verbatim; Lean `sixj` vs `su2plaq.su2.wigner.six_j` on all $3^6=729$ doubled-spin tuples; ≥ 50 non-zero entries; `validCodes` = `enc.inner_codes()` | $10^{-12}$; 300 s | exact $q\sqrt r$ of magnitude ≤ 1 evaluated in float64 vs the float Racah implementation (itself verified against sympy to $8.9\cdot10^{-16}$, reports/tests/003): both ≈ $10^{-15}$; $10^{-12}$ is the project's standard exact-vs-float margin (prompts/006 §7). 300 s: one Mathlib-free `lake env lean` (measured ≤ 5 s) + margin for a cold olean build |
| `test_M3X_W2_semantics_gate_list_and_qiskit_matrices` | file exists, Mathlib-free, `ub_h_count` (= 2), `ub_exact_all_codes`; `gate_ints(build_UB(1.0))` = 48 gates, names/qubits gate-for-gate with `qc.data`, rz integers = `angle_ints`; `gate_literal` verbatim in the file and $\beta$-independent; Lean gate images at $\beta=0.61$ vs Qiskit `Operator` on 3 qubits for x, cx (both orientations), rccx (two wirings), h, rz($-7$), rz($3$) | $10^{-12}$; 300 s | the Lean images are exact Gaussian-integer Laurent coefficients evaluated at $z=e^{i\beta/4}$ (one complex exponential, ≈ $10^{-16}$) vs Qiskit's float matrices; same margin as above |
| `test_M3X_W3_spectrum_states_and_multiplicities` | file exists, Mathlib-free, five statements with 433 / the two literal lists; Lean `states` (as $y+256o$) = the encoding's 433 codes; `enc.h_magnetic()` symmetric to $10^{-12}$ and `eigvalsh` multiplicities of $2\lambda$ = 16/96/16/177/16/96/16 | $10^{-12}$ symmetry; $10^{-9}$ eigenvalue binning; 300 s | $H_B$ entries are exact half-integers rounded to float; `eigvalsh` of a $433\times433$ symmetric matrix with $\|H_B\|=2$ is accurate to ≈ $10^{-14}$; neighbouring eigenvalues differ by ≥ $\tfrac12$, so $10^{-9}$ bins cannot merge or split classes |
| `test_M3X_L_exact_theorems_kernel_checked` | the 12 theorem names exist; axioms ⊆ {propext, Classical.choice, Quot.sound}; `no_sorry() == []`; `Bridge.lean` imports `Circuit`, states `tables_agree` over `validInnerCodes`/`couplingTable`; `lean/Su2Plaq.lean` imports `Su2Plaq.SpinNet.Bridge` | 900 s | one `print_axioms` call (Mathlib import, 10–15 s measured for M3-L1/L2); 900 s as in M2/M3 |

## 6. Do-not-retry (tried in the prototype; see research §3)
- Dense $433\times433$ eigen-check calling the 6j-valued `kEntry?` inside the loop: killed at 9 GB after 133 s (kernel whnf cache). Use the integer table inside the blocks and tie the table to 6j once (`k_from_6j_full`, 47 × 47).
- `Nat.sqrt` or `Rat` inside `decide` (kernel gets stuck / unbounded); bounded integer-sqrt search with `List.range 512` is enough (largest reduced denominator $4096$).
- `~~~` on `Nat` (no `Complement Nat` instance): clear a bit with `x ^^^ (1 <<< q)` guarded by the bit test.
- `ulimit -v` around Lean (thread creation fails); guard memory by polling RSS (`scratch/planner/lean/run_guarded.sh`).
- Importing `Circuit.lean` (→ Mathlib) into the files with heavy `decide`s: ≈ 8 GB baseline + 2 GB would hit the 10 GB cap. Only `Bridge.lean` imports it.
- `native_decide` anywhere in `lean/Su2Plaq/`; re-proving the laptop's counts; rebuilding `Structure/Counts.lean`.
- Proving "spectrum" through Mathlib's `Matrix.charpoly`/`IsHermitian.eigenvalues` (heavy, no gain over the explicit orthogonal eigenbasis — stated as such in METHODS §9 and Report 3).

## 7. Risks and stop condition
- A theorem is false in production although the prototype passed (e.g. after renaming or a different `#eval`-friendly definition): `decide` prints "proved that the proposition … is false" — first compare the Lean definition with the prototype line by line; if the exact Lean $K$ or circuit output disagrees with the float evaluator (W1 or W2 test green but theorem false, or vice versa), **stop and ask Digonto** (exact vs float disagreement is a finding, never a tolerance question).
- Kernel time/memory in production exceeds 3× the prototype (≥ 60 s or ≥ 5 GB per file): check `set_option` lines and that no Mathlib import crept in; split the `all` over `validCodes` into two theorems; after one `fixer` NOT FIXED → planner.
- The laptop's bundle arrives mid-way: finish the current step, run the tester on it, commit, then switch to M4 (this plan's remaining steps continue only in idle time).
- The lock: `tools/lock.py` accepts any folder name; `acceptance-check` compares `tests/acceptance` against the latest `acceptance-vN` tag, so the coordinator must lock **before** the first builder step (otherwise every session-start check fails).

## 8. Expected cost
Builder: W0 ≈ 0.5 h; W1 ≈ 3 h (prototype exists; the `#eval` parsers are the work); W2 ≈ 4 h (rendering + Qiskit cross-check); W3 ≈ 1.5 h; W4 ≈ 1 h. Lean elaboration (measured on the prototype, cores 0–9): Recoupling 8.2 s / 1.49 GB, Semantics 4.1 s / 1.65 GB, Spectrum 11.2 s / 1.89 GB, all-in-one 22.4 s / 1.91 GB; `Bridge.lean` ≈ 15 s / ≈ 8 GB (Mathlib import). Tests: W1–W3 ≈ 5–10 s each; L ≈ 20 s, ≈ 8 GB (run the m3x folder with `-n 1`). No cluster time, no new results files.

## 9. For STATUS (coordinator)
- Pending note "METHODS-spinnet §3 fallback wording": already reads "$G^z_c$ eigenvalue $\pm\tfrac12$" (checked 2026-11-06) — close it.
- After this plan: counters reset; current milestone "M3x (prompts/102), step W0"; M4 still waiting on the laptop bundle.

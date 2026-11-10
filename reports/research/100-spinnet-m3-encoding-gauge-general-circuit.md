# Research 100 — Spin-network encoding (M3): codec, route-B target with the gauge, Paulo's 15-qubit circuit, a 4-rotation general circuit, Lean counts

- Date: 2026-11-06 · Author: planner (Claude Fable 5.1, high) · Git commit: `f0cbef1` (branch `m3-spin-network`, clone `~/Projects/su2qc-spinnet`)
- Prompt in force: `prompts/002` + addenda `003`–`006` (laptop machinery); this note feeds `prompts/100-spinnet-m3-plan.md` and `docs/METHODS-spinnet.md`.
- Related: `reports/research/001` §1 (6j plaquette, Fig. 2 claim), `reports/audits/001` N5 (route-B signs are gauge at $j_{\max}=\tfrac12$), `reports/audits/003` N2/N4/N5 (outer row, sibling step order, global phase), `reports/tests/006` (M0-X5/X6), `docs/report-1-twelve-qubit-general-circuit.md`.
- Prototypes (all numbers below): `scratch/planner/proto_m3_spinnet.py` (Python, 4.5 s total, `PYTHONPATH=src taskset -c 0-9 python …`), `scratch/planner/lean/SpinNetCounts.lean` (`cd lean && taskset -c 0-9 lake env lean ../scratch/planner/lean/SpinNetCounts.lean`, 11.1 s, 8.3 GB RSS). Env `su2qc-coding` (qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.2, scipy 1.18.0), Lean v4.35.0, Mathlib v4.35.0.

Jargon, once: see the header of `docs/METHODS-spinnet.md` (label, code, bright/dark, pair, gauge, frame, phase walk, flag).

## 0. Summary of findings
| Question | Answer | Evidence |
|---|---|---|
| Does the binding 16-qubit codec fit the laptop's evaluator unchanged? | Yes. Data = 4 inner-link + 4 corner qubits, outer = 8 link qubits; 433 unit codes, 47 valid inner codes; `evaluate` runs the `inner_span` fast path (no outer read) and the `physical` method (128 blocks for the outer row) in 0.2 s. The only encoding-specific hook is `decode_state`, which must be total on the code space (§2). | §1, §2 |
| What is "route B with `gauge_align`" concretely? | Target $=e^{-i\beta H_B^{\rm B}}$ from the 6j operator in label order; route A is the same up to a real diagonal $D=\pm1$ (64 minus signs; residual $2.7\cdot10^{-15}$); $V_B=D^\dagger V_AD$ to $2.4\cdot10^{-15}$; decoded vectors $D_k\psi^A_k$. | §1 |
| $K$ on the inner codes | Matching: 8 bright pairs (partner $=\mathrm{code}\oplus0b1111$, corner bits 0), couplings $-2$ (0000↔1111), $-\tfrac12$ (0101↔1010), $+1$ (six); 31 dark codes (any corner bit). Mixed signs in the route-B gauge. | §1 table |
| Sign of $\beta$ | A gauge in this encoding at $j_{\max}=\tfrac12$: $U_B(-\beta)=D'U_B(\beta)D'$ with one $-1$ per pair. Paulo's file implements $e^{+i\beta K}$ in route-B signs, i.e. $U_B(\beta)$ in the opposite pair-sign convention. | §3 |
| Paulo's 15-qubit circuit on the open 433 states | **Valid** up to that gauge: block residual $2.9\cdot10^{-15}$, full-evaluator error $9.8\cdot10^{-15}$, leak 0, Gauss $5\cdot10^{-16}$, outer bits read 0 (Fig. 2 claim holds). 68 CX, 4 exact `p` rotations, 64 T, 7 ancillas, depth 90 (Table I). | §3 |
| General circuit | Frame + 7 flag ancillas + 4-rotation Walsh walk, angles solved from $K$: 54 CX, 4 rotations ($-\tfrac72,-1,3,\tfrac32)\beta$, 56 fixed T, depth 67; exact $1.4\cdot10^{-14}$ at three $\beta$, both step orders; $T(10^{-6})=310$ ($U_B$), 566 (step 1). | §4 |
| spinnet_v2 skeletons re-solved in our gauge | `pairs9` 34 CX / 9 rot / 24 T; `flags4` 44 CX / 4 rot / 48 T; both exact ($8\cdot10^{-15}$) once `rc3x` is uncomputed with its true inverse (Qiskit `RC3X` is not self-inverse: $\|R^2-1\|=2$). | §5 |
| Lean | 12 kernel-checked `decide` theorems (47/16/31/8; multiplicities 16/96/16, 256/177/433; code injectivity; corner rule) compile in 11 s reusing the laptop's `fuse`/`bit`/`sumOver`. | §6 |

## 1. Encoding and target (prototype P1)
Code of a label $(j_0..j_{11};J_0..J_3)$: $\sum_{l<4}[j_l{=}\tfrac12]2^l+\sum_c[J_c{=}1]2^{4+c}+\sum_k[j_{o_k}{=}\tfrac12]2^{8+k}$ (link order $b,r,t,l$; corners $c_0..c_3=(0,0),(1,0),(1,1),(0,1)$; outer $o_0..o_7$ as METHODS §1). Route-B labels (`exact.spinnet.labels`) are in the same order as `physical_basis().labels` (unit test `test_label_order_identical_to_route_a`; asserted again in M3-C1). Measured: 433 distinct codes; 47 inner codes, 16 without a corner bit.

Gauge: `gauge_align(H_A, H_B^{6j})` → real $D$, 64 entries $-1$, residual $2.66\cdot10^{-15}$; $\max|e^{-i\beta H_B}-D^\dagger e^{-i\beta H_A}D|=1.3\cdot10^{-15}$ (β = 0.61), $2.4\cdot10^{-15}$ (1.0), $5\cdot10^{-16}$ (0.23).

Couplings of $K=K_{\rm inner}$ on the sorted inner codes (bits = $j_b j_r j_t j_l$, corner bits 0):
| link pattern | partner | $K$ | class |
|---|---|---|---|
| 0000 ↔ 1111 | | $-2$ | vacuum pair (Paulo Eq. 37) |
| 0101 ↔ 1010 | | $-\tfrac12$ | alternating ($b,t$ vs $r,l$) |
| 0001,0010,0011,0100,0110,0111 ↔ complements | | $+1$ | six pairs |
Every bright row has exactly one off-diagonal entry at $\mathrm{code}\oplus0b1111$; the 31 codes with a corner bit have zero rows. The spectrum $\{\pm2,\pm1(\times6),\pm\tfrac12,0(\times31)\}$ of $K$ and the 433-state multiplicities $16/96/16/177/16/96/16$ follow by counting outer completions (§6).

## 2. Decoding for the Gauss check (prototype P1/P5)
The laptop's evaluator calls `enc.decode_state` on every output component whose data code is in `inner_codes()` (for any outer pattern) and feeds the result to `gauss_residuals_coo`. For a basis encoding this includes $47\cdot256-433=11\,599$ inadmissible labels. Decoding them to zero or raising would either hide a wrong circuit (zero vector ⇒ zero residual) or crash the evaluator. Chosen rule: product state with every spin-$\tfrac12$ end at corner $c$ at $m=+\tfrac12$ (corner bit 0) / $-\tfrac12$ (corner bit 1), far ends $+\tfrac12$. Verified on all 11 599 codes: unit norm, Gauss residual minimum exactly $0.5$ (analytic $k/2$, $k\ge1$ aligned ends), overlap with every physical state $0$ (120 seeded samples, exact zeros), mutual overlaps $0$ (60 seeded pairs). Sensitivity through the real evaluator: `x` on a corner qubit, `x` on a link qubit, `cx(link→corner)` against the identity target are all rejected with `leak` amplitude 1 and Gauss residual 1.

## 3. Paulo's 15-qubit gate file (prototype P2)
Parsed (`cx h x t tdg p`, file qubits → `d[0..3]`, `d[4..7]`=file $q_{12..15}$, ancillas `a[0..6]`=file $q_{16..22}$; $q_{4..11}$ never appear): `{'cx': 68, 'h': 34, 't': 32, 'tdg': 32, 'x': 12, 'p': 4}`, `logical_metrics` cx 68, depth 90, n_rot 4, t_fixed 64, 7 ancillas; `p` angles $0.025, 0.05, 0.1, -0.2=\alpha_P\times(\tfrac14,\tfrac12,1,-2)$, $\alpha_P=0.1\Rightarrow\beta=0.05$.
- 47×47 block on the inner codes (`run_batch` + `encoded_block`): leak 0. Direct comparison with $e^{-i\beta K}$: op-norm error $0.1997$. After removing the global phase (phase $1+3\cdot10^{-18}i$) `gauge_align` finds a real $D$ with residual $2.9\cdot10^{-15}$; $D=-1$ exactly on the 8 codes $1000..1111$ (one member of each bright pair), $+1$ on all dark codes.
- Full evaluator on the 433 open states (23 qubits incl. the idle outer register), gauge-fixed target $D_{433}VD_{433}^\dagger$, `method="physical"`, `gauss=True`: `ok`, error $9.84\cdot10^{-15}$, leak 0, Gauss $5.4\cdot10^{-16}$, `outer_bits_read` 0, `n_blocks` 1, 0.2 s. Against the raw route-B target: error $0.1997$ (rejected); against the gauge-fixed $-\beta$ target: $0.1997$ (rejected) — consistent with $U_B(-\beta)=D'U_B(\beta)D'$: his circuit is $e^{+i\beta K}$ in route-B signs.
- Interpretation. Paulo's intertwiner convention (Eq. 44: $\epsilon$-contracted singlet–singlet vs $\sigma^i$-contracted triplet–triplet) fixes basis signs differently from the 6j $F$-symbols; since $K$ is a matching the difference is a per-pair sign, physically unobservable (audit 001 N5). The locked test M3-P1 therefore compares up to a real diagonal gauge **found from the circuit's own block**, records it, and requires everything else (leak, ancillas, Gauss, outer read-only, exact-angle tolerance $10^{-10}$ since the rotations are exact `p` gates) through the unchanged evaluator. Expected and measured: valid — Paulo's Fig. 2 claim (notes p. 9) holds on the open plaquette in the (inner | outer) pairing, in agreement with M0-X5.
- $T(10^{-6})$ by pygridsynth: $64+252=316$.

## 4. General circuit (prototype P3)
Candidates compared:
| Candidate | CX | rot | $T_{\rm fixed}$ | anc | Correctness / notes |
|---|---|---|---|---|---|
| Flag-controlled Walsh walk over $(F,m_1,m_2,m_3)$ with the don't-care slot $(F{=}0,m{=}100)$ | ≈ 48 | 16 | 24 | 3 | exact in principle; 16 rotations because $g(m)$ has all 8 Walsh terms and $F\cdot g$ doubles them (rejected on T cost) |
| **G7** (chosen): frame, flags $A,B,F,P,Q,G_1,G_2$ (7 `rccx`), 4-rotation walk | **54** | **4** | **56** | **7** | exact $1.0$–$1.4\cdot10^{-14}$ at $\beta=0.23,0.61,1.0$; steps $1.2\cdot10^{-14}$; $-\beta$ rejected (1.88); solve residual $4.0\cdot10^{-15}$ |
| G8 (same with $G_1,G_2$ from $F\wedge\bar m_1\wedge P$ directly) | 60 | 4 | 64 | 8 | exact ($1.2\cdot10^{-14}$); superseded by G7 (shared $Q=FP$) |
| spinnet_v2 `flags4` (sibling; `rc3x`) | 44 | 4 | 48 | 3 | exact; vendored as a comparison row, not as "our" general circuit (relies on nested `rccx` toggles into the walk wire and `rc3x`; less transparent) |
| spinnet_v2 `pairs9` | 34 | 9 | 24 | 3 | exact; best CX, 9 rotations |
Error analysis of G7: all gates are exact Clifford+`rccx`+`rz`; the only float work is the angle solve (4 unknowns, 16 constraint rows, residual $4\cdot10^{-15}$) and the simulation; measured verdict errors are at the $10^{-14}$ float floor, far from the $10^{-10}$ tolerance. Angles: $\theta=(-\tfrac72,-1,3,\tfrac32)\beta$; closed-form check: dark $0$; six pairs $2\beta$; vacuum $-4\beta$; alternating $-\beta$ ⇒ $R_z(2\beta k)$ with $k=1,-2,-\tfrac12$.
$T(\varepsilon)$ (pygridsynth / Qiskit CT seed 12345): $U_B$ 230/310/396/468 (225/308/389/462) at $\varepsilon=10^{-4},10^{-6},10^{-8},10^{-10}$; step order 1: 406/566/724/884 (397/542/717/842). Synthesised re-verification (sparse engine, `synth_tolerances`): $U_B$ $10^{-4}$: $1.01\cdot10^{-4}$ vs $4\cdot10^{-4}$; $10^{-6}$: $1.30\cdot10^{-6}$ vs $4.0\cdot10^{-6}$; $10^{-10}$: $7.4\cdot10^{-11}$ vs $1.4\cdot10^{-9}$; step: $1.80\cdot10^{-4}$, $2.38\cdot10^{-6}$ (Gauss $2.8\cdot10^{-7}$), $1.83\cdot10^{-10}$ vs $8\cdot10^{-4}$, $8.0\cdot10^{-6}$, $1.8\cdot10^{-9}$. Per-rotation T at $10^{-6}$ for $\theta=(-2.135,-0.61,1.83,0.915)$: 66, 64, 62, 62. Outer-electric row synthesised: `writes_outer` (as M1).

## 5. spinnet_v2 vendoring (prototype P4)
The sibling's skeletons were re-implemented in the same step language with angles solved from our $K$ (their `B_sn` equals $K/2$ in the code basis up to the per-pair signs). First attempt failed for `flags4` (error 2.0) because Qiskit's `RC3XGate` was used as its own inverse; `Operator(RC3XGate())**2` differs from the identity by 2.0, while `RCCXGate` squares to the identity exactly (0.0). With `RC3XGate().inverse()` (`rcccx_dg`, definition 6 CX, 4 H, 4 T, 4 T†) in the uncompute both skeletons are exact ($8.0\cdot10^{-15}$): `pairs9` 34 CX, 9 rotations, 24 T, depth 38, 3 ancillas; `flags4` 44 CX, 4 rotations, 48 T, depth 60, 3 ancillas (sibling results JSON: `A_plaq` 34 CX, 9 rotations, 564 T at $10^{-6}$; `flags4` "fewest gates/T"). The vendored module records `SOURCE` (path, results commit `feadc42`, date 2026-10-28).

## 6. Lean prototype
`scratch/planner/lean/SpinNetCounts.lean` imports `Su2Plaq.Structure.Counts` (laptop, read-only) and proves by `decide` (no `native_decide`, standard axioms): `innerLabels = 47`, `brightLabels = 16`, `darkLabels = 31`, `brightPairs = 8`, `multVac = 16`, `multAlt = 16`, `multOne = 96`, `brightStates = 256`, `darkStates = 177`, `totalStates = 433`, `corner_jbit_injective`, `corner_bit_needs_four_half`. Compile: 11.1 s wall, 8.27 GB RSS (Mathlib import through `Counts.lean`; no Mathlib is needed by the proofs themselves — if memory becomes a concern the definitions can be duplicated Mathlib-free, at the cost of not sharing the laptop's `fuse`). Definitions: `cornerJs ia ib oc od = fuse(ia,ib) ∩ fuse(oc,od)`, `innerLabelCount n = ∏_c |fuse(inner pair)|`, `brightCount n o = ∏_c |cornerJs ∩ {0,½}|`, `pairClass` (2 = vacuum, 1 = alternating, 0 = other), sums by the laptop's `sumOver` over 16 inner × 256 outer patterns. The multiplicities are the pair-class counts; with the couplings $|K|=2,1,\tfrac12$ (numerical; native through the laptop's structure certificate) they give the $H_B$ spectrum $16/96/16/177/16/96/16$ measured in M0-X8.

## 7. Decisions taken for prompts/100 (and reasons)
1. Target = route B (6j) in label order; route A enters only through `gauge_align` (and `decode_state` uses $D_k\psi_k^A$): matches the binding decision, keeps one `PhysicalBasis`, and makes the Gauss check consistent with the target.
2. External circuits compared up to a real diagonal gauge found from their own inner block (not by trying $\pm\beta$): the sign of $\beta$ is a gauge here (§3), so this is the only well-defined comparison; the gauge is recorded in `results/spinnet/UB.json`.
3. Inadmissible codes decode to the aligned product state (§2): isometric, orthogonal to the physical span, Gauss residual $\ge\tfrac12$ — keeps prompts/004's span-leak argument valid on this encoding.
4. General circuit = G7 (4 rotations, 54 CX, angle-linear, only `rccx`/`cx`/`x`/`h`/`rz`): most transparent 4-rotation design that uses only the project's allowed macros and no `rc3x`; the sibling's cheaper skeletons are comparison rows and M4 seeds.
5. spinnet_v2 vendored by skeleton + re-solve (not by importing its compiled text files): angle-linear circuits in our gauge for the like-for-like rows and for M4 seeds; `SOURCE` cites the sibling path and results commit.
6. Lean: reuse the laptop's `Structure/Counts.lean` definitions; new theorems only in `SpinNet/`; per-circuit certificate pending the laptop's checker (prompts/006 2.L4+), exporter written now.
7. Tolerances identical to M1 (exact-angle $10^{-10}$, weights $10^{-20}$, synthesised `synth_tolerances`); measured margins $\ge10^{3}$ for exact circuits and $3$–$4\times$ for synthesised ones.

## 8. Sources
- Paulo (Bedaque), notes `~/Projects/siblings/su2qc-paulo-code/hamiltonian-gauge-theories-circuits.pdf`, Sec. IV.B pp. 7–10 (Eqs. 40–44, Fig. 1–2, Table I), file `spin_network_plaquette3.gates.txt` (sha256 in `refs/paulo/SOURCE.md`).
- Zache, González-Cuadra, Zoller, arXiv:2304.02527, PRL 131, 171902 (2023), Eq. (2) (6j plaquette); Edmonds, *Angular Momentum in Quantum Mechanics*, Eqs. (6.1.5), (6.3.7).
- Welch, Greenbaum, Mostame, Aspuru-Guzik, "Efficient quantum circuits for diagonal unitaries without ancillas", New J. Phys. 16, 033040 (2014), arXiv:1306.3991 (Walsh series for diagonal unitaries; one rotation per Walsh term between CNOT toggles) — abstract page checked 2026-11-06.
- Maslov, "On the advantages of using relative phase Toffolis with an application to multiple control Toffoli optimization", Phys. Rev. A 93, 022311 (2016), arXiv:1508.03273 (relative-phase Toffoli; phases cancel in compute/uncompute pairs around a diagonal) — abstract page checked 2026-11-06; the project's kernel-checked form is `Su2Plaq.sandwich` (METHODS §11.1).
- Ross, Selinger, arXiv:1403.2975 (pygridsynth $T_r(\varepsilon)$); Qiskit 2.5.2 `RC3XGate` (`qiskit.circuit.library`, checked numerically: not self-inverse).
- su2qc-trotter `src/su2trotter/designs/spinnet_v2.py`, `src/su2trotter/spinnet.py`, `docs/compression/results_spinnet_v2.json` (commit `feadc42`, 2026-10-28).

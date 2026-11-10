# 204 — Rishon amendment: determinant term as a third Trotter layer, rishon prune cap 10 %, and how M5/M6 continue

Date: 2026-11-10 · Author: planner · Git commit at writing: `ece4fa3` (branch `merge-desktop-tracks`) · Track R (rishon, numbers 200–299)
Plan in force for track R = `prompts/203-rishon-m6-plan.md` **as amended by this file** (on top of `prompts/200`–`202`, `001`–`006`). Everything not mentioned here stays binding.
Research: `reports/research/203-rishon-det-term-prune-cap.md`. Methods: `docs/METHODS-rishon.md` R13–R16 (added by this run; pointers added in R1, R6, R10). Locked tests: `tests/acceptance/{m5,m5x,m6}` changed by this run, `tests/acceptance/LOCK.json` updated by hand for exactly those files (`python tools/check_lock.py` → `LOCK OK`).

Jargon, once. *Rishon*: a fermion that makes up one end of a gauge link in a quantum link model (QLM). *Det term*: $\det U_\ell+\det U_\ell^\dagger$ on a link; it moves both rishons of the link to the other end. *Trotter layer*: one factor $e^{-i\theta H_k}$ of a product formula. *Inner codes*: the 1296 valid 16-bit patterns of the four plaquette links. *Unit* (my label): the two-layer operator $U_B(\beta)U_E(\alpha)$ that the compression loop works on. *Prune cap*: the largest share of the error budget that the simulator's rounding bound `dropped_total` may use before a verdict is rejected as `pruning_bound`. *Evaluator hash*: sha256 over the source files that decide a verdict; each archive entry stores it. *Replay* (my label): re-running stored rounds with the same programs under a new evaluator hash. *Shim*: a scratch prototype of the new interface that I used to check the tests.

## 0. Trigger and decisions already taken by Digonto (2026-11-10, `notes/STATUS.md` Decisions)
(a) **Add the det coupling** as a third Trotter layer (audit `reports/audits/200-m5-rishon-audit.md` N1: without it the dynamics is U(2)-invariant). (b) **Rishon prune cap 10 % of `tol_err`** ($10^{-12}\to10^{-11}$), encoding-specific. (c) Mark `test_M5_T1_t_table_and_synth_verify[step]` slow (`prompts/202` §7). (d) Errata E1–E3 of `prompts/203` §13 accepted as they stand (no change here).
Inputs read: `reports/tests/221-m6-round-004-step-6-4b.md` §4 (what the changes invalidate; the name clash on "gamma"), `notes/STATUS-rishon-m5-m6.md` (RESTART HERE), `notes/merge-notes-rishon.md`, `prompts/200`, `203`, `docs/METHODS-rishon.md`.

## 1. Diagnosis (no failure was escalated; what was open)
1. The M5/M6 model had $\gamma=0$ by a planner default. Audit 200 N1: the Hamiltonian then conserves a U(1) charge at every corner (431 sectors) — it is the U(2) model with static charges, not the SU(2) QLM of Brower–Chandrasekharan–Wiese.
2. The 1 % prune cap rejected exact rishon circuits on simulator rounding alone (`prompts/203` §13 E2): rccx / mcx ladder seeds and the Qiskit L3 seed, `dropped_total` $2.7$–$3.8\times10^{-12}$ with block error $\le3.7\times10^{-13}$.
3. Tester 221 §4: a det layer inside the loop's target would invalidate all 16 archive entries; and "gamma" already names the $\sqrt2\beta$ coefficient in `recognise_angle` / `Laurent3`.

## 2. Method — the det term

### 2.1 Symbols (new; say so in every report)
$\lambda_D$ = coefficient of the det term in $H$ (this is Wiese's $\gamma$ and BCW's $J'$). $\eta=\lambda_D\,dt$ = angle of the det layer. Code names `lam_d`, `eta`. **The letter $\gamma$ / `gamma` is not used for the det coupling anywhere**; it keeps its meaning "the $\sqrt2\beta$ slot" (`prompts/203` §2, METHODS-rishon R12).

### 2.2 Operator, normalisation, sign (sources: BCW arXiv:hep-th/9704106 Eq. 2.20, 4.5–4.6; Wiese arXiv:1305.1602 Sec. 4.3, sentence after Eq. 4.11 and Eq. 4.14; conventions of METHODS-rishon R1–R2)
$$H=\frac{g^2}{2}H_E+\frac{1}{g^2}H_B+\lambda_D H_D,\qquad H_D=\sum_{\ell=1}^{12}\big(\det U_\ell+\det U_\ell^\dagger\big),$$
$$\det U=U_{11}U_{22}-U_{12}U_{21}=2\,c_{L1}c^\dagger_{R1}c_{L2}c^\dagger_{R2}\quad(N=2\text{ in BCW Eq. 4.6}),\qquad U_{ij}=c_{L,i}c^\dagger_{R,j}.$$
With the Jordan–Wigner map of R2 (link qubits $L_1L_2R_1R_2$, codes $A$ = 3, $B$ = 12): $\det U=+2|B\rangle\langle A|$ on the two-rishon sector, the only non-zero entry of the $16\times16$ matrix (measured; Lean `det_u_sector`, `det_u_identity` already prove it). Per link
$$H_D^{\rm link}=2\big(|B\rangle\langle A|+|A\rangle\langle B|\big):\quad+2\text{ on }\tfrac{A+B}{\sqrt2},\quad-2\text{ on }\tfrac{A-B}{\sqrt2},\quad0\text{ on the four quartet codes}.$$
Coefficient 1 on $(\det U+\det U^\dagger)$ and the plus sign are conventions: $S=\prod_\ell e^{i\frac\pi4(n_R-n_L)_\ell}$ gives $SH_DS^\dagger=-H_D$, $SH_ES^\dagger=H_E$, $SH_BS^\dagger=H_B$ (measured $2\times10^{-16}$), so spectra depend on $|\lambda_D|$ only.
Structure facts (all measured exact, research 203 §3.1–3.3; each is a locked test): $[L_a,\det U]=[R_a,\det U]=0$; $[n_R-n_L,\det U]=4\det U$; $[H_D,H_E]=0$; $\|[H_D^{\rm in},H_B^{\rm in}]\|_2=16\sqrt2=22.627$; the eight outer det terms commute with $H_E$, $H_B$ and the four inner ones.

### 2.3 Target operators and Trotter orders
Inner part: $H_D^{\rm in}=\sum_{\ell\in\{b,r,t,l\}}(\det U_\ell+{\rm h.c.})$ on the 1296 inner codes (real symmetric, entries 0 / 2; spectrum $2(n_+-n_-)$ with multiplicities $\{\pm8:1,\pm6:16,\pm4:100,\pm2:304,0:454\}$).
$$U_D(\eta)=e^{-i\eta H_D^{\rm in}}=\bigotimes_{\ell\in\{b,r,t,l\}}\Big[\mathbb 1+(\cos2\eta-1)\big(|A\rangle\langle A|+|B\rangle\langle B|\big)-i\sin2\eta\,\big(|A\rangle\langle B|+|B\rangle\langle A|\big)\Big]_\ell .$$
Angle map: $\alpha=\tfrac{g^2dt}{2}$, $\beta=\tfrac{dt}{g^2}$ (METHODS §2), $\eta=\lambda_D\,dt$. Because $[U_D,U_E]=0$ there are still only two non-commuting groups ($H_B$ against $H_E+H_D$):
$$\textbf{order 1:}\quad U_1(\alpha,\beta,\eta)=U_B(\beta)\,U_D(\eta)\,U_E(\alpha)\qquad(\text{circuit order: electric, then det, then magnetic}),$$
$$\textbf{order 2:}\quad U_2(\alpha,\beta,\eta)=U_E(\tfrac\alpha2)\,U_D(\tfrac\eta2)\,U_B(\beta)\,U_D(\tfrac\eta2)\,U_E(\tfrac\alpha2).$$
Local error $O(dt^2)$ and $O(dt^3)$ (Hatano–Suzuki arXiv:math-ph/0506007); measured slopes 1.994 and 2.994 between $dt=0.05$ and $0.025$ at $g^2=1.1014$, $\lambda_D=0.4316$. Exact identity (measured $3\times10^{-15}$): with $L(x)=U_D(x\eta)U_E(x\alpha)$, $U_2^{\,n}=L(\tfrac12)\,U_1^{\,n}\,L(-\tfrac12)$.
$\eta$ absent (`eta=None`) means the two-layer M5 objects, bit-identical to today.

### 2.4 Nominal angles to verify at
$(\alpha,\beta,\eta)=(0.37,0.61,0.29)$; alternates $(0.91,0.23,0.53)$ and $(1.70,1.00,1.07)$ (same gate skeleton). $2\eta$ and $4\eta$ are at least 0.2 rad from every multiple of $\pi/4$. The nominal $\eta$ equals $\lambda_D=0.4316$ at the couplings behind $(0.37,0.61)$ ($g^2=\sqrt{2\alpha/\beta}=1.1014$, $dt=\sqrt{2\alpha\beta}=0.6719$). It is a generic test angle, not a physics value (BCW and Wiese leave the coupling free). Observable tables also use $\lambda_D\in\{0,0.2,0.5\}$ at $g^2\in\{0.5,1,2\}$ (0.2 is the audit's probe value).

### 2.5 What the det term does to the physical space (computed by `scratch/planner/proto_rishon_det_sectors_204.py`, 3.6 s; locked in M5-DT5)
The rishon SU(2)-Gauss space has 38 432 states (the 433 Kogut–Susskind labels weighted by $2^{\#j=0}$). It is invariant under every link's det term (weight leaving it $\le6\times10^{-11}$).

| | $\lambda_D=0$ | det on the 4 inner links | det on all 12 links |
|---|---|---|---|
| corner charges $Q_c$ | conserved, 431 sectors | changed by $\pm2$ on the two corners of the link (total conserved; rank 3) | also $\pm2$ on a single corner (rank 4: no U(1) charge left) |
| dynamical blocks of $H$ (connected components) | 31 870 (sizes 1, 2, 3) | 4 976 (largest 17) | 305 (largest 4 352) |
| block of the reference state ${\rm vac}_A$ | 3 states, 1 charge sector | 17 states (16 electric vacua $\{A,B\}^4$ + loop), 15 charge sectors | 4 352 states = the closed sector, all 431 charge tuples |

Closed sector with the full det term factorises exactly as (17-dim inner block) ⊗ (8 outer two-level links), because the outer det row commutes with everything else. Inner $17\times17$ block (vacua indexed by bits "link $\ell$ is type $B$", then the loop): $H=\tfrac{g^2}2\,3|{\rm loop}\rangle\langle{\rm loop}|-\tfrac4{g^2}\big(|{\rm loop}\rangle(\langle{\rm vac}_A|+\langle{\rm vac}_B|)+{\rm h.c.}\big)+2\lambda_D\sum_\ell X_\ell$; zero levels 15 at $\lambda_D=0$, 5 at $\lambda_D=0.2,0.5$. ${\rm vac}_A$ stays the reference *state* for the shared observables; it is no longer close to an eigenstate. $P(1)=0$ still holds. Kogut–Susskind has no counterpart of the det term: the KS column of Report 5 stays a $\lambda_D=0$ comparison.

## 3. Method — rishon prune cap (decision (b))
$$\texttt{pruning\_bound}\iff\texttt{dropped\_total}>\texttt{RISHON\_PRUNE\_FRACTION}\times\texttt{tol\_err},\qquad\texttt{RISHON\_PRUNE\_FRACTION}=10^{-1}.$$
Exact-angle cap $10^{-11}$; synthesised cap $0.1\,(N_{\rm rot}\varepsilon+10^{-9})$. The error bound is **unchanged**: `op_norm_error` = `block_error` + `leak_amplitude` + `dropped_total` $\le$ `tol_err` (`prompts/004`, `prompts/005` §1–§2) is rigorous for any pruning; the cap only limits the simulator's share. Budget with the worst measured rate ($1.1\times10^{-15}$ per branching gate, `prompts/203` §13 E2): $\lfloor10^{-11}/1.1\times10^{-15}\rfloor=9090$ branching gates (was 909).

**Mechanism — rishon-local; `src/su2plaq/evaluate/*` and `src/su2plaq/compress/*` stay byte-identical.** In `su2plaq.rishon.verify.verify` (the single place every rishon verdict passes through: M5 results, loop evaluator, `verify_synthesised`), after the shared `evaluate` returns `iv`:
- `iv.reason != "pruning_bound"` → unchanged (the shared cascade tests the cap first, so every other shared verdict already has `dropped_total` $\le10^{-2}$ `tol_err`);
- `iv.reason == "pruning_bound"` → re-judge with the shared cascade and the rishon cap: `dropped_total` > cap → `pruning_bound` (`failing_inputs` = the two numbers); else `leak_amplitude` > `tol_err` → `"dirty_ancilla"` if `dirty_ancilla` $\ge\tfrac12$ `max_leak` else `"leak"` (label only: the shared `Verdict` does not carry the invalid-code weight; validity is unaffected); else `op_norm_error` > `tol_err` → `"error"`; else the Gauss sample decides exactly as today (`gauss` / `unsimulable_gauss` / `ok`);
- `prune_fraction` smaller than the shared `PRUNE_FRACTION` → `ValueError` (the rishon cap can only be looser; a stricter one cannot be re-judged from a shared `ok`);
- `RishonVerdict.inner_verdict` keeps the shared verdict untouched; `extra` gains `prune_fraction`, `prune_cap`, `laptop_reason`.

**Which hashes go stale.** Only the rishon evaluator hash `su2plaq.rishon.compress.code_hash()` (now `43ae85b4…` for rounds 2–4, `d45ffb31…` for rounds 0–1): `rishon/verify.py` and `rishon/compress/spec.py` are in `RISHON_EVALUATOR_FILES`, as they must be (they decide verdicts / the spec text). Not stale: the shared `provenance.code_hash()` (twelve, spinnet, fuzzy, LSH loops), `TaskSpec.sha256()` (`bb0b575b…`: the dataclass has no cap field), every program sha. The det code of §4–§5 touches further hashed rishon files (`operators`, `circuits`, `encodings`, `physical`); **all hashed edits are done in Phase D, before the single replay of §6.2.**

## 4. Method — general circuit of the det layer (gate set, counts)
Per link, qubits $(L_1,L_2,R_1,R_2)$. Frame: `cx(L1,L2)`, `cx(R1,R2)` send $A\to(1,0,0,0)$, $B\to(0,0,1,0)$, every quartet code to $(\cdot,1,\cdot,1)$. On the block $L_2=0$ the Pauli $X_{L_1}X_{R_1}$ exchanges the images of $A$ and $B$ (the other two patterns there are invalid codes, don't-care), so
$$e^{-2i\eta(|A\rangle\langle B|+{\rm h.c.})}\;\widehat{=}\;e^{-i\eta X_{L_1}X_{R_1}}\,e^{-i\eta X_{L_1}X_{R_1}Z_{L_2}}:$$
`h(L1) h(R1) cx(L1,R1) rz(2η,R1) cx(L2,R1) rz(2η,R1) cx(L2,R1) cx(L1,R1) h(L1) h(R1)`, then `cx(R1,R2)`, `cx(L1,L2)` (Qiskit `rz(θ)` $=e^{-i\theta Z/2}$). **Per link 8 CX, 2 rotations (both `rz(2η)`), 4 H, no ancilla, global phase 1; gates from the allowed set only.**

| circuit (measured, research 203 §3.4) | qubits | CX | rotations | $T_{\rm fixed}$ | $T(10^{-6})$ | depth / depth$_{\rm CT}$ | `op_norm_error` |
|---|---|---|---|---|---|---|---|
| `build_UD(0.29)` (4 inner links) | 16 (48 with `o`), 0 ancillas | 32 | 8 | 0 | 496 (mean 500.8 over the eta set, range 480–512) | 10 / 326 | $2.4\times10^{-14}$ |
| outer det row (8 outer links, separate) | 32 | +64 | +16 | 0 | — | 10 | certificate bound $4.0\times10^{-15}$ (all 12 links) |
| general three-layer step, order 1 (counts = M5 step + det layer; additivity is a locked check) | 26 | 10 134 = 10 102 + 32 | 174 = 166 + 8 | 10 218 | — (results step D6) | — | $5.0\times10^{-13}$ |
| **headline `r04-F1-004` + det layer** | 53 | **260** = 228 + 32 | 18 = 10 + 8 | — | **1 342** = 846 + 496 | 1 743 = 1 417 + 326 | $1.8$–$2.0\times10^{-13}$ at the three triples |

Lower bound used in the decision of §6.1: the det layer alone needs 2 $\eta$-dependent rotations per link (three distinct eigenphases $e^{\mp2i\eta}$, 1; one rotation has two). 8 CX per link is not proved minimal (research 203 §3.5).
Second-order step: half-angle gadgets on both sides of $U_B$ (`build_step(..., order=2, eta=...)`): +64 CX, +16 rotations over the M5 order-2 step.

## 5. Interface (builder: stubs first, then real; the locked tests call exactly these names)
```python
# src/su2plaq/rishon/operators.py
def h_det_inner() -> np.ndarray                      # 1296x1296 real symmetric H_D^in (same matrix as det_term_inner(), which stays)
def hamiltonian_inner(g2: float, lam_d: float = 0.0) -> np.ndarray     # (g2/2) diag(H_E^in) + H_B^in/g2 + lam_d H_D^in, complex128
def inner_target(kind, alpha, beta, order=1, eta=None) -> np.ndarray
    # kind "UD": exp(-i eta H_D^in), eta required (ValueError if None); kinds "UE"/"UB": eta must be None (ValueError otherwise);
    # kind "step": eta None -> today's two-layer target, bit-identical; eta a number -> order 1 = UB(beta) UD(eta) UE(alpha),
    # order 2 = UE(alpha/2) UD(eta/2) UB(beta) UD(eta/2) UE(alpha/2)
def closed_block_full(g2: float, lam_d: float = 0.0) -> np.ndarray     # 17x17; lam_d = 0.0 returns today's array unchanged

# src/su2plaq/encodings/rishon.py
RISHON_NOMINAL_ETA = 0.29 ; RISHON_ALT_ETA = (0.53, 1.07)
class RishonEncoding: inner_target(self, kind, alpha, beta, order=1, eta=None) ; target(self, kind, alpha, beta, order=1, states=None, eta=None)

# src/su2plaq/rishon/verify.py
RISHON_PRUNE_FRACTION = 1e-1
def verify(qc, enc, kind, alpha, beta, order=1, *, eta=None, prune_fraction=None, tol_err=1e-10, tol_gauss=None, gauss=True, gauss_sample=256,
           seed=20261104, engine="auto", cap=5_000_000, target=None, states=None) -> RishonVerdict       # section 3 rule; kind "UD" allowed
def physical_cross_check(qc, enc, kind, alpha, beta, order=1, states=None, eta=None) -> dict

# src/su2plaq/circuits/rishon.py
def build_UD(eta, with_outer=False, include_outer_det=False) -> QuantumCircuit     # registers d (+ o); metadata {"kind": "UD", "eta": eta};
    # include_outer_det (needs with_outer, else ValueError) adds the gadget on the 8 outer links
def build_step(alpha, beta, order=1, with_outer=False, ladder="ccx", eta=None)     # eta None: today's circuit gate for gate
def prepend_det_layer(unit: QuantumCircuit, eta) -> QuantumCircuit                 # new circuit on unit's registers (first register must be d[16],
    # else ValueError): det gadgets on d, then all of unit's instructions unchanged and in order

# src/su2plaq/rishon/physical.py
def det_sector_structure(basis=None) -> dict
    # {"dim": 38432, "u1_sectors": 431, "blocks": {"lam0","inner_det","full_det"}, "max_block": {...}, "ref_block_dim": {...},
    #  "ref_block_u1_sectors": {...}, "charge_change_rank": {...}, "leaving_weight": float}; reference state = closed_indices(basis)[0]

# src/su2plaq/rishon/observables.py
def observables(alpha, beta, n_steps=2, order=1, eta=None) -> dict     # eta given: the "rishon" rows use the three-layer step; "ks" rows unchanged
def closed_spectra(g2_list=(0.5, 1.0, 2.0), lam_d=0.0) -> dict        # rishon: the 17 closed levels grouped (eigenvalues, multiplicities); lam_d = 0.0 unchanged
def det_observables_table(triples=..., lam_d_list=(0.0, 0.2, 0.5)) -> dict   # the JSON of results/rishon/observables_det.json (keys: section 7 DT7)

# src/su2plaq/rishon/results.py
def outer_det_certify(qc, enc, eta, tol_err=1e-10) -> dict     # as outer_electric_certify: method "outer_det_gadgets", target exp(-i eta (det U + det U^dag))
    # on the 6 sector codes (16 x 6 block), phase per link = arg tr(T^dag V) (fitted), same keys and reasons (ancilla_register, cross_link_gate, error)

# src/su2plaq/rishon/compress/replay.py      (new; NOT in RISHON_EVALUATOR_FILES)
TAG = "204"
def replay(kind="step", root=None, tag=TAG, lean=False) -> dict   # section 6.2; CLI: python -m su2plaq.rishon.compress.replay [--kind step] [--root R]

# src/su2plaq/rishon/compress/three_layer.py  (new; NOT in RISHON_EVALUATOR_FILES)
DET_TRIPLES = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
ETA_SET_SEED, ETA_SET_N, ETA_SET_RANGE = 20261110, 20, (0.05, 1.2)
ETA_SET: tuple[float, ...]                    # numpy.random.default_rng(ETA_SET_SEED).uniform(0.05, 1.2, 20)
def det_layer_metrics(eta=0.29) -> dict       # laptop metrics(build_UD(eta, with_outer=True), rishon_spec("step"), measured=True): "cx","n_rot","t_fixed","t_eps",
    # "depth_ct","qubits","key"; plus "t_eps_set" (20 ints over ETA_SET), "t_sum", "t_mean", "eta"
def verify_three_layer(entry_id=None, kind="step", root=None) -> dict
    # entry = robust.headline(kind)["id"] unless given; program rebuilt at the three (alpha, beta); full = prepend_det_layer(unit, eta);
    # {"entry","program_sha256","triples","verdicts": [{"ok","certified","reason","op_norm_error","block_error","leak_amplitude","dropped_total",
    #  "gauss_residual"} x3],"skeleton_equal","ok","unit_key","det_key","three_layer_key" (= compress.metrics.key(metrics(full, measured=True)) at the nominal
    #  triple),"unit_t_mean","det_t_mean","three_layer_t_mean","outer_touched"}
# CLI: python -m su2plaq.rishon.compress.three_layer [--entry ID] -> results/compress/rishon/three-layer.json (+ "evaluator_sha256", "provenance")

# src/su2plaq/rishon/lean_cert.py (with step 6.L2/6.L3 of prompts/203)
def recognise_angle_single(theta, base, max_den=64, tol=1e-12) -> tuple[int, int] | None    # (m, d): theta = m base / d, smallest d <= max_den, gcd-reduced; 0 -> (0, 1)
def certify_det_layer(qc, eta, out_dir=None, timeout=900.0) -> LeanCert   # cert3 certificate (same schema) with eta in the first formal slot:
    # gate exponents (m, 0, 0), target from the closed form of section 2.3, provenance {"kind": "UD", "angle_slots": {"alpha": "eta"}, ...}
```
`rishon/compress/spec.py`: `prune_budget` and the Correctness sentence of `render_spec` use `RISHON_PRUNE_FRACTION` (cap text `1e-11`, "prune cap = 0.1 x tolerance for this encoding", budget 9090, and the clause about rejected circuits replaced by "the uncompressed circuit in bare h/t form, its rccx-ladder variants and its Qiskit L3 transpile use about 3 500–4 400 of them and pass"); the string `1e-12` must not occur in the rendered spec. `brief.py` takes the cap number from the same constant. `scripts/m5_det_results.py` (new; `scripts/m5_results.py` untouched).

## 6. Decisions on how M6 continues

### 6.1 Compression unit: **stays $U_B(\beta)U_E(\alpha)$**; the det layer is added in front, outside the loop
Three-layer first-order step $=U_BU_DU_E=[U_BU_E]\,U_D$ (exact, $[U_D,U_E]=0$) = `prepend_det_layer(unit, η)`. Reasons, with numbers:
- The loop's target does not contain $\eta$: all 16 archive entries, 15 of 20 proposer sessions, tester reports 217–221 and the robust headline `r04-F1-004` $(228,16876,0,28328,53)$ stay valid physics. I verified the headline program with the det layer in front against the three-layer target at the three triples: `ok`, certified, error $\le2.0\times10^{-13}$, Gauss $\le1.2\times10^{-15}$.
- What joint compression could gain is small: the det layer needs 2 rotations per link in any frame; sharing the per-link parity CX with $U_E$ saves at most 2 CX per link = 8 of 260 CX (3 %). The laptop key is CX-first, so rotation-saving tricks that cost CX would not be chosen.
- The shared `TaskSpec` has two angles and fixed kinds (`step`, `UB`, `UE`); a three-angle unit cannot be expressed without editing shared files.
- The three-variable angle rule, `recognise_angle`, `Laurent3` (step 6.L2) and the $(\alpha,\beta)$ robust angle set are unchanged; no fourth variable.
Cost accounting: three-layer key = (CX$_{\rm unit}$ + CX$_D$, $T_{\rm unit}+T_D$, depth$_{\rm CT}$ of the composite, max qubits) — today $(260,1342,1743,53)$; angle-averaged $\bar T=843.8+500.8=1344.6$ (det layer over the eta set of §5). Report 6 quotes the unit and the three-layer step side by side; the three-layer row is "one Trotter step of the model".
The det layer is **not** sent through the proposer loop (4 copies of a 4-qubit gadget at its rotation minimum). Optional later hand work is listed in §12.

### 6.2 Replay of rounds 0–4 under the new evaluator hash (`su2plaq.rishon.compress.replay`)
Needed because of §3 (and the det code): locked `test_M6_G1` requires the best entry's `evaluator_sha256` to equal the current hash. Procedure of `replay(kind, root, tag)`:
1. Refuse (`ValueError`) if `results/compress/rishon/replay-<tag>.json` or a `pre-<tag>` folder already exists.
2. Read the existing `results/compress/rishon/round-*.json`: per round the ordered candidates (`id`, `label`, `program_path`, `valid`, `reason`, `key`), the round's `evaluator_sha256`.
3. **Move** (nothing is deleted; everything is also in git history) `results/compress/rishon/{round-*.json, feedback/, robust.json, summary.json}` to `results/compress/rishon/pre-<tag>/` and `compress/archive/rishon/` to `compress/archive/rishon-pre-<tag>/`; remember the bytes of `compress/attempts/rishon.jsonl` and `compress/discoveries/rishon.md`.
4. For $r=0,1,\dots$: `run_round(kind, r, evaluate=True, dry_run=False, root=root, proposals=None if r == 0 else [that round's program paths in recorded order], lean=lean)`.
5. Restore the attempts log and the discoveries file byte for byte (a replay is not a new attempt); record whether they were restored.
6. Write `replay-<tag>.json`: `{"tag","encoding","kind","prune_fraction","rounds": [0..R],"evaluator_sha256","evaluator_sha256_old": [...],"entries": [{"id","round","label","old": {"valid","reason","key"},"new": {"valid","reason","key","dropped_total"},"key_equal"}],"newly_valid": [...],"lost": [...],"best_old": {"id","key"},"best_new": {"id","key"},"attempts_unchanged","discoveries_unchanged","backup": [...],"provenance"}`.
Expected outcome (research 203 §3.6, `round-000.json`): the 16 valid entries keep their keys; `r00-seed-001` (general-rccx, $2.9\times10^{-12}$), `r00-seed-002` (general-mcx, $2.7\times10^{-12}$), `r00-seed-qiskit_l3` ($3.8\times10^{-12}$) become valid; round-0 best becomes the rccx variant; global best and headline unchanged. The replay is not a round: stop-rule counter (0), proposer sessions (15/20) and `MAX_ROUNDS` bookkeeping are unchanged. **Any later edit of a file in `RISHON_EVALUATOR_FILES` needs a new replay with a new tag** before G1/G5 can pass.

### 6.3 Rounds 5… and the gate
Unchanged protocol (`prompts/203` §2, §5 rows 6.7–6.8, §13 E3): briefs regenerated after the replay (cap text $10^{-11}$), same families, same stop rule on the robust key of the unit. Gate additions: ids H3, H4, G5, G6, L9 (§7); `scripts/m6_results.py` writes unit / det layer / three-layer rows; Report 6 additions in §9.

### 6.4 Lean
- Unit: three-angle checker exactly as `prompts/203` §3.2 (step 6.L2 not yet built; design unchanged).
- Det layer: the same checker with $\eta$ in the first formal slot (`certify_det_layer`); certificate target from §2.3 ($\cos2\eta=\tfrac12(z^{2d}+z^{-2d})$, $z=e^{i\eta/d}$). Three-layer step for all $(\alpha,\beta,\eta)$ = composition of the two certificates (documented argument, METHODS-rishon R16; not a Lean theorem).
- Exporter rule (tester 221 N1): an archive entry may be `certified` only if the exponents the exporter emits equal the `angle_fit` of `robust_metrics` (confirmed at the 20 pairs, $\rho=0$); otherwise status `n_a`, reason `angle_fit_not_confirmed` (added to the reasons L7 accepts).

## 7. Milestones → steps (one builder call each unless marked; tester verifies the ids; commit after PASS; `graphify update .` after every builder step)
Commands: `tools/pytest-safe -n 4 -m "not slow" <ids>` on the assigned cores; heavy scripts under `tools/run-capped`.
Regression done-check for every Phase D step: `tools/pytest-safe -n 4 -m "not slow" tests/acceptance/m5 tests/acceptance/m5x tests/acceptance/m6` shows no new non-`PENDING` failure; rishon unit tests green.

**Phase D — M5 addendum (all edits of hashed rishon files happen here, in this order)**

| Step | Builds | Done-check (tester) | Acceptance ids |
|---|---|---|---|
| D1 | prune cap: `verify.RISHON_PRUNE_FRACTION`, re-judge rule of §3, `verify(prune_fraction=)`; `compress/spec.py` (`prune_budget`, Correctness sentence), `brief.py`; regenerate `compress/specs/rishon-step.md` and `rishon-structure.json`; unit tests updated (cap text, budget 9090) | U_B rccx: `ok`, `dropped_total` $2.28\times10^{-12}$, shared verdict `pruning_bound`; `git diff --stat src/su2plaq/evaluate src/su2plaq/compress` empty; `python -c "from su2plaq.compress import provenance as P; print(P.code_hash())"` equals its value before the step | `tests/acceptance/m5/test_rishon_prune_cap.py::test_M5_V2_rishon_prune_cap`, `tests/acceptance/m6/test_rishon_m6_spec.py::test_M6_K2_structure_facts_and_spec_text` |
| D2 | stubs for every other name / keyword of §5 (`NotImplementedError("PENDING: ...")` on the new paths); then `operators.h_det_inner`, `hamiltonian_inner`, `inner_target(eta=)`, `closed_block_full(lam_d=)`, encoding pass-through and the two eta constants | `pytest --collect-only -q tests/acceptance` clean; all det tests fail only with `PENDING:`; then the three ids green; `inner_target("step", 0.37, 0.61)` array-equal to its value before the step | `tests/acceptance/m5/test_rishon_det.py::test_M5_DT1_link_det_operator` (already green), `::test_M5_DT2_inner_det_hamiltonian`, `::test_M5_DT3_targets` (3 triples), `::test_M5_DT3_trotter_orders` |
| D3 | `circuits.build_UD`, `build_step(eta=)`, `prepend_det_layer`; `verify(eta=)`, `physical_cross_check(eta=)` | `build_UD(0.29)`: 32 CX, 8 rotations, 16 qubits; `build_step(0.37, 0.61)` skeleton identical to before; M5 `S1`, `B1`, `E1` still green | `::test_M5_DT4_det_layer_circuit` (3 etas), `::test_M5_DT4_three_layer_step` (2 orders), `::test_M5_DT4_physical_cross_check_and_compose` |
| D4 | `physical.det_sector_structure`; `observables(eta=)`, `closed_spectra(lam_d=)`, `det_observables_table` | block counts 31 870 / 4 976 / 305; M5 `O1` still green | `::test_M5_DT5_sector_structure_with_det`, `::test_M5_DT6_observables_with_det` (3 triples), `::test_M5_DT6_closed_spectrum_with_det` |
| D5 | `results.outer_det_certify` | 12-link bound $\le10^{-10}$ (prototype $4\times10^{-15}$) | `tests/acceptance/m5x/test_rishon_outer_det_row.py::test_M5X_O2_outer_det_row_certified` |
| D6 | `scripts/m5_det_results.py`; **coordinator** runs it on a clean commit in the background (`tools/run-capped`), commits the files: `results/rishon/{UD,step3,step3_order2}.json` (+ `.qpy`, `.qasm3`), `UD_outer_row_certified.json`, `observables_det.json` | files present, `git_dirty: false`; numbers of §4 reproduced | `tests/acceptance/m5/test_rishon_det.py::test_M5_DT7_det_results_files` (3), `::test_M5_DT7_det_observables_file`, `tests/acceptance/m5x/test_rishon_outer_det_row.py::test_M5X_O2_outer_det_row_results_file` |
| D7 | **Mini-gate "M5d"** (coordinator): tester `full` on m0, m1, m5, m5x (incl. slow) + unit + `check_lock` + `acceptance-check`; auditor on the Phase D diff (normalisation and sign of $H_D$, layer order, the re-judge rule, the sector claims, the outer-row argument); benchmark compare with `reports/benchmarks/200`; tag `milestone-5d`; Report 5 addendum §3.8 (content in §9) | — | all m5 / m5x ids |

**Phase C — M6 continuation**

| Step | Builds | Done-check | Acceptance ids |
|---|---|---|---|
| C1 | `rishon/compress/replay.py` (+ CLI, unit test: dry replay of a kind-`UE` seed round in a temporary root), `rishon/compress/three_layer.py` (+ CLI) | H3, H4 green on the present archive; `code_hash()` unchanged by this step | `tests/acceptance/m6/test_rishon_m6_three_layer.py::test_M6_H3_det_layer_metrics_and_eta_set`, `::test_M6_H4_three_layer_headline` |
| C2 | **coordinator:** clean commit, then `taskset -c <cores> tools/run-capped python -m su2plaq.rishon.compress.replay --kind step` in the background; **tester** (mode `step`, next report number): the 16 keys identical, the three newly valid seeds, headline and robust key unchanged, `git diff` empty on the attempts log and discoveries file, round files carry the new hash; commit `compress rishon replay 204 (prompts/204, reports/tests/NNN)` | `replay-204.json` as §6.2 | `::test_M6_G5_replay_record`, `tests/acceptance/m6/test_rishon_m6_seeds.py::test_M6_S3_round0_recorded` (slow), `tests/acceptance/m6/test_rishon_m6_gate.py::test_M6_G1_archive_best_valid_and_not_worse_than_seed` (slow), `::test_M6_G2_best_synthesised_reverified`, `::test_M6_G3_best_touches_no_outer_qubit`, `::test_M6_G4_summary_and_budgets`, H1, H2 (slow) |
| C3 | rounds 5… (coordinator + proposers + tester per round) as `prompts/203` row 6.7 | per-round tester report | as `prompts/203` |
| C4 | Lean 6.L1–6.L4 of `prompts/203` plus `recognise_angle_single`, `certify_det_layer`, the exporter rule of §6.4 | as `prompts/203` rows 6.L2–6.L4; det layer certified | L1–L8 of `prompts/203`, `tests/acceptance/m6/test_rishon_m6_lean.py::test_M6_L9_det_layer_certificate` |
| C5 | results (extends row 6.8): `python -m su2plaq.rishon.compress.three_layer` on the final headline (clean commit) → `results/compress/rishon/three-layer.json`; `scripts/m6_results.py` rows unit / det layer / three-layer / outer rows | three-layer key = unit + det | `tests/acceptance/m6/test_rishon_m6_three_layer.py::test_M6_G6_three_layer_summary` |
| C6 | gate as `prompts/203` row 6.8 with the ids above; `milestone-6`; Report 6 (§9) | — | all m6 ids |

Order: D1 → D2 → D3 → D4 → D5 → D6 → D7 → C1 → C2 → C3 (C4 alongside the rounds, as before) → C5 → C6. C1 may be built before D7 finishes, but C2 only after D7 (no hashed file may change after the replay).

## 8. Acceptance tests added / changed, tolerances and why

**Changed (existing ids).**
| Test | Change | Justification |
|---|---|---|
| `m5/test_rishon_metrics.py::test_M5_T1_t_table_and_synth_verify[step]` | marked `slow` (one `pytest.param`) | decision (c); `prompts/202` §7: 581–671 s in one process; still runs at every gate; nothing weakened |
| `m6/…_spec.py::test_M6_K2_…` | requires `RISHON_PRUNE_FRACTION == 0.1`; spec phrase `1e-12` → `1e-11`, and `1e-12` must be absent; `budget_at_cap == floor(1e-11 / rate)` | decision (b); the spec must state the rule in force; budget identity is arithmetic |
| `m6/…_seeds.py::test_M6_S3_…` | `PENDING` until the replay record exists; round-0 file must carry the replay's hash; judged rows: `ok` rows also need `dropped_total` $\le10^{-11}$, a rejected row `dropped_total` $>10^{-11}$ (was $10^{-12}$) | decision (b). **Loosened tolerance** $10^{-12}\to10^{-11}$: Digonto's decision, quantitative basis in §3 (bound stays rigorous; 10 % of budget; measured $2.7$–$3.8\times10^{-12}$ on exact circuits) |
| `m6/…_gate.py::test_M6_G1_…` | `PENDING` until cap + replay exist; `dropped_total <= 1e-11` (was `1e-12`) | same as S3; G1 must test the validity rule in force, otherwise a valid best could fail the gate |
| `m6/…_lean.py::test_M6_L7_…` | n_a reason prefix `angle_fit_not_confirmed` allowed | §6.4 exporter rule (tester 221 N1) |
Unchanged on purpose: `M6_E3`, `M6_E4` keep `dropped_total <= 1e-12` — their circuits measure 0 and $3.7\times10^{-13}$; nothing is loosened where it is not needed.

**New.**
| Id (file) | What | Tolerance / limit | Justification |
|---|---|---|---|
| `M5_DT1` (`m5/test_rishon_det.py`) | link det operator, eigenvalues, SU(2) invariance, U(1) breaking | $10^{-12}$ | $16\times16$ matrices with entries in $\{0,\pm\tfrac12,\pm1,2\}$, at most 4 products |
| `M5_DT2` | $H_D^{\rm in}$ vs own construction; spectrum; commutators; sign symmetry; `hamiltonian_inner` | $10^{-12}$ entries; $[H_D,H_E]$ exactly 0 (integer × dyadic); $\|[H_D,H_B]\|_2=16\sqrt2$ to $10^{-9}$; spectra $10^{-10}$ | integer-entry matrices; `eigvalsh` / SVD error $\sim10^{-13}$ on norms $\le25$ |
| `M5_DT3_targets` ×3, `M5_DT3_trotter_orders` | $U_D$, three-layer orders, `eta=None` bit-identical, $U_2^n$ identity; slopes | $10^{-10}$ (1296-dim exponentials by two routes, error $\sim10^{-14}$); $10^{-12}$ for $[U_D,U_E]$ and `eta=0.0`; separations $>10^{-2}$ (true 1.6); slopes within 0.05 of 2 and 3 | measured slope deviations 0.006 at $dt=0.05\to0.025$ (8× margin); integer orders differ by 1 |
| `M5_DT4_det_layer_circuit` ×3, `…_three_layer_step` ×2, `…_physical_cross_check_and_compose` | circuits exact on 1296 codes; ceilings CX $\le32$, rotations $\le8$; sign; orders; additivity; 273-state cross-check | `tol_err` $10^{-10}$, Gauss $10^{-10}$ (METHODS §6, unchanged); rejections $>10^{-3}$ / $10^{-2}$ (true $\ge1.6$); counts exact | ceilings = the general gadget of §4 (a cheaper circuit still passes) |
| `M5_DT5` | sector structure, own code-level computation vs `det_sector_structure` | integers exact; leaving weight $\le10^{-9}$ | measured $5.8\times10^{-11}$ (sum of $5\times10^5$ squared amplitudes); a real violation is $O(1)$ |
| `M5_DT6` ×3 + spectrum | observables and closed spectrum vs the own $17\times17$ model | $10^{-10}$; $P(1)=0$ and `eta=0.0` to $10^{-12}$ | 1296-dim vs 17-dim exponentials (as M5-O1) |
| `M5_DT7` ×4 | det results files | schema; validity numbers as above; `dropped_total` $\le10^{-11}$ | definitions |
| `M5_V2` (`m5/test_rishon_prune_cap.py`) | constant 0.1; rccx-ladder $U_B$ `ok` with $10^{-12}<$ `dropped_total` $\le10^{-11}$; threshold at 0.9× / 1.1× the measured bound; shared verdict untouched; wrong circuit still `error` | constant exact; band factors 2.3 and 4.4 around the measured $2.281\times10^{-12}$ | pins the rule and the cascade, not the rounding noise |
| `M5X_O2` ×2 (`m5x/test_rishon_outer_det_row.py`) | 12-link det row certificate, own per-link operators, sparse run on 24 seeded valid codes, 6 mutants; results file | bound $\le10^{-10}$ (measured $4\times10^{-15}$); own operators $10^{-12}$; amplitudes $10^{-10}$; $10^{-7}$ mutant in $[2\times10^{-8},2\times10^{-7}]$ (measured $5.0\times10^{-8}$); wrong sign $\ge1$ (measured 13.2) | as M5x-O1 |
| `M6_H3`, `M6_H4` (`m6/test_rishon_m6_three_layer.py`) | eta set definition and det-layer metrics; headline + det layer = three-layer step at the three triples; additivity | integers exact; validity $10^{-10}$ / $10^{-11}$ / $10^{-10}$; Ross–Selinger band per rotation | definitions; rules in force |
| `M6_G5`, `M6_G6` | replay record; three-layer summary file | exact | definitions (§6.2, §5) |
| `M6_L9` (`m6/test_rishon_m6_lean.py`) | det layer certified / rejected / n_a; `recognise_angle_single` | statuses exact; 300 s | 4 gadgets × 1296 single-code inputs: milliseconds in the checker (as L3) |

## 9. What is invalidated, what is regenerated, what stays
**M5 (general circuits, Report 5).** Nothing is invalidated: every existing file under `results/rishon/` stays valid — as the two layers $U_E$, $U_B$ (independent of $\lambda_D$) and as the $\lambda_D=0$ limit of the step and of the observables. Not regenerated: `UE`, `UB`, `step`, `step_order2`, `UE_outer_row*`, `register_rows`, `observables`, `ks_projection`; counts 38 432 / 4 352 / 1 296; all M5/M5x Lean theorems; tag `milestone-5`. **New** (step D6): `UD.json`, `step3.json`, `step3_order2.json`, `UD_outer_row_certified.json`, `observables_det.json`. **Report 5 gets an addendum §3.8** (coordinator, from those files only): the model is now the SU(2) QLM with det coupling $\lambda_D$ (symbols of §2.1); table of the det layer and the three-layer steps (qubits, CX, rotations, $T$, verification); observables at the three triples next to the $\lambda_D=0$ values; closed spectra at $\lambda_D\in\{0,0.2,0.5\}$; the sector table of §2.5; the outer det row as a separate certified row; and one paragraph listing which earlier statements are $\lambda_D=0$ statements (431 conserved sectors, 15 zero levels, closed forms of the echo, the KS comparison). §2 and §5 of Report 5 get a one-line pointer to §3.8.
**M6.** Stale after Phase D and regenerated by the replay: `evaluator_sha256` of all 16 entries and of rounds 0–4, `compress/cache/<old hash>/`, `results/compress/rishon/{round-000…004.json, feedback/, robust.json, summary.json}`, `compress/archive/rishon/index.json`; re-rendered: `compress/specs/rishon-step.md`, `rishon-structure.json`, round-5 briefs. Changed verdicts: three round-0 seeds become valid; the "general" baseline of Report 6 gets a second row (cheapest valid seed = rccx ladder, about 6 870 CX: 228 CX is then about 30× fewer, and 44× fewer than the ccx-ladder general circuit). Statements in tester reports 217–221 about the margin to the cap ($\ge5.6\times$ below $10^{-12}$) become $\ge56\times$ below $10^{-11}$. **Not invalidated:** the 19 program files and their sha256, all keys and robust keys, the headline, families and ideation, proposer-session count, stop-rule counter, `spec_sha256`, the second-engine verifications of reports 217–221 (they test the physics, which is unchanged), the shared code hash and every other track. **Report 6 additions:** unit vs three-layer table (§6.1), the replay record, both baselines, the cap bookkeeping.

## 10. How the tests were checked
- `pytest --collect-only -q tests/acceptance`: 313 tests, clean. `python tools/check_lock.py`: `LOCK OK`. (`~/.claude/bin/acceptance-check` fails until the coordinator locks: uncommitted planner changes.)
- Without the shim (production as it is): the 32 new or changed tests → 31 fail, every one with a `PENDING:` message (no `AttributeError` / `TypeError` / import error), 1 passes (`M5_DT1`, pure link algebra that exists since M5). 1.6 s.
- With the shim (`PYTHONPATH=scratch/planner/shim204:. tools/pytest-safe -p shim204 -n 4 -m "slow or not slow" <ids>`, 263 s, 4 workers, < 4 GB each): 21 pass (all DT1–DT6, V2, O2 certificate, H3, H4); 5 are `PENDING` on result files, 3 on unbuilt modules (G5, G6, L9), G1 and S3 `PENDING` on the replay, and K2 fails on `909 == 9090` (the production budget not yet updated) — the intended reason.
- Slowest tests with the shim: `DT4_three_layer_step` 95 s each, `V2` 63 s, `H4` 63 s, `DT3_targets` 49 s each, `DT3_trotter_orders` 37 s. Non-slow m5 suite grows by about 3 min on 4 workers.
- Files my runs touched: `scratch/planner/*204*`, `scratch/planner/shim204/`, `scratch/planner/t204/`; no tracked file under `src/`, `results/`, `compress/`.

## 11. Do-not-retry list (additions to `prompts/203` §10)
- Calling the det coupling `gamma` / $\gamma$ in code, JSON, specs or reports.
- Putting $\eta$ into the loop's `TaskSpec`, the unit's target, `recognise_angle`, `Laurent3`, or the $(\alpha,\beta)$ `ANGLE_SET`; a four-variable Lean checker.
- Editing or monkey-patching `src/su2plaq/evaluate/*` or `src/su2plaq/compress/*` for the cap (incl. overwriting `PRUNE_FRACTION` at run time).
- Editing archive entries in place to give them the new hash; re-ranking or re-parenting during the replay; counting the replay as a round.
- Editing a file of `RISHON_EVALUATOR_FILES` after the replay without planning a new replay.
- Placing the det layer after $U_B$ (error 1.6 at the nominal triple), or the outer det row inside a circuit judged by the inner-block verdict (it writes the outer register).
- Anchoring the outer-det-row phase at the type-$A$ code (its target entry $\cos2\eta$ vanishes at $\eta=\pi/4$).
- Regenerating the existing M5 result files, or changing `scripts/m5_results.py`.
- Loosening `M6_E3` / `M6_E4`, or any tolerance not listed in §8.

## 12. Risks, stop conditions, optional follow-ups
- **Replay changes a key or loses an entry** (`lost != []` or `key_equal` false): stop, call `fixer`; if it is not a code bug → **ask Digonto** (it would contradict "the looser cap cannot invalidate").
- **A seed stays `pruning_bound` under the 10 % cap** (rounding differs on this machine): allowed by S3 ("as judged"); report the number. If `dropped_total` of an *archive* entry exceeds $10^{-11}$: stop and ask.
- **Soundness contradiction** (inner block `ok`, Gauss sample above tolerance) on a det circuit: stop and ask (as `prompts/203` §11).
- **`DT5` block counts differ** from 31 870 / 4 976 / 305 in the test's own computation: the test is then wrong, not the code — stop and ask (any agent believing a locked test wrong must stop).
- **Lean:** if the det-layer certificate cannot reuse the checker (e.g. the JSON reader rejects the provenance key), record `n_a` for the det layer and ask the planner; it never blocks rounds.
- **Stop and ask Digonto** also for: a physics value or range for $\lambda_D$; whether the det layer should be hand-optimised.
- Optional follow-ups (not planned, need Digonto's yes): (i) a joint link layer $U_DU_E$ per link (saves the shared parity CX: $-8$ CX on the general three-layer step, not available for a compressed unit); (ii) Hamming-weight phasing of the 8 equal rotations (about 4 rotations fewer, i.e. about $-250$ T, for Toffolis and extra CX; against the CX-first key).

## 13. Expected cost
Builder: D1 1 call; D2 1–2; D3 1–2; D4 1; D5 1; D6 1; C1 1–2; C4 as `prompts/203` + 1. Run time: Phase D acceptance (new non-slow ids) ≈ 4–5 min on 4 workers, peak < 4 GB per worker; `scripts/m5_det_results.py` ≈ 30–40 min (two general-size synthesised re-verifications at $\varepsilon=10^{-6}$, ≈ 300–600 s each; T tables), ≤ 2.5 GB; replay ≈ 45–110 min wall (round 0 ≈ 22 min with a warm gridsynth cache, up to 100 min cold; rounds 1–4 ≈ 2–3 min each + one robust-cache rebuild ≈ 100 s), ≤ 2.5 GB, background; `three_layer` CLI ≈ 1–2 min. Tester: one report for D1–D5, one for D6/D7 gate, one for the replay.

## 14. Decisions taken by default (for Digonto to confirm or override) and open questions
Defaults:
1. Symbols $\lambda_D$ (Hamiltonian) and $\eta$ (angle); $\gamma$ stays the $\sqrt2\beta$ slot.
2. $H_D=+\sum_\ell(\det U_\ell+\det U_\ell^\dagger)$ with coefficient 1 (BCW / Wiese form); sign immaterial.
3. Nominal $\eta=0.29$, alternates 0.53 and 1.07; tables at $\lambda_D\in\{0,0.2,0.5\}$.
4. Det term on all 12 links; the 8 outer ones as a separate, exactly commuting, certified row outside the main counts (mirrors the outer electric row).
5. Step orders of §2.3 (det layer between the electric and magnetic layers; symmetric halves for order 2).
6. Compression unit unchanged; det layer in front, general gadget (32 CX, 8 rotations), not sent through the proposer loop.
7. Cap applied by re-judging inside `rishon.verify`; the `dirty_ancilla` / `leak` label rule for circuits above the old cap.
8. Replay with the old files moved to `pre-204` folders (nothing deleted).
9. `M6_E3` / `M6_E4` keep the stricter $10^{-12}$; `S3` keeps the "as judged" form.
10. Mini-gate M5d with tag `milestone-5d`; Report 5 addendum §3.8 instead of a rewritten report.
11. Lean: det layer through slot reuse; three-layer exactness by composition as a documented argument.
12. File numbers 204 / 203 follow the track range given by the coordinator (`next-num` proposed 401).
Open questions:
- Which $\lambda_D$ (or $\lambda_D/g^{-2}$ range) does Digonto want in the physics tables?
- Report 6 headline: quote the unit (228 CX), the three-layer step (260 CX), or both (default: both)?
- Is hand optimisation of the det layer wanted later (it is 37 % of the three-layer $T$ count: 496 of 1 342)?

## 15. Coordinator
Run `~/.claude/bin/acceptance-lock "prompts/204-rishon-det-term-amendment.md"` (LOCK.json is already updated by hand for the nine files: `m5/test_rishon_metrics.py`, `m5/test_rishon_det.py` (new), `m5/test_rishon_prune_cap.py` (new), `m5x/test_rishon_outer_det_row.py` (new), `m6/test_rishon_m6_spec.py`, `m6/test_rishon_m6_seeds.py`, `m6/test_rishon_m6_gate.py`, `m6/test_rishon_m6_lean.py`, `m6/test_rishon_m6_three_layer.py` (new)); reset the counters in STATUS; record §14 under Decisions / For Digonto; copy the "requested laptop change no longer needed" note into `notes/merge-notes-rishon.md` (M6 item 3, the `prune_fraction` keyword, is superseded by §3); start step D1.

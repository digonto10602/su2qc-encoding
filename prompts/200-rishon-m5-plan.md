# 200 — M5 plan: rishon (quantum link model) encoding, general one-Trotter-step circuit → Report 5

Date: 2026-11-06 · Author: planner (Claude Fable 5.1, high) · Git commit at writing: `7dd1326` (branch `m5-rishon`, clone `~/Projects/su2qc-rishon`)
Trigger: desktop track R kickoff (`~/Projects/su2qc-desktop-package/START_HERE.md` §5; plan 001 §3 M5/M6 and its "Exact per encoding" row). No prior failures.
Plan in force for M5 = this file on top of `prompts/002` + addenda `003`–`006` (all conventions, tolerances and the Lean trust levels there stay binding). Research: `reports/research/200-rishon-qlm-model-and-verification.md`. Methods: `docs/METHODS-rishon.md` (never `docs/METHODS.md`). Locked tests: `tests/acceptance/m5/` (this run; the coordinator locks with `python tools/lock.py m5` and `acceptance-lock`).
File ownership (binding, START_HERE §0 rules 4–6): track R writes only `src/su2plaq/encodings/rishon.py`, `src/su2plaq/circuits/rishon.py`, `src/su2plaq/rishon/*`, `tests/unit/test_rishon_*.py`, `scripts/m5_*.py`, `results/rishon/`, `lean/Su2Plaq/Rishon/`, `lean/Su2PlaqCert/Rishon/`, `lean/certs/rishon-*.lean`, import lines in `lean/Su2Plaq.lean` / `lean/Su2PlaqCert.lean`, `docs/METHODS-rishon.md`, `docs/report-5-rishon-*.md`, `notes/merge-notes-rishon.md`. **M5 must not import `su2plaq.compress.*`.**

## 0. Environment and commands (exact)
```bash
source ~/anaconda3/etc/profile.d/conda.sh && conda activate su2qc-coding
cd ~/Projects/su2qc-rishon && export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
taskset -c 10-19 pytest -n 10 tests/unit                                  # after every edit
taskset -c 10-19 pytest -n 10 -m "not slow" tests/acceptance/m5           # step acceptance; -k M5_B1 etc.
taskset -c 10-19 pytest -n 10 tests/acceptance                            # milestone gate (m0, m1, m5; m2 may be PENDING)
taskset -c 10-19 pytest --collect-only -q tests/acceptance                # must stay clean
source ~/.elan/env && cd lean && taskset -c 10-19 lake build Su2Plaq.Rishon.Counts   # never rebuild Structure/Counts.lean on purpose
graphify update .                                                          # after code changes
```
Memory ≤ 15 GB per job (a Lean file importing Mathlib takes ~9 GB RSS).

## 1. Method (summary; equations and sources in `docs/METHODS-rishon.md`, derivations in research 200)

* **Model (decided).** SU(2) quantum link model, two fermionic rishons per link (6-state link space, BCW hep-th/9704106 Sec. 4; Wiese 1305.1602 Sec. 4.3), $U_{ij}=c_{L,i}c^\dagger_{R,j}$, $L_a=c_L^\dagger T_ac_L$, $R_a=c_R^\dagger T_ac_R$, $T_a=\sigma_a/2$; SU(2) Gauss law $G^a_c=\sum_{\rm ends}c^\dagger T_ac$ only; $H=\tfrac{g^2}2H_E+\tfrac1{g^2}H_B$, $H_E=\sum_\ell\tfrac12\sum_a(L_a^2+R_a^2)$ ($=j(j+1)$: $0,0,\tfrac34$ on types $A,B,Q$), $H_B=-(\mathrm{Tr}U_P+{\rm h.c.})$; determinant coupling $\gamma=0$ (defined, not built). $U_E(\alpha)$, $U_B(\beta)$, step orders, nominal $(0.37,0.61)$ and alternates $(0.91,0.23),(1.70,1.00)$ as METHODS §2.
* **Register.** 48 qubits: link $\ell$ at qubits $4\ell..4\ell+3=(L_1,L_2,R_1,R_2)$, JW $c_k=(\prod_{m<k}Z_m)\sigma^-_k$; `d` = qubits 0–15, `o` = 16–47; link codes $A$=`1100`(3), $B$=`0011`(12), $Q$=`1010`(5),`0110`(6),`1001`(9),`0101`(10); 1296 inner codes; outer far ends fixed (type $Q$: far colour 1). Link bilinears are string-free (4-qubit local), end bilinears 2-qubit local.
* **Physical space.** 38 432 states (corner kernels × link types), closed sector 4352 = $2^8\times17$, 431 U(1) sectors (U(2) sector 2192), inner span = all 1296 codes.
* **Targets.** Inner operators on the 1296 codes: $U_E^{\rm in}=\mathrm{diag}(e^{-i\frac34\alpha\,\#Q})$, $U_B^{\rm in}=e^{-i\beta H_B^{\rm in}}$ with $H_B^{\rm in}=-\sum_{p=1}^{81}\kappa_p(|u_p\rangle\langle v_p|+{\rm h.c.})$, $\kappa\in\{1^{\times32},2^{\times48},4\sqrt2^{\times1}\}$; closed bright block couplings $4,4$.
* **Verification.** `rishon.verify.verify`: laptop `evaluate` on the **inner view** (certifies all 38 432 states for outer-blind circuits; first order) + sampled rishon Gauss check (17 closed + 256 seeded states); `outer_read_unsupported` if an outer qubit is read (M6 block-wise path). Tolerances unchanged (prompts/003–005).
* **Shared observables vs KS.** $E_{\rm link}(n)$, $P(n)=\langle\mathrm{Re\,Tr}U_P\rangle$ ($P(1)\equiv0$ in both theories), Loschmidt echo $\mathcal L(n)$, closed-sector spectrum; definitions METHODS-rishon R5, values research 200 §8.

## 2. Interface (the builder implements exactly these names; stubs raising `NotImplementedError` first; the locked tests import them through `_api.api`)

### 2.1 `su2plaq.rishon.algebra` — one link, 4 modes, 16×16 complex matrices
```python
N_MODES = 4; LINK_QUBITS = ("L1", "L2", "R1", "R2")
T_SPIN: list[np.ndarray]                       # sigma_a / 2
def jw_annihilation(k: int, n_modes: int) -> np.ndarray      # c_k = (prod_{m<k} Z_m) sigma^-_k, little-endian, 2^n x 2^n
class RishonLink:                              # cached singleton semantics are fine
    c: list[np.ndarray]; cdag: list[np.ndarray]            # modes 0..3 = L1 L2 R1 R2
    def U(self, i: int, j: int) -> np.ndarray              # c_{L,i} c^dag_{R,j}
    def Udag(self, i, j) -> np.ndarray
    L: list[np.ndarray]; R: list[np.ndarray]               # 3 generators each, T_a normalisation
    N: np.ndarray; T_bcw: np.ndarray                       # rishon number; N_R - N_L
    casimir_L: np.ndarray; casimir_R: np.ndarray
    det_U: np.ndarray
    sector: np.ndarray                                     # int64 [3, 5, 6, 9, 10, 12] (N = 2 codes, sorted)
    def link_type(self, code: int) -> str | None           # 'A' | 'B' | 'Q' | None (invalid)
    def end_generator(self, a: int, end: str) -> np.ndarray   # 4x4 matrix of L_a ('L') or R_a ('R') on the end's two qubits (bit 0 = colour 1)
CODE_A, CODE_B, CODES_Q = 3, 12, (5, 6, 9, 10)
def embed_link_op(M16: np.ndarray, link: int, n_links: int) -> scipy.sparse.csr_matrix   # kron embedding, link 0 least significant
def global_bilinear(k: int, l: int, n_modes: int) -> np.ndarray   # c_k c_l^dag with the GLOBAL JW on n_modes (for the string-freeness test)
```
### 2.2 `su2plaq.rishon.physical` — basis, counts, Gauss
```python
LINK_TYPES = ("A", "B", "Q"); N_QUBITS = 48; N_DATA = 16; N_OUTER = 32
def near_shift(link: int) -> int                # qubit index of the near end's first qubit (inner links: L end = 4*link)
def far_shift(link: int) -> int
def corner_kernel(types_roles: tuple[tuple[str, str], ...]) -> tuple[list[list[int]], np.ndarray, tuple[float, ...]]
    # ((type, role),)*4 in Corner.ends order ('out' = L end, 'in' = R end); returns (end code lists, kernel vectors [D,k] real orthonormal, J labels of ends 0,1), phase: first max-modulus component positive
@dataclass class RishonBasis:
    diagram: Diagram; labels: list[tuple[tuple[str,...], tuple[float,...]]]   # (types of the 12 links, (J_0..J_3))
    keys: list[np.ndarray]; amps: list[np.ndarray]                             # 48-bit int64 COO per state
    dim: int                                                                   # 38432
    def index(self, label) -> int
    @staticmethod def inner_key(keys) -> np.ndarray; @staticmethod def outer_key(keys) -> np.ndarray   # keys & 0xFFFF, keys >> 16
    def u1_charges(self, k: int) -> tuple[int, int, int, int]                  # Q_c = sum of end occupations at corner c (near ends of outer links included)
def rishon_basis() -> RishonBasis                   # cached; builds all 38432 states (≈ 1 min budget)
def count_by_fusion() -> dict                        # {"dim": 38432, "closed": 4352, "n_u1_sectors": 431, "u2_sector": 2192, "type_patterns": int}  — combinatorial, no states built
def counts(basis) -> dict                            # same keys from the built basis + {"coo_entries": int, "max_components": int}
def closed_indices(basis) -> list[int]               # the 17 closed reference states (outer links near-end-empty), vac_A first, vac_B second, loop third
def sample_indices(basis, n: int = 256, seed: int = 20261104) -> list[int]      # seeded, distinct, excludes the closed reference states
def gauss_residuals_coo(keys_list, amps_list) -> np.ndarray      # per state, max over corners and a of ||G^a_c psi|| with the 2-qubit end generators (48-bit keys)
def gauss_residual(keys, amps) -> float
def inner_span(basis) -> np.ndarray                  # (1296, r) orthonormal basis of the span of inner components over all states and outer patterns (r = 1296 expected)
def inner_span_rank_by_corners() -> int              # corner factorisation (research 200 §5), no states built
```
### 2.3 `su2plaq.rishon.operators` — inner operators (1296×1296)
```python
def inner_codes() -> np.ndarray                      # sorted int64, 6^4 = 1296 valid 16-bit data codes
def plaquette_W_inner() -> np.ndarray                # Tr(U_b U_r U_t^dag U_l^dag) restricted to inner codes (real)
def h_electric_inner() -> np.ndarray                 # diagonal vector, 3/4 per Q link
def h_magnetic_inner() -> np.ndarray                 # -(W + W^dag)
def gauss_inner(corner: int, a: int) -> np.ndarray   # inner-end part of G^a_c on the 1296 codes
def heights(code: int) -> tuple[int, int, int, int]
def bright_pairs() -> list[tuple[np.ndarray, np.ndarray, float]]   # (u, v, kappa) with H_B^in = -sum kappa (|u><v| + h.c.); u, v real unit vectors on the 1296 codes, sign: first max-modulus component positive; sorted by (kappa, first support index)
def dark_codes() -> np.ndarray
def inner_target(kind: str, alpha: float | None, beta: float | None, order: int = 1) -> np.ndarray   # 'UE' | 'UB' | 'step' (orders 1, 2), unitary 1296x1296
def closed_block(g2: float) -> np.ndarray            # 3x3 in (vac_A, loop, vac_B)
def closed_codes() -> tuple[int, int, np.ndarray]     # (code of vac_A, code of vac_B, 16 loop codes) as inner 16-bit integers
def det_term_inner() -> np.ndarray                   # sum_l (det U_l + h.c.) on the inner codes (defined, gamma = 0 in M5)
```
### 2.4 `su2plaq.encodings.rishon`
```python
NOMINAL_ANGLES["rishon"] = (0.37, 0.61)   # do NOT edit encodings/base.py: define RISHON_NOMINAL = (0.37, 0.61) in this module
class RishonEncoding(Encoding): name = "rishon"; n_data = 16; n_outer = 32; is_basis_encoding = False
    registers = {"d": [0..15], "o": [16..47], "link_b": [0,1,2,3], "link_r", "link_t", "link_l", "outer_0": [16..19], ..., "outer_7": [44..47]}
    basis: RishonBasis                                    # NOT a KS PhysicalBasis (duck-typed; the laptop evaluator's Gauss path is never used)
    def inner_codes(self) -> np.ndarray                   # = operators.inner_codes()
    def physical_vectors(self, which: str = "all", n_sample: int = 256, seed: int = 20261104) -> EncodedBasis   # 'all' (38432), 'closed' (17), 'sample' (17 closed + n_sample seeded); codes = 48-bit (data | outer<<16)
    def decode(self, code: int) -> tuple[str, ...] | None        # 12 link types or None (invalid: wrong weight, far end not fixed)
    def decode_state(self, codes, amps) -> tuple[np.ndarray, np.ndarray]   # identity on valid codes (keys are the codes), raises ValueError on invalid
    def inner_target(self, kind, alpha, beta, order=1) -> np.ndarray      # = operators.inner_target
    def target(self, kind, alpha, beta, order=1, states: list[int] | None = None) -> np.ndarray
        # states=None -> raises ValueError("the 38432-dim physical target is never materialised; use inner_target or pass states");
        # states -> <Psi_k'|(V_in ⊗ 1)|Psi_k> for k, k' in states (exact matrix elements)
    def inner_view(self) -> "RishonInnerView"
    def layout_of(self, qc) -> Layout                    # as twelve: register 'd' (16) / 'o' (32) / rest ancilla
    def describe(self) -> str; def import_map(self, source) -> dict | str   # every source -> reason string (no external rishon circuits)
class RishonInnerView:   # encoding-like object for the laptop evaluator (prompts/002 §2.7 duck typing)
    name = "rishon_inner"; n_data = 16; n_outer = 32; is_basis_encoding = True; registers = same as RishonEncoding
    def inner_codes(self) -> np.ndarray; def physical_vectors(self) -> EncodedBasis   # 1296 single-code states, outer bits 0
    def layout_of(self, qc) -> Layout; def decode_state(self, codes, amps)            # identity
```
### 2.5 `su2plaq.circuits.rishon`
```python
N_DATA, N_OUTER = 16, 32
def build_UE(alpha: float, with_outer: bool = False, include_outer_electric: bool = False) -> QuantumCircuit   # registers d[16] (+ o[32]); parity trick (METHODS-rishon R7); metadata {"kind":"UE","alpha":alpha}
def build_UB(beta: float, with_outer: bool = False) -> QuantumCircuit    # registers d (+ o) then ancillas; allowed gates only (BASIS ∪ MACROS of prompts/002 §2.10; no native mcx ≥ 3, no unitary); exact at every beta; metadata {"kind":"UB","beta":beta,"n_pairs":81}
def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False) -> QuantumCircuit
def pair_frames(beta: float) -> list[dict]        # design data per bright pair: {"kappa", "pivot", "controls", "frame_gates"}; used by build_UB and reported
```
### 2.6 `su2plaq.rishon.verify`
```python
@dataclass class RishonVerdict: ok: bool; reason: str; certified: bool; op_norm_error: float; block_error: float; leak_amplitude: float; dropped_total: float; max_leak: float; dirty_ancilla: float; phase: complex; gauss_residual: float; gauss_states: int; outer_bits_read: int; method: str; engine: str; seconds: float; tolerances: dict; failing_inputs: list; inner_verdict: Verdict | None; extra: dict
def verify(qc, enc: RishonEncoding, kind: str, alpha: float | None, beta: float | None, order: int = 1, *, tol_err: float = 1e-10, tol_gauss: float | None = None, gauss: bool = True, gauss_sample: int = 256, seed: int = 20261104, engine: str = "auto", cap: int = 5_000_000, target: np.ndarray | None = None) -> RishonVerdict
    # 1. layout + outer reads via evaluator.classify_outer_gates -> reason 'outer_read_unsupported' if any outer qubit is read; 'writes_outer' if written
    # 2. inner_verdict = evaluate(qc, enc.inner_view(), target or enc.inner_target(kind, alpha, beta, order), gauss=False, tol_err=tol_err, engine=engine, cap=cap); copies block_error, leak_amplitude, dropped_total, op_norm_error, certified, engine, phase, max_leak, dirty_ancilla, failing_inputs
    # 3. if gauss: one sparse run_batch of the inner codes (reason 'unsimulable_gauss' if SimCapExceeded), outputs of closed_indices + sample_indices assembled per outer pattern, gauss_residual via physical.gauss_residuals_coo; tol_gauss None -> 1e-10
    # reason: inner_verdict.reason if not ok, else 'gauss' if residual > tol_gauss, else 'ok'; method = 'inner_block'
def physical_cross_check(qc, enc, kind, alpha, beta, order=1, states: list[int] | None = None) -> dict   # {"max_abs_diff", "n_states", "phase"}: explicit A on the sample vs enc.target(..., states)
def synth_tolerances(n_rot, eps) -> dict          # re-export of evaluator.synth_tolerances
```
### 2.7 `su2plaq.rishon.observables`
```python
def ks_closed_block(g2: float) -> np.ndarray      # 2x2 from METHODS §4 (for the table; independent of exact.operators)
def closed_spectra(g2_list=(0.5, 1.0, 2.0)) -> dict   # {"rishon": {g2: {"eigenvalues": [...], "multiplicities": [...]}}, "ks": {...}} per outer singlet choice
def observables(alpha: float, beta: float, n_steps: int = 2, order: int = 1) -> dict
    # {"rishon": {n: {"E_link", "P", "echo"}}, "ks": {...}} computed from operators.inner_target restricted to the closed codes and from exact.operators.target on the KS closed states
def closed_forms(alpha, beta) -> dict             # n = 1 closed forms (METHODS-rishon R5)
def observables_table(angles=((0.37,0.61),(0.91,0.23),(1.70,1.00))) -> dict   # the Report-5 table, JSON-able
```
### 2.8 `scripts/m5_results.py` → `results/rishon/{UE,UB,step}.json` (+ `step_order2`, `UE_outer_row`, `observables.json`, `register_rows.json`)
Schema as prompts/002 §2.11 with `verification` = `RishonVerdict` fields (plus `inner_verdict` nested), `extra["register_variants"] = {"jw_4_per_link": 48, "codeword_3_per_link": 36, "touched": 16}`, `extra["physics"] = {"dim": 38432, "closed": 4352, "u2_sector": 2192, "inner_span_rank": 1296, "bright_pairs": 81}`.

### 2.9 Lean (`lean/Su2Plaq/Rishon/Counts.lean`, `lean/Su2Plaq/Rishon/JW.lean`, `lean/Su2PlaqCert/Rishon/HB.lean`, `lean/certs/rishon-hb-structure.lean`; `su2plaq.rishon.lean_export`)
```lean
-- Su2Plaq.Rishon.Counts (import Su2Plaq.Structure.Counts; kernel decide)
def zeros (n : Nat) : Nat; def rishonTotal : Nat; def rishonClosed : Nat
theorem card_rishon_physical : rishonTotal = 38432 := by decide +kernel
theorem card_rishon_closed : rishonClosed = 4352 := by decide +kernel
-- Su2Plaq.Rishon.JW (computable; decide)
def FOp (n : Nat) := Fin (2^n) → Option (Fin (2^n) × Int)     -- signed partial permutation (monomial operator)
def jwC (n k : Nat) : FOp n; def jwCdag (n k : Nat) : FOp n; def comp ...; def anticomm ...
theorem car_4 : ∀ k l, anticommutator (jwC 4 k) (jwCdag 4 l) = delta k l  (as a decidable Bool-valued statement over Fin 4 × Fin 4)
theorem car_8 ...; theorem bilinear_string_free_8 : ∀ k l ∈ link 1, comp (jwC 8 k) (jwCdag 8 l) = embed 1 (comp (jwC 4 (k-4)) (jwCdag 4 (l-4)))
theorem sector_card : (weight-2 strings of Fin 16).card = 6; theorem u_ladder : U maps A → Q, Q → B ∪ {0}, B → 0; theorem det_u_sector : detU = 2 |B><A| on the sector; theorem end_bilinear_local ...
-- Su2PlaqCert.Rishon.HB (Mathlib-free computable checker over Z[√2] pairs) : def checkHB (cert : HBCert) : Bool
-- lean/certs/rishon-hb-structure.lean : theorem rishon_hb_structure : checkHB rishonHBCert = true := by native_decide
```
```python
# su2plaq.rishon.lean_export
RISHON_COUNT_THEOREMS = ("Su2Plaq.card_rishon_physical", "Su2Plaq.card_rishon_closed"); RISHON_JW_THEOREMS = (...)   # the locked names of 2.9
def export_hb_certificate(out_path) -> pathlib.Path    # 4u_p, 4v_p as integer pairs (a, b) meaning a + b√2; kappa as pairs; W as integer entries
def write_hb_lean(cert_path, out_path) -> pathlib.Path  # generates lean/Su2PlaqCert/Rishon/HBData.lean + lean/certs/rishon-hb-structure.lean
def check_hb(lean_file, timeout=900) -> dict           # {"status": "certified" | "rejected" | "error", "axioms": set, "seconds"} via su2plaq.lean.project.lake(["env", "lean", ...]) and print_axioms
```

## 3. Milestone M5 — steps (each row = one builder call; tester verifies the listed ids; commit after PASS)

| Step | Builds | Done-check (tester) | Acceptance ids (`tests/acceptance/m5/`) |
|---|---|---|---|
| 5.0 | stubs for every name in §2 (`NotImplementedError`), `src/su2plaq/rishon/__init__.py`, `tests/unit/test_rishon_*.py` skeleton; `docs/METHODS-rishon.md` already written (planner) | `pytest --collect-only -q tests/acceptance` clean; `pytest tests/acceptance/m5` fails only with `PENDING:` | — |
| 5.1 | `rishon/algebra.py` | BCW Eq. 4.1 relations exact (≤ 1e-13); sector codes; Casimirs; det U; string-freeness vs global JW on 8 and 12 modes | `test_rishon_algebra.py::test_M5_D1_link_algebra`, `::test_M5_D1_string_free_and_sector` |
| 5.2 | `rishon/physical.py` (corner kernels, basis, counts, Gauss, sample, inner span) | 38 432 by `count_by_fusion` and by the built basis; closed 4352; U(2) sector 2192; Gauss ≤ 1e-10 on all states (production) and on a sample with the test's independent operators; inner span rank 1296 | `test_rishon_physical.py::test_M5_C1_counts_two_routes`, `::test_M5_C1_states_gauss_orthonormal`, `::test_M5_C1_inner_span_full` |
| 5.3 | `rishon/operators.py` (+ `observables.py` closed blocks) | $W$ equals the test's independent construction (1e-12); hermitian, real; $[W,G^{\rm in}]=0$; heights +1; spectrum multiplicities; 81 pairs, κ multiset, alphabet; closed block 4, 4; `inner_target` unitary, compositions | `test_rishon_operators.py::test_M5_X1_plaquette_structure`, `::test_M5_X1_bright_pairs_and_closed_block`, `::test_M5_X1_inner_target_properties` |
| 5.4 | `encodings/rishon.py` (`RishonEncoding`, `RishonInnerView`) | codec bijection on 1296 codes; outer codes; `physical_vectors('all')` = 38 432 unit vectors, orthogonal on a sample, Gauss via production ≤ 1e-10; `target(states=closed)` unitary 17×17 | `test_rishon_codec.py::test_M5_C1_encoding_codec_and_vectors` |
| 5.5 | `rishon/verify.py`, `rishon/observables.py` complete | sensitivity: identity accepted as `UE(0)`; X on an ancilla → `dirty_ancilla`; Z on a data qubit → error; X on outer → `writes_outer`; CZ(outer, inner) → `outer_read_unsupported`; synth tolerances re-exported | `test_rishon_verify.py::test_M5_B1_verifier_sensitivity`; `test_rishon_observables.py::test_M5_O1_*` |
| 5.6 | `circuits/rishon.build_UE` | exact on the 1296 codes at two α (1e-10); phase of $|Q\rangle$ is $e^{-3i\alpha/4}$; 8 CX, 4 rotations; outer row | `test_rishon_circuits.py::test_M5_E1_electric_step` |
| 5.7 | `circuits/rishon.build_UB` (+ `pair_frames`) | exact on the 1296 codes at β ∈ {0.61, 0.23, 1.00, 2.0} (1e-10), leak ≤ 1e-10 as amplitude, ancillas clean, Gauss sample ≤ 1e-10, `outer_bits_read = 0` with `o` present, allowed gates only; independent check in the test with `run_batch` + `encoded_block` | `::test_M5_B1_magnetic_inner_block`, `::test_M5_B1_physical_with_outer_and_gauss` |
| 5.8 | `build_step` | orders 1, 2 at nominal + alternate (1e-10); wrong order rejected | `::test_M5_S1_step_orders` |
| 5.9 | metrics + T(ε) tables; synthesised circuits re-verified through `verify` with `synth_tolerances` | bands; Qiskit CT within 10 %; synthesised UE/UB/step certified | `test_rishon_metrics.py::test_M5_T1_t_table_and_synth_verify` |
| 5.10 | `scripts/m5_results.py`, `results/rishon/*.json` | files, schema, register rows, observables table | `test_rishon_results.py::test_M5_R1_results_files`, `::test_M5_R1_observables_and_register_rows` |
| 5.L1 | `lean/Su2Plaq/Rishon/Counts.lean` + import line in `lean/Su2Plaq.lean`; `rishon/lean_export.py` names | both theorems kernel-checked, standard axioms, no `native_decide`/`sorry`; `lake build Su2Plaq.Rishon.Counts` ≤ 600 s, ≤ 15 GB | `test_rishon_lean.py::test_M5_L1_counts_kernel_checked` |
| 5.L2 | `lean/Su2Plaq/Rishon/JW.lean` | the six JW/sector theorems by `decide`, standard axioms | `::test_M5_L2_jw_facts_kernel_checked` |
| 5.L3 | `lean/Su2PlaqCert/Rishon/HB.lean`, `HBData.lean` (generated), `lean/certs/rishon-hb-structure.lean`, `lean_export.export_hb_certificate/write_hb_lean/check_hb` | certificate accepted (`true`, one native axiom); tampered κ (2 → 1) rejected | `::test_M5_L3_hb_structure_certificate` (slow) |
| 5.11 | gate: tester full (m0, m1, m5, unit) → auditor → benchmark (`results/benchmarks/rishon-*`: basis build time, `verify` time on `build_UB`, `inner_target` time) → `git tag milestone-5` → `docs/report-5-rishon-general-circuit.md` (coordinator, from JSON; structure of Report 1 + §3.5 shared-observable table vs KS + §3.6 register rows incl. the 36-qubit codeword variant + outer-electric row + Lean status column) → bundle | — |

Order: 5.0 → 5.1 → 5.2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.7 → 5.8 → 5.9 → 5.10; the Lean steps 5.L1–5.L3 run in parallel with 5.4–5.9 (second builder allowed only in the Lean files). `graphify update .` after every builder step.

## 4. Acceptance tests and tolerances (why each number)

| Id | Tolerance | Justification |
|---|---|---|
| M5-D1 | 1e-13 | 16×16 matrices with entries in $\{0,\pm1,\pm\tfrac12,\pm\tfrac i2\}$; products of ≤ 4 such matrices are exact in float64 up to one rounding |
| M5-C1 counts | exact | combinatorial; three routes (fusion formula, built basis, KS labels × $2^{n_0}$) and Lean |
| M5-C1 Gauss / norm / Gram | 1e-10 / 1e-12 / 1e-12 | kernels from `eigh` on ≤ 16×16 (residual ~1e-15), products of 4 corners — as M0-X1 |
| M5-C1 inner span | rank exactly 1296, orthonormality 1e-10 | exact combinatorial fact (corner factorisation); SVD of a 1296×P matrix |
| M5-X1 $W$ vs independent | 1e-12 | two constructions of the same integer-entry sparse operator (entries 0, ±1) |
| M5-X1 commutators, hermiticity | 1e-12 | integer/half-integer matrices of size 1296 |
| M5-X1 spectrum, pairs, closed block | eigenvalues 1e-9, couplings 1e-12, counts exact | `eigh` on a 1296×1296 integer matrix (condition O(10)); couplings are exact integers (4) |
| M5-E1, B1, S1 | `op_norm_error` ≤ 1e-10 (block + leak amplitude + pruning), weights ≤ 1e-20, Gauss ≤ 1e-10 | exact-angle circuits; float64 over ≤ 10⁴ gates (~1e-13 amplitude); prompts/004 leak-as-amplitude; Gauss rule prompts/003 |
| M5-T1 | synthesised: `op_norm_error` ≤ $N_{\rm rot}\varepsilon+10^{-9}$, Gauss ≤ the same; bands as METHODS §7; Qiskit CT within 10 % | triangle inequality over rotations (prompts/003 §2, 004); two gridsynth implementations |
| M5-O1 | closed forms vs matrix exponentials 1e-12; production vs test 1e-10 | 2×2 / 3×3 exact blocks; `expm` on tiny matrices |
| M5-R1 | schema exact; verification numbers as E1/B1/S1 | definitions |
| M5-L1/L2 | exact (kernel) | theorems |
| M5-L3 | exact (native); build ≤ 900 s | certificate check is integer-pair arithmetic; compiled |
No tolerance differs from prompts/002–005. The only new acceptance quantity is the sampled Gauss residual on 273 states (17 closed + 256 seeded, seed 20261104); its tolerance is the binding Gauss rule.

## 5. Do-not-retry list
* Dense $38\,432\times38\,432$ targets, or the laptop `evaluate` with `physical_vectors('all')` (needs > 20 GB) — the inner view is the method.
* Building $U_B$ as a product formula of the 16 Pauli-expanded hopping terms (not exact; the target is the exact exponential).
* Qiskit native `mcx` with ≥ 3 controls, `mcrx`, `cu`, `unitary` in submitted circuits (prompts/002 §7).
* Editing `encodings/base.py` (`NOMINAL_ANGLES`) or any laptop-owned file; monkeypatching `gauss_residuals_coo`.
* Lean `decide` on the 1296-dim $H_B$ identity (kernel: hours) — native certificate only; `native_decide` outside `lean/certs/`.
* Rescaling β to match the KS closed-sector coupling (the models differ; report raw values).
* Imposing the U(1) Gauss law or adding the det term to the targets in M5.

## 6. Risks and stop conditions
* **$U_B$ general circuit size/sparse simulability.** 81 pairs with multi-controlled rotations may give O(10³–10⁴) CX and many Hadamard frames; the sparse engine's cap (5·10⁶ amplitudes, 1296 inputs) may be hit if many frames are open at once → builder keeps frames local (apply $F_p$, rotate, $F_p^\dagger$ per pair) so at most ~4 branching qubits are open; `verify` falls back to aer_mps only for synthesised tolerances. If the general circuit cannot be verified by either engine: stop and ask.
* **Irrational angle $8\sqrt2\beta$** (closed block): fine numerically; Lean per-circuit certificate `n_a` until the laptop checker accepts a third base angle — recorded in `notes/merge-notes-rishon.md` as a requested feature, not a blocker.
* **Memory.** `rishon_basis()` holds 0.5 M COO entries (fine); never expand to dense per-outer-pattern blocks. Lean count file ~9 GB RSS: never build two Mathlib-importing files concurrently in this clone.
* **Laptop evaluator duck typing.** `evaluate` calls `enc.inner_codes()`, `enc.physical_vectors()`, `enc.layout_of()`, and (only with `gauss=True`) `enc.decode_state` / `enc.basis` — `verify` always passes `gauss=False`; a future laptop change to `_phys_data` could break the inner view → the unit tests pin the three calls; if a merge breaks them, the fix is a 3-line laptop diff (write it in the merge notes).
* **Stop and ask Digonto** when: a locked tolerance is believed wrong; the count 38 432 or the inner-span rank 1296 is contradicted by an independent computation; `build_UB` passes the inner-block check but a sampled Gauss residual exceeds tolerance with no bug found (would contradict the soundness theorem); the per-circuit Lean checker arrives with an incompatible interface.

## 7. Expected cost per step
5.1 ≈ 1 builder call (16×16 algebra, minutes). 5.2 ≈ 1–2 calls; `rishon_basis()` ≤ 60 s (prototype: 713 states/64 s with naive Python loops — vectorise over corner combos; target ≤ 60 s for all 38 432). 5.3 ≈ 1 call (W build 0.06 s, `eigh` 1296: 1 s). 5.4 ≈ 1 call. 5.5 ≈ 1–2 calls. 5.6 trivial. 5.7 ≈ 2–3 calls (the hard step; `verify` on the general circuit ≈ 10–120 s sparse). 5.8–5.10 ≈ 1 call each. Lean: 5.L1 one call (8 s decide); 5.L2 1–2 calls; 5.L3 2 calls. M5 acceptance suite target: < 10 min excluding slow tests on 10 cores.

## 8. Report 5 (`docs/report-5-rishon-general-circuit.md`, coordinator, from `results/rishon/*.json` only)
Sections as Report 1: 1 what was asked; 2 what was done (model decision with the two citations, register, verification method with the certified/sampled statement); 3 results at (0.37, 0.61): 3.1 exactness (inner block on 1296 codes = all 38 432 states; Gauss on 273 sampled outputs), 3.2 gates (48 qubits; 16 touched; ancillas), 3.3 T counts (ε grid) + outer-electric row, 3.4 **shared observables vs KS** (table of METHODS-rishon R5 at the three angle pairs, $n=1,2$; closed-sector spectra at $g^2\in\{0.5,1,2\}$ with multiplicities), 3.5 register rows (JW 48 / codeword 36 / touched 16), 3.6 Lean status (counts kernel-checked, JW facts kernel-checked, $H_B$ structure native-certified, per-circuit `pending laptop checker; n_a for U_B (angle 8√2β)`); 4 physics findings (two singlets per link, 4352-fold vacuum degeneracy, $W$ as a simultaneous raising operator, 81 bright pairs, $P(1)\equiv0$ identity, U(1) sectors); 5 problems and assumptions (γ = 0, far-end fixing, normalisation factor 4 vs 1).

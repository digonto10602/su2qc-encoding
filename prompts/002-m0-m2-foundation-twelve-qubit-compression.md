# 002 — Executable plan for M0 (foundation), M1 (12-qubit general circuit), M2 (compression machinery + first loop)

> Amended 2026-11-04 by `prompts/003-gauss-tolerance-synthesised-circuits-engine-policy.md` (Gauss tolerance of synthesised circuits = N_rot·ε + 1e-9; `evaluate(..., tol_gauss=None)`, `synth_tolerances`, `Verdict.tolerances`; aer_mps certification policy; M0-E5/M1-P1/M1-T1 amended). This file remains the plan in force.

Date: 2026-11-04 · Commit at writing: `067a22f` · Author: planner (kickoff)
Supersedes `prompts/001-plaquette-five-encodings-plan.md` for M0–M2 only; M3–M10 stay as written there (§10 below).
Trigger: kickoff of the physics loop (STATUS "Next action"); no prior failures. Research: `reports/research/001-plaquette-kickoff-spin-network-6j-tcount-conventio.md`. Methods: `docs/METHODS.md` (written with this plan). Locked tests: `tests/acceptance/{conftest.py,m0/,m1/,m2/}`.

## 0. Environment and commands (exact)

```bash
source /home/digimonk/anaconda3/etc/profile.d/conda.sh && conda activate coding   # python 3.12.14, qiskit 2.5.2, qiskit-aer 0.17.2, pygridsynth 1.2.0, numpy 2.5.2, scipy 1.18.0, sympy 1.14.0, pytest 9.1.1, xdist 3.8.0
cd /home/digimonk/Projects/su2qc-encoding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1      # also set in tests/acceptance/conftest.py before numpy is imported
pytest -n auto tests/unit                                             # fast check after every edit (builder)
pytest -n auto tests/acceptance/m0                                    # milestone acceptance (tester); m1, m2 likewise; add -m "not slow" for the fast subset
pytest -n auto tests/acceptance/m0 tests/acceptance/m1 tests/acceptance/m2 tests/unit   # milestone gate, full
python tools/check_lock.py && ~/.claude/bin/acceptance-check          # lock integrity (tester, coordinator)
pytest --collect-only -q tests/acceptance                             # must collect without errors at every commit
```
`pytest.ini` (builder, step 0.1): `[pytest] testpaths = tests  pythonpath = src  addopts = -p no:cacheprovider  markers = slow: long-running (minutes)`. No `pip install` of the package is needed (`pythonpath = src`); `pygridsynth` must stay at 1.2.0 (`pip install --no-deps pygridsynth==1.2.0` if ever reinstalled).

## 1. Method (summary; equations and sources in `docs/METHODS.md`)

* Hamiltonian $H=\tfrac{g^2}{2}H_E+\tfrac1{g^2}H_B$, $H_E=\sum_{\ell}j_\ell(j_\ell+1)$, $H_B=-(\mathrm{Tr}\,U_P+\mathrm{Tr}\,U_P^\dagger)$, $U_P=U_bU_rU_t^\dagger U_l^\dagger$ (Paulo Eq. 16, $a=1$). $U_E(\alpha)=e^{-i\alpha H_E^{\rm inner}}$, $U_B(\beta)=e^{-i\beta H_B}$, $\alpha=g^2dt/2$, $\beta=dt/g^2$; Paulo's $\alpha_P=2\beta$. Step order 1: $U_B(\beta)U_E(\alpha)$ ($U_E$ first in the circuit); order 2: $U_E(\alpha/2)U_B(\beta)U_E(\alpha/2)$. Gate conventions: `p(λ)=diag(1,e^{iλ})`, `rz(θ)=diag(e^{−iθ/2},e^{iθ/2})`. Nominal $(\alpha,\beta)=(0.37,0.61)$; alternates $(0.91,0.23)$, $(1.70,1.00)$.
* Route A (reference): electric basis $|j,m_L,m_R\rangle$ (CG conventions), 433 physical states from corner singlets labelled by the inner-pair spin $J$; sparse COO; $H_B^{\rm phys}=-(\Psi^\dagger(W\otimes1)\Psi+{\rm h.c.})$.
* Route B (cross-check and the spin-network target): labels $(j_1..j_{12};J_0..J_3)$, plaquette $=\prod_{c}F^{J_c\,j_{p(c)}\,j_{n(c)}}_{\frac12\,j'_{n(c)}\,j'_{p(c)}}$ (4 recoupling symbols, Zache et al. arXiv:2304.02527 Eq. 2 specialised to the (inner \| outer) split), $47\times47$ inner matrix $K$; equals route A up to a diagonal $\pm1$ gauge (prototype: residual $3\cdot10^{-15}$).
* Paulo's link basis = CG basis conjugated by the signed permutation $V_P$: $|mm'\rangle_P=s(m)s(m')|\tfrac12,-m,-m'\rangle_{\rm CG}$.
* Evaluator: one global phase, op-norm error on the physical block, leak, ancilla cleanliness, block-diagonality in outer controls, Gauss residual. Metrics: our level-0 lowering; $T(\varepsilon)=T_{\rm fixed}+\sum_rT_r(\varepsilon)$ with pygridsynth, Qiskit CT pass manager as the second implementation, Ross–Selinger estimate $3\log_2(1/\varepsilon)$ per rotation beside it.
* Compression: Gu et al. loop (program = Python `build(spec) -> Builder`; MAP-Elites over $(\mathrm{CX},T_\varepsilon)$ cells; lexicographic key $(\mathrm{CX},T_{10^{-6}},\mathrm{depth},\mathrm{qubits})$).

## 2. Interface (the builder implements exactly these names; the locked tests import them)

Package root `src/su2plaq/` (`pythonpath = src`). All arrays `float64`/`complex128`; spins as Python floats (0.0, 0.5, 1.0); labels as tuples of floats. Qubit integers are **little-endian**: qubit $k$ = bit $k$ of the basis-state integer.

### 2.1 `su2plaq.geometry`
```python
@dataclass(frozen=True) class Link:   index: int; name: str; start: tuple[int,int]; end: tuple[int,int]; inner: bool; near_end: str | None  # 'L' (starts at its corner) or 'R' (ends there) for outer links, None for inner
@dataclass(frozen=True) class Corner: index: int; site: tuple[int,int]; ends: tuple[tuple[int,str], ...]  # ((link_index,'out'|'in'),)*4 in canonical order (inner_a, inner_b, outer_c, outer_d), inner/outer each by increasing link index
class Diagram:  links: list[Link]; corners: list[Corner]; loop: list[tuple[int,int]]   # [(0,+1),(1,+1),(2,-1),(3,-1)]
    def inner_links(self) -> list[int]; def outer_links(self) -> list[int]; def corner_of_end(self, link:int, role:str) -> int
def plaquette_diagram() -> Diagram
@dataclass class SplitGraph: sites: list[tuple[str,int]]; edges: dict[int, tuple[tuple[str,int], tuple[str,int]]]; loop_sites: list[tuple[str,int]]; virtual: dict[int,int]  # corner -> virtual edge index (12+c)
def point_split(d: Diagram) -> SplitGraph
```
Fixed data: links 0–3 = `b`=$U_1(0,0)$ (0,0)→(1,0), `r`=$U_2(1,0)$ (1,0)→(1,1), `t`=$U_1(0,1)$ (0,1)→(1,1), `l`=$U_2(0,0)$ (0,0)→(0,1); outer 4–11 = `o0`=$U_1(-1,0)$→(0,0), `o1`=$U_2(0,-1)$→(0,0), `o2`=$U_1(1,0)$ from (1,0), `o3`=$U_2(1,-1)$→(1,0), `o4`=$U_1(1,1)$ from (1,1), `o5`=$U_2(1,1)$ from (1,1), `o6`=$U_1(-1,1)$→(0,1), `o7`=$U_2(0,1)$ from (0,1). Corners 0–3 = (0,0),(1,0),(1,1),(0,1). `SplitGraph`: sites `('in',c)` (inner pair + virtual) and `('out',c)` (outer pair + virtual), 16 edges (0–11 real, 12+c virtual), `loop_sites = [('in',0),('in',1),('in',2),('in',3)]`.

### 2.2 `su2plaq.su2.algebra`, `su2plaq.su2.wigner`
```python
SIGMA: list[np.ndarray]; def spin_matrices(j) -> list[np.ndarray]; def m_values(j) -> list[float]; def clebsch_gordan(j1,m1,j2,m2,J,M) -> float
class LinkSpace:  # copy of su2qc-skqd src/skqd/su2.py (cite the source commit in the docstring)
    def __init__(self, jmax: float = 0.5); spins; states: list[tuple]; index: dict; dim: int
    def U(self) -> list[list[np.ndarray]]; def generators(self) -> tuple[list[np.ndarray], list[np.ndarray]]; def casimir(self) -> np.ndarray
PAULO_ORDER = ("0", "++", "+-", "-+", "--")
def paulo_U() -> list[list[np.ndarray]]        # Eq. 28 in PAULO_ORDER, colour index 0 ↔ +, 1 ↔ −
def paulo_adapter() -> np.ndarray              # V_P (5×5, entries 0/±1): V_P @ U_cg[i][j] @ V_P.T == paulo_U()[i][j]
# wigner
def triangle(a,b,c) -> bool; def six_j(a,b,c,d,e,f) -> float   # Racah closed formula, cached on 2x-integers; 0 for inadmissible args
def f_symbol(j1,j2,j12,j3,J,j23) -> float      # (-1)^{j1+j2+j3+J} sqrt((2j12+1)(2j23+1)) {j1 j2 j12; j3 J j23}
```

### 2.3 `su2plaq.exact.physical`
```python
def corner_singlets(js: tuple[float,float,float,float], roles: tuple[str,str,str,str]) -> tuple[np.ndarray, tuple[float,...]]
    # kernel of sum_a (sum_ends G_a)^2 on the product of the 4 end spaces (end order = js order; 'out' end carries L=-J^T, 'in' end carries R=+J),
    # columns = orthonormal real vectors sorted by the inner-pair Casimir eigenvalue J(J+1) of ends 0,1; phase: largest |component| positive. Returns (vectors[D,k], J labels).
@dataclass class PhysicalBasis:
    diagram: Diagram; jmax: float; convention: str                 # 'cg' | 'paulo'
    labels: list[tuple[tuple[float,...], tuple[float,...]]]       # ((j_0..j_11),(J_0..J_3)) per state, J by corner index
    keys: list[np.ndarray]; amps: list[np.ndarray]                # COO per state over the electric multi-index: key = sum_i s_i 5^i, s_i = LinkSpace index of link i in `convention`; far end of every outer link fixed to the first m value (+1/2 in 'cg')
    dim: int
    def index(self, label) -> int
    @staticmethod def inner_key(keys) -> np.ndarray; @staticmethod def outer_key(keys) -> np.ndarray   # keys % 625, keys // 625
def physical_basis(diagram: Diagram | None = None, jmax: float = 0.5, convention: str = "cg") -> PhysicalBasis   # cached per (jmax, convention)
def apply_link_op(keys, amps, link: int, M: np.ndarray) -> tuple[np.ndarray, np.ndarray]   # coalesced COO
def gauss_residual(basis: PhysicalBasis, keys, amps) -> float      # max over corners c and a of || sum_{ends of c} G_a psi ||  (G = L for 'out', R for 'in', in basis.convention)
def gauss_residuals(basis) -> np.ndarray                            # per physical state
def gram(basis) -> np.ndarray                                       # dim×dim overlaps
def counts(basis) -> dict   # {"dim", "closed", "link_strings", "ambiguous", "far_end_weighted"}
def s_o_support(basis) -> dict[int, np.ndarray]   # outer electric key -> sorted inner keys that occur
def s_o_dims(basis) -> dict[int, int]             # outer electric key -> rank of the span of the inner components over all states
def inner_span(basis) -> np.ndarray               # (625, r) orthonormal basis of span_o S_o
def to_convention(basis, convention: str) -> PhysicalBasis   # apply V_P per link (signed permutation of local indices)
```

### 2.4 `su2plaq.exact.operators`, `su2plaq.exact.spinnet`, `su2plaq.exact.compare`
```python
def plaquette_W(link: LinkSpace | None = None, convention: str = "cg") -> np.ndarray   # 625×625, Tr(U_b U_r U_t^† U_l^†); index = sum_l s_l 5^l, link 0 least significant
def h_electric_inner(basis) -> np.ndarray; def h_electric_outer(basis) -> np.ndarray   # diagonals, length dim
def h_magnetic_phys(basis, W: np.ndarray | None = None) -> tuple[np.ndarray, float]     # (-(Psi^†(W⊗1)Psi + h.c.), physical leak max_k | ||W psi_k||^2 - sum_k' |A_k'k|^2 |)
def hamiltonian_phys(basis, g2: float, include_outer_electric: bool = False) -> np.ndarray
def target(basis, kind: str, alpha: float | None = None, beta: float | None = None, order: int = 1, include_outer_electric: bool = False) -> np.ndarray
    # kind 'UE': diag(exp(-i α HE_inner)); 'UB': expm(-i β HB_phys); 'step': order 1 → UB @ UE, order 2 → UE(α/2) @ UB @ UE(α/2); dim×dim complex128 in basis order
# spinnet (route B)
def labels(diagram=None, jmax=0.5) -> list[tuple]      # same tuples as PhysicalBasis.labels; route-B enumeration by triangle rules at the 8 trivalent sites
def inner_labels(jmax=0.5) -> list[tuple]              # ((j_b,j_r,j_t,j_l),(J_0..J_3)), 47 at jmax=1/2
def plaquette_P(labels) -> np.ndarray                  # P[new, old] = prod_c f_symbol(J_c, j_p(c), j_n(c), 1/2, j'_n(c), j'_p(c)); corner pairs (p,n): c0 (l,b), c1 (b,r), c2 (r,t), c3 (t,l)
def K_inner(jmax=0.5) -> np.ndarray                    # -(P + P^T) on inner_labels
def h_magnetic_phys_6j(labels) -> np.ndarray           # -(P + P^T) on the full labels (433×433)
def h_electric_6j(labels, inner_only=True) -> np.ndarray
# compare
def gauge_align(A, B, tol=1e-9) -> tuple[np.ndarray | None, float]     # diagonal unitary D with A ≈ D B D^†; residual = max|A - D B D^†| (None, max||A|-|B|| if moduli differ)
def spectra_match(HE_A, HB_A, HE_B, HB_B, g2_list=(0.5, 1.0, 2.0)) -> float   # max |eigvalsh(g2/2 HE + HB/g2)_A − (…)_B|
def outer_block_structure(HB_phys, basis, K=None) -> dict   # {"max_offblock": float, "max_J_violation": float, "n_blocks": int, "worst_gauge_residual": float, "worst_abs_diff": float, "block_dims": list[int]}
```

### 2.5 `su2plaq.encodings.base`, `su2plaq.encodings.twelve`
```python
@dataclass class Layout: data: list[int]; outer: list[int]; ancilla: list[int]
@dataclass class EncodedBasis: codes: list[np.ndarray]; amps: list[np.ndarray]; n_data: int; n_outer: int   # per physical state, COO over the (data|outer) computational integer (data bits 0..n_data-1, outer bits n_data..n_data+n_outer-1)
class Encoding(Protocol):
    name: str; n_data: int; n_outer: int; registers: dict[str, list[int]]; is_basis_encoding: bool
    basis: PhysicalBasis                                   # route-A basis (CG) the targets are built from
    def inner_codes(self) -> np.ndarray                    # sorted int64 data-register codes that are valid (625 for twelve)
    def physical_vectors(self) -> EncodedBasis
    def decode(self, code: int) -> int | None              # (data|outer) integer -> electric key in self.basis.convention, None if invalid
    def target(self, kind: str, alpha: float, beta: float, order: int = 1) -> np.ndarray   # = operators.target(self.basis, …)
    def layout_of(self, qc: QuantumCircuit) -> Layout      # data = first n_data qubits; outer = qubits of register 'o' if present (must have n_outer qubits) else []; ancilla = the rest
    def describe(self) -> str                              # markdown register/codec table for the task spec
    def import_map(self, source: str) -> dict | str        # {"qubit_map": list[int], "angles": callable(alpha,beta)->dict, "fixed_angle": bool} or a reason string
NOMINAL_ANGLES = {"twelve": (0.37, 0.61)}; ALT_ANGLES = ((0.91, 0.23), (1.70, 1.00))
class TwelveQubit(Encoding):  name="twelve"; n_data=12; n_outer=16; is_basis_encoding=False
    LINK_CODE = {"0": 0b000, "++": 0b111, "+-": 0b110, "-+": 0b101, "--": 0b100}   # bits (q_j q_m q_m') with q_m' = bit 0, q_m = bit 1, q_j = bit 2 at qubits (3l, 3l+1, 3l+2); link l = 0..3 = b,r,t,l; Paulo basis
    OUTER_CODE: outer link k (0..7) at qubits (12+2k, 12+2k+1) = (q_m_near, q_j); j=0 → 00; j=1/2, m_near=+ → q_m=1; m_near=− → q_m=0   # Paulo basis, far end fixed
    registers = {"d": [0..11], "link_b": [0,1,2], …, "o": [12..27], "outer_0": [12,13], …}
    basis = physical_basis(convention="cg"); physical_vectors() uses to_convention(basis,"paulo") then the codecs above
```

### 2.6 `su2plaq.circuits.twelve`
```python
def build_UE(alpha: float, with_outer: bool = False) -> QuantumCircuit    # registers d[12] (+ o[16] if with_outer); p(-3α/4) on qubits 2,5,8,11; metadata {"kind":"UE","alpha":alpha}
def build_UB(beta: float, with_outer: bool = False) -> QuantumCircuit     # registers d[12] (+ o), p[4], e[4], w[7], g[3], tmp[3], h[1]; port of Paulo's notebook with alpha_P = 2β; only BASIS ∪ MACROS gates (mcrx expressed with rccx + crx + rccx on a clean ancilla or equivalent — no native mcrx/cu)
def build_step(alpha: float, beta: float, order: int = 1, with_outer: bool = False) -> QuantumCircuit
def paulo_logical(beta: float = 1.0) -> QuantumCircuit                   # faithful reconstruction of the notebook circuit (registers d p e w g tmp h; keeps its mcrx/crx and cu-free structure as in the notebook; alpha_P = 2β) — for cross-checks only (M1-P2), NOT an allowed-gate circuit
def paulo_circuit() -> QuantumCircuit                                     # refs/paulo/SU2_plaquette_jmax_half_CT.qpy (β = 1), registers renamed to d + ancillas
```
Register order in every circuit: `d` first (qubits 0–11), then `o` if present (12–27), then ancillas. Ancillas start and must end in $|0\rangle$.

### 2.7 `su2plaq.evaluate.sparse_sim`, `su2plaq.evaluate.evaluator`, `su2plaq.evaluate.aer_check`
```python
SIM_BASIS = ["x","z","s","sdg","t","tdg","h","sx","rz","p","u","cx","cz","cp","swap","ccx","ccz","unitary"]
@dataclass class Batch: keys: np.ndarray; cols: np.ndarray; amps: np.ndarray; n_qubits: int   # COO of all output states, cols = input index
class SimCapExceeded(RuntimeError)
def run_batch(qc: QuantumCircuit, inputs: np.ndarray, cap: int = 5_000_000) -> Batch   # inputs: int64 basis integers over qc.num_qubits (ancillas 0); raises SimCapExceeded when the number of stored amplitudes exceeds cap
def encoded_block(batch: Batch, codes: np.ndarray, n_inputs: int, code_mask: int) -> tuple[np.ndarray, np.ndarray]   # (M[len(codes), n_inputs], leak[n_inputs]); leak = weight of outputs with bits outside code_mask set or (key & code_mask) not in codes
class OuterWriteError(ValueError)
def classify_outer_gates(qc, layout: Layout) -> set[int]   # outer qubits touched by diagonal gates; raises OuterWriteError if any gate is non-diagonal on an outer qubit (numerical check, 1e-12)
def specialise(qc, read_qubits: set[int], pattern: int) -> QuantumCircuit   # resolve the read outer bits classically
@dataclass class Verdict: ok: bool; reason: str; op_norm_error: float; max_leak: float; dirty_ancilla: float; phase: complex; outer_bits_read: int; n_blocks: int; gauss_residual: float; method: str; engine: str; seconds: float; failing_inputs: list; n_inputs: int
def evaluate(qc, enc: Encoding, target: np.ndarray, *, tol_err: float = 1e-10, tol_leak: float = 1e-12, tol_gauss: float | None = None, gauss: bool = True, method: str = "auto", engine: str = "auto") -> Verdict   # tol_gauss None -> 1e-10 (exact-angle); synthesised circuits pass synth_tolerances(n_rot, eps) — AMENDED by prompts/003 §4 (also Verdict.tolerances, synth_tolerances)
    # engine 'sparse' = run_batch (COO); 'aer_mps' = qiskit-aer matrix_product_state per input (truncation threshold 0, Aer's memory estimate overridden with max_memory_mb, amplitudes by contracting save_matrix_product_state); 'auto' = sparse, falling back to aer_mps when SimCapExceeded. Verdict.engine records the engine used.
    # method 'inner_span' (only if no outer bit is read): ||(M − e^{iφ} V_inner) P_S||_2 with V_inner = the 625×625 inner operator and P_S = inner_span projector; 'physical': explicit A[k',k] = <psi_k'|U|psi_k> on the 433 states (required when outer bits are read); 'auto' = inner_span if possible else physical.
    # global phase φ = arg tr(V^† A) (one for the whole operator). reason ∈ {"ok","writes_outer","error","leak","dirty_ancilla","gauss","unsimulable","disallowed_gate"}; failing_inputs = up to 10 (label/index, error) pairs.
def inner_target(enc, kind, alpha, beta, order=1) -> np.ndarray   # 625×625 inner operator in the encoding's local basis order (for the fast path)
def aer_statevector_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int) -> tuple[np.ndarray, np.ndarray]   # same as encoded_block but through qiskit-aer statevector; qc.num_qubits ≤ 24
def aer_mps_block(qc, inputs: np.ndarray, codes: np.ndarray, code_mask: int, bond_dim: int | None = None) -> tuple[np.ndarray, np.ndarray, dict]   # per-input MPS run, exact (truncation 0); returns (M, leak, {"max_bond_dim", "seconds"}); never save_amplitudes
# run_batch applies qc.global_phase; gates are executed in a topological order of the circuit DAG chosen to keep few branching (h/sx/u/unitary) qubits open at once (optional heuristic; any topological order is exact)
```

### 2.8 `su2plaq.metrics.logical`, `su2plaq.metrics.cliffordt`
```python
LOGICAL_BASIS = ["cx","h","s","sdg","t","tdg","x","z","rz"]; SEED = 20261104
def lower(qc) -> QuantumCircuit                       # transpile(qc, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=SEED); raises on 'unitary'/'mcx(≥3)'/measure
def is_clifford_t_angle(theta, tol=1e-9) -> bool      # multiple of π/4
def logical_metrics(qc) -> dict   # {"cx","depth","n_rot","t_fixed","qubits","ancilla","gates","rz_angles"}; n_rot = rz not at multiples of π/4; t_fixed = t + tdg + rz at odd multiples of π/4; qubits = qc.num_qubits; ancilla = qubits − size of register "d" − size of register "o" (if present)
def ct_compile(qc, eps: float, level: int = 3, seed: int = 12345) -> tuple[QuantumCircuit, dict]   # Paulo's settings; dict {"cx","t","depth","qubits","gates"}
def pygridsynth_word(theta: float, eps: float) -> str; def pygridsynth_tcount(theta, eps) -> int; def word_error(word, theta) -> float   # min_phi ||U_word − e^{iφ} rz(θ)||_2
def t_estimate(n_rot: int, t_fixed: int, eps: float) -> float   # t_fixed + n_rot·3·log2(1/eps)
def synthesize(qc, eps: float) -> tuple[QuantumCircuit, dict]   # lower() first; rz at multiples of π/4 → exact S/T words; every other rz → its pygridsynth word (W dropped, X → H S S H); order of gates preserved; dict {"n_rot","t_rot","error_bound_sum","per_rotation":[…]}
def t_table(qc, eps_list=(1e-4,1e-6,1e-8,1e-10), qiskit: bool = True) -> list[dict]   # per eps: {"eps","t_fixed","n_rot","t_rot_pygridsynth","t_total","t_est","t_qiskit","cx_qiskit","depth_qiskit"}
```

### 2.9 `su2plaq.results.store`, `su2plaq.results.report`, `su2plaq.metrics.provenance`
```python
SCHEMA_VERSION = 1
RESULT_KEYS = ("schema_version","encoding","circuit_id","kind","params","provenance","verification","metrics","files","extra")
def provenance(seeds: dict | None = None) -> dict   # {"git_commit","git_dirty","versions":{"python","numpy","scipy","qiskit","qiskit_aer","pygridsynth"},"platform","cpu_count","seeds","timestamp_utc"}
def save_result(path, *, encoding, circuit_id, kind, params, verification, metrics, files=None, extra=None) -> pathlib.Path
def load_result(path) -> dict
def render(paths: list) -> str   # markdown table from JSON only; deterministic (same input → identical text)
```

### 2.10 `su2plaq.compress.*` (design B names; Qiskit `QuantumCircuit` is the circuit representation)
```python
# builder.py
BASIS = {"x","z","h","s","sdg","t","tdg","rz","p","cx","cz"}
MACROS = {"ccx","rccx","ccz","swap","ch","crz","crx","cp"}
MACRO_COST = {"ccx":(6,7,0),"rccx":(3,4,0),"ccz":(6,7,0),"swap":(3,0,0),"ch":(1,2,0),"crz":(2,0,2),"crx":(2,0,2),"cp":(2,0,3),"cz":(1,0,0)}   # (CX, T_fixed, N_rot) after level-0 lowering (measured, METHODS §7)
class BuilderError(Exception)
class Builder:
    def __init__(self, spec: TaskSpec | None = None, n_qubits: int | None = None)   # with spec: fixed qubits = data + outer of the encoding; bare builder: n_qubits fixed qubits (tests, library routines)
    def reg(self, name) -> list[int]; def alloc(self, n=1, name=None) -> list[int]; def free(self, qubits)
    def x/z/h/s/sdg/t/tdg(self, q); rz(self, theta, q); p(self, lam, q); cx(self, c, t); cz(self, a, b); ccx/rccx/ccz(self, a, b, t); ch(self, c, t); swap(self, a, b); crz/crx/cp(self, theta, c, t)
    def mcx(self, controls: list[int], target: int)      # ≤2 controls → cx/ccx; k≥3 → (k−2) rccx + ccx + (k−2) rccx on clean ancillas allocated internally
    def append_qiskit(self, qc: QuantumCircuit, qubit_map: list[int])   # only BASIS ∪ MACROS gates; anything else (native mcx ≥ 3, mcrx, cu, unitary, measure, …) → BuilderError
    def discover(self, line: str)   # at most 3 lines; the 4th raises BuilderError
    def circuit(self) -> QuantumCircuit; peak_qubits: int; discoveries: list[str]
# spec.py
@dataclass class TaskSpec: encoding: str; kind: str; alpha: float; beta: float; order: int = 1; alt_angles: tuple = ALT_ANGLES; tol_err: float = 1e-10; tol_leak: float = 1e-12; eps: float = 1e-6; eval_budget_s: float = 300.0; support_cap: int = 5_000_000; max_qubits: int | None = None; cell_k: int = 8; trial_inputs: int = 64; trial_seed: int = 0
    def sha256(self) -> str; def render(self) -> str; def write(self, path=None) -> pathlib.Path   # compress/specs/<encoding>-<kind>.md
    def with_angles(self, alpha: float, beta: float) -> TaskSpec   # copy with other nominal angles (skeleton checks)
def default_spec(encoding: str = "twelve", kind: str = "step") -> TaskSpec
# oracle.py
def target(spec) -> np.ndarray; def column(spec, j: int | tuple, top: int = 20) -> list[tuple[int, complex]]   # (row, value) sorted by |value| descending
def element(spec, i, j) -> complex; def codec(spec) -> str; def block(spec, outer_pattern: int) -> np.ndarray   # unitary block of the target on the states with that outer electric pattern (pattern 0 = closed, 2×2)   # + CLI: python -m su2plaq.compress.oracle --encoding E --target step|ub|ue [--column j] [--element i j] [--codec] [--block o]
# evaluate.py
@dataclass class ProgramResult: valid: bool; reason: str; verdict: Verdict | None; verdicts_alt: list; skeleton_equal: bool; metrics: dict | None; program_sha256: str; wall_s: float; discoveries: list[str]; summary: str
def load_program(path) -> module   # importlib; checks the contract (build, SUMMARY:)
def skeleton(qc) -> list[tuple]    # (gate name, qubit tuple) per instruction after level-0 lowering of macros? NO: on the Builder circuit as emitted (params ignored)
def evaluate_program(path, spec: TaskSpec, mode: str = "full") -> ProgramResult   # 'trial': trial_inputs physical inputs (seeded), nominal angles, t_estimate; 'full': all states, 3 angle pairs, skeleton check, pygridsynth
def evaluate_circuit(qc, spec, mode="full") -> ProgramResult   # same checks for an already-built circuit (seeds, baselines)
# metrics.py
def metrics(qc, spec, measured: bool = True) -> dict   # {"cx","t_fixed","n_rot","t_eps","t_estimate":{eps: t_fixed + 3 n_rot log2(1/eps) for eps in (1e-6, 1e-10)},"synth_error_bound","depth","depth_ct","qubits","gates"}; qubits = qc.num_qubits (data + outer + ancillas); measured=False → t_eps from the estimate, no gridsynth
# synth.py
def gridsynth_T(theta: float, eps: float) -> int   # = metrics.cliffordt.pygridsynth_tcount, cached on disk under compress/cache/gridsynth/
def key(m: dict) -> tuple; def cell(m: dict, k: int = 8) -> tuple; INVALID_KEY = (inf, inf, inf, inf)
# passes.py, baselines.py
def polish(qc, spec) -> tuple[QuantumCircuit, list[str]]   # optional deterministic passes; returns the input unchanged if nothing is strictly better and still valid
def general_circuit(spec) -> QuantumCircuit; def general_program_path(spec) -> pathlib.Path   # compress/programs/<enc>/seed/000-general.py (the general circuit, with the outer register, expressed through Builder)
def qiskit_l3(spec, seed: int = 12345) -> QuantumCircuit
@dataclass class SeedCircuit: qc: QuantumCircuit; source: str; fixed_angle: bool; alpha: float | None; beta: float | None; kind: str; can_be_parent: bool
def import_seed(spec, source: str) -> SeedCircuit | str          # sources "paulo34" (fixed angle β = 1, kind UB), "lean22_v2", "spinnet15"; a str = reason why not applicable
def evaluate_seed(spec, seed: SeedCircuit, mode: str = "full") -> ProgramResult   # fixed-angle seeds: target at the seed's own angles/kind, no alternate angles (synthesised tolerances N_rot·ε)
# archive.py, provenance.py
@dataclass class Entry: id: str; program_path: str; program_sha256: str; parent: str | None; family: str; round: int; valid: bool; reason: str; key: tuple; cell: tuple; metrics_raw: dict; metrics_polished: dict | None; verdict_nominal: dict; verdicts_alt: list; skeleton_equal: bool; discoveries: list; summary: str; evaluator_sha256: str; spec_sha256: str; git_commit: str; versions: dict; seeds: dict; machine: str; wall_s: float; written_utc: str
class Archive:  @classmethod def load(cls, encoding, root=None) -> Archive; def insert(self, entry) -> bool (False and untouched if invalid); def elites(self) -> dict[tuple, Entry]; def best(self) -> Entry | None; def family_best(self, f) -> Entry | None; def save(self); def entries(self) -> list[Entry]
def entry_from_result(result: ProgramResult, *, program_path: str, family: str, round: int, parent: str | None) -> Entry
def code_hash(files: list[pathlib.Path] | None = None) -> str   # sha256 over an explicit list of evaluator/physics source files (default list in provenance.EVALUATOR_FILES)
def cache_path(evaluator_sha, program_sha, spec_sha, root=None) -> pathlib.Path   # <root>/compress/cache/<evaluator_sha>/<program_sha>-<spec_sha>.json
# brief.py, run_candidate.py, round.py, report.py
def make_ideation_brief(encoding, kind, root=None) -> pathlib.Path; def make_brief(encoding, kind, round: int, family: str, root=None) -> pathlib.Path   # brief text contains the line "Rewrite the parent to improve the key; return the complete program"
# CLIs: python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step [--trial|--full] [--json out.json]
#       python -m su2plaq.compress.round --encoding twelve --kind step --seed | --round r --evaluate [--dry-run]
#       python -m su2plaq.compress.report --encoding twelve --kind step [--out path]
def run_round(encoding, kind, round: int, evaluate: bool, dry_run: bool = False, root=None, proposals: list[str] | None = None) -> dict   # round 0: seeds (general, general+polish, Qiskit L3, external); round r: evaluate the proposals (default: new programs under compress/programs/<enc>/*/); writes <root>/results/compress/<enc>/round-rrr.json, appends <root>/compress/attempts/<enc>.jsonl and discoveries/<enc>.md; returns {"round","n_valid","n_invalid","best_key","entries":[ids]}; dry_run = no git interaction, root may be a temporary directory
def report_table(encoding, kind, root=None) -> str   # markdown with columns qubits | CX | T_fixed | N_rot | T(1e-6) | T_est(1e-6) | T(1e-10) | depth | verdict | entry; rows general, general+polish, Qiskit L3, seeds, best per family, global best; also writes <root>/results/compress/<enc>/summary.json
```
Program contract (`compress/programs/<enc>/<family>/NNN-slug.py`): the file starts with the module docstring whose first line is `SUMMARY: …`, optional `DISCOVERY: …` lines (≤3); `FAMILY = "…"; PARENT = "…" | None`; `def build(spec) -> Builder`. Programs may import `su2plaq.compress.oracle` and `numpy`; nothing else from the project.

### 2.11 Results JSON (one per circuit, `results/<enc>/<circuit_id>.json`)
`schema_version, encoding, circuit_id, kind, params{alpha,beta,order}, provenance{…}, verification{ok,reason,op_norm_error,max_leak,dirty_ancilla,phase,outer_bits_read,n_blocks,gauss_residual,method,seconds,n_inputs}, metrics{logical{cx,depth,n_rot,t_fixed,qubits,ancilla}, t_table:[…], macro_counts}, files{qpy,qasm3,sha256}, extra{}`.

## 3. Milestone M0 — foundation (each row = one builder call; tester verifies the listed ids)

| Step | Builds | Done-check (tester) | Acceptance ids (`tests/acceptance/m0/`) |
|---|---|---|---|
| 0.1 | `pyproject.toml` (name `su2plaq`, no install needed), `pytest.ini` (§0), `src/su2plaq/__init__.py` + **stubs for every name in §2 raising `NotImplementedError`**, `tools/lock.py`, `tools/check_lock.py` (from su2qc-qcadvantage, SHARED list = `tests/acceptance/conftest.py`, `tests/acceptance/_api.py`, `tools/check_lock.py`, `tools/lock.py`), `refs/paulo/` copies (notebook, qasm, qpy, metadata, gate file + `SOURCE.md` with sha256), `tests/unit/` skeleton, `.gitignore` additions (`compress/cache/`, `results/**/tmp`) | `pytest --collect-only -q tests/acceptance` collects; `pytest -n auto tests/acceptance/m0` fails only with `PENDING:`/`NotImplementedError`; `python tools/check_lock.py` OK after the coordinator locks | — |
| 0.2 | `geometry.py` | counts and roles as §2.1 | `test_geometry.py::test_M0_G1_diagram`, `::test_M0_G2_point_split` |
| 0.3 | `su2/algebra.py` (+`paulo_U`, `paulo_adapter`), `su2/wigner.py` | commutators ≤ 1e-12 at jmax ½ and 1; $V_P$ residual ≤ 1e-14; 6j vs sympy ≤ 1e-13 | `test_algebra.py::test_M0_A1_link_algebra`, `::test_M0_A2_six_j_vs_sympy`, `::test_M0_A3_paulo_adapter` |
| 0.4 | `exact/physical.py` | 433 states, counts 2/256/95/17362, Gauss ≤ 1e-10, Gram ≤ 1e-12, `to_convention` round trip | `test_physical.py::test_M0_C1_dimension`, `::test_M0_C2_closed`, `::test_M0_C3_link_strings`, `::test_M0_C4_ambiguous`, `::test_M0_C5_far_end_weighted`, `::test_M0_C6_jmax1_count_slow` (slow), `::test_M0_X1_gauss_and_gram` |
| 0.5 | `exact/operators.py` | $H_B^{\rm phys}$ hermitian, leak ≤ 1e-10, closed block, `target` unitary and composition rules | `test_operators.py::test_M0_X2_plaquette_leak`, `::test_M0_X3_hermitian_and_electric`, `::test_M0_X7_closed_block`, `::test_M0_X8_target_properties` |
| 0.6 | `exact/spinnet.py`, `exact/compare.py` | spectra A vs B ≤ 1e-10; block structure; gauge residual ≤ 1e-10 | `test_spinnet.py::test_M0_X4_spectra_A_vs_B`, `::test_M0_X5_outer_block_structure_and_J`, `::test_M0_X6_gauge_align_K` |
| 0.7 | `evaluate/sparse_sim.py`, `evaluate/aer_check.py` | vs Aer (≤ 12 qubits) and dense `Operator` (≤ 8) ≤ 1e-12 | `test_sparse_sim.py::test_M0_E1_vs_aer`, `::test_M0_E2_vs_dense_operator` |
| 0.8 | `encodings/base.py`, `encodings/twelve.py` **codec + physical_vectors + layout_of only** (needed by the evaluator tests), `evaluate/evaluator.py` | sensitivity cases (identity, X on ancilla, Z on data, CX inner→outer, CZ(outer,inner), outer-dependent block, block-dependent phase) | `test_evaluator.py::test_M0_E3_sensitivity`, `::test_M0_E4_outer_control_blocks`, `::test_M0_E5_gauss_of_outputs` |
| 0.9 | `metrics/logical.py`, `metrics/cliffordt.py` | macro table; pygridsynth band + word error ≤ ε; Qiskit CT within ±6 and deterministic; `synthesize` re-verifies | `test_metrics.py::test_M0_M1_macro_costs`, `::test_M0_M2_pygridsynth_band`, `::test_M0_M3_qiskit_ct_pm` |
| 0.10 | `results/store.py`, `results/report.py`, `metrics/provenance.py` | schema keys; commit = `git rev-parse --short HEAD`; `render` idempotent | `test_results.py::test_M0_R1_results_json_and_report` |
| 0.11 | `docs/METHODS.md` cross-check (builder adds nothing new; coordinator reviews), `graphify update .`, STATUS | gate: tester full → auditor → benchmark (`reports/benchmarks`: route A build time, evaluator time on the 625-code identity circuit) → tag `milestone-0` | — |

Expected cost per step: route A build ≈ 2 s (prototype 1.3 s), full route A/B comparison ≈ 20 s, evaluator fast path on a 3000-gate 34-qubit circuit ≈ 1–5 s (sparse COO, 625 inputs batched), pygridsynth ≈ 0.1 s per rotation; M0 suite < 3 min on 8 cores excluding the slow test (jmax = 1 route B count, ≈ 1–2 min).

## 4. Milestone M1 — 12-qubit encoding, general circuit → Report 1

| Step | Builds | Done-check | Ids (`tests/acceptance/m1/`) |
|---|---|---|---|
| 1.1 | `encodings/twelve.py` complete (`inner_codes`, `decode`, `target`, `describe`, `import_map` for `paulo34`, `lean22_v2`, `spinnet15`→reason string) | bijection; 433 vectors norm 1; Gauss via decode ≤ 1e-10 | `test_twelve_codec.py::test_M1_C1_codec_and_vectors` |
| 1.2 | `circuits/twelve.build_UE` | ≤ 1e-10 at two α; single-link phase $e^{-3i\alpha/4}$ | `test_twelve_circuits.py::test_M1_E1_electric_step` |
| 1.3 | `circuits/twelve.build_UB` (port; $\alpha_P=2\beta$; macros only) | exact on 625 codes at β ∈ {0.4, 1, 2}, leak ≤ 1e-12 | `::test_M1_B1_magnetic_inner_block` |
| 1.4 | physical verification with the outer register (`with_outer=True`, method `physical`) | ≤ 1e-10 on 433 states, leak ≤ 1e-12, ancillas clean, Gauss ≤ 1e-10, `outer_bits_read = 0` | `::test_M1_B2_physical_states`, `::test_M1_B3_gauss_outputs`, `::test_M1_B4_outer_blind_and_clean` |
| 1.5 | `build_step` | orders 1 and 2 ≤ 1e-10 | `::test_M1_S1_step_orders` |
| 1.6 | `paulo_circuit()`, `paulo_logical(β)`, `aer_mps_block` + `engine="aer_mps"` in the evaluator; Paulo cross-checks | his QPY (β = 1): error ≤ 2e-5, leak ≤ 1e-9 (planner measured 2.9e-6 with Aer MPS, 139 s); `paulo_logical(1.0)` exact on 625 codes, $T_{\rm fixed}=296$, 294 CX, 14 rotations, compiled with his settings within 5 % of `_metadata.json` | `test_twelve_paulo.py::test_M1_P1_paulo_qpy_verifies` (slow), `::test_M1_P2_port_reproduces_counts` |
| 1.7 | metrics + T(ε) table for $U_E$, $U_B$, step; synthesised circuits re-verified | bound holds; pygridsynth vs Qiskit T within 10 % | `test_twelve_metrics.py::test_M1_T1_t_table_and_synth_verify` |
| 1.8 | outer-control analysis (`s_o_dims`, `inner_span`) | 6561-entry table (zeros allowed); rank reported; two computations agree | `test_twelve_outer.py::test_M1_O1_outer_dont_care_table` |
| 1.9 | `results/twelve/{UE,UB,step}.json` + `reports/…` Report 1 (coordinator writes the report from `render`) | files exist, schema OK, numbers traceable | `test_twelve_results.py::test_M1_R1_results_files` |

## 5. Milestone M2 — compression machinery + first loop → Report 2

| Step | Builds | Done-check | Ids (`tests/acceptance/m2/test_compress_machinery.py::`) |
|---|---|---|---|
| 2.0 | **Coordinator:** `~/.claude/agents/proposer.md`; guard-hook `WRITE_ALLOW["proposer"]` (already present in `~/.claude/hooks/guard.py` as `["compress/programs/", "compress/ideation/", "scratch/"]` — verify); roles-table row | piped fake PreToolUse JSON: proposer `Write` to `src/x.py` denied, to `compress/programs/twelve/F1/001-x.py` allowed | — |
| 2.1 | `compress/spec.py`, `compress/oracle.py` (+CLI), `compress/specs/TEMPLATE.md` | oracle column == target column | `test_oracle_matches_exact_step` |
| 2.2 | `compress/builder.py` | gate check; macro costs == level-0 lowering; `mcx` library routine | `test_builder_gateset`, `test_macro_costs_match_lowering`, `test_builder_mcx_chain` |
| 2.3 | `compress/evaluate.py`, `compress/metrics.py`, `compress/synth.py`, `compress/provenance.py` | 7 sensitivity cases; metrics == Qiskit counts; T band; determinism | `test_evaluator_accepts_general_circuit`, `test_evaluator_accepts_global_phase`, `test_evaluator_rejects_wrong_gate`, `test_evaluator_rejects_dirty_ancilla`, `test_evaluator_rejects_angle_error`, `test_evaluator_rejects_partial`, `test_evaluator_rejects_control_change`, `test_metrics_match_qiskit_count_ops`, `test_t_eps_in_ross_selinger_band`, `test_t_eps_deterministic`, `test_t_estimate_formula` |
| 2.4 | `compress/archive.py`, cache | round trip; elites = min key per cell; invalid never inserted; cache keyed by code hash | `test_archive_roundtrip_and_elites`, `test_archive_rejects_invalid`, `test_cache_keyed_by_code_hash`, `test_entry_has_provenance_fields` |
| 2.5 | `compress/passes.py`, `compress/baselines.py`, general program `compress/programs/twelve/seed/000-general.py`, `round.py --seed` | polish valid and not worse; L3 baseline valid; seeds declared | `test_polish_valid_and_not_worse`, `test_qiskit_l3_baseline_valid`, `test_seed_import_declared`, `test_skeleton_angle_independent_general` |
| 2.6 | `compress/run_candidate.py`, `compress/brief.py`, `round.py --evaluate`, `report.py`, `compress/briefs/TEMPLATE.md` | `--trial` < 10 s; dry round end to end; report table | `test_run_candidate_cli_trial_and_full`, `test_round_dry_run_end_to_end`, `test_report_table_from_results` |
| 2.7 | **Run the loop** on `twelve`/`step` (protocol in prompts/001 §4; ≤ 6 rounds, ≤ 5 proposers per round) | archive best valid; key ≤ round-0 best; tester re-verifies with Aer on a ≤ 24-qubit specialisation (or the sparse simulator with a second seed subset if the best has > 24 qubits) | gate: `test_archive_best_valid_and_not_worse_than_seed` |
| 2.8 | Report 2 (coordinator, from `report_table` + results JSON) | — | — |

Task-specification hand-text (Gu et al. Extended Data Fig. 1 structure) — `compress/specs/TEMPLATE.md` renders this with the numbers filled from `TaskSpec`:

> **Task.** Implement $U=U_B(\beta)\,U_E(\alpha)$ (electric layer first) for the SU(2) plaquette at $j_{\max}=\tfrac12$ in the 12-qubit encoding, exactly (up to one global phase) on every one of the 433 physical states, at $(\alpha,\beta)=(0.37,0.61)$ and, with the same gate skeleton, at $(0.91,0.23)$ and $(1.70,1.00)$. Unphysical inputs are don't-care. Every ancilla you allocate must be returned to $|0\rangle$ on physical inputs.
> **Registers.** Data `d[0..11]`: link $l\in\{b,r,t,l\}$ at qubits $(3l,3l+1,3l+2)=(q_{m'},q_m,q_j)$; codes $|0\rangle\to000$, $|{+}{+}\rangle\to111$, $|{+}{-}\rangle\to110$, $|{-}{+}\rangle\to101$, $|{-}{-}\rangle\to100$ (bits $q_jq_mq_{m'}$); 001/010/011 unused. Outer controls `o[0..15]`: outer link $k$ at $(12+2k,12+2k+1)=(q_m,q_j)$; the target never changes them; you may read them (diagonal gates only). Physical states are superpositions of inner codes entangled with the outer register (`oracle --codec`, `oracle --block o`).
> **Circuit model.** Gates `x z h s sdg t tdg rz p cx cz` and macros `ccx rccx ccz swap ch crz crx cp` with costs (CX, T, rotations): ccx (6,7,0), rccx (3,4,0), ccz (6,7,0), swap (3,0,0), ch (1,2,0), crz (2,0,2), crx (2,0,2), cp (2,0,3), cz (1,0,0). `Builder.alloc/free` for clean ancillas; `Builder.mcx` for ≥3 controls; no measurement; emission-time classical computation (including oracle queries) is allowed.
> **Correctness.** op-norm error ≤ $10^{-10}$ on the physical block after one global phase; leak (weight outside the physical span or on any ancilla ≠ 0) ≤ $10^{-12}$; identical skeleton at the three angle pairs; evaluation wall ≤ 300 s. The evaluator is ground truth.
> **Cost.** Key $(\mathrm{CX},\,T_{10^{-6}},\,\mathrm{depth}_{\rm CT},\,\mathrm{qubits})$, lexicographic. $T_\varepsilon=T_{\rm fixed}+\sum_r T_r$, $T_r$ measured with pygridsynth at $\varepsilon=10^{-6}$ (≈ 62–64 per rotation); estimate $3\log_2(1/\varepsilon)$ per rotation. MAP-Elites cells $(\lfloor8\log_2(\mathrm{CX}+1)\rfloor,\lfloor8\log_2(T_\varepsilon+1)\rfloor)$.
> **Tools.** `python -m su2plaq.compress.run_candidate <program.py> --encoding twelve --kind step --trial` (seconds; 64 physical inputs, nominal angles, T estimate) / `--full`; `python -m su2plaq.compress.oracle --encoding twelve --kind step [--column j] [--element i j] [--codec] [--block o]`. Write ONE program to `compress/programs/twelve/<family>/NNN-slug.py` with `SUMMARY:` and ≤ 3 `DISCOVERY:` lines.

## 6. Acceptance tests and tolerances (why each number)

| Id | Tolerance | Justification |
|---|---|---|
| M0-A1 | 1e-12 | closed-form CG, ≤ 20 float64 operations per entry |
| M0-A2 | 1e-13 | rationals × square roots, two independent closed formulas |
| M0-A3 | 1e-14 | signed permutation: exact up to one rounding |
| M0-C1–C6 | exact | combinatorial |
| M0-X1 | Gauss 1e-10, Gram 1e-12 | kernels from `eigh` on ≤ 16-dim matrices (residual ~1e-15), products of 4 corners |
| M0-X2 | 1e-10 | $[W,G]=0$ exactly; float64 contraction over ≤ 1296 components |
| M0-X3 | 1e-12 | hermiticity of a 433×433 matrix built from real CGs |
| M0-X4 | 1e-10 | `eigvalsh` on 433×433, condition number O(10) |
| M0-X5 | off-block exact 0 ; J-violation 1e-12 ; gauge residual 1e-10 ; \|block\|–\|K\| 1e-12 | structural zeros come from disjoint supports (exactly 0 in the prototype); the rest is float64 |
| M0-X6 | 1e-10 | as X4 |
| M0-X7 | 1e-12 | 2×2 block of exact numbers |
| M0-E1/E2 | 1e-12 | two float64 simulators |
| M0-E3/E4 | error 0 / ≥ 0.5 / ≥ 0.1; leak 1 | discrete, large separations |
| M0-E5 | sparse 1e-10 ; aer_mps clause 1e-9 (certified) | as X1; aer_mps engine floor 2e-10 (reports/tests/008) — amended by prompts/003 §2 |
| M0-M1 | exact | Qiskit level-0 decompositions are fixed |
| M0-M2 | band $[3\log_2(1/\varepsilon)-4,\ 3\log_2(1/\varepsilon)+3\log_2\log_2(1/\varepsilon)+10]$, word error ≤ ε | Ross–Selinger typical case + measured offsets +2..+6 |
| M0-M3 | ±6 T vs pygridsynth; identical counts under the same seed | two implementations of the same algorithm |
| M1-E1, B1, B2, S1 | 1e-10 error, 1e-12 leak | exact-angle circuits; float64 over ≤ 3·10³ gates (~1e-13) |
| M1-P1 | 2e-5 error, 1e-9 leak, 2e-5 Gauss | ≤ 16 synthesised rotations × 1e-6 (triangle inequality); leak ≤ (1.6e-5)²; Gauss residual ≤ ‖G‖·‖U−U_ex‖ shares the rounding budget (prompts/003 §2) |
| M1-P2 | 5 % | same Qiskit/seed/settings ⇒ equality expected; 5 % absorbs pass-manager drift |
| M1-T1 | synthesised error ≤ N_rot·ε + 1e-9, leak ≤ (N_rot ε)² + 1e-12, Gauss ≤ N_rot·ε + 1e-9; pygridsynth vs Qiskit ≤ 10 % | triangle inequality (Gauss: prompts/003 §2); two gridsynth implementations |
| M2 evaluator cases | same as M0-E3 | — |
| M2 archive gate | key ≤ round-0 best; valid under full evaluation | definition of improvement |

Collection rule: every acceptance module imports the project through `tests/acceptance/_api.py::api(...)`, which converts `ImportError`/`AttributeError`/`NotImplementedError` into `pytest.fail("PENDING: …")`, so an unbuilt module is a failing test, never a collection error.

## 7. Do-not-retry list
* Dense $5^{12}$ (or $2^{28}$) operators or state vectors for the reference — sparse COO only.
* Qiskit's native `mcx` with ≥ 3 controls or `mcrx`/`cu` in submitted circuits (not Clifford+T-exact at level 0; see research §3.5).
* `qiskit-aer` `save_amplitudes` with `matrix_product_state` (returns zeros in 0.17.2).
* Fixing the route-A/route-B phase gauge analytically — compare up to diagonal gauge instead.
* Importing `refs/su2_plaquette_encodings.py` anywhere in `src/` or `tests/` (independence requirement).
* Cross-project imports from su2qc-trotter/skqd — vendor with the source commit.

## 8. Risks and stop conditions
* Paulo's QPY fails M1-P1 by > 2e-5 after the port verifies (M1-B1 passes): then the discrepancy is in his compiled file, not ours — report, do not loosen (`proto_paulo_check.py` result in research §6 tells us in advance).
* Evaluator "physical" path too slow for |R| = 8 outer bits read (256 blocks): acceptable for acceptance tests (minutes); the loop caches blocks by specialised-circuit hash. If > 10 min, builder adds the cache; not a plan change.
* Inner-span rank < 625 (M1-O1): then outer-blind circuits have don't-care freedom on the inner register too; the evaluator's fast path already handles it. Report the rank, no plan change.
* **Stop and ask Digonto** when: any locked tolerance is believed wrong; a physics identity (X4/X5/X6/X7) fails with no bug found; the loop's best circuit cannot be re-verified by the tester's second engine; or the proposer role cannot be created as in step 2.0.

## 9. Expected cost
M0: builder ≈ 10 calls, test suite < 3 min (fast) + 2 min (slow). M1: 9 calls; M1-P1 ≈ 10–60 s with the sparse simulator (Paulo's 3207-gate circuit on 625 inputs; the pure-Python dict prototype needs ~15 min — the COO/numpy batched simulator must be used). M2: 7 builder calls + the loop (6 rounds × ≤ 5 proposers × ~30 min wall, parallel; evaluation ≤ 5 min per round).

## 10. M3–M10 (unchanged; one line each, see prompts/001 §3)
M3/M4 spin network (16 qubits; target = `K_inner` embedded; Paulo's 15-qubit file at $\alpha_P=0.1$ through the evaluator; tests M3-C1…R1, M4 gate). M5/M6 rishon (BCW hep-th/9704106; research §4.1 lists what the planner must fix first). M7/M8 LSH (arXiv:1912.06133; use the (inner \| outer) point splitting at all four corners so that LSH = route B; research §4.2). M9/M10 fuzzy (arXiv:2308.05253; 4 qubits/link confirmed; $\mathcal K_1$ default; research §4.3). A planner run precedes M3, M5, M7, M9 to write their locked tests.

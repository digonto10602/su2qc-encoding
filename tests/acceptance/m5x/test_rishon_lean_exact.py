"""M5x (M5 extension, prompts/202) — kernel-checked exact statements of the rishon encoding, Lean 4.

m5x is an extension folder: m5 is locked (acceptance-v8) and m6 belongs to the compression milestone, so the wait-time
Lean work of prompts/202 gets its own folder, locked with `python tools/lock.py m5x` + acceptance-lock.

W1 (lean/Su2Plaq/Rishon/HBLink.lean, Mathlib-free): the eight sparse 6x6 link matrices of the H_B certificate
    (HBData.lean, certificate data so far) equal `Uop i j` / `Udop i j` of JW.lean restricted to the two-rishon sector,
    and the Ud lists are the transposes (hb_link_ops_from_jw); det U = U11 U22 - U12 U21 = 2 U11 U22 as an operator
    identity on the whole 4-mode link space (det_u_identity, BCW hep-th/9704106 Eq. 4.6); [U_ij, U_kl] = 0 (u_commute).
W2 (lean/Su2Plaq/Rishon/CornerKernel.lean, Mathlib-free): for all 81 end configurations of a corner (each end empty,
    full or one rishon) the joint kernel of the JW-built Gauss generators 2G^z, G^+, G^- has dimension = SU(2) fusion
    count of the end spins (integer rank, corner_kernel_dims) -- the step of the counting reduction that was numerical.
W3 (lean/Su2Plaq/Rishon/UESemantics.lean, Mathlib-free): exact gate semantics (Qiskit x, cx, p) over Z[i][z, z^-1],
    z = e^{i alpha/4}; the 12-gate build_UE and the 36-gate outer-row variant rendered from the Qiskit circuits;
    ue_exact_all_codes: build_UE maps every one of the 1296 inner codes exactly to z^{-3 #Q}|y> for all alpha;
    ue_gadget_sector + ue_outer_gates_structure: the outer row is 12 disjoint gadgets, each exact on the 6 sector codes.
L  (lean/Su2Plaq/Rishon/Bridge.lean imports Su2Plaq.Rishon.Counts): cornerCountR = the laptop's cornerCount
    (corner_count_agree); every theorem above depends on the standard axioms only (no native_decide, no sorry).

Numbers: float cross-checks of exact values use 1e-12 (Gaussian-integer Laurent coefficients at one complex exponential,
~1e-16, vs Qiskit float matrices; the project's exact-vs-float margin, prompts/006 section 7); time limits: lean_eval 300 s
per call (Mathlib-free #eval, measured <= 6 s), print_axioms 900 s (one Mathlib import, as M2/M5).  Prototype numbers:
scratch/planner/lean/RishonExactProto.lean 5.95 s / 2.02 GB, UESemProto.lean 5.64 s / 1.84 GB (reports/research/201)."""
import itertools
import pathlib
import time

import numpy as np
import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
NS = "Su2Plaq.Rishon."
HBLINK_THEOREMS = ("hb_link_ops_from_jw", "hb_link_ops_count", "det_u_identity", "u_commute")
CORNER_THEOREMS = ("corner_kernel_dims",)
UE_THEOREMS = ("card_inner_codes", "ue_gadget_sector", "ue_gates_structure", "ue_outer_gates_structure", "ue_exact_all_codes")
BRIDGE_THEOREMS = ("corner_count_agree",)
ALL_THEOREMS = tuple(NS + n for n in HBLINK_THEOREMS + CORNER_THEOREMS + UE_THEOREMS + BRIDGE_THEOREMS)
UE_GATE_NAMES = ("x", "cx", "p")
N_CORNER_CONFIGS = 81           # 3 end states (empty, full, one rishon) ^ 4 ends
N_INNER_CODES = 1296            # 6^4
TOL_EXACT = 1e-12


def _lean_file(root: pathlib.Path, rel: str) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    p = d / rel
    if not p.exists():
        pytest.fail(f"PENDING: {p.relative_to(root)} missing (prompts/202 steps W1-W4)", pytrace=False)
    return p


def _no_native_no_sorry(src: str):
    assert "native_decide" not in src and "sorry" not in src and "admit" not in src


def _imports(src: str) -> list:
    return [line.split()[1] for line in src.splitlines() if line.startswith("import ")]


def _statement(src: str, short: str) -> str:
    assert f"theorem {short}" in src, short
    return src.split(f"theorem {short}", 1)[1].split(":= by", 1)[0]


def _own_jw(n: int) -> list:
    """c_k = Z^{(x) k} sigma^-_k on n modes, little-endian (no project import)."""
    Z = np.diag([1.0, -1.0])
    sm = np.array([[0.0, 1.0], [0.0, 0.0]])   # |0><1|
    I2 = np.eye(2)
    out = []
    for k in range(n):
        M = np.ones((1, 1))
        for q in range(n):           # qubit 0 least significant: kron(q_{n-1}, ..., q_0)
            f = Z if q < k else (sm if q == k else I2)
            M = np.kron(f, M)
        out.append(M)
    return out


def _singlet_count(spins: tuple) -> int:
    """Multiplicity of J = 0 in the tensor product of spins (doubled integers), by sequential SU(2) coupling."""
    mult = {0: 1}
    for s in spins:
        new = {}
        for J, m in mult.items():
            for J2 in range(abs(J - s), J + s + 1, 2):
                new[J2] = new.get(J2, 0) + m
        mult = new
    return mult.get(0, 0)


def test_M5X_W1_hb_link_ops_tied_to_jw(root, tmp_path):
    """HBLink.lean exists, imports only JW.lean and HBData.lean, takes `linkOpsData` verbatim from the certificate, states
    the four theorems without native_decide/sorry; the certificate's eight link matrices equal the test's own 4-mode
    Jordan-Wigner U_ij = c_{L,i} c^dag_{R,j} (and its adjoint) restricted to the sorted weight-2 codes, exactly, with
    Ud = U^T; RishonLink.det_U equals U11 U22 - U12 U21 and 2 U11 U22 (the operator identity, 1e-12)."""
    p = _lean_file(root, "Su2Plaq/Rishon/HBLink.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert set(_imports(src)) == {"Su2Plaq.Rishon.JW", "Su2PlaqCert.Rishon.HBData"}, _imports(src)
    assert "def linkOpsData : List (List (Nat × Nat × Int)) := rishonHBCert.linkOps" in src
    s = _statement(src, "hb_link_ops_from_jw")
    assert "Uop" in s and "Udop" in s and "linkOpsData" in s and "sectorEntries" in s
    assert "(e.2.1, e.1, e.2.2)" in s or "transpose" in s.lower(), "the Ud = U^T clause is missing"
    assert "= 8" in _statement(src, "hb_link_ops_count")
    s = _statement(src, "det_u_identity")
    assert "detU" in s and "Uop 0 1" in s and "Uop 1 0" in s and "Uop 0 0" in s and "Uop 1 1" in s
    assert "OpEq 4" in _statement(src, "u_commute")
    # certificate data vs own JW
    LE = api("su2plaq.rishon.lean_export")
    import json
    cert = json.loads(pathlib.Path(LE.export_hb_certificate(tmp_path / "hb.json")).read_text())
    c = _own_jw(4)
    sec = [s_ for s_ in range(16) if bin(s_).count("1") == 2]
    assert sec == [3, 5, 6, 9, 10, 12]
    ops = {}
    for i in range(2):
        for j in range(2):
            U = c[i] @ c[2 + j].T              # c_{L,i} c^dag_{R,j}
            ops[f"U{i}{j}"] = U[np.ix_(sec, sec)]
            ops[f"Ud{i}{j}"] = U.T[np.ix_(sec, sec)]
            assert np.abs(U[np.ix_([k for k in range(16) if k not in sec], sec)]).max() == 0.0   # sector preserved
    names = [op["name"] for op in cert["link_ops"]]
    assert names == ["U00", "U01", "U10", "U11", "Ud00", "Ud01", "Ud10", "Ud11"]
    for op in cert["link_ops"]:
        M = np.zeros((6, 6))
        for r, col, v in op["entries"]:
            assert M[r, col] == 0.0
            M[r, col] = v
        assert np.array_equal(M, ops[op["name"]]), op["name"]
        if op["name"].startswith("Ud"):
            assert np.array_equal(M, ops["U" + op["name"][2:]].T)
    # operator identity det U = U11 U22 - U12 U21 = 2 U11 U22 on the full 16-dim link space
    RL = api("su2plaq.rishon.algebra:RishonLink")()
    U = [[RL.U(i, j) for j in range(2)] for i in range(2)]
    det = U[0][0] @ U[1][1] - U[0][1] @ U[1][0]
    assert np.abs(det - 2 * U[0][0] @ U[1][1]).max() <= TOL_EXACT
    assert np.abs(det - RL.det_U).max() <= TOL_EXACT
    for (i, j), (k, l) in itertools.product(itertools.product(range(2), repeat=2), repeat=2):
        assert np.abs(U[i][j] @ U[k][l] - U[k][l] @ U[i][j]).max() <= TOL_EXACT


def test_M5X_W2_corner_kernel_dims_match_production(root):
    """CornerKernel.lean exists, is Mathlib-free, builds the generators from JW.lean's modes and states corner_kernel_dims
    over the 81 configurations; Lean's kerDim (via #eval) equals the production corner_kernel dimension for every
    configuration and the test's own SU(2) singlet count; the configurations with a kernel are exactly those of the
    fusion rule."""
    p = _lean_file(root, "Su2Plaq/Rishon/CornerKernel.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert _imports(src) == ["Su2Plaq.Rishon.JW"], _imports(src)
    assert "mode true 8" in src and "mode false 8" in src and "comp" in src
    assert "def kerDim" in src and "def rank" in src and "def cornerBasis" in src
    s = _statement(src, "corner_kernel_dims")
    assert "(List.range 81)" in s and "kerDim" in s and "cornerCountR" in s and "invariant" in s
    LE = api("su2plaq.rishon.lean_export")
    corner_kernel = api("su2plaq.rishon.physical:corner_kernel")
    t0 = time.time()
    dims = LE.lean_corner_kernel_dims()
    assert time.time() - t0 <= 300
    assert len(dims) == N_CORNER_CONFIGS and all(isinstance(d, int) for d in dims)
    # m_e = 0 empty, 1 full, 2 one rishon; production: empty end = type A seen from its R end ('in'), full = A from its
    # L end ('out'), one rishon = Q ('out'); the kernel dimension depends only on the end spins
    kind = {0: ("A", "in"), 1: ("A", "out"), 2: ("Q", "out")}
    total_weighted = 0
    for m in range(N_CORNER_CONFIGS):
        ends = tuple((m // 3 ** e) % 3 for e in range(4))
        _, K, _ = corner_kernel(tuple(kind[x] for x in ends))
        spins = tuple(1 if x == 2 else 0 for x in ends)
        own = _singlet_count(spins)
        assert dims[m] == K.shape[1] == own, (m, ends, dims[m], K.shape[1], own)
        total_weighted += dims[m]
    assert total_weighted > 0 and dims[0] == 1 and dims[80] == 2           # all empty: 1 singlet; all one-rishon: 2 singlets


def test_M5X_W3_ue_semantics_gate_list_and_qiskit_matrices(root):
    """UESemantics.lean exists, is Mathlib-free, states the five theorems (card_inner_codes = 1296) and carries the two
    generated gate lists exactly as build_UE(1.0) (12 gates) and build_UE(1.0, with_outer=True, include_outer_electric=True)
    (36 gates): names, little-endian qubit indices, p angles as integers in units of alpha/4 (all -3); the literals are
    alpha-independent; the Lean gate semantics evaluated at alpha = 0.37 reproduce Qiskit's matrices of x, cx (both
    orientations) and p on 2 qubits to 1e-12 (the only link between the Lean model and Qiskit's gate definitions)."""
    p = _lean_file(root, "Su2Plaq/Rishon/UESemantics.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert _imports(src) == ["Su2Plaq.Rishon.JW"], _imports(src)
    assert "-- BEGIN generated exact" in src and "-- END generated exact" in src
    assert "= 1296" in _statement(src, "card_inner_codes")
    assert "sector.all" in _statement(src, "ue_gadget_sector") and "linkQ" in _statement(src, "ue_gadget_sector")
    assert "(List.range 4).flatMap gadget" in _statement(src, "ue_gates_structure")
    assert "(List.range 12).flatMap gadget" in _statement(src, "ue_outer_gates_structure")
    assert "innerCodes.all" in _statement(src, "ue_exact_all_codes") and "ueTarget" in _statement(src, "ue_exact_all_codes")
    LE = api("su2plaq.rishon.lean_export")
    build_UE = api("su2plaq.circuits.rishon:build_UE")
    for with_outer, n_gates, n_qubits in ((False, 12, 16), (True, 36, 48)):
        qc = build_UE(1.0, with_outer=with_outer, include_outer_electric=with_outer)
        assert qc.num_qubits == n_qubits
        gates = LE.ue_gate_ints(qc)
        assert len(gates) == len(qc.data) == n_gates
        assert all(g[0] in UE_GATE_NAMES for g in gates)
        for g, ins in zip(gates, qc.data):
            assert g[0] == ins.operation.name
            assert list(g[1:1 + len(ins.qubits)]) == [qc.find_bit(q).index for q in ins.qubits]
        assert [g[2] for g in gates if g[0] == "p"] == [-3] * (n_gates // 3)
        lit = LE.ue_gate_literal(qc)
        name = "ueOuterGates" if with_outer else "ueGates"
        assert f"def {name} : List Gate := {lit}" in src, f"the Lean gate list {name} differs from the shipped build_UE"
        assert LE.ue_gate_literal(build_UE(0.37, with_outer=with_outer, include_outer_electric=with_outer)) == lit
    Operator = api("qiskit.quantum_info:Operator")
    QuantumCircuit = api("qiskit:QuantumCircuit")
    alpha = 0.37
    t0 = time.time()
    for gate in (("x", 0), ("x", 1), ("cx", 0, 1), ("cx", 1, 0), ("p", 1, -3), ("p", 0, 5)):
        M = LE.lean_ue_gate_images(gate, 2, alpha)
        ref = QuantumCircuit(2)
        if gate[0] == "p":
            ref.p(gate[2] * alpha / 4, gate[1])
        else:
            getattr(ref, gate[0])(*gate[1:])
        R = Operator(ref).data
        assert M.shape == R.shape == (4, 4)
        assert np.abs(M - R).max() <= TOL_EXACT, (gate, np.abs(M - R).max())
    assert time.time() - t0 <= 300


def test_M5X_L_exact_theorems_kernel_checked(root):
    """All eleven theorems exist (names locked in lean_export.RISHON_M5X_THEOREMS), are proved without native_decide or
    sorry, and depend on the standard axioms only; Bridge.lean ties cornerCountR to the laptop's cornerCount; lean/
    Su2Plaq.lean imports Su2Plaq.Rishon.Bridge; no_sorry() is clean."""
    for rel in ("Su2Plaq/Rishon/HBLink.lean", "Su2Plaq/Rishon/CornerKernel.lean", "Su2Plaq/Rishon/UESemantics.lean"):
        _no_native_no_sorry(_lean_file(root, rel).read_text())
    bridge = _lean_file(root, "Su2Plaq/Rishon/Bridge.lean").read_text()
    _no_native_no_sorry(bridge)
    assert "import Su2Plaq.Rishon.Counts" in bridge
    s = _statement(bridge, "corner_count_agree")
    assert "cornerCountR" in s and "cornerCount " in s + " "
    assert "import Su2Plaq.Rishon.Bridge" in (root / "lean" / "Su2Plaq.lean").read_text()
    LE = api("su2plaq.rishon.lean_export")
    assert set(LE.RISHON_M5X_THEOREMS) == set(ALL_THEOREMS)
    P = api("su2plaq.lean.project")
    t0 = time.time()
    ax = P.print_axioms(list(ALL_THEOREMS), timeout=900)
    assert time.time() - t0 <= 900
    missing = [n for n in ALL_THEOREMS if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in ALL_THEOREMS if ax[n] - STANDARD}
    assert not bad, bad
    assert P.no_sorry() == []

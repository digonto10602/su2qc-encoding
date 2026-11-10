"""M9-K1, M9-B1, M9-S1 — general circuits of the fuzzy encoding (prompts/300 §1, §3 steps 9.5a–c; METHODS-fuzzy F3, F5, F6).
Exact-angle circuits: op-norm error <= 1e-10 after one global phase (block error + leak amplitude, prompts/004), weights
<= 1e-20 = (1e-10)^2 (float64 over <= 3e4 gates accumulates ~1e-12 in amplitude).  Every link state is a code, so a full
16x16 (one link) or 256x256 (row block) unitary equality certifies exactness on every physical state.
Cost note (prompts/301): the two M9_S1 tests form np.kron of four 16x16 blocks as a dense 65536x65536 complex matrix (69 GB each,
68-135 GB peak per test) — run this file with `pytest -n 1` (or `-k "not S1"` in parallel); K1 uses a seeded-state check instead."""
import numpy as np
import pytest

from scipy.linalg import expm

from tests.acceptance.m9._fz import (ALLOWED, ALTS, NOMINAL, SEED, api, op_norm_after_phase, ops_of, qubits_touched,
                                     ref_K1, ref_K2, ref_plaquette_row, ref_gauss_residual)


def _unitary(qc, n_expected=None):
    from qiskit.quantum_info import Operator
    if n_expected is not None:
        assert qc.num_qubits == n_expected
    return Operator(qc).data


def _is_linear_in(build, x0, x1, tol=1e-9):
    """Rotation angles of the circuit are linear in the parameter: angles(2 x0) - 2 angles(x0) = 0 and the skeleton is identical."""
    a0 = [(i.operation.name, tuple(qc_q), tuple(float(p) for p in i.operation.params)) for qc_q, i in
          ((tuple(build(x0).find_bit(q).index for q in inst.qubits), inst) for inst in build(x0).data)]
    a1 = [(i.operation.name, tuple(qc_q), tuple(float(p) for p in i.operation.params)) for qc_q, i in
          ((tuple(build(x1).find_bit(q).index for q in inst.qubits), inst) for inst in build(x1).data)]
    assert [(n, q) for n, q, _ in a0] == [(n, q) for n, q, _ in a1]
    for (_, _, p0), (_, _, p1) in zip(a0, a1):
        for u, v in zip(p0, p1):
            # angle(x1) = angle(x0) * x1/x0 for every parametrised gate (fixed-angle gates are the same in both)
            assert abs(v - u * (x1 / x0)) <= tol or abs(v - u) <= tol


@pytest.mark.parametrize("alpha", [0.37, 0.91])
def test_M9_K1_electric_link_and_layout(alpha):
    """link_UE(alpha): 4-qubit circuit equal to exp(-i alpha/2 K1) (16x16, 1e-10), angles linear in alpha; build_UE(alpha) acts
    the same block on each of the 4 inner links (register 'd' of 16 qubits) and, with with_outer=True, on all 12 links (48 qubits,
    'd' then 'o').  The one-link phases are e^{-i alpha {0, 3/4, 1}}: vacuum copy Psi = 1/2 gets phase 1 and the flux unit E_{2,0}
    (row 2 = lower block spin up, col 0) gets e^{-3 i alpha/4} — the KS j = 1/2 value — the sign is tested, not assumed."""
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    V = tg.UE_link(alpha)
    assert np.abs(V - expm(-0.5j * alpha * ref_K1())).max() <= 1e-12
    qc = circ.link_UE(alpha)
    assert ops_of(qc) <= ALLOWED
    assert op_norm_after_phase(_unitary(qc, 4), V) <= 1e-10
    _is_linear_in(circ.link_UE, 0.37, 0.74)
    # phases
    vac = np.zeros(16, complex); vac[[0b0000, 0b0101, 0b1010, 0b1111]] = 0.5
    out = _unitary(qc) @ vac
    assert abs(abs(np.vdot(vac, out)) - 1) <= 1e-10
    e = np.zeros(16, complex); e[0b1000] = 1            # E_{2,0}: q1=1 (lower block), q2=0, col 0
    ph = np.vdot(e, _unitary(qc) @ e) / np.vdot(vac, out)
    assert abs(ph - np.exp(-0.75j * alpha)) <= 1e-10
    # 48-qubit layout through the verify adapter / evaluator (a true Verdict per link block)
    verify_link = api("su2plaq.fuzzy.verify:verify_link")
    v = verify_link(qc, V)
    assert v.ok and v.op_norm_error <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    big = circ.build_UE(alpha)
    assert big.num_qubits == 16 and [r.name for r in big.qregs] == ["d"] and ops_of(big) <= ALLOWED
    U16 = _unitary(qc)
    # build_UE == kron(U16, U16, U16, U16) up to ONE global phase, checked on 8 seeded random 16-qubit states (prompts/301: the
    # dense 65536x65536 Operator(big) needed 69 GB and was infeasible).  The reference is applied link by link via tensordot on
    # the (16,16,16,16) reshape (axis 0 = qubits 12..15, little-endian like Operator), never forming the 65536^2 matrix.  The
    # phase is fixed from the first state and reused for all others; per-state error <= 1e-10 (float64: measured ~1e-15).
    from qiskit.quantum_info import Statevector
    rng = np.random.default_rng(SEED)
    phase = None
    for _ in range(8):
        psi = rng.normal(size=65536) + 1j * rng.normal(size=65536)
        psi /= np.linalg.norm(psi)
        out = Statevector(psi).evolve(big).data
        ref = psi.reshape(16, 16, 16, 16)
        for ax in range(4):
            ref = np.moveaxis(np.tensordot(U16, ref, axes=([1], [ax])), 0, ax)
        ref = ref.reshape(65536)
        if phase is None:
            ov = np.vdot(ref, out)
            phase = ov / abs(ov)
        assert np.linalg.norm(out - phase * ref) <= 1e-10
    bo = circ.build_UE(alpha, with_outer=True)
    assert bo.num_qubits == 48 and [r.name for r in bo.qregs] == ["d", "o"]
    assert qubits_touched(bo) == set(range(48))
    lm = api("su2plaq.metrics.logical:logical_metrics")(bo)
    assert lm["n_rot"] == 12 * api("su2plaq.metrics.logical:logical_metrics")(qc)["n_rot"]


@pytest.mark.parametrize("kappa2", [0.185, 0.455])
def test_M9_K1_kinetic_K2_link(kappa2):
    """link_UK(kappa2) equals exp(-i kappa2 K2) (16x16, 1e-10), angles linear in kappa2; eigenphases e^{-i kappa2 {-4,...,4}};
    U_K flips the flavour sector (it does not commute with Z_3) but commutes with calT_L, calT_R; build_UK layouts as build_UE.
    kappa2 = 0 gives the identity (the K1 theory is recovered)."""
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    V = tg.UK_link(kappa2)
    assert np.abs(V - expm(-1j * kappa2 * ref_K2())).max() <= 1e-12
    qc = circ.link_UK(kappa2)
    assert ops_of(qc) <= ALLOWED and op_norm_after_phase(_unitary(qc, 4), V) <= 1e-10
    _is_linear_in(circ.link_UK, 0.185, 0.37)
    assert op_norm_after_phase(_unitary(circ.link_UK(0.0)), np.eye(16)) <= 1e-10
    assert abs(tg.kappa2_of(0.37, 1.0) - 0.185) <= 1e-15 and tg.kappa2_of(0.37, 0.0) == 0.0
    verify_link = api("su2plaq.fuzzy.verify:verify_link")
    v = verify_link(qc, V)
    assert v.ok and v.op_norm_error <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    # commutes with the Gauss generators of a link, exact
    lk = api("su2plaq.fuzzy.link")
    U16 = _unitary(qc)
    for A in range(3):
        for T in (lk.calT_L(A), lk.calT_R(A)):
            assert np.abs(U16 @ T - T @ U16).max() <= 1e-10
    # U_EK = U_K U_E exactly (commuting terms)
    assert op_norm_after_phase(tg.UEK_link(0.37, kappa2), tg.UK_link(kappa2) @ tg.UE_link(0.37)) <= 1e-12
    big = circ.build_UK(kappa2, with_outer=True)
    assert big.num_qubits == 48 and [r.name for r in big.qregs] == ["d", "o"] and ops_of(big) <= ALLOWED


@pytest.mark.parametrize("beta", [0.61, 0.23, 1.00])
def test_M9_B1_magnetic_block(beta):
    """build_UB(beta): registers 'd' (16) then ancillas (<= 8, clean); touches only the 8 row qubits {4l+2, 4l+3} and ancillas;
    the 256x256 row block equals exp(+2 i beta W) (1e-10, one global phase) through verify_plaquette (a true Verdict on the
    complete row basis via FuzzyBlockEncoding(8)); W is the reference plaquette; N_rot <= 4000 (plan cap); the opposite sign
    exp(-2 i beta W) is rejected (error > 0.1); W commutes with the block (Gauss/plaquette conservation)."""
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    W = ref_plaquette_row()
    V = tg.UB_row(beta)
    assert np.abs(V - expm(2j * beta * W)).max() <= 1e-12
    qc = circ.build_UB(beta)
    assert qc.qregs[0].name == "d" and qc.qregs[0].size == 16 and "o" not in [r.name for r in qc.qregs]
    assert qc.num_qubits <= 24 and ops_of(qc) <= ALLOWED
    rows = {4 * l + 2 for l in range(4)} | {4 * l + 3 for l in range(4)}
    assert qubits_touched(qc) <= rows | set(range(16, qc.num_qubits))
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["n_rot"] <= 4000 and lm["cx"] > 0
    verify_plaquette = api("su2plaq.fuzzy.verify:verify_plaquette")
    v = verify_plaquette(qc, V)
    assert v.ok, (v.reason, v.op_norm_error, v.block_error, v.leak_amplitude)
    assert v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    assert v.extra.get("touches_column") is False
    v2 = verify_plaquette(qc, V.conj().T)
    assert not v2.ok and v2.op_norm_error > 0.1
    assert np.abs(V @ W - W @ V).max() <= 1e-10


@pytest.mark.parametrize("order", [1, 2])
@pytest.mark.parametrize("r", [1.0, 0.0])
def test_M9_S1_step_orders(order, r):
    """build_step(alpha, beta, kappa2, order): order 1 = U_B U_K U_E (kinetic layers first in the circuit), order 2 =
    U_E(a/2) U_K(k/2) U_B U_K(k/2) U_E(a/2); kappa2 = r alpha/2 (r = 1 nominal, r = 0 = K1 theory).  Checked on the 16 inner qubits
    by verify_step_samples: dense statevector on >= 32 seeded random product states and >= 8 seeded physical states (inner part),
    error <= 1e-10 against apply_step; Gauss residual of the outputs on seeded 48-qubit physical states <= 1e-10 (exact angles);
    order mismatch is detected (> 1e-3: orders differ at O(alpha beta)); with_outer=True adds the outer kinetic blocks on 'o'."""
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    vs = api("su2plaq.fuzzy.verify:verify_step_samples")
    for alpha, beta in (NOMINAL, ALTS[1]):
        k2 = tg.kappa2_of(alpha, r)
        qc = circ.build_step(alpha, beta, kappa2=k2, order=order)
        assert ops_of(qc) <= ALLOWED and qc.qregs[0].name == "d" and qc.qregs[0].size == 16 and qc.num_qubits <= 24
        res = vs(qc, alpha, beta, k2, order, n_random=32, n_phys=8, seed=SEED)
        assert res["err"] <= 1e-10 and res["gauss"] <= 1e-10 and res["n_inputs"] >= 40
    # apply_step consistency with the one-link and plaquette targets on a random vector (independent composition)
    alpha, beta = NOMINAL
    k2 = tg.kappa2_of(alpha, r)
    rng = np.random.default_rng(SEED)
    psi = rng.normal(size=65536) + 1j * rng.normal(size=65536)
    psi /= np.linalg.norm(psi)
    UEK = tg.UEK_link(alpha, k2)
    def kron4(A, v):
        # np.kron(np.kron(np.kron(A, A), A), A) @ v applied factor by factor (prompts/007): the same operator, never formed as
        # the dense 65536x65536 matrix (68.7 GB, twice for order 2; this supersedes the file-header cost note for this test).
        # np.kron puts its FIRST factor on the MOST significant index = axis 0 of the C-order (16,16,16,16) reshape.
        t = v.reshape(16, 16, 16, 16)
        t = np.einsum("ai,ijkl->ajkl", A, t)
        t = np.einsum("bj,ajkl->abkl", A, t)
        t = np.einsum("ck,abkl->abcl", A, t)
        t = np.einsum("dl,abcl->abcd", A, t)
        return t.reshape(65536)
    rows = np.arange(65536)
    row_idx = sum((((rows >> (4 * l + 2)) & 3) << (2 * l)) for l in range(4))
    col_idx = sum((((rows >> (4 * l)) & 3) << (2 * l)) for l in range(4))
    UB = tg.UB_row(beta)
    def apply_UB(v):
        M = np.zeros((256, 256), complex)
        M[row_idx, col_idx] = v
        return (UB @ M)[row_idx, col_idx]
    if order == 1:
        ref = apply_UB(kron4(UEK, psi))
    else:
        h = tg.UEK_link(alpha / 2, k2 / 2)
        ref = kron4(h, apply_UB(kron4(h, psi)))
    out = tg.apply_step(psi, alpha, beta, k2, order)
    assert np.linalg.norm(out - ref) <= 1e-10
    # order mismatch
    res = vs(circ.build_step(alpha, beta, kappa2=k2, order=1), alpha, beta, k2, 2, n_random=8, n_phys=2, seed=SEED)
    assert res["err"] > 1e-3
    qo = circ.build_step(alpha, beta, kappa2=k2, order=order, with_outer=True)
    assert [reg.name for reg in qo.qregs][:2] == ["d", "o"] and qo.qregs[1].size == 32
    assert set(range(16, 48)) <= qubits_touched(qo) or r == 0.0 and alpha == 0.0


def test_M9_S1_outer_row_and_gauss_on_outputs():
    """The outer-link kinetic row: build_step(..., with_outer=True) minus build_step(...) is exactly 8 copies each of link_UE and
    link_UK on the outer links (gate-count difference = 8 x (gates of link_UE + gates of link_UK)); the 48-qubit step applied to
    seeded physical COO states keeps the Gauss residual <= 1e-10 (gauss_residual_outputs, independent reference here)."""
    circ = api("su2plaq.circuits.fuzzy")
    tg = api("su2plaq.fuzzy.targets")
    alpha, beta = NOMINAL
    k2 = tg.kappa2_of(alpha, 1.0)
    inner = circ.build_step(alpha, beta, kappa2=k2, order=1)
    outer = circ.build_step(alpha, beta, kappa2=k2, order=1, with_outer=True)
    n_link = len(circ.link_UE(alpha).data) + len(circ.link_UK(k2).data)
    assert len(outer.data) - len(inner.data) == 8 * n_link
    gz = api("su2plaq.fuzzy.gauss")
    states = gz.sample_physical_states(4, SEED, max_components=1024)
    gro = api("su2plaq.fuzzy.verify:gauss_residual_outputs")
    assert gro(outer, states) <= 1e-10
    for keys, amps in states:
        assert ref_gauss_residual(np.asarray(keys), np.asarray(amps)) <= 1e-10

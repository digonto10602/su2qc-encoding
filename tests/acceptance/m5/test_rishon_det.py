"""M5-DT1..DT7 — the determinant term of the SU(2) quantum link model as a third Trotter layer (prompts/204 sections 2-5;
METHODS-rishon R13-R15; research 203).  Digonto's decision 2026-11-10: the det coupling is ADDED (audit 200 N1).

Symbols (prompts/204 section 2.1): lambda_D = coefficient of H_D = sum_links (det U + det U^dag) in the Hamiltonian (Wiese's
gamma, BCW's J'); eta = lambda_D dt = angle of the det layer U_D(eta) = exp(-i eta H_D).  The letter gamma stays reserved for the
sqrt2 beta slot of the three-variable angle rule (prompts/203 section 2).

Every reference in this file is built by the test itself (own Jordan-Wigner link operators of tests/acceptance/m5/_ref.py, own
17 x 17 closed-sector model, own code-level sector counting, scipy expm / eigh); the production code is compared with it.
Tolerances: 1e-12 for integer-entry constructions and 16 x 16 link algebra; 1e-10 for 1296-dimensional exponentials and for
circuits (METHODS section 6 tol_err, unchanged); Trotter-order slopes within 0.05 of the integers 2 and 3 (prompts/204 section 7).
"""
import functools
import inspect
import itertools
import json
import math

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.linalg import expm

from tests.acceptance._api import api, op_norm_after_phase
from tests.acceptance.m5 import _ref

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
# (alpha, beta, eta): nominal and the two alternates (prompts/204 section 2.4); generic, 2 eta and 4 eta not near multiples of pi/4
TRIPLES = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))
CODE_A, CODE_B = 3, 12


# Interface of prompts/204 section 5 that this file exercises: new names, and new keywords on existing functions.  Until all of them
# exist (builder step D0 creates stubs raising NotImplementedError) every test below fails with `PENDING:`, never with an
# AttributeError / TypeError.
_NEW_NAMES = ("su2plaq.rishon.operators:h_det_inner", "su2plaq.rishon.operators:hamiltonian_inner", "su2plaq.circuits.rishon:build_UD",
              "su2plaq.circuits.rishon:prepend_det_layer", "su2plaq.rishon.physical:det_sector_structure",
              "su2plaq.rishon.verify:RISHON_PRUNE_FRACTION")
_NEW_KEYWORDS = (("su2plaq.rishon.operators:inner_target", "eta"), ("su2plaq.rishon.operators:closed_block_full", "lam_d"),
                 ("su2plaq.circuits.rishon:build_step", "eta"), ("su2plaq.rishon.verify:verify", "eta"),
                 ("su2plaq.rishon.verify:verify", "prune_fraction"), ("su2plaq.rishon.verify:physical_cross_check", "eta"),
                 ("su2plaq.rishon.observables:observables", "eta"), ("su2plaq.rishon.observables:closed_spectra", "lam_d"))


def _require_interface():
    for dotted in _NEW_NAMES:
        api(dotted)
    fns = [(dotted, api(dotted), kw) for dotted, kw in _NEW_KEYWORDS]
    fns.append(("su2plaq.encodings.rishon:RishonEncoding.inner_target", api("su2plaq.encodings.rishon:RishonEncoding").inner_target, "eta"))
    fns.append(("su2plaq.encodings.rishon:RishonEncoding.target", api("su2plaq.encodings.rishon:RishonEncoding").target, "eta"))
    for dotted, fn, kw in fns:
        if kw not in inspect.signature(fn).parameters:
            pytest.fail(f"PENDING: {dotted} has no keyword {kw!r} yet (prompts/204 step D0)", pytrace=False)


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.rishon:RishonEncoding")()


@functools.lru_cache(maxsize=None)
def _ref_HD() -> np.ndarray:
    """Own H_D^in = sum over the four inner links of (det U_l + h.c.) on the 1296 inner codes (from the own JW link)."""
    lk = _ref.link()
    hd = lk.det_U + lk.det_U.conj().T
    codes = _ref.inner_codes()
    D = sp.csr_matrix((16 ** 4, 16 ** 4), dtype=complex)
    for l in range(4):
        D = D + _ref.embed(hd, l, 4)
    out = D[codes][:, codes].toarray()
    assert np.abs(out.imag).max() == 0.0
    return out.real


@functools.lru_cache(maxsize=None)
def _ref_parts():
    W = _ref.W_inner()
    HB = -(W + W.conj().T).real
    return _ref.HE_inner(), HB, _ref_HD()


def _ref_exp(H: np.ndarray, t: float) -> np.ndarray:
    w, v = np.linalg.eigh(H)
    return (v * np.exp(-1j * t * w)) @ v.conj().T


def _ref_step(alpha, beta, eta, order):
    HE, HB, HD = _ref_parts()
    UE = lambda a: np.diag(np.exp(-1j * a * HE))
    UB, UD = _ref_exp(HB, beta), (lambda e: _ref_exp(HD, e))
    if order == 1:
        return UB @ UD(eta) @ UE(alpha)
    return UE(alpha / 2) @ UD(eta / 2) @ UB @ UD(eta / 2) @ UE(alpha / 2)


def _model17(g2: float, lam_d: float) -> np.ndarray:
    """Own closed-sector model in the basis (16 vacua {A,B}^4 with bit l = 1 for type B on inner link l, loop):
    H = (g2/2) 3 |loop><loop| - (4/g2)(|loop><vac_A| + |loop><vac_B| + h.c.) + 2 lam_d sum_l X_l on the vacua
    (METHODS-rishon R4 closed block; det U = 2 |B><A| per link)."""
    H = np.zeros((17, 17))
    for k in range(16):
        for l in range(4):
            H[k, k ^ (1 << l)] += 2.0 * lam_d
    H[16, 16] = 1.5 * g2
    for k in (0b1100, 0b0011):          # vac_A = types (A, A, B, B), vac_B = (B, B, A, A)
        H[16, k] = H[k, 16] = -4.0 / g2
    return H


def _ops(qc):
    return {inst.operation.name for inst in qc.data}


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


# ------------------------------------------------------------------------------------------------------------ DT1
def test_M5_DT1_link_det_operator():
    """One link (16 x 16, production RishonLink vs the own JW link): det U = U11 U22 - U12 U21 = 2 c_L1 c_R1^dag c_L2 c_R2^dag
    (BCW Eq. 4.6, N = 2) has the single non-zero entry <B|det U|A> = +2; H_D^link = det U + det U^dag has eigenvalues
    (+2, -2, 0 x4) on the two-rishon sector (eigenvectors (A +- B)/sqrt2, kernel = the quartet); it commutes with all six SU(2)
    generators L_a, R_a and with the Casimir (so with H_E), and breaks the link U(1): [n_R - n_L, det U] = 4 det U."""
    rl = api("su2plaq.rishon.algebra:RishonLink")()
    lk = _ref.link()
    det = np.asarray(rl.det_U)
    assert np.abs(det - lk.det_U).max() <= 1e-12
    assert np.abs(det - 2.0 * lk.c[0] @ lk.cd[2] @ lk.c[1] @ lk.cd[3]).max() <= 1e-12
    nz = np.argwhere(np.abs(det) > 1e-12)
    assert nz.tolist() == [[CODE_B, CODE_A]] and abs(det[CODE_B, CODE_A] - 2.0) <= 1e-12
    hd = det + det.conj().T
    sec = [int(s) for s in rl.sector]
    assert sec == list(_ref.SECTOR)
    ev = np.sort(np.linalg.eigvalsh(hd[np.ix_(sec, sec)]))
    assert np.abs(ev - np.array([-2.0, 0, 0, 0, 0, 2.0])).max() <= 1e-12
    plus = np.zeros(16); plus[CODE_A] = plus[CODE_B] = 1 / np.sqrt(2)
    minus = np.zeros(16); minus[CODE_A], minus[CODE_B] = 1 / np.sqrt(2), -1 / np.sqrt(2)
    assert np.abs(hd @ plus - 2 * plus).max() <= 1e-12 and np.abs(hd @ minus + 2 * minus).max() <= 1e-12
    for q in (5, 6, 9, 10):
        assert np.abs(hd[:, q]).max() <= 1e-12
    for a in range(3):
        assert np.abs(rl.L[a] @ det - det @ rl.L[a]).max() <= 1e-12 and np.abs(rl.R[a] @ det - det @ rl.R[a]).max() <= 1e-12
    cas = rl.casimir_L + rl.casimir_R
    assert np.abs(cas @ hd - hd @ cas).max() <= 1e-12
    assert np.abs(rl.T_bcw @ det - det @ rl.T_bcw - 4.0 * det).max() <= 1e-12
    assert np.abs(rl.N @ det - det @ rl.N).max() <= 1e-12


# ------------------------------------------------------------------------------------------------------------ DT2
def test_M5_DT2_inner_det_hamiltonian():
    """H_D^in = h_det_inner() on the 1296 inner codes equals the own construction (1e-12), is real symmetric with integer
    entries 0 / 2; spectrum 2 (n_+ - n_-) with the multinomial multiplicities (per link +2, -2, 0 x4); [H_D, H_E] = 0 exactly;
    ||[H_D, H_B]||_2 = 16 sqrt2 (own value, 1e-9); H_D commutes with the inner Gauss generators (SU(2) invariant);
    hamiltonian_inner(g2, lam_d) = (g2/2) H_E + H_B / g2 + lam_d H_D; the sign of lam_d is a convention: the diagonal unitary
    S = prod_links exp(i (pi/4)(n_R - n_L)) maps H_D -> -H_D and leaves H_E, H_B unchanged, so spec H(lam_d) = spec H(-lam_d)."""
    _require_interface()
    O = api("su2plaq.rishon.operators")
    D = np.asarray(O.h_det_inner())
    Dr = _ref_HD()
    assert D.shape == (1296, 1296) and np.abs(np.imag(D)).max() <= 1e-12 and np.abs(D - Dr).max() <= 1e-12
    assert np.abs(D - D.T).max() <= 1e-12 and set(np.unique(np.round(np.real(D), 12)).tolist()) == {0.0, 2.0}
    assert np.abs(np.asarray(O.det_term_inner()) - Dr).max() <= 1e-12
    want = {}
    for n_p, n_m in itertools.product(range(5), repeat=2):
        if n_p + n_m <= 4:
            n_0 = 4 - n_p - n_m
            want[2 * (n_p - n_m)] = want.get(2 * (n_p - n_m), 0) + math.factorial(4) // (math.factorial(n_p) * math.factorial(n_m) * math.factorial(n_0)) * 4 ** n_0
    assert sum(want.values()) == 1296
    ev = np.round(np.linalg.eigvalsh(np.real(D)), 9)
    got = {int(v): int(c) for v, c in zip(*np.unique(ev, return_counts=True))}
    assert got == want, (got, want)
    HE, HB, _ = _ref_parts()
    assert np.abs(np.asarray(O.h_electric_inner()) - HE).max() <= 1e-12
    assert np.abs(D @ np.diag(HE) - np.diag(HE) @ D).max() == 0.0
    c = np.linalg.norm(D @ HB - HB @ D, 2)
    assert abs(c - 16 * np.sqrt(2)) <= 1e-9, c
    for corner in range(4):
        for a in range(3):
            G = _ref.gauss_inner(corner, a)
            assert np.abs(D @ G - G @ D).max() <= 1e-12
    codes = _ref.inner_codes()
    ph = np.ones(1296, dtype=complex)
    for i, code in enumerate(codes):
        for l in range(4):
            nib = (int(code) >> (4 * l)) & 15
            ph[i] *= np.exp(1j * np.pi / 4 * (bin(nib >> 2).count("1") - bin(nib & 3).count("1")))
    S = np.diag(ph)
    assert np.abs(S @ Dr @ S.conj().T + Dr).max() <= 1e-12 and np.abs(S @ HB @ S.conj().T - HB).max() <= 1e-12
    for g2, lam in ((1.0, 0.2), (2.0, 0.5)):
        H = np.asarray(O.hamiltonian_inner(g2, lam))
        Href = 0.5 * g2 * np.diag(HE) + HB / g2 + lam * Dr
        assert np.abs(H - Href).max() <= 1e-12 and np.abs(H - H.conj().T).max() <= 1e-12
        Hm = np.asarray(O.hamiltonian_inner(g2, -lam))
        assert np.abs(np.linalg.eigvalsh(H) - np.linalg.eigvalsh(Hm)).max() <= 1e-10
    assert np.abs(np.asarray(O.hamiltonian_inner(1.0)) - (0.5 * np.diag(HE) + HB)).max() <= 1e-12


# ------------------------------------------------------------------------------------------------------------ DT3
@pytest.mark.parametrize("alpha,beta,eta", list(TRIPLES))
def test_M5_DT3_targets(alpha, beta, eta):
    """inner_target: 'UD' = exp(-i eta H_D^in) (own eigh reference, 1e-10; unitary; group law; per-link closed form
    cos 2eta on A, B and -i sin 2eta between them); [U_D, U_E] = 0; three-layer 'step': order 1 = U_B U_D U_E (electric layer
    first, det second, magnetic last), order 2 = U_E(a/2) U_D(eta/2) U_B U_D(eta/2) U_E(a/2); eta = None is the two-layer M5
    target unchanged (bit-identical), eta = 0.0 equals it (1e-12); the exact identity U_2^n = L(1/2) U_1^n L(-1/2) with the
    commuting link layer L(x) = U_D(x eta) U_E(x alpha); UE/UB with an eta raise ValueError; 'UD' without eta raises."""
    _require_interface()
    O = api("su2plaq.rishon.operators")
    enc = _enc()
    HE, HB, HD = _ref_parts()
    UD = np.asarray(O.inner_target("UD", None, None, eta=eta))
    assert UD.shape == (1296, 1296) and UD.dtype == np.complex128
    assert np.abs(UD - _ref_exp(HD, eta)).max() <= 1e-10 and np.abs(UD.conj().T @ UD - np.eye(1296)).max() <= 1e-10
    assert np.abs(np.asarray(O.inner_target("UD", None, None, eta=0.2)) @ np.asarray(O.inner_target("UD", None, None, eta=eta - 0.2)) - UD).max() <= 1e-10
    codes = _ref.inner_codes()
    va, vb = _ref.vac_codes()
    ia = int(np.searchsorted(codes, va))
    flipped = (va & ~0xF) | CODE_B          # link b: A -> B
    jf = int(np.searchsorted(codes, flipped))
    c2, s2 = np.cos(2 * eta), np.sin(2 * eta)
    assert abs(UD[ia, ia] - c2 ** 4) <= 1e-10 and abs(UD[jf, ia] - (-1j * s2) * c2 ** 3) <= 1e-10
    UE = np.asarray(O.inner_target("UE", alpha, None))
    UB = np.asarray(O.inner_target("UB", None, beta))
    assert np.abs(UD @ UE - UE @ UD).max() <= 1e-12
    S1 = np.asarray(O.inner_target("step", alpha, beta, 1, eta=eta))
    S2 = np.asarray(O.inner_target("step", alpha, beta, 2, eta=eta))
    assert np.abs(S1 - _ref_step(alpha, beta, eta, 1)).max() <= 1e-10 and np.abs(S1 - UB @ UD @ UE).max() <= 1e-10
    assert np.abs(S2 - _ref_step(alpha, beta, eta, 2)).max() <= 1e-10
    assert np.linalg.norm(S1 - UD @ UB @ UE, 2) > 1e-2        # the det layer does not commute with U_B
    two = np.asarray(O.inner_target("step", alpha, beta, 1))
    assert np.array_equal(two, np.asarray(O.inner_target("step", alpha, beta, 1, eta=None)))
    assert np.abs(two - UB @ UE).max() <= 1e-12
    assert np.abs(np.asarray(O.inner_target("step", alpha, beta, 1, eta=0.0)) - two).max() <= 1e-12
    assert np.linalg.norm(S1 - two, 2) > 1e-2
    L = lambda x: np.asarray(O.inner_target("UD", None, None, eta=x * eta)) @ np.asarray(O.inner_target("UE", x * alpha, None))
    n = 3
    assert np.abs(np.linalg.matrix_power(S2, n) - L(0.5) @ np.linalg.matrix_power(S1, n) @ L(-0.5)).max() <= 1e-10
    assert np.abs(np.asarray(enc.inner_target("step", alpha, beta, 1, eta=eta)) - S1).max() <= 1e-12
    with pytest.raises(ValueError):
        O.inner_target("UD", None, None)
    with pytest.raises(ValueError):
        O.inner_target("UE", alpha, None, eta=eta)


def test_M5_DT3_trotter_orders():
    """Local Trotter error of the three-layer step against exp(-i dt H), H = (g2/2) H_E + H_B/g2 + lam_d H_D with
    alpha = g2 dt/2, beta = dt/g2, eta = lam_d dt (METHODS section 2 angle map + prompts/204): order 1 error ~ dt^2, order 2 ~ dt^3.
    Slopes from dt = 0.05, 0.025, 0.0125 within 0.05 of 2 and 3 (measured 1.994 / 2.994 at (0.05, 0.025), planner prototype)."""
    _require_interface()
    O = api("su2plaq.rishon.operators")
    HE, HB, HD = _ref_parts()
    g2, lam = 1.1014, 0.4316              # the couplings behind the nominal triple: dt = sqrt(2 alpha beta) = 0.6719
    H = 0.5 * g2 * np.diag(HE) + HB / g2 + lam * HD
    w, v = np.linalg.eigh(H)
    dts = (0.05, 0.025, 0.0125)
    errs = {1: [], 2: []}
    for dt in dts:
        ex = (v * np.exp(-1j * dt * w)) @ v.conj().T
        for order in (1, 2):
            U = np.asarray(O.inner_target("step", g2 * dt / 2, dt / g2, order, eta=lam * dt))
            errs[order].append(np.linalg.norm(U - ex, 2))
    for order, want in ((1, 2.0), (2, 3.0)):
        e = errs[order]
        slopes = [np.log(e[i] / e[i + 1]) / np.log(2.0) for i in range(2)]
        assert all(abs(s - want) <= 0.05 for s in slopes), (order, slopes, e)
        assert e[0] > e[1] > e[2] > 1e-9


# ------------------------------------------------------------------------------------------------------------ DT4
@pytest.mark.parametrize("eta", [0.29, 0.53, 1.07])
def test_M5_DT4_det_layer_circuit(eta):
    """build_UD(eta): register d (16 qubits), no ancilla, allowed gates, at most 32 CX and 8 rotations, no fixed T (the general
    gadget of prompts/204 section 4: 8 CX + 2 rz(2 eta) per link; a cheaper circuit passes too); exact on all 1296 inner codes
    against the own exp(-i eta H_D^in) (run_batch + encoded_block, 1e-10, zero leak) and by the production verdict (ok, certified,
    Gauss sample 273 states <= 1e-10, no outer bit read); the sign of eta is tested, not assumed; skeleton independent of eta."""
    _require_interface()
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    lm = api("su2plaq.metrics.logical:logical_metrics")
    qc = C.build_UD(eta)
    assert qc.num_qubits == 16 and [r.name for r in qc.qregs] == ["d"] and _ops(qc) <= ALLOWED
    m = lm(qc)
    assert 1 <= m["n_rot"] <= 8 and m["cx"] <= 32 and m["t_fixed"] == 0
    codes = enc.inner_codes()
    batch = run_batch(qc, codes)
    M, leak = encoded_block(batch, codes, len(codes), code_mask=(1 << 16) - 1)
    assert leak.max() <= 1e-20
    V = _ref_exp(_ref_HD(), eta)
    assert op_norm_after_phase(M, V) <= 1e-10
    v = Vf.verify(qc, enc, "UD", None, None, eta=eta)
    assert v.ok and v.certified and v.method == "inner_block", (v.reason, v.op_norm_error)
    assert v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20
    assert v.gauss_residual <= 1e-10 and v.gauss_states == 273 and v.outer_bits_read == 0
    bad = Vf.verify(C.build_UD(-eta), enc, "UD", None, None, eta=eta, gauss=False)
    assert not bad.ok and bad.op_norm_error > 1e-2
    assert _skeleton(C.build_UD(0.29)) == _skeleton(C.build_UD(0.83))
    qo = C.build_UD(eta, with_outer=True)
    assert qo.num_qubits == 48 and [r.name for r in qo.qregs] == ["d", "o"]
    assert not ({qo.find_bit(q).index for inst in qo.data for q in inst.qubits} & set(range(16, 48)))
    with pytest.raises(ValueError):
        C.build_UD(eta, include_outer_det=True)


@pytest.mark.parametrize("order", [1, 2])
def test_M5_DT4_three_layer_step(order):
    """build_step(alpha, beta, order, eta=eta) equals the three-layer inner target of the same order (1e-10; Gauss sample;
    clean ancillas) at the nominal triple and at an alternate; eta = None gives the M5 two-layer circuit gate for gate; the
    two-layer circuit is NOT the three-layer step and vice versa, and the other order is rejected (first-order detection);
    counts are additive (CX and rotations of the step = two-layer step + det layers)."""
    _require_interface()
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    lm = api("su2plaq.metrics.logical:logical_metrics")
    for alpha, beta, eta in (TRIPLES[0], TRIPLES[2]):
        qc = C.build_step(alpha, beta, order=order, eta=eta)
        assert _ops(qc) <= ALLOWED and [r.name for r in qc.qregs][0] == "d"
        v = Vf.verify(qc, enc, "step", alpha, beta, order=order, eta=eta)
        assert v.ok and v.certified and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20, (v.reason, v.op_norm_error)
        assert v.gauss_residual <= 1e-10 and v.gauss_states == 273
    alpha, beta, eta = TRIPLES[0]
    two = C.build_step(alpha, beta, order=order)
    assert _skeleton(two) == _skeleton(C.build_step(alpha, beta, order=order, eta=None))
    three = C.build_step(alpha, beta, order=order, eta=eta)
    v = Vf.verify(two, enc, "step", alpha, beta, order=order, eta=eta, gauss=False)
    assert not v.ok and v.op_norm_error > 1e-3
    v = Vf.verify(three, enc, "step", alpha, beta, order=order, gauss=False)
    assert not v.ok and v.op_norm_error > 1e-3
    v = Vf.verify(three, enc, "step", alpha, beta, order=3 - order, eta=eta, gauss=False)
    assert not v.ok and v.op_norm_error > 1e-3
    m2, m3, md = lm(two), lm(three), lm(C.build_UD(eta))
    n_det = 1 if order == 1 else 2
    assert m3["cx"] == m2["cx"] + n_det * md["cx"] and m3["n_rot"] == m2["n_rot"] + n_det * md["n_rot"] and m3["qubits"] == m2["qubits"]


def test_M5_DT4_physical_cross_check_and_compose():
    """With the outer register present the three-layer step is outer-blind and agrees with the restricted physical target on the
    17 closed + 256 seeded physical states (explicit <Psi'|U|Psi>, 1e-10); prepend_det_layer(unit, eta) puts the det layer
    in front of a two-layer unit (here the general U_B U_E circuit) on the unit's own registers and gives the three-layer step."""
    _require_interface()
    enc = _enc()
    C = api("su2plaq.circuits.rishon")
    Vf = api("su2plaq.rishon.verify")
    alpha, beta, eta = TRIPLES[0]
    qc = C.build_step(alpha, beta, order=1, with_outer=True, eta=eta)
    assert [r.name for r in qc.qregs][:2] == ["d", "o"]
    assert not ({qc.find_bit(q).index for inst in qc.data for q in inst.qubits} & set(range(16, 48)))
    x = Vf.physical_cross_check(qc, enc, "step", alpha, beta, eta=eta)
    assert x["n_states"] == 273 and x["max_abs_diff"] <= 1e-10
    x0 = Vf.physical_cross_check(qc, enc, "step", alpha, beta)
    assert x0["max_abs_diff"] > 1e-3
    unit = C.build_step(alpha, beta, order=1, with_outer=True)
    full = C.prepend_det_layer(unit, eta)
    assert full.num_qubits == unit.num_qubits and [r.name for r in full.qregs] == [r.name for r in unit.qregs]
    assert _skeleton(full)[-len(unit.data):] == _skeleton(unit) and len(full.data) == len(unit.data) + len(C.build_UD(eta).data)
    v = Vf.verify(full, enc, "step", alpha, beta, eta=eta)
    assert v.ok and v.certified and v.op_norm_error <= 1e-10 and v.gauss_residual <= 1e-10 and v.outer_bits_read == 0


# ------------------------------------------------------------------------------------------------------------ DT5
def _own_sector_structure(basis) -> dict:
    """Own code-level computation on the 38 432 physical states: H_B from the own W, det terms as the nibble flip
    A (3) <-> B (12) with amplitude 2 on link l; matrices in the physical basis as P^dag T P; blocks = connected components."""
    from scipy.sparse.csgraph import connected_components

    n = basis.dim
    lens = np.array([len(k) for k in basis.keys])
    allk = np.concatenate([np.asarray(k, dtype=np.int64) for k in basis.keys])
    alla = np.concatenate([np.asarray(a, dtype=np.complex128) for a in basis.amps])
    uk, row = np.unique(allk, return_inverse=True)
    Nu = len(uk)
    P = sp.csr_matrix((alla, (row, np.repeat(np.arange(n), lens))), shape=(Nu, n))
    codes = _ref.inner_codes()
    ipos = np.searchsorted(codes, uk & 0xFFFF)
    outer = uk >> 16
    W = _ref.W_inner()
    HB = sp.csc_matrix(-(W + W.conj().T))
    rr, cc, vv = [], [], []
    for i in range(1296):
        src = np.flatnonzero(ipos == i)
        if not len(src):
            continue
        for j, val in zip(HB.indices[HB.indptr[i]:HB.indptr[i + 1]], HB.data[HB.indptr[i]:HB.indptr[i + 1]]):
            if abs(val) < 1e-14:
                continue
            tgt = (outer[src] << 16) | codes[j]
            p = np.minimum(np.searchsorted(uk, tgt), Nu - 1)
            ok = uk[p] == tgt
            rr.append(p[ok]); cc.append(src[ok]); vv.append(np.full(int(ok.sum()), val))
    TB = sp.csr_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))), shape=(Nu, Nu))
    leaving = [0.0]

    def phys(T):
        X = T @ P
        M = (P.conj().T @ X).tocsr()
        leaving[0] = max(leaving[0], abs(float(X.multiply(X.conj()).sum().real - M.multiply(M.conj()).sum().real)))
        M.data[np.abs(M.data) < 1e-12] = 0
        M.eliminate_zeros()
        return M

    def det_link(l):
        nib = (uk >> (4 * l)) & 15
        src = np.flatnonzero((nib == CODE_A) | (nib == CODE_B))
        tgt = uk[src] ^ (np.int64(15) << (4 * l))
        p = np.minimum(np.searchsorted(uk, tgt), Nu - 1)
        assert np.all(uk[p] == tgt), "the det term maps a valid physical code to a code no physical state contains"
        return sp.csr_matrix((np.full(len(src), 2.0), (p, src)), shape=(Nu, Nu))

    HBp = phys(TB)
    Din = phys(sum((det_link(l) for l in range(1, 4)), det_link(0)))
    Dout = phys(sum((det_link(l) for l in range(5, 12)), det_link(4)))
    q = np.array([basis.u1_charges(k) for k in range(n)])
    own_q = np.zeros((n, 4), dtype=np.int64)       # own charges from the first code of each state
    for c, ends in enumerate(_ref.CORNERS):
        for l, role in ends:
            sh = 4 * l + (0 if role == "out" else 2)
            own_q[:, c] += np.array([bin((int(k[0]) >> sh) & 3).count("1") for k in basis.keys])
    assert np.array_equal(q, own_q)

    def comps(M):
        return connected_components((abs(M) > 1e-12).astype(np.int8), directed=False)

    def dq(Ms):
        rows = set()
        for M in Ms:
            coo = M.tocoo()
            rows |= {tuple(int(y) for y in x) for x in (q[coo.row] - q[coo.col])}
        return rows

    (n0, l0), (n1, l1), (n2, l2) = comps(HBp), comps(HBp + Din), comps(HBp + Din + Dout)
    k0 = api("su2plaq.rishon.physical:closed_indices")(basis)[0]
    rank = lambda rows: int(np.linalg.matrix_rank(np.array(sorted(rows))))
    comm = lambda A, B: float(abs(A @ B - B @ A).max()) if (A @ B - B @ A).nnz else 0.0
    return {"u1_sectors": len({tuple(x) for x in q}), "blocks": {"lam0": int(n0), "inner_det": int(n1), "full_det": int(n2)},
            "max_block": {"lam0": int(np.bincount(l0).max()), "inner_det": int(np.bincount(l1).max()), "full_det": int(np.bincount(l2).max())},
            "ref_block_dim": {"lam0": int(np.sum(l0 == l0[k0])), "inner_det": int(np.sum(l1 == l1[k0])), "full_det": int(np.sum(l2 == l2[k0]))},
            "ref_block_u1_sectors": {"lam0": len({tuple(x) for x in q[l0 == l0[k0]]}), "inner_det": len({tuple(x) for x in q[l1 == l1[k0]]}),
                                     "full_det": len({tuple(x) for x in q[l2 == l2[k0]]})},
            "charge_change_rank": {"lam0": rank(dq([HBp])), "inner_det": rank(dq([HBp, Din])), "full_det": rank(dq([HBp, Din, Dout]))},
            "dq_HB": dq([HBp]), "dq_in": dq([Din]), "dq_out": dq([Dout]), "leaving_weight": leaving[0],
            "comm_out_HB": comm(Dout, HBp), "comm_out_in": comm(Dout, Din), "comm_in_HB": comm(Din, HBp)}


def test_M5_DT5_sector_structure_with_det():
    """What the det term does to the 38 432-state SU(2)-Gauss space (own computation vs physical.det_sector_structure):
    the physical space is invariant under every link's det term (weight leaving it <= 1e-9: SU(2) Gauss law kept); at lam_d = 0
    there are 431 U(1) charge sectors and H_B changes no corner charge; an inner det term moves charge 2 between the two corners
    of its link, an outer one changes one corner charge by 2 (rank of the charge changes 3, resp. 4: no U(1) charge survives the
    full det term); the outer det row commutes with H_B and with the inner det terms (exact factor); dynamical blocks (connected
    components of H) 31 870 -> 4 976 (inner det) -> 305 (all 12 links); the reference vacuum's block grows 3 -> 17 -> 4 352 states
    and spreads over 1 -> 15 -> 431 charge sectors.  Integers are compared exactly; they are computed here, not typed in, except
    the three documented block counts, which pin the planner prototype (scratch/planner/proto_rishon_det_sectors_204.py)."""
    _require_interface()
    P = api("su2plaq.rishon.physical")
    basis = P.rishon_basis()
    own = _own_sector_structure(basis)
    assert own["leaving_weight"] <= 1e-9
    assert own["u1_sectors"] == _ref.N_U1_SECTORS == 431
    assert own["dq_HB"] == {(0, 0, 0, 0)}
    assert all(sorted(abs(x) for x in r) == [0, 0, 2, 2] and sum(r) == 0 for r in own["dq_in"]) and len(own["dq_in"]) == 8
    assert all(sorted(abs(x) for x in r) == [0, 0, 0, 2] for r in own["dq_out"]) and len(own["dq_out"]) == 8
    assert own["comm_out_HB"] <= 1e-12 and own["comm_out_in"] <= 1e-12 and own["comm_in_HB"] > 1.0
    assert own["charge_change_rank"] == {"lam0": 0, "inner_det": 3, "full_det": 4}
    assert own["blocks"] == {"lam0": 31870, "inner_det": 4976, "full_det": 305}
    assert own["ref_block_dim"] == {"lam0": 3, "inner_det": 17, "full_det": 4352}
    assert own["ref_block_u1_sectors"] == {"lam0": 1, "inner_det": 15, "full_det": 431}
    assert own["max_block"] == {"lam0": 3, "inner_det": 17, "full_det": 4352}
    got = P.det_sector_structure(basis)
    for key in ("u1_sectors", "blocks", "max_block", "ref_block_dim", "ref_block_u1_sectors"):
        assert got[key] == own[key], (key, got[key], own[key])
    assert got["charge_change_rank"]["inner_det"] == 3 and got["charge_change_rank"]["full_det"] == 4
    assert got["dim"] == 38432 and got["leaving_weight"] <= 1e-9


# ------------------------------------------------------------------------------------------------------------ DT6
@pytest.mark.parametrize("alpha,beta,eta", list(TRIPLES))
def test_M5_DT6_observables_with_det(alpha, beta, eta):
    """E_link(n), P(n), Loschmidt echo after n = 1, 2 three-layer first-order steps from vac_A: production (1296-dim inner
    target) vs the own 17 x 17 closed-sector model (1e-10); P(1) = 0 still holds (U_D U_E |vac_A> is a superposition of electric
    vacua, <vac|H_B|vac'> = 0); eta = None reproduces the M5 two-layer numbers exactly and eta = 0.0 to 1e-12; the Kogut-Susskind
    column is unchanged (KS has no det term)."""
    _require_interface()
    Ob = api("su2plaq.rishon.observables")
    got = Ob.observables(alpha, beta, n_steps=2, eta=eta)
    HB17 = _model17(1.0, 0.0) - np.diag(np.diag(_model17(1.0, 0.0)))      # g2 = 1: -(4)(|loop><vac| + h.c.) = H_B on the closed sector
    HD17 = _model17(1.0, 1.0) - _model17(1.0, 0.0)
    HE17 = np.diag([0.0] * 16 + [3.0])
    U = expm(-1j * beta * HB17) @ expm(-1j * eta * HD17) @ expm(-1j * alpha * HE17)
    psi = np.zeros(17, dtype=complex)
    psi[0b1100] = 1.0
    for n in (1, 2):
        psi = U @ psi
        ref = {"E_link": float(0.25 * np.real(np.vdot(psi, HE17 @ psi))), "P": float(-0.5 * np.real(np.vdot(psi, HB17 @ psi))),
               "echo": float(abs(psi[0b1100]) ** 2)}
        for key in ("E_link", "P", "echo"):
            assert abs(got["rishon"][n][key] - ref[key]) <= 1e-10, (n, key, got["rishon"][n][key], ref[key])
    assert abs(got["rishon"][1]["P"]) <= 1e-12
    base = Ob.observables(alpha, beta, n_steps=2)
    none = Ob.observables(alpha, beta, n_steps=2, eta=None)
    zero = Ob.observables(alpha, beta, n_steps=2, eta=0.0)
    for n in (1, 2):
        for key in ("E_link", "P", "echo"):
            assert none["rishon"][n][key] == base["rishon"][n][key] and abs(zero["rishon"][n][key] - base["rishon"][n][key]) <= 1e-12
            assert got["ks"][n][key] == base["ks"][n][key]
    assert abs(got["rishon"][1]["echo"] - base["rishon"][1]["echo"]) > 1e-4      # the det layer changes the physics


def test_M5_DT6_closed_spectrum_with_det():
    """Closed sector (per outer singlet choice, inner det only): closed_block_full(g2, lam_d) is 17 x 17 and has the spectrum
    of the own model (1e-10); closed_spectra(lam_d) groups it with multiplicities summing to 17; the 15-fold zero level of
    lam_d = 0 splits (the number of zero levels is the own model's: 15 at 0, fewer with det); spec(lam_d) = spec(-lam_d)."""
    _require_interface()
    O = api("su2plaq.rishon.operators")
    Ob = api("su2plaq.rishon.observables")
    for lam in (0.0, 0.2, 0.5):
        sp_ = Ob.closed_spectra((0.5, 1.0, 2.0), lam_d=lam)
        for g2 in (0.5, 1.0, 2.0):
            ref = np.linalg.eigvalsh(_model17(g2, lam))
            Hc = np.asarray(O.closed_block_full(g2, lam_d=lam))
            assert Hc.shape == (17, 17) and np.abs(Hc - Hc.conj().T).max() <= 1e-12
            assert np.abs(np.linalg.eigvalsh(Hc) - ref).max() <= 1e-10
            R = sp_["rishon"][g2]
            ev, mult = np.array(R["eigenvalues"], float), np.array(R["multiplicities"], int)
            assert mult.sum() == 17 and (lam != 0.0 or mult.tolist() == [1, 15, 1])
            full = np.sort(np.repeat(ev, mult))
            assert len(full) == 17 and np.abs(full - ref).max() <= 1e-10
            n_zero = int(np.sum(np.abs(ref) <= 1e-9))
            assert int(sum(m for e, m in zip(ev, mult) if abs(e) <= 1e-9)) == n_zero
            assert (n_zero == 15) if lam == 0.0 else (1 <= n_zero < 15)
            assert np.abs(np.linalg.eigvalsh(np.asarray(O.closed_block_full(g2, lam_d=-lam))) - ref).max() <= 1e-10
    assert np.abs(np.asarray(O.closed_block_full(1.0)) - np.asarray(O.closed_block_full(1.0, lam_d=0.0))).max() == 0.0


# ------------------------------------------------------------------------------------------------------------ DT7
@pytest.mark.parametrize("name,kind,order", [("UD", "UD", None), ("step3", "step", 1), ("step3_order2", "step", 2)])
def test_M5_DT7_det_results_files(name, kind, order, root):
    """results/rishon/{UD,step3,step3_order2}.json (scripts/m5_det_results.py, clean commit): schema keys, eta = 0.29 in the
    parameters, verification ok / certified by the inner-block method with the Gauss sample under the rishon prune cap (0.1),
    logical metrics and the 4-row T(eps) table; step3 counts = M5 step counts + det layer(s)."""
    p = root / "results" / "rishon" / f"{name}.json"
    if not p.exists():
        pytest.fail(f"PENDING: missing {p} (prompts/204 step D6)", pytrace=False)
    d = json.loads(p.read_text())
    assert list(d.keys()) == list(api("su2plaq.results.store:RESULT_KEYS"))
    assert d["encoding"] == "rishon" and d["kind"] == kind and d["circuit_id"] == name
    assert d["params"]["eta"] == 0.29 and d["params"].get("order") == order
    if kind == "step":
        assert d["params"]["alpha"] == 0.37 and d["params"]["beta"] == 0.61
    prov = d["provenance"]
    assert isinstance(prov["git_commit"], str) and len(prov["git_commit"]) >= 7 and prov["git_dirty"] is False
    ver = d["verification"]
    assert ver["ok"] and ver["certified"] and ver["method"] == "inner_block" and ver["reason"] == "ok"
    assert ver["op_norm_error"] <= 1e-10 and ver["leak_amplitude"] <= 1e-10 and ver["max_leak"] <= 1e-20
    assert ver["dropped_total"] <= 0.1 * 1e-10 and ver["gauss_residual"] <= 1e-10 and ver["gauss_states"] == 273 and ver["outer_bits_read"] == 0
    assert ver["extra"]["prune_fraction"] == 0.1
    lg = d["metrics"]["logical"]
    assert len(d["metrics"]["t_table"]) == 4
    ud = json.loads((root / "results" / "rishon" / "UD.json").read_text())["metrics"]["logical"]
    assert 1 <= ud["n_rot"] <= 8 and ud["cx"] <= 32 and ud["t_fixed"] == 0
    if kind == "step":
        base = json.loads((root / "results" / "rishon" / ("step.json" if order == 1 else "step_order2.json")).read_text())["metrics"]["logical"]
        assert lg["cx"] == base["cx"] + order * ud["cx"] and lg["n_rot"] == base["n_rot"] + order * ud["n_rot"] and lg["qubits"] == base["qubits"]


def test_M5_DT7_det_observables_file(root):
    """results/rishon/observables_det.json: the three (alpha, beta, eta) triples, n = 1, 2 rows, closed spectra at
    g2 in {0.5, 1, 2} x lam_d in {0, 0.2, 0.5}, the sector structure, definitions (naming lambda_D and eta), provenance; the
    stored numbers are reproduced by the production functions (1e-12)."""
    _require_interface()
    p = root / "results" / "rishon" / "observables_det.json"
    if not p.exists():
        pytest.fail(f"PENDING: missing {p} (prompts/204 step D6)", pytrace=False)
    d = json.loads(p.read_text())
    assert set(d) >= {"triples", "rishon", "closed_spectra", "sector_structure", "definitions", "provenance"}
    assert [tuple(t) for t in d["triples"]] == [tuple(t) for t in TRIPLES] and len(d["rishon"]) == 3
    Ob = api("su2plaq.rishon.observables")
    for (a, b, e), row in zip(TRIPLES, d["rishon"]):
        got = Ob.observables(a, b, n_steps=2, eta=e)["rishon"]
        for n in (1, 2):
            for key in ("E_link", "P", "echo"):
                assert abs(row[str(n)][key] - got[n][key]) <= 1e-12
    cs = d["closed_spectra"]
    assert set(map(float, cs["g2"])) == {0.5, 1.0, 2.0} and set(map(float, cs["lam_d"])) == {0.0, 0.2, 0.5}
    ss = d["sector_structure"]
    assert ss["u1_sectors"] == 431 and ss["blocks"] == {"lam0": 31870, "inner_det": 4976, "full_det": 305}
    assert ss["ref_block_dim"] == {"lam0": 3, "inner_det": 17, "full_det": 4352}
    text = json.dumps(d["definitions"])
    assert "lambda_D" in text and "eta" in text and prov_ok(d["provenance"])


def prov_ok(prov: dict) -> bool:
    return isinstance(prov.get("git_commit"), str) and len(prov["git_commit"]) >= 7 and prov.get("git_dirty") is False

"""M5-D1 — rishon link algebra (prompts/200 §2.1; METHODS-rishon R1, R2; BCW hep-th/9704106 Eqs. 4.1-4.6).
Tolerance 1e-13: 16x16 matrices with entries in {0, ±1, ±1/2, ±i/2}; products of ≤ 4 are exact up to one rounding."""
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api
from tests.acceptance.m5 import _ref

TOL = 1e-13


def _levi(a, b, c):
    return int((a, b, c) in [(0, 1, 2), (1, 2, 0), (2, 0, 1)]) - int((a, b, c) in [(0, 2, 1), (2, 1, 0), (1, 0, 2)])


def _comm(A, B):
    return A @ B - B @ A


def test_M5_D1_link_algebra():
    """CAR; [L_a,U_ij] = -(T_a U)_ij, [R_a,U_ij] = +(U T_a)_ij; su(2)_L x su(2)_R; [L,R] = [U,U] = [N,U] = 0;
    [T_bcw, U] = 2U (BCW Eq. 4.1); the N = 2 sector is {3,5,6,9,10,12} with Casimirs (0,3/4,3/4,3/4,3/4,0);
    det U = 2 c_L1 c_R1^dag c_L2 c_R2^dag = 2 |B><A| on the sector (Banerjee et al. 1211.2242); link types; the matrices
    equal the independent reference construction (same JW convention, fixed by METHODS-rishon R2)."""
    A = api("su2plaq.rishon.algebra")
    lk = A.RishonLink()
    ref = _ref.link()
    assert A.N_MODES == 4 and tuple(A.LINK_QUBITS) == ("L1", "L2", "R1", "R2")
    assert (A.CODE_A, A.CODE_B, tuple(A.CODES_Q)) == (3, 12, (5, 6, 9, 10))
    for k in range(4):
        assert np.abs(A.jw_annihilation(k, 4) - ref.c[k]).max() <= TOL
        assert np.abs(lk.c[k] - ref.c[k]).max() <= TOL and np.abs(lk.cdag[k] - ref.cd[k]).max() <= TOL
    I16 = np.eye(16)
    for k, l in itertools.product(range(4), repeat=2):
        assert np.abs(lk.c[k] @ lk.cdag[l] + lk.cdag[l] @ lk.c[k] - (I16 if k == l else 0)).max() <= TOL
        assert np.abs(lk.c[k] @ lk.c[l] + lk.c[l] @ lk.c[k]).max() <= TOL
    T = A.T_SPIN
    assert all(np.abs(T[a] - _ref.T_SPIN[a]).max() <= TOL for a in range(3))
    for a in range(3):
        for i, j in itertools.product(range(2), repeat=2):
            U = lk.U(i, j)
            assert np.abs(U - ref.U(i, j)).max() <= TOL and np.abs(lk.Udag(i, j) - U.conj().T).max() <= TOL
            assert np.abs(_comm(lk.L[a], U) + sum(T[a][i, k] * lk.U(k, j) for k in range(2))).max() <= TOL
            assert np.abs(_comm(lk.R[a], U) - sum(lk.U(i, k) * T[a][k, j] for k in range(2))).max() <= TOL
    for a, b in itertools.product(range(3), repeat=2):
        assert np.abs(_comm(lk.L[a], lk.L[b]) - sum(1j * _levi(a, b, c) * lk.L[c] for c in range(3))).max() <= TOL
        assert np.abs(_comm(lk.R[a], lk.R[b]) - sum(1j * _levi(a, b, c) * lk.R[c] for c in range(3))).max() <= TOL
        assert np.abs(_comm(lk.L[a], lk.R[b])).max() <= TOL
    for i, j, k, l in itertools.product(range(2), repeat=4):
        assert np.abs(_comm(lk.U(i, j), lk.U(k, l))).max() <= TOL
    for i, j in itertools.product(range(2), repeat=2):
        assert np.abs(_comm(lk.N, lk.U(i, j))).max() <= TOL
        assert np.abs(_comm(lk.T_bcw, lk.U(i, j)) - 2 * lk.U(i, j)).max() <= TOL
    # sector, Casimirs, types
    assert lk.sector.dtype == np.int64 and lk.sector.tolist() == [3, 5, 6, 9, 10, 12]
    nd = np.real(np.diag(lk.N)).round().astype(int)
    assert np.flatnonzero(nd == 2).tolist() == [3, 5, 6, 9, 10, 12]
    casL = np.real(np.diag(lk.casimir_L))[lk.sector]
    casR = np.real(np.diag(lk.casimir_R))[lk.sector]
    assert np.abs(casL - [0, 0.75, 0.75, 0.75, 0.75, 0]).max() <= TOL and np.abs(casR - casL).max() <= TOL
    assert np.abs(lk.casimir_L - sum(lk.L[a] @ lk.L[a] for a in range(3))).max() <= TOL
    assert [lk.link_type(int(s)) for s in lk.sector] == ["A", "Q", "Q", "Q", "Q", "B"]
    assert all(lk.link_type(s) is None for s in range(16) if s not in (3, 5, 6, 9, 10, 12))
    # determinant
    D = lk.det_U
    assert np.abs(D - (lk.U(0, 0) @ lk.U(1, 1) - lk.U(0, 1) @ lk.U(1, 0))).max() <= TOL
    assert np.abs(D - 2 * lk.c[0] @ lk.cdag[2] @ lk.c[1] @ lk.cdag[3]).max() <= TOL
    Ds = D[np.ix_(lk.sector, lk.sector)]
    expect = np.zeros((6, 6))
    expect[5, 0] = 2.0        # |B><A| : B = index 5 (code 12), A = index 0 (code 3)
    assert np.abs(Ds - expect).max() <= TOL
    # U moves one rishon L -> R: A -> Q, Q -> B, B -> 0
    for i, j in itertools.product(range(2), repeat=2):
        Us = lk.U(i, j)[np.ix_(lk.sector, lk.sector)]
        col_A, col_B = Us[:, 0], Us[:, 5]
        assert np.abs(col_B).max() <= TOL and np.abs(col_A[[0, 5]]).max() <= TOL and np.abs(col_A).max() > 0.5
        for q in range(1, 5):
            assert np.abs(Us[[0, 1, 2, 3, 4], q]).max() <= TOL
    # end generators are 2-qubit local
    for a in range(3):
        assert np.abs(_ref.kron_all([lk.end_generator(a, "L"), np.eye(4)]) - lk.L[a]).max() <= TOL
        assert np.abs(_ref.kron_all([np.eye(4), lk.end_generator(a, "R")]) - lk.R[a]).max() <= TOL


def test_M5_D1_string_free_and_sector():
    """With link-contiguous modes the link bilinears carry no Jordan-Wigner string outside their link: on 8 modes
    (two links) the GLOBAL c_k c_l^dag of link 1 equals the embedded link-local U (and likewise for link 0); the 6 weight-2
    link codes are exactly the N = 2 sector; `embed_link_op` places link 0 on the least significant qubits."""
    A = api("su2plaq.rishon.algebra")
    lk = A.RishonLink()
    ref = _ref.link()
    for i, j in itertools.product(range(2), repeat=2):
        g1 = A.global_bilinear(4 + i, 6 + j, 8)                    # link 1: modes 4..7
        e1 = A.embed_link_op(lk.U(i, j), 1, 2).toarray()
        assert g1.shape == (256, 256) and np.abs(g1 - e1).max() <= TOL
        assert np.abs(e1 - _ref.embed(ref.U(i, j), 1, 2).toarray()).max() <= TOL
        g0 = A.global_bilinear(i, 2 + j, 8)
        assert np.abs(g0 - A.embed_link_op(lk.U(i, j), 0, 2).toarray()).max() <= TOL
    # end bilinears of link 1 (modes 4,5 and 6,7) are local too
    for i, j in itertools.product(range(2), repeat=2):
        gl = A.global_bilinear(4 + i, 4 + j, 8)                    # c_{L,i} c^dag_{L,j} of link 1
        loc = lk.c[i] @ lk.cdag[j]
        assert np.abs(gl - A.embed_link_op(loc, 1, 2).toarray()).max() <= TOL
    weight2 = [s for s in range(16) if bin(s).count("1") == 2]
    assert weight2 == lk.sector.tolist() == [3, 5, 6, 9, 10, 12]
    # embedding order: a diagonal marker on link 2 of 4 shows up at bit positions 8..11
    marker = np.diag(np.arange(16, dtype=complex))
    E = A.embed_link_op(marker, 2, 4)
    d = np.real(E.diagonal())
    idx = np.arange(16 ** 4)
    assert np.abs(d - ((idx >> 8) & 15)).max() <= TOL

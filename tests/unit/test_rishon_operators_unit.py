"""Unit tests for su2plaq.rishon.operators (step 5.3).  No expected totals are hard-coded: structure is checked by
consistency (rank = 2 x pairs, independent 16-qubit construction, commutation relations)."""
import itertools

import numpy as np
import pytest
import scipy.sparse as sp
from scipy.linalg import expm

from su2plaq.geometry import plaquette_diagram
from su2plaq.rishon import observables as OB
from su2plaq.rishon import operators as O
from su2plaq.rishon.algebra import CODE_A, CODE_B, CODES_Q, RishonLink, embed_link_op


@pytest.fixture(scope="module")
def codes():
    return O.inner_codes()


def test_W_matches_full_16_qubit_construction(codes):
    """Independent route: sparse 65536-dim product with embed_link_op on the 16-qubit register, restricted to codes."""
    rl = RishonLink()
    W = sp.csr_matrix((16 ** 4, 16 ** 4), dtype=complex)
    for a, b, c, d in itertools.product(range(2), repeat=4):
        W = W + (embed_link_op(rl.U(a, b), 0, 4) @ embed_link_op(rl.U(b, c), 1, 4)
                 @ embed_link_op(rl.Udag(d, c), 2, 4) @ embed_link_op(rl.Udag(a, d), 3, 4))
    Wr = W[codes][:, codes].toarray()
    # W maps the code space into itself; (U_t^dag)_cd = (U_dc)^dag
    outside = np.setdiff1d(np.arange(16 ** 4), codes)
    assert abs(W[outside][:, codes]).max() <= 1e-13
    assert np.abs(O.plaquette_W_inner() - Wr).max() <= 1e-13


def test_W_real_heights_and_nilpotent(codes):
    W = O.plaquette_W_inner()
    assert W.dtype == np.complex128 and np.abs(W.imag).max() == 0.0
    assert np.abs(W @ W @ W).max() <= 1e-13
    rows, cols = np.nonzero(np.abs(W) > 1e-12)
    for r, c in zip(rows, cols):
        assert np.subtract(O.heights(int(codes[r])), O.heights(int(codes[c]))).tolist() == [1, 1, 1, 1]
    HB = O.h_magnetic_inner()
    assert np.abs(HB + (W + W.conj().T)).max() == 0.0 and np.abs(HB - HB.conj().T).max() == 0.0


def test_heights_values():
    va = CODE_A | (CODE_A << 4) | (CODE_B << 8) | (CODE_B << 12)
    assert O.heights(va) == (0, 0, 0, 0)
    q = CODES_Q[0]
    assert O.heights(q | (q << 4) | (q << 8) | (q << 12)) == (1, 1, 1, 1)
    with pytest.raises(ValueError):
        O.heights(0)


def test_electric_and_gauss(codes):
    HE = O.h_electric_inner()
    n_q = sum(np.isin((codes >> (4 * l)) & 15, CODES_Q).astype(int) for l in range(4))
    assert np.allclose(HE, 0.75 * n_q)
    D = plaquette_diagram()
    W = O.plaquette_W_inner()
    for c in range(len(D.corners)):
        for a in range(3):
            G = O.gauss_inner(c, a)
            assert np.abs(G - G.conj().T).max() <= 1e-13
            assert np.abs(W @ G - G @ W).max() <= 1e-12
            assert np.abs(G * HE[None, :] - HE[:, None] * G).max() <= 1e-12
    with pytest.raises(ValueError):
        O.gauss_inner(4, 0)
    with pytest.raises(ValueError):
        O.gauss_inner(0, 3)


def test_gauss_algebra_su2():
    """Corner generators of the inner ends close into su(2): [G^1, G^2] = i G^3."""
    for c in range(4):
        G = [O.gauss_inner(c, a) for a in range(3)]
        assert np.abs(G[0] @ G[1] - G[1] @ G[0] - 1j * G[2]).max() <= 1e-12


def test_bright_pairs_structure(codes):
    pairs = O.bright_pairs()
    HB = O.h_magnetic_inner().real
    ev = np.linalg.eigvalsh(HB)
    rank = int(np.sum(np.abs(ev) > 1e-9))
    assert rank == 2 * len(pairs)
    H = np.zeros_like(HB)
    vecs = []
    for u, v, k in pairs:
        assert abs(np.linalg.norm(u) - 1) <= 1e-12 and abs(np.linalg.norm(v) - 1) <= 1e-12
        first = np.flatnonzero(np.abs(u) >= np.abs(u).max() - 1e-10)[0]
        assert u[first] > 0
        H -= k * (np.outer(u, v) + np.outer(v, u))
        vecs += [u, v]
    V = np.array(vecs)
    assert np.abs(V @ V.T - np.eye(len(vecs))).max() <= 1e-10
    assert np.abs(H - HB).max() <= 1e-10
    ks = [k for *_, k in pairs]
    assert list(np.round(ks, 9)) == sorted(np.round(ks, 9))      # sorted by kappa
    assert np.allclose(sorted(set(np.round(ks, 9))), sorted(set(np.round(np.abs(ev[np.abs(ev) > 1e-9]), 9))))
    # returned copies are independent
    pairs[0][0][:] = 0.0
    assert np.linalg.norm(O.bright_pairs()[0][0]) > 0.5


def test_dark_codes(codes):
    dark = O.dark_codes()
    HB = O.h_magnetic_inner()
    pos = np.searchsorted(codes, dark)
    assert np.array_equal(codes[pos], dark)
    assert np.abs(HB[pos]).max() == 0.0 and np.abs(HB[:, pos]).max() == 0.0
    nondark = np.setdiff1d(np.arange(len(codes)), pos)
    assert np.all(np.abs(HB[nondark]).max(axis=1) > 0.5)
    assert len(dark) + len(nondark) == len(codes)


def test_closed_codes_and_block(codes):
    va, vb, loop = O.closed_codes()
    assert va != vb and len(loop) == 16 and np.all(np.isin(loop, codes))
    ia, ib = np.searchsorted(codes, [va, vb])
    W = O.plaquette_W_inner()
    assert np.array_equal(np.sort(loop), codes[np.abs(W[:, ia]) > 1e-12])
    for g2 in (0.5, 1.0, 2.0):
        Hc = O.closed_block(g2)
        assert Hc.shape == (3, 3) and Hc.dtype == np.complex128 and np.abs(Hc - Hc.conj().T).max() <= 1e-13
        assert abs(Hc[1, 1] - 1.5 * g2) <= 1e-13 and Hc[0, 0] == 0 and Hc[2, 2] == 0 and Hc[0, 2] == 0
        e = np.sort(np.linalg.eigvalsh(Hc))
        s = np.sqrt(9 * g2 ** 2 / 16 + (np.linalg.norm(W[:, ia]) ** 2 * 2) / g2 ** 2)
        assert np.allclose(e, [0.75 * g2 - s, 0.0, 0.75 * g2 + s], atol=1e-12)


def test_ks_closed_block_spectrum():
    for g2 in (0.5, 1.0, 2.0):
        e = np.linalg.eigvalsh(OB.ks_closed_block(g2))
        s = np.sqrt(9 * g2 ** 2 / 16 + 4 / g2 ** 2)
        assert np.allclose(e, [0.75 * g2 - s, 0.75 * g2 + s], atol=1e-12)


def test_det_term(codes):
    D = O.det_term_inner()
    assert np.abs(D - D.conj().T).max() <= 1e-13
    va = O.closed_codes()[0]
    ia = np.searchsorted(codes, va)
    flipped = np.searchsorted(codes, (va & ~0xF) | CODE_B)
    assert abs(D[flipped, ia] - 2.0) <= 1e-13


def test_inner_target_unitarity_and_composition(codes):
    HB = O.h_magnetic_inner().real
    HE = O.h_electric_inner()
    a, b = 0.91, 0.23
    UB = O.inner_target("UB", None, b)
    assert np.abs(UB - expm(-1j * b * HB)).max() <= 1e-12
    assert np.abs(UB.conj().T @ UB - np.eye(1296)).max() <= 1e-12
    assert np.abs(O.inner_target("UB", None, 0.0) - np.eye(1296)).max() == 0.0
    assert np.abs(O.inner_target("UB", None, 0.3) @ O.inner_target("UB", None, 0.4) - O.inner_target("UB", None, 0.7)).max() <= 1e-12
    UE = O.inner_target("UE", a, None)
    assert np.abs(np.diag(UE) - np.exp(-1j * a * HE)).max() == 0.0
    assert np.abs(O.inner_target("step", a, b, 1) - UB @ UE).max() <= 1e-14
    UEh = O.inner_target("UE", a / 2, None)
    assert np.abs(O.inner_target("step", a, b, 2) - UEh @ UB @ UEh).max() <= 1e-14


def test_inner_target_errors():
    with pytest.raises(ValueError):
        O.inner_target("step", 0.1, 0.1, order=3)
    with pytest.raises(ValueError):
        O.inner_target("nope", 0.1, 0.1)
    with pytest.raises(ValueError):
        O.inner_target("UE", None, 0.1)
    with pytest.raises(ValueError):
        O.inner_target("UB", 0.1, None)

"""M5-X1 — inner rishon operators on the 1296 codes: plaquette, electric, Gauss, structure, closed block, targets
(prompts/200 §2.3, §4; METHODS-rishon R4; research 200 §6-§7).  1e-12 for integer-entry constructions, 1e-9 for
eigenvalues of the 1296x1296 integer matrix, exact counts."""
import functools
from collections import Counter

import numpy as np
import pytest
from scipy.linalg import expm

from tests.acceptance._api import api, op_norm_after_phase
from tests.acceptance.m5 import _ref

SQ2 = np.sqrt(2.0)


@functools.lru_cache(maxsize=None)
def _ops():
    return api("su2plaq.rishon.operators")


def _heights(types):
    hb = {"A": 0, "Q": 1, "B": 2}
    ht = {"B": 0, "Q": 1, "A": 2}
    return (hb[types[0]], hb[types[1]], ht[types[2]], ht[types[3]])


def test_M5_X1_plaquette_structure():
    """W = Tr(U_b U_r U_t^dag U_l^dag) on the inner codes equals the independent construction (1e-12), is real; H_B^in
    hermitian; H_E^in = 3/4 per quartet link; [W, G^a_c(inner ends)] = 0 and [H_E, G] = 0 (1e-12); W raises all four
    link heights by exactly one (hence W^3 = 0); 990 dark codes."""
    O = _ops()
    codes = O.inner_codes()
    assert codes.dtype == np.int64 and len(codes) == 1296 and np.array_equal(codes, _ref.inner_codes())
    W = O.plaquette_W_inner()
    Wr = _ref.W_inner()
    assert W.shape == (1296, 1296) and np.abs(W - Wr).max() <= 1e-12 and np.abs(np.imag(W)).max() <= 1e-12
    HB = O.h_magnetic_inner()
    assert np.abs(HB + (W + W.conj().T)).max() <= 1e-12 and np.abs(HB - HB.conj().T).max() <= 1e-12
    HE = O.h_electric_inner()
    assert HE.shape == (1296,) and np.abs(HE - _ref.HE_inner()).max() <= 1e-12
    for c in range(4):
        for a in range(3):
            G = O.gauss_inner(c, a)
            assert np.abs(G - _ref.gauss_inner(c, a)).max() <= 1e-12
            assert np.abs(W @ G - G @ W).max() <= 1e-12
            assert np.abs(np.diag(HE) @ G - G @ np.diag(HE)).max() <= 1e-12
    rows, cols = np.nonzero(np.abs(W) > 1e-12)
    for r, c in zip(rows[:4000], cols[:4000]):
        hr, hc = O.heights(int(codes[r])), O.heights(int(codes[c]))
        assert tuple(np.subtract(hr, hc)) == (1, 1, 1, 1)
        assert hr == _heights(_ref.types_of(int(codes[r])))
    assert np.abs(W @ W @ W).max() <= 1e-12
    dark = O.dark_codes()
    assert len(dark) == 990 and set(dark.tolist()) <= set(codes.tolist())
    pos = np.searchsorted(codes, dark)
    assert np.abs(HB[pos, :]).max() <= 1e-12 and np.abs(HB[:, pos]).max() <= 1e-12


def test_M5_X1_bright_pairs_and_closed_block():
    """Spectrum of H_B^in: ±4√2 (1), ±2 (48), ±1 (32), 0 (1134).  81 bright pairs (u_p, v_p, kappa_p) reconstruct H_B
    (1e-10), are orthonormal and real, kappa multiset {1: 32, 2: 48, 4√2: 1}, amplitudes in {1, 1/√2, 1/2, 1/4} (1e-9).
    Closed sector: codes of vac_A, vac_B and the 16 loop codes; <loop|W|vac_A> = <vac_B|W|loop> = 4; the 3x3 block at
    g^2 in {0.5, 1, 2} equals (g^2/2) diag(0,3,0) - (4/g^2) adjacency (1e-12) with eigenvalues 0, 3g^2/4 ± sqrt(9g^4/16 + 32/g^4).
    The determinant term (gamma = 0 in M5, defined only) flips one link A <-> B with amplitude 2."""
    O = _ops()
    codes = O.inner_codes()
    HB = O.h_magnetic_inner()
    W = O.plaquette_W_inner()
    ev = np.linalg.eigvalsh(HB)
    got = Counter(np.round(ev, 6).tolist())
    expect = Counter({round(k, 6): v for k, v in _ref.SPECTRUM_HB.items()})
    assert got == expect, got
    pairs = O.bright_pairs()
    assert len(pairs) == 81
    kap = Counter(round(float(k), 6) for _, _, k in pairs)
    assert kap == Counter({round(k, 6): v for k, v in _ref.KAPPA_MULTISET.items()}), kap
    vecs = []
    H = np.zeros((1296, 1296))
    for u, v, k in pairs:
        assert u.shape == v.shape == (1296,) and np.abs(np.imag(u)).max() <= 1e-12 and np.abs(np.imag(v)).max() <= 1e-12
        u, v = np.real(u), np.real(v)
        H -= float(k) * (np.outer(u, v) + np.outer(v, u))
        vecs += [u, v]
        for x in np.concatenate([u, v]):
            if abs(x) > 1e-12:
                assert min(abs(abs(x) - a) for a in _ref.AMPLITUDE_ALPHABET) <= 1e-9, x
    V = np.array(vecs)
    assert np.abs(V @ V.T - np.eye(162)).max() <= 1e-10
    assert np.abs(H - HB).max() <= 1e-10
    # closed sector
    va, vb, loop = O.closed_codes()
    ra, rb = _ref.vac_codes()
    assert (va, vb) == (ra, rb) and len(loop) == 16 and all(_ref.types_of(int(c)) == ("Q",) * 4 for c in loop)
    ia, ib = int(np.searchsorted(codes, va)), int(np.searchsorted(codes, vb))
    wa = W[:, ia]
    assert abs(np.linalg.norm(wa) - 4.0) <= 1e-12 and np.count_nonzero(np.abs(wa) > 1e-12) == 16
    ln = wa / 4.0
    assert set(codes[np.abs(wa) > 1e-12].tolist()) == set(int(c) for c in loop)
    assert abs(np.vdot(ln, W[:, ia]) - 4.0) <= 1e-12 and abs(W[ib] @ ln - 4.0) <= 1e-12
    assert np.abs(W.conj().T[:, ia]).max() <= 1e-12 and np.abs(W[:, ib]).max() <= 1e-12
    for g2 in (0.5, 1.0, 2.0):
        Hc = O.closed_block(g2)
        assert Hc.shape == (3, 3) and np.abs(Hc - _ref.rishon_closed_block(g2)).max() <= 1e-12
        r, _ = _ref.closed_eigs(g2)
        assert np.abs(np.sort(np.linalg.eigvalsh(Hc)) - r).max() <= 1e-10
        # the block is the restriction of the full inner Hamiltonian
        B = np.array([np.eye(1296)[ia], ln, np.eye(1296)[ib]])
        Hfull = 0.5 * g2 * np.diag(O.h_electric_inner()) + HB / g2
        assert np.abs(B @ Hfull @ B.T - Hc).max() <= 1e-12
    D = O.det_term_inner()
    assert np.abs(D - D.conj().T).max() <= 1e-12
    flipped = (va & ~0xF) | _ref.CODE_B          # link b: A -> B
    jf = int(np.searchsorted(codes, flipped))
    assert abs(D[jf, ia] - 2.0) <= 1e-12 and np.count_nonzero(np.abs(D[:, ia]) > 1e-12) == 4


@pytest.mark.parametrize("alpha,beta", [(0.37, 0.61), (1.70, 1.00)])
def test_M5_X1_inner_target_properties(alpha, beta):
    """inner_target: unitary 1296x1296 (1e-10); UE(a)UE(b) = UE(a+b); UB(beta) = expm(-i beta H_B^in); step order 1 =
    UB UE, order 2 = UE(a/2) UB UE(a/2); the two orders differ by O(alpha beta); every target commutes with the inner
    Gauss generators (1e-10)."""
    O = _ops()
    HB = O.h_magnetic_inner()
    HE = O.h_electric_inner()
    UE = O.inner_target("UE", alpha, None)
    UB = O.inner_target("UB", None, beta)
    S1 = O.inner_target("step", alpha, beta, order=1)
    S2 = O.inner_target("step", alpha, beta, order=2)
    I = np.eye(1296)
    for U in (UE, UB, S1, S2):
        assert U.shape == (1296, 1296) and U.dtype == np.complex128 and np.abs(U.conj().T @ U - I).max() <= 1e-10
    assert np.abs(UE - np.diag(np.exp(-1j * alpha * HE))).max() <= 1e-12
    assert np.abs(O.inner_target("UE", 0.2, None) @ O.inner_target("UE", 0.3, None) - O.inner_target("UE", 0.5, None)).max() <= 1e-12
    assert np.abs(UB - expm(-1j * beta * HB)).max() <= 1e-10
    assert np.abs(S1 - UB @ UE).max() <= 1e-12
    UEh = O.inner_target("UE", alpha / 2, None)
    assert np.abs(S2 - UEh @ UB @ UEh).max() <= 1e-12
    assert op_norm_after_phase(S1, S2) > 1e-3
    for c in range(4):
        for a in range(3):
            G = O.gauss_inner(c, a)
            assert np.abs(UB @ G - G @ UB).max() <= 1e-10
    with pytest.raises(ValueError):
        O.inner_target("step", alpha, beta, order=3)

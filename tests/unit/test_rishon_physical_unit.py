"""Unit tests for su2plaq.rishon.physical (step 5.2): corner kernels, counts, Gauss, sample, inner span.
No expected totals are hard-coded here: counts are compared between two independent routes inside the module."""
import numpy as np
import pytest

from su2plaq.geometry import plaquette_diagram
from su2plaq.rishon import physical as P
from su2plaq.rishon.algebra import RishonLink


@pytest.fixture(scope="module")
def basis():
    return P.rishon_basis()


def test_shifts():
    D = plaquette_diagram()
    for l in D.inner_links():
        assert P.near_shift(l) == 4 * l and P.far_shift(l) == 4 * l + 2
    for l in D.outer_links():
        near = D.links[l].near_end
        assert P.near_shift(l) == 4 * l + (0 if near == "L" else 2)
        assert {P.near_shift(l) - 4 * l, P.far_shift(l) - 4 * l} == {0, 2}
    with pytest.raises(ValueError):
        P.near_shift(12)
    with pytest.raises(ValueError):
        P.far_shift(-1)


def test_corner_kernel_qq_pair_spin_and_orthonormal():
    tr = (("Q", "out"), ("Q", "in"), ("Q", "out"), ("Q", "in"))
    codes, K, J = P.corner_kernel(tr)
    assert codes == [[1, 2]] * 4 and K.shape == (16, 2) and J == (0.0, 1.0)
    assert np.abs(K.T @ K - np.eye(2)).max() < 1e-13 and K.dtype == np.float64
    for i in range(2):
        v = K[:, i]
        first = np.flatnonzero(np.abs(v) >= np.abs(v).max() - 1e-10)[0]
        assert v[first] > 0


def test_corner_kernel_singlet_pairs_and_empty_cases():
    # two Q ends + two singlet ends: one state, pair spin 0, amplitudes +-1/sqrt2
    codes, K, J = P.corner_kernel((("Q", "out"), ("Q", "in"), ("A", "out"), ("B", "in")))
    assert K.shape == (4, 1) and J == (0.0,)
    assert sorted(np.round(np.abs(K[np.abs(K[:, 0]) > 1e-12, 0]), 12).tolist()) == [round(1 / np.sqrt(2), 12)] * 2
    # one Q end alone cannot make a singlet
    _, K, J = P.corner_kernel((("Q", "out"), ("A", "in"), ("A", "out"), ("B", "in")))
    assert K.shape[1] == 0 and J == ()
    # J = 1/2 on the pair when the other pair is Q + singlet
    _, K, J = P.corner_kernel((("Q", "out"), ("A", "in"), ("Q", "out"), ("B", "in")))
    assert K.shape[1] == 1 and J == (0.5,)


def test_corner_kernel_annihilated_by_generators():
    rl = RishonLink()
    tr = (("Q", "out"), ("Q", "in"), ("Q", "in"), ("A", "out"))
    codes, K, J = P.corner_kernel(tr)
    assert K.shape[1] == 0       # three Q ends: odd spin, no singlet
    tr = (("Q", "out"), ("Q", "in"), ("Q", "out"), ("Q", "in"))
    codes, K, J = P.corner_kernel(tr)
    dims = [len(c) for c in codes]
    for a in range(3):
        G = sum(P._embed_end(P._gen_restricted(a, r, codes[e]), e, dims) for e, (_, r) in enumerate(tr))
        assert np.abs(G @ K).max() < 1e-13
    assert rl is not None


def test_counts_two_routes_agree(basis):
    f = P.count_by_fusion()
    c = P.counts(basis)
    for k in f:
        assert f[k] == c[k]
    assert c["coo_entries"] == sum(len(k) for k in basis.keys)
    assert c["closed"] < c["dim"] and c["u2_sector"] < c["dim"]


def test_basis_states_are_normalised_valid_and_gauss_clean(basis):
    allk = np.concatenate(basis.keys)
    assert allk.dtype == np.int64 and allk.min() >= 0 and allk.max() < 2 ** 48
    assert all(a.dtype == np.complex128 for a in basis.amps[:50])
    norms = np.array([np.linalg.norm(a) for a in basis.amps])
    assert np.abs(norms - 1).max() < 1e-12
    g = P.gauss_residuals_coo(basis.keys, basis.amps)
    assert g.shape == (basis.dim,) and g.max() < 1e-10
    assert abs(P.gauss_residual(basis.keys[5], basis.amps[5]) - g[5]) < 1e-14


def test_gauss_residual_detects_a_violation(basis):
    k = next(i for i in range(basis.dim) if len(basis.keys[i]) > 1)
    keys, amps = basis.keys[k], basis.amps[k].copy()
    assert P.gauss_residual(keys, amps) < 1e-12
    amps[0] *= -1.0                       # breaks the relative sign of the singlet components
    assert P.gauss_residual(keys, amps) > 1e-3


def test_labels_unique_and_index_roundtrip(basis):
    assert len(set(basis.labels)) == basis.dim
    for k in (0, 1, basis.dim // 3, basis.dim - 1):
        assert basis.index(basis.labels[k]) == k
    with pytest.raises(KeyError):
        basis.index((("Q",) + ("A",) * 11, (0.0, 0.0, 0.0, 0.0)))


def test_u1_charges_from_bits(basis):
    q = np.array([basis.u1_charges(k) for k in range(0, basis.dim, 97)])
    assert q.min() >= 0 and q.max() <= 8
    D = basis.diagram
    k = 123
    key = int(basis.keys[k][0])
    for c, corner in enumerate(D.corners):
        occ = sum(bin((key >> (4 * l + (0 if r == "out" else 2))) & 3).count("1") for l, r in corner.ends)
        assert basis.u1_charges(k)[c] == occ


def test_key_helpers():
    keys = np.array([0xABCDE12345 & ((1 << 48) - 1), 7], dtype=np.int64)
    assert np.array_equal(P.RishonBasis.inner_key(keys), keys & 0xFFFF)
    assert np.array_equal(P.RishonBasis.outer_key(keys), keys >> 16)


def test_closed_indices_and_sample(basis):
    cl = P.closed_indices(basis)
    assert len(cl) == len(set(cl)) and len(cl) == 2 ** 4 + 1
    assert basis.labels[cl[0]][0][:4] == ("A", "A", "B", "B") and basis.labels[cl[1]][0][:4] == ("B", "B", "A", "A")
    assert basis.labels[cl[2]][0][:4] == ("Q",) * 4 and len(basis.keys[cl[2]]) == 16
    s = P.sample_indices(basis, 40, 7)
    assert s == P.sample_indices(basis, 40, 7) and len(set(s)) == 40 and not set(s) & set(cl)
    assert s != P.sample_indices(basis, 40, 8)
    with pytest.raises(ValueError):
        P.sample_indices(basis, basis.dim, 1)


def test_inner_span_full_rank_and_orthonormal(basis):
    S = P.inner_span(basis)
    n = S.shape[0]
    assert S.shape[1] == P.inner_span_rank_by_corners() == n
    assert np.abs(S.conj().T @ S - np.eye(n)).max() < 1e-10

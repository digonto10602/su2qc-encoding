"""M5-C1 — rishon physical states: counts by two routes, Gauss, orthonormality, inner span (prompts/200 §2.2, §4;
METHODS-rishon R3; research 200 §4-§5).  Counts are exact; Gauss 1e-10 / norms and Gram 1e-12 as M0-X1."""
import functools

import numpy as np
import pytest
import scipy.sparse as sp

from tests.acceptance._api import api
from tests.acceptance.m5 import _ref


@functools.lru_cache(maxsize=None)
def _basis():
    return api("su2plaq.rishon.physical:rishon_basis")()


def test_M5_C1_counts_two_routes():
    """Route 1 (link types x corner fusion, combinatorial): dim 38 432, closed 4352, 431 U(1) sectors, U(2) sector 2192 —
    production `count_by_fusion` and the independent enumeration here agree.  Route 2: the 433 KS labels of the laptop's
    `physical_basis` weighted by 2^{#j=0} give the same totals.  The built basis has the same counts."""
    P = api("su2plaq.rishon.physical")
    ref = _ref.fusion_counts()
    assert ref["dim"] == _ref.N_PHYS and ref["closed"] == _ref.N_CLOSED
    assert ref["u2_sector"] == _ref.N_U2 and ref["n_u1_sectors"] == _ref.N_U1_SECTORS
    prod = P.count_by_fusion()
    for k in ("dim", "closed", "n_u1_sectors", "u2_sector", "type_patterns"):
        assert prod[k] == ref[k], (k, prod[k], ref[k])
    ks = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    tot, closed = _ref.ks_weighted_count(ks.labels)
    assert (tot, closed) == (_ref.N_PHYS, _ref.N_CLOSED)
    basis = _basis()
    assert basis.dim == _ref.N_PHYS and len(basis.labels) == len(basis.keys) == len(basis.amps) == basis.dim
    c = P.counts(basis)
    for k in ("dim", "closed", "n_u1_sectors", "u2_sector", "type_patterns"):
        assert c[k] == ref[k], (k, c[k], ref[k])
    assert c["coo_entries"] == sum(len(k) for k in basis.keys) and c["max_components"] <= 1296
    assert len({lab[0] for lab in basis.labels}) == ref["type_patterns"]
    assert all(len(lab[0]) == 12 and set(lab[0]) <= {"A", "B", "Q"} and len(lab[1]) == 4 for lab in basis.labels)
    # U(1) charges: sum over corners of Q_c = 2 * (number of near ends) ... each corner charge in 0..8; the all-4 sector count
    q = np.array([basis.u1_charges(k) for k in range(basis.dim)])
    assert q.shape == (basis.dim, 4) and q.min() >= 0 and q.max() <= 8
    assert int(np.sum(np.all(q == 4, axis=1))) == _ref.N_U2 and len({tuple(r) for r in q}) == _ref.N_U1_SECTORS
    # index round trip
    for k in (0, 17, basis.dim // 2, basis.dim - 1):
        assert basis.index(basis.labels[k]) == k


def test_M5_C1_states_gauss_orthonormal(rng):
    """Every state: 48-bit int64 keys that are valid codes (two rishons per link, far ends fixed), unit norm (1e-12);
    production Gauss residual <= 1e-10 on all states; the independent 2-qubit end operators give <= 1e-10 on 200 seeded
    states; 500 seeded pairs orthogonal (1e-12); the 17 closed reference states and the seeded sample are as specified."""
    P = api("su2plaq.rishon.physical")
    basis = _basis()
    assert (P.N_QUBITS, P.N_DATA, P.N_OUTER) == (48, 16, 32)
    allk = np.concatenate(basis.keys)
    assert allk.dtype == np.int64 and allk.min() >= 0 and allk.max() < 2 ** 48
    norms = np.array([np.linalg.norm(a) for a in basis.amps])
    assert np.abs(norms - 1).max() <= 1e-12
    assert np.array_equal(P.RishonBasis.inner_key(allk[:10]), allk[:10] & 0xFFFF)
    assert np.array_equal(P.RishonBasis.outer_key(allk[:10]), allk[:10] >> 16)
    sel = rng.integers(0, basis.dim, size=300)
    assert all(_ref.valid_code(int(c)) for k in sel for c in basis.keys[k])
    g = P.gauss_residuals_coo(basis.keys, basis.amps)
    assert g.shape == (basis.dim,) and g.max() <= 1e-10
    worst = max(_ref.gauss_residual(basis.keys[k], basis.amps[k]) for k in sel[:200])
    assert worst <= 1e-10
    assert abs(P.gauss_residual(basis.keys[0], basis.amps[0]) - g[0]) <= 1e-14
    for _ in range(500):
        i, k = rng.integers(0, basis.dim, size=2)
        if i == k:
            continue
        common, ii, kk = np.intersect1d(basis.keys[i], basis.keys[k], return_indices=True)
        assert abs(np.vdot(basis.amps[i][ii], basis.amps[k][kk])) <= 1e-12
    # closed reference states: outer links near-end-empty; vac_A, vac_B, loop first
    cl = P.closed_indices(basis)
    assert len(cl) == 17 and len(set(cl)) == 17
    outer = _ref.outer_near_empty_code()
    va, vb = _ref.vac_codes()
    for k in cl:
        assert np.all(basis.keys[k] >> 16 == outer >> 16)
    assert basis.keys[cl[0]].tolist() == [va | outer] and basis.keys[cl[1]].tolist() == [vb | outer]
    loop_keys = basis.keys[cl[2]]
    assert len(loop_keys) == 16 and all(_ref.types_of(int(c) & 0xFFFF) == ("Q",) * 4 for c in loop_keys)
    assert np.abs(np.abs(basis.amps[cl[2]]) - 0.25).max() <= 1e-12
    assert basis.labels[cl[0]][0][:4] == ("A", "A", "B", "B") and basis.labels[cl[1]][0][:4] == ("B", "B", "A", "A")
    for k in cl[3:]:
        assert set(basis.labels[k][0][:4]) <= {"A", "B"} and len(basis.keys[k]) == 1
    s1 = P.sample_indices(basis, 256, 20261104)
    s2 = P.sample_indices(basis, 256, 20261104)
    assert s1 == s2 and len(s1) == 256 and len(set(s1)) == 256 and not (set(s1) & set(cl))
    assert P.sample_indices(basis, 256, 1) != s1


def test_M5_C1_inner_span_full():
    """The span of the inner components of all physical states (over every outer pattern) is the whole 1296-dim code
    space: corner factorisation gives 1296; `inner_span` is a 1296x1296 orthonormal basis; an independent Gram
    accumulation over all states has rank 1296."""
    P = api("su2plaq.rishon.physical")
    O = api("su2plaq.rishon.operators")
    basis = _basis()
    assert P.inner_span_rank_by_corners() == 1296
    S = P.inner_span(basis)
    assert S.shape == (1296, 1296) and np.abs(S.conj().T @ S - np.eye(1296)).max() <= 1e-10
    codes = O.inner_codes()
    assert np.array_equal(codes, _ref.inner_codes())
    pos = {int(c): i for i, c in enumerate(codes)}
    rows, cols, vals, col = [], [], [], 0
    for keys, amps in zip(basis.keys, basis.amps):
        outer = keys >> 16
        inner = keys & 0xFFFF
        for o in np.unique(outer):
            m = outer == o
            rows.extend(pos[int(c)] for c in inner[m])
            cols.extend([col] * int(m.sum()))
            vals.extend(amps[m])
            col += 1
    Z = sp.csr_matrix((np.array(vals), (np.array(rows), np.array(cols))), shape=(1296, col))
    G = (Z @ Z.conj().T).toarray()
    w = np.linalg.eigvalsh((G + G.conj().T) / 2)
    assert int(np.sum(w > 1e-9 * w.max())) == 1296

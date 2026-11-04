"""M0-C1..C6, M0-X1 — physical states by corner singlets (prompts/002 §2.3, METHODS §4).
Reference numbers are the note's counts (refs/su2_plaquette_truncations_encodings.md §5), reproduced here by an
independent code path; this file never imports refs/su2_plaquette_encodings.py."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import api


@functools.lru_cache(maxsize=None)
def _basis():
    return api("su2plaq.exact.physical:physical_basis")(jmax=0.5, convention="cg")


def test_M0_C1_dimension():
    """433 physical states (route A) = 433 route-B labels; labels unique and identical as sets. Exact."""
    basis = _basis()
    assert basis.dim == 433 and len(basis.labels) == 433 and len(basis.keys) == 433
    assert len(set(basis.labels)) == 433
    labs_B = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    assert len(labs_B) == 433 and set(labs_B) == set(basis.labels)
    # every label: 12 link spins in {0, 1/2}, 4 corner spins in {0, 1/2, 1}
    for j, J in basis.labels:
        assert len(j) == 12 and len(J) == 4
        assert set(j) <= {0.0, 0.5} and set(J) <= {0.0, 0.5, 1.0}
    # convention change is a signed permutation of local indices: round trip and Gauss law in Paulo's convention
    to_conv = api("su2plaq.exact.physical:to_convention")
    bp = to_conv(basis, "paulo")
    assert bp.convention == "paulo" and bp.dim == 433
    back = to_conv(bp, "cg")
    for k in range(433):
        order_a = np.argsort(basis.keys[k])
        order_b = np.argsort(back.keys[k])
        assert np.array_equal(basis.keys[k][order_a], back.keys[k][order_b])
        assert np.abs(basis.amps[k][order_a] - back.amps[k][order_b]).max() <= 1e-14
    gres = api("su2plaq.exact.physical:gauss_residuals")(bp)
    assert gres.max() <= 1e-10


def test_M0_C2_closed():
    """Closed plaquette (all outer j = 0): exactly 2 states, labels vacuum and all-half with J = 0. Exact."""
    basis = _basis()
    counts = api("su2plaq.exact.physical:counts")(basis)
    assert counts["closed"] == 2
    closed = [lab for lab in basis.labels if all(x == 0.0 for x in lab[0][4:])]
    assert sorted(closed) == sorted([((0.0,) * 12, (0.0,) * 4), ((0.5, 0.5, 0.5, 0.5) + (0.0,) * 8, (0.0,) * 4)])


def test_M0_C3_link_strings():
    """256 distinct link-spin strings among the 433 states. Exact."""
    basis = _basis()
    counts = api("su2plaq.exact.physical:counts")(basis)
    assert counts["link_strings"] == 256 == len({lab[0] for lab in basis.labels})


def test_M0_C4_ambiguous():
    """95 link-spin strings carry more than one state (a corner with two singlets). Exact."""
    basis = _basis()
    counts = api("su2plaq.exact.physical:counts")(basis)
    mult = {}
    for lab in basis.labels:
        mult[lab[0]] = mult.get(lab[0], 0) + 1
    assert counts["ambiguous"] == 95 == sum(1 for v in mult.values() if v > 1)


def test_M0_C5_far_end_weighted():
    """Far-end-free Hilbert-space dimension sum_k prod_outer (2j+1) = 17 362. Exact."""
    basis = _basis()
    counts = api("su2plaq.exact.physical:counts")(basis)
    weighted = sum(int(np.prod([2 * j + 1 for j in lab[0][4:]])) for lab in basis.labels)
    assert counts["far_end_weighted"] == 17362 == weighted
    assert counts["dim"] == 433


@pytest.mark.slow
def test_M0_C6_jmax1_count_slow():
    """j_max = 1: 65 250 open spin-network labels (route B), 3 closed. Exact (note §5)."""
    labs = api("su2plaq.exact.spinnet:labels")(jmax=1.0)
    assert len(labs) == 65250
    assert sum(1 for lab in labs if all(x == 0.0 for x in lab[0][4:])) == 3


def test_M0_X1_gauss_and_gram():
    """Gauss residual max_{c,a} ||G^a_c psi_k|| <= 1e-10 for every state (kernels from eigh on <= 16-dim matrices,
    residual ~1e-15, products of 4 corners); Gram matrix = identity to 1e-12."""
    basis = _basis()
    gres = api("su2plaq.exact.physical:gauss_residuals")(basis)
    assert gres.shape == (433,) and gres.max() <= 1e-10
    G = api("su2plaq.exact.physical:gram")(basis)
    assert np.abs(G - np.eye(433)).max() <= 1e-12
    # amplitudes are real in the CG convention with the positive-largest-component phase
    assert max(np.abs(a.imag).max() for a in basis.amps) <= 1e-14
    # every state has <= 1296 components and keys inside 5^12
    assert all(0 < len(k) <= 1296 for k in basis.keys)
    assert all(k.dtype == np.int64 and k.min() >= 0 and k.max() < 5 ** 12 for k in basis.keys)

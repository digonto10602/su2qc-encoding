"""Unit tests for su2plaq.exact.physical (own checks)."""
import numpy as np
import pytest

from su2plaq.exact.physical import (apply_link_op, corner_singlets, counts, gauss_residual, inner_span,
                                    physical_basis, s_o_dims, to_convention)
from su2plaq.su2.algebra import LinkSpace


def test_corner_singlet_counts_and_phase():
    # (1/2,1/2 | 1/2,1/2): J=0 and J=1 singlets; (1/2,1/2|0,0): only J=0 (outer pair is a singlet); (0,0|0,0): one
    v, Js = corner_singlets((0.5, 0.5, 0.5, 0.5), ("out", "out", "in", "in"))
    assert Js == (0.0, 1.0) and v.shape == (16, 2)
    v2, Js2 = corner_singlets((0.5, 0.5, 0.0, 0.0), ("out", "out", "in", "in"))
    assert Js2 == (0.0,) and v2.shape == (16 // 4, 1)
    v3, Js3 = corner_singlets((0.5, 0.0, 0.0, 0.0), ("out", "out", "in", "in"))
    assert v3.shape[1] == 0
    for col in v.T:
        assert col[np.argmax(np.abs(col))] > 0 and abs(np.linalg.norm(col) - 1) < 1e-14


def test_closed_states_and_counts():
    b = physical_basis()
    c = counts(b)
    assert c["closed"] == 2 and c["dim"] == b.dim == len(b.keys)
    vac = b.index(((0.0,) * 12, (0.0,) * 4))
    assert list(b.keys[vac]) == [0] and abs(b.amps[vac][0] - 1) < 1e-14


def test_apply_link_op_identity_and_coalesce():
    b = physical_basis()
    k = b.keys[100]
    kk, aa = apply_link_op(k, b.amps[100], 3, np.eye(5))
    order = np.argsort(k)
    assert np.array_equal(kk, k[order]) and np.abs(aa - b.amps[100][order]).max() < 1e-15


def test_gauss_detects_violation():
    b = physical_basis()
    # a single basis vector with a lone half link is not gauge invariant
    keys = np.array([LinkSpace(0.5).index[(0.5, 0.5, 0.5)]], dtype=np.int64)
    assert gauss_residual(b, keys, np.ones(1, dtype=complex)) > 0.1


def test_convention_round_trip_preserves_norm():
    b = physical_basis()
    bp = to_convention(b, "paulo")
    assert bp is physical_basis(convention="paulo") or bp.convention == "paulo"
    for a, ap in zip(b.amps[:20], bp.amps[:20]):
        assert abs(np.linalg.norm(a) - np.linalg.norm(ap)) < 1e-14


def test_inner_span_rank_bounds():
    b = physical_basis()
    S = inner_span(b)
    assert S.shape[0] == 625 and 0 < S.shape[1] <= 625
    assert np.abs(S.conj().T @ S - np.eye(S.shape[1])).max() < 1e-12
    dims = s_o_dims(b)
    assert all(1 <= v <= 625 for v in dims.values())


def test_jmax_one_not_supported_for_route_a():
    with pytest.raises(NotImplementedError):
        physical_basis(jmax=1.0)

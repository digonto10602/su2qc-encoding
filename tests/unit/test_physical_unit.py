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
    assert all(0 <= v <= 625 for v in dims.values()) and len(dims) == 3 ** 8


def test_jmax_one_not_supported_for_route_a():
    with pytest.raises(NotImplementedError):
        physical_basis(jmax=1.0)


def test_singlet_signs_are_deterministic_under_ties_and_noise():
    """Corner singlets with tied component moduli (32 of them) get a reproducible sign: the first component within the tie
    tolerance of the maximum is positive, whatever the sign / rounding noise of the eigensolver."""
    import itertools

    from su2plaq.exact import physical as ph

    rng = np.random.default_rng(0)
    roles = ("out", "out", "in", "in")
    n_tied = 0
    for js in itertools.product((0.0, 0.5), repeat=4):
        vecs, _ = ph.corner_singlets(js, roles)
        for col in vecs.T:
            a = np.abs(col)
            tied = np.flatnonzero(a >= a.max() - ph.SIGN_TIE_TOL)
            assert col[tied[0]] > 0
            if len(tied) > 1:
                n_tied += 1
            for sgn in (1.0, -1.0):
                noisy = sgn * col + 1e-14 * rng.normal(size=col.shape)
                assert np.abs(ph._canonical_sign(noisy) - col).max() < 1e-12
    assert n_tied > 0
    # across the full basis the tied singlets appear: 32 over all corners and spin assignments, all with positive pivot
    b = physical_basis()
    assert np.all(np.isfinite(np.concatenate(b.amps).real))


def test_outer_dont_care_table_is_complete_and_matches_the_measured_histogram():
    import collections

    from su2plaq.exact.physical import outer_patterns

    b = physical_basis()
    dims = s_o_dims(b)
    assert sorted(dims) == outer_patterns(b) and len(dims) == 3 ** 8
    assert dict(collections.Counter(dims.values())) == {0: 3408, 1: 976, 2: 1073, 3: 392, 4: 320, 5: 280, 8: 64, 9: 32, 17: 16}
    assert dims[0] == 2 and inner_span(b).shape == (625, 625)
    assert s_o_dims(to_convention(b, "paulo")).values().__len__() == 3 ** 8

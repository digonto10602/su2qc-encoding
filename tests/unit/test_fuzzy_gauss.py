"""Unit tests for fuzzy Gauss law, counts and seeded physical states."""
import numpy as np
import pytest

from su2plaq.fuzzy import gauss as gz
from su2plaq.fuzzy import link as lk


def test_corner_singlet_dim():
    assert gz.corner_singlet_dim(0.5, 0.5, 0.5, 0.5) == 2
    assert gz.corner_singlet_dim(0, 0, 0, 0) == 1
    assert gz.corner_singlet_dim(1, 0, 0.5, 0.5) == 1
    assert gz.corner_singlet_dim(1, 1, 1, 1) == 3
    assert gz.corner_singlet_dim(0.5, 0, 0, 0) == 0


def test_counts():
    assert gz.isolated_plaquette_count() == 50
    assert gz.physical_count(False, outer_vacuum=True) == 12800
    assert gz.physical_count(False) == 101_197_218
    assert gz.physical_count(True) == 6_767_266_914
    assert gz.physical_count_characters(False, n_points=24) == pytest.approx(101_197_218, abs=1e-2)


def test_corner_spin_matrices_su2():
    for t in (0, 1, 2):
        J = gz._spin_mats(t)
        assert np.allclose(J[0] @ J[1] - J[1] @ J[0], 1j * J[2])
        C = sum(j @ j for j in J)
        assert np.allclose(C, t / 2 * (t / 2 + 1) * np.eye(t + 1))


def test_link_irrep_basis_standard_matrices():
    for jl2, jr2, f in gz._resolve_copies():
        E = gz._link_irrep_basis(jl2, jr2, f)
        flat = E.reshape(-1, 16)
        assert np.allclose(flat.conj() @ flat.T, np.eye(len(flat)), atol=1e-12)
        JL, JR = gz._spin_mats(jl2), gz._spin_mats(jr2)
        for A in range(3):
            lhs = np.einsum("ij,abj->abi", lk.calT_L(A), E)
            rhs = np.einsum("ac,cbi->abi", JL[A].T, E)   # T e_a = sum_c e_c J_{ca}
            assert np.allclose(lhs, rhs, atol=1e-12)
            lhs = np.einsum("ij,abj->abi", lk.calT_R(A), E)
            rhs = np.einsum("bc,aci->abi", JR[A].T, E)
            assert np.allclose(lhs, rhs, atol=1e-12)


def test_copies_resolved():
    assert len(gz._resolve_copies()) == 6


def test_gauss_residual_detects_flux_and_accepts_vacuum_link_states():
    # single non-invariant link state: matrix unit E_{3,0} on link b with all others in identity: build a tiny COO
    keys = np.array([0b1100], dtype=np.int64)
    amps = np.array([1.0 + 0j])
    assert gz.gauss_residual(keys, amps) > 0.1
    # zero vector
    assert gz.gauss_residual(np.zeros(0, np.int64), np.zeros(0, complex)) == 0.0


def test_sample_physical_states_seeded():
    s1 = gz.sample_physical_states(4, 11)
    s2 = gz.sample_physical_states(4, 11)
    s3 = gz.sample_physical_states(4, 12)
    for (k1, a1), (k2, a2) in zip(s1, s2):
        assert np.array_equal(k1, k2) and np.allclose(a1, a2)
        assert abs(np.linalg.norm(a1) - 1) < 1e-12 and gz.gauss_residual(k1, a1) < 1e-10 and len(k1) <= 4096
    assert not all(np.array_equal(x[0], y[0]) for x, y in zip(s1, s3))


def test_generator_hermitian_on_basis_states():
    """Matrix elements <i|G^A_c|j> = conj(<j|G^A_c|i>) between computational basis states."""
    basis = [np.array([k], dtype=np.int64) for k in (0b0001, 0b0100, 0b1000, 0b0010, 0b1001)]
    for c in range(4):
        for A in range(3):
            for ki in basis:
                for kj in basis:
                    gj = gz.corner_generator_apply(c, A, kj, np.ones(1, complex))
                    gi = gz.corner_generator_apply(c, A, ki, np.ones(1, complex))
                    mij = gj[1][gj[0] == ki[0]].sum()
                    mji = gi[1][gi[0] == kj[0]].sum()
                    assert abs(mij - np.conj(mji)) < 1e-14

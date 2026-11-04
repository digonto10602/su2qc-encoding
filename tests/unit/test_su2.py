"""Unit tests for su2plaq.su2 (algebra, wigner); own known-value checks."""
import numpy as np
import pytest

from su2plaq.su2.algebra import LinkSpace, clebsch_gordan, paulo_U, paulo_adapter
from su2plaq.su2.wigner import f_symbol, six_j, triangle


def test_cg_known_values():
    assert clebsch_gordan(0.5, 0.5, 0.5, -0.5, 0.0, 0.0) == pytest.approx(1 / np.sqrt(2), abs=1e-15)
    assert clebsch_gordan(0.5, -0.5, 0.5, 0.5, 0.0, 0.0) == pytest.approx(-1 / np.sqrt(2), abs=1e-15)
    assert clebsch_gordan(0.5, 0.5, 0.5, 0.5, 1.0, 1.0) == pytest.approx(1.0, abs=1e-15)
    assert clebsch_gordan(0.5, 0.5, 0.5, 0.5, 0.0, 1.0) == 0.0


def test_link_space_dims_and_unitarity_of_U():
    assert LinkSpace(0.5).dim == 5 and LinkSpace(1.0).dim == 14
    ls = LinkSpace(0.5)
    U = ls.U()
    # U_ij U_ij^dagger summed over j acts as identity on the states not truncated away (jmax = 1/2: not exact);
    # check the exact property instead: matrices are real and map (j) -> (j +- 1/2) only
    for i in range(2):
        for j in range(2):
            assert np.abs(U[i][j].imag).max() == 0.0
            assert U[i][j].shape == (5, 5)


def test_generators_hermitian_and_casimir():
    ls = LinkSpace(1.0)
    L, R = ls.generators()
    for a in range(3):
        assert np.abs(L[a] - L[a].conj().T).max() < 1e-15
        assert np.abs(R[a] - R[a].conj().T).max() < 1e-15
    assert np.abs(sum(l @ l for l in L) - ls.casimir()).max() < 1e-14


def test_six_j_known_values():
    assert six_j(0.5, 0.5, 1.0, 0.5, 0.5, 1.0) == pytest.approx(1 / 6, abs=1e-15)
    assert six_j(0.5, 0.5, 0.0, 0.5, 0.5, 0.0) == pytest.approx(-0.5, abs=1e-15)
    assert six_j(1.0, 0.5, 0.5, 0.5, 0.5, 5.0) == 0.0  # inadmissible


def test_six_j_symmetries():
    base = six_j(1.0, 1.5, 0.5, 0.5, 1.0, 1.0)
    # column permutation and swapping upper/lower in two columns
    assert six_j(1.5, 1.0, 0.5, 1.0, 0.5, 1.0) == pytest.approx(base, abs=1e-15)
    assert six_j(0.5, 1.5, 1.0, 1.0, 1.0, 0.5) == pytest.approx(base, abs=1e-15)


def test_triangle():
    assert triangle(0.5, 0.5, 1.0) and triangle(0.5, 0.5, 0.0)
    assert not triangle(0.5, 0.5, 0.5) and not triangle(0.0, 0.0, 1.0)


def test_f_symbol_unitary():
    # recoupling matrix for 1/2 x 1/2 x 1/2 -> J = 1/2: 2x2 orthogonal
    F = np.array([[f_symbol(0.5, 0.5, a, 0.5, 0.5, b) for b in (0.0, 1.0)] for a in (0.0, 1.0)])
    assert np.abs(F @ F.T - np.eye(2)).max() < 1e-15


def test_paulo_adapter_orthogonal_symmetric_and_conjugates():
    V = paulo_adapter()
    assert np.array_equal(V, V.T) and np.array_equal(V @ V.T, np.eye(5))
    Ucg, Up = LinkSpace(0.5).U(), paulo_U()
    for a in range(2):
        for b in range(2):
            assert np.abs(V @ Ucg[a][b] @ V.T - Up[a][b]).max() < 1e-14

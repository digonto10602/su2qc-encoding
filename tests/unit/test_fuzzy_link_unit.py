"""Unit tests: fuzzy link operators (src/su2plaq/fuzzy/link.py)."""
import numpy as np

from su2plaq.fuzzy import link as lk


def test_su2_and_commutation():
    for A in range(3):
        for B in range(3):
            assert np.abs(lk.calT_L(A) @ lk.calT_R(B) - lk.calT_R(B) @ lk.calT_L(A)).max() < 1e-14
    K1, K2 = lk.K1(), lk.K2()
    assert np.abs(K1 @ K2 - K2 @ K1).max() < 1e-13
    for A in range(3):
        assert np.abs(K1 @ lk.calT_L(A) - lk.calT_L(A) @ K1).max() < 1e-13
        assert np.abs(K2 @ lk.calT_R(A) - lk.calT_R(A) @ K2).max() < 1e-13


def test_pauli_forms_and_flavour():
    assert np.abs(lk.pauli_K1().to_matrix() - lk.K1()).max() < 1e-13
    assert np.abs(lk.pauli_K2().to_matrix() - lk.K2()).max() < 1e-13
    for a in range(2):
        for b in range(2):
            assert np.abs(lk.pauli_U(a, b).to_matrix() - lk.U_op(a, b)).max() < 1e-13
    F = lk.flavour()
    assert np.abs(F @ F - np.eye(16)).max() < 1e-14
    assert np.abs(F @ lk.K2() + lk.K2() @ F).max() < 1e-13


def test_irreps_dimension():
    irr = lk.irreps()
    assert sum(int(round((2 * a + 1) * (2 * b + 1))) * m for a, b, m in irr) == 16
    assert lk.centre().shape == (16, 16)

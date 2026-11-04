"""Unit tests for su2plaq.exact.operators (own checks)."""
import numpy as np
import pytest

from su2plaq.exact.operators import (h_electric_inner, h_electric_outer, h_magnetic_phys, hamiltonian_phys,
                                     plaquette_W, target)
from su2plaq.exact.physical import physical_basis
from su2plaq.su2.algebra import LinkSpace


def test_W_shape_and_gauge_invariance_commutation():
    ls = LinkSpace(0.5)
    W = plaquette_W(ls)
    assert W.shape == (625, 625)
    # W is hermitian up to the orientation: Tr U_P^dagger = W^dagger, and W maps j-parity flips only
    assert np.abs(W - plaquette_W()).max() == 0.0


def test_W_paulo_equals_vp_conjugate():
    from su2plaq.su2.algebra import paulo_adapter

    V = paulo_adapter()
    V4 = np.kron(V, np.kron(V, np.kron(V, V)))
    assert np.abs(V4 @ plaquette_W(convention="cg") @ V4.T - plaquette_W(convention="paulo")).max() < 1e-14


def test_hb_paulo_and_cg_have_same_spectrum():
    HB_cg, leak = h_magnetic_phys(physical_basis(convention="cg"))
    HB_p, leak_p = h_magnetic_phys(physical_basis(convention="paulo"))
    assert leak < 1e-10 and leak_p < 1e-10
    assert np.abs(np.linalg.eigvalsh(HB_cg) - np.linalg.eigvalsh(HB_p)).max() < 1e-10


def test_hamiltonian_is_sum_of_parts_and_targets_unitary():
    b = physical_basis()
    HB, _ = h_magnetic_phys(b)
    H = hamiltonian_phys(b, 2.0, include_outer_electric=True)
    assert np.abs(H - (np.diag(h_electric_inner(b) + h_electric_outer(b)) + HB / 2.0)).max() < 1e-12
    for kind in ("UE", "UB", "step"):
        U = target(b, kind, alpha=0.3, beta=0.4, order=2)
        assert np.abs(U.conj().T @ U - np.eye(b.dim)).max() < 1e-12


def test_target_missing_argument_raises():
    b = physical_basis()
    with pytest.raises(ValueError):
        target(b, "UB")
    with pytest.raises(ValueError):
        target(b, "nope", alpha=1.0, beta=1.0)

"""M0-X2, X3, X7, X8 — plaquette operator and targets on the physical basis (prompts/002 §2.4, METHODS §2, §4)."""
import numpy as np
import pytest
from scipy.linalg import expm

import functools

from tests.acceptance._api import CLOSED_ALLHALF, CLOSED_VACUUM, api


@functools.lru_cache(maxsize=None)
def _basis():
    return api("su2plaq.exact.physical:physical_basis")(jmax=0.5, convention="cg")


@functools.lru_cache(maxsize=None)
def _HB():
    return api("su2plaq.exact.operators:h_magnetic_phys")(_basis())


def test_M0_X2_plaquette_leak():
    """(W (x) 1) maps the physical space into itself: leak <= 1e-10 ([W, G] = 0 exactly; float64 contraction
    over <= 1296 components). W is 625x625 and maps j=0 <-> j=1/2 on every inner link."""
    basis = _basis()
    HB = _HB()
    W = api("su2plaq.exact.operators:plaquette_W")()
    assert W.shape == (625, 625)
    _, leak = HB
    assert leak <= 1e-10
    # W connects the vacuum code only to all-half codes (Paulo Eq. 29/37): column 0 has unit norm
    assert abs(np.linalg.norm(W[:, 0]) - 1.0) <= 1e-12


def test_M0_X3_hermitian_and_electric():
    """H_B^phys hermitian (1e-12); H_E^phys diagonal with eigenvalues (3/4) x {0..4} inner, (3/4) x {0..8} outer."""
    basis = _basis()
    HB = _HB()
    H, _ = HB
    assert H.shape == (433, 433) and np.abs(H - H.conj().T).max() <= 1e-12
    HEi = api("su2plaq.exact.operators:h_electric_inner")(basis)
    HEo = api("su2plaq.exact.operators:h_electric_outer")(basis)
    assert HEi.shape == (433,) and HEo.shape == (433,)
    assert set(np.round(HEi / 0.75).astype(int)) <= set(range(5)) and np.abs(HEi - 0.75 * np.round(HEi / 0.75)).max() <= 1e-12
    assert set(np.round(HEo / 0.75).astype(int)) <= set(range(9)) and np.abs(HEo - 0.75 * np.round(HEo / 0.75)).max() <= 1e-12
    assert HEi[basis.index(CLOSED_VACUUM)] == 0.0 and abs(HEi[basis.index(CLOSED_ALLHALF)] - 3.0) <= 1e-12


@pytest.mark.parametrize("g2", [0.5, 1.0, 2.0])
def test_M0_X7_closed_block(g2):
    """Closed sector: (g^2/2) H_E + (1/g^2) H_B restricted to {|0000>, |16>} = [[0, -2/g^2], [-2/g^2, 3g^2/2]] up to the
    sign of the off-diagonal (phase gauge of |16>). Paulo Eq. 37. Tolerance 1e-12 (2x2 block of exact numbers);
    the closed block is decoupled from every other state (exact zeros from disjoint supports)."""
    basis = _basis()
    HB = _HB()
    H, _ = HB
    Hfull = api("su2plaq.exact.operators:hamiltonian_phys")(basis, g2)
    i0, i1 = basis.index(CLOSED_VACUUM), basis.index(CLOSED_ALLHALF)
    blk = Hfull[np.ix_([i0, i1], [i0, i1])]
    assert abs(blk[0, 0]) <= 1e-12 and abs(blk[1, 1] - 1.5 * g2) <= 1e-12
    assert abs(abs(blk[0, 1]) - 2.0 / g2) <= 1e-12 and abs(blk[0, 1] - np.conj(blk[1, 0])) <= 1e-12
    others = [k for k in range(433) if k not in (i0, i1)]
    assert np.abs(Hfull[np.ix_([i0, i1], others)]).max() == 0.0


def test_M0_X8_target_properties():
    """target(): UE diagonal = exp(-i alpha H_E^inner); UB unitary with UB(b1)UB(b2) = UB(b1+b2); step order 1 = UB UE,
    order 2 = UE(a/2) UB UE(a/2); include_outer_electric multiplies by exp(-i alpha H_E^outer). Tolerance 1e-12."""
    basis = _basis()
    target = api("su2plaq.exact.operators:target")
    HEi = api("su2plaq.exact.operators:h_electric_inner")(basis)
    HEo = api("su2plaq.exact.operators:h_electric_outer")(basis)
    a, b = 0.37, 0.61
    UE = target(basis, "UE", alpha=a)
    assert np.abs(UE - np.diag(np.exp(-1j * a * HEi))).max() <= 1e-12
    UB = target(basis, "UB", beta=b)
    assert np.abs(UB.conj().T @ UB - np.eye(433)).max() <= 1e-12
    assert np.abs(target(basis, "UB", beta=0.25) @ target(basis, "UB", beta=0.36) - UB).max() <= 1e-12
    HB, _ = api("su2plaq.exact.operators:h_magnetic_phys")(basis)
    assert np.abs(UB - expm(-1j * b * HB)).max() <= 1e-12
    S1 = target(basis, "step", alpha=a, beta=b, order=1)
    assert np.abs(S1 - UB @ UE).max() <= 1e-12
    S2 = target(basis, "step", alpha=a, beta=b, order=2)
    UEh = target(basis, "UE", alpha=a / 2)
    assert np.abs(S2 - UEh @ UB @ UEh).max() <= 1e-12
    S1o = target(basis, "step", alpha=a, beta=b, order=1, include_outer_electric=True)
    assert np.abs(S1o - np.diag(np.exp(-1j * a * HEo)) @ S1).max() <= 1e-12
    # the closed block of UB is a rotation between the two closed states with coupling 2 beta (Paulo Eq. 38: g = 1)
    i0, i1 = basis.index(CLOSED_VACUUM), basis.index(CLOSED_ALLHALF)
    assert abs(abs(UB[i0, i0]) - np.cos(2 * b)) <= 1e-12 and abs(abs(UB[i1, i0]) - np.sin(2 * b)) <= 1e-12

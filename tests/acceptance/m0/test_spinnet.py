"""M0-X4, X5, X6 — route B (spin network, 6j) vs route A; outer-block structure; J conservation
(prompts/002 §2.4, METHODS §5). Settles plan-001 claim (ii): Paulo's Fig. 2 holds in the (inner|outer) pairing."""
import numpy as np
import pytest

import functools

from tests.acceptance._api import CLOSED_ALLHALF, CLOSED_VACUUM, api


@functools.lru_cache(maxsize=None)
def _routes():
    basis = api("su2plaq.exact.physical:physical_basis")(jmax=0.5, convention="cg")
    HB_A, _ = api("su2plaq.exact.operators:h_magnetic_phys")(basis)
    HE_A = np.diag(api("su2plaq.exact.operators:h_electric_inner")(basis))
    labs = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    HB_B = api("su2plaq.exact.spinnet:h_magnetic_phys_6j")(labs)
    HE_B = api("su2plaq.exact.spinnet:h_electric_6j")(labs)
    perm = np.array([basis.index(lab) for lab in labs])            # align route A to route-B label order
    return basis, labs, HB_A[np.ix_(perm, perm)], HE_A[np.ix_(perm, perm)], HB_B, HE_B, perm


def test_M0_X4_spectra_A_vs_B():
    """Spectra of (g^2/2) H_E + (1/g^2) H_B agree between the electric-basis construction (A) and the 6j
    construction (B) at g^2 in {0.5, 1, 2}; also the spectrum of H_B alone. Tolerance 1e-10 (eigvalsh on 433x433,
    condition number O(10))."""
    routes = _routes()
    basis, labs, HB_A, HE_A, HB_B, HE_B, perm = routes
    assert HB_B.shape == (433, 433) and np.abs(HB_B - HB_B.conj().T).max() <= 1e-12
    assert np.abs(HE_A - HE_B).max() <= 1e-12
    worst = api("su2plaq.exact.compare:spectra_match")(HE_A, HB_A, HE_B, HB_B, (0.5, 1.0, 2.0))
    assert worst <= 1e-10
    eA, eB = np.linalg.eigvalsh(HB_A), np.linalg.eigvalsh(HB_B)
    assert np.abs(eA - eB).max() <= 1e-10
    # H_B eigenvalues lie in [-2, 2] (bright pairs with couplings 2g, g in {1, 1/2, 1/4}) and 0 for the dark states
    assert eA.min() >= -2 - 1e-10 and eA.max() <= 2 + 1e-10


def test_M0_X5_outer_block_structure_and_J():
    """H_B^phys (route A) is block-diagonal in the 8 outer spins (128 blocks; structural zeros exact), conserves
    the corner spins J (<= 1e-12), and every block equals the restriction of the single 47x47 K_inner up to a
    diagonal gauge (gauge residual <= 1e-10, |block| = |K| to 1e-12). This is Paulo's Fig. 2 claim; the note's
    'depends on the outer links' holds only in other intertwiner pairings (research 001 §1.3)."""
    routes = _routes()
    basis, labs, HB_A, HE_A, HB_B, HE_B, perm = routes
    K = api("su2plaq.exact.spinnet:K_inner")(jmax=0.5)
    inner_labels = api("su2plaq.exact.spinnet:inner_labels")(jmax=0.5)
    assert K.shape == (47, 47) and len(inner_labels) == 47 and np.abs(K - K.T).max() <= 1e-12
    # independent structural checks on route A in route-B label order
    outer = [lab[0][4:] for lab in labs]
    Jl = [lab[1] for lab in labs]
    n = 433
    off = max(abs(HB_A[i, k]) for i in range(n) for k in range(n) if outer[i] != outer[k])
    assert off == 0.0
    jviol = max(abs(HB_A[i, k]) for i in range(n) for k in range(n) if Jl[i] != Jl[k])
    assert jviol <= 1e-12
    assert len(set(outer)) == 128
    info = api("su2plaq.exact.compare:outer_block_structure")(HB_A, basis, K)
    assert info["max_offblock"] == 0.0 and info["max_J_violation"] <= 1e-12
    assert info["n_blocks"] == 128 and sum(info["block_dims"]) == 433 and min(info["block_dims"]) == 2 and max(info["block_dims"]) == 17
    assert info["worst_abs_diff"] <= 1e-12 and info["worst_gauge_residual"] <= 1e-10
    # dark labels: any corner with J = 1 is annihilated (31 of 47); bright labels: 16
    dark = [i for i, lab in enumerate(inner_labels) if np.abs(K[i]).max() <= 1e-12]
    assert len(dark) == 31 and all(1.0 in inner_labels[i][1] for i in dark)
    assert all(1.0 not in lab[1] for i, lab in enumerate(inner_labels) if i not in dark)
    # the physical block with that structure is the same in route B by construction
    assert max(abs(HB_B[i, k]) for i in range(n) for k in range(n) if outer[i] != outer[k]) == 0.0


def test_M0_X6_gauge_align_K():
    """Route A equals route B up to a diagonal unitary (phase gauge of the spin-network states): gauge_align residual
    <= 1e-10, D real (+-1). Vacuum <-> all-half (J = 0) element of K has modulus 2 (Paulo Eq. 37: TrW|0000> = |16>)."""
    routes = _routes()
    basis, labs, HB_A, HE_A, HB_B, HE_B, perm = routes
    gauge_align = api("su2plaq.exact.compare:gauge_align")
    D, res = gauge_align(HB_A, HB_B)
    assert D is not None and res <= 1e-10
    assert np.abs(np.abs(D) - 1).max() <= 1e-12 and np.abs(D.imag).max() <= 1e-12
    assert np.abs(HB_A - np.diag(D) @ HB_B @ np.diag(D).conj().T).max() <= 1e-10
    K = api("su2plaq.exact.spinnet:K_inner")(jmax=0.5)
    inner_labels = api("su2plaq.exact.spinnet:inner_labels")(jmax=0.5)
    i_vac = inner_labels.index(((0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0)))
    i_all = inner_labels.index(((0.5, 0.5, 0.5, 0.5), (0.0, 0.0, 0.0, 0.0)))
    assert abs(abs(K[i_vac, i_all]) - 2.0) <= 1e-12
    assert np.count_nonzero(np.abs(K[i_vac]) > 1e-12) == 1
    # consistency with the closed block of route A
    i0, i1 = labs.index(CLOSED_VACUUM), labs.index(CLOSED_ALLHALF)
    assert abs(abs(HB_A[i0, i1]) - 2.0) <= 1e-12
    # gauge_align must report failure when moduli differ
    D2, res2 = gauge_align(HB_A, 2 * HB_B)
    assert D2 is None and res2 > 1.0

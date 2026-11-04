"""Unit tests for su2plaq.exact.spinnet and compare (own checks; route A used only as a cross-check)."""
import numpy as np

from su2plaq.exact.compare import gauge_align, outer_block_structure, spectra_match
from su2plaq.exact.operators import h_magnetic_phys
from su2plaq.exact.physical import physical_basis
from su2plaq.exact.spinnet import (K_inner, h_electric_6j, h_magnetic_phys_6j, inner_labels, labels, plaquette_P)


def test_label_order_identical_to_route_a():
    # compare.outer_block_structure relies on route-B labels and route-A basis.labels having the same order
    assert labels(jmax=0.5) == physical_basis().labels


def test_P_is_orthogonal_on_bright_subspace_and_K_symmetric():
    K = K_inner()
    assert K.shape == (47, 47) and np.abs(K - K.T).max() < 1e-15
    ev = np.linalg.eigvalsh(K)
    assert abs(ev).max() <= 2 + 1e-12
    assert np.count_nonzero(np.abs(K).sum(axis=1) < 1e-12) == 31


def test_inner_P_matches_full_P_restricted():
    labs = labels(jmax=0.5)
    il = inner_labels(0.5)
    P_full = plaquette_P(labs)
    # first state of each inner label with outer all zero = a state whose outer part is closed
    idx = {lab: i for i, lab in enumerate(labs)}
    P_in = plaquette_P(il)
    for a, la in enumerate(il):
        for b, lb in enumerate(il):
            la_f = (la[0] + (0.0,) * 8, la[1])
            lb_f = (lb[0] + (0.0,) * 8, lb[1])
            if la_f in idx and lb_f in idx:
                assert abs(P_full[idx[la_f], idx[lb_f]] - P_in[a, b]) < 1e-15


def test_route_b_matches_route_a_up_to_signs():
    b = physical_basis()
    HA, _ = h_magnetic_phys(b)
    HB = h_magnetic_phys_6j(labels(jmax=0.5))
    HE = h_electric_6j(labels(jmax=0.5))
    D, res = gauge_align(HA, HB)
    assert D is not None and res < 1e-10
    assert spectra_match(np.diag(np.diag(HE)), HA, HE, HB) < 1e-10
    info = outer_block_structure(HA, b, K_inner())
    assert info["n_blocks"] == 128 and info["max_offblock"] == 0.0


def test_gauge_align_recovers_known_gauge():
    rng = np.random.default_rng(0)
    B = rng.normal(size=(6, 6)) + 1j * rng.normal(size=(6, 6))
    B = B + B.conj().T
    d = np.exp(1j * rng.uniform(0, 2 * np.pi, 6))
    A = d[:, None] * B * d.conj()[None, :]
    D, res = gauge_align(A, B)
    assert D is not None and res < 1e-12
    D2, r2 = gauge_align(A, 3 * B)
    assert D2 is None and r2 > 1.0

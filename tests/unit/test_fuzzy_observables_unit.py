"""Unit tests for su2plaq.fuzzy.observables (M9-O1 support)."""
import numpy as np
from scipy.linalg import expm

from su2plaq.fuzzy import observables as ob

G2 = ob.g2_of(0.37, 0.61)


def test_closed_sector_dims_and_hermiticity():
    H1, d1 = ob.closed_sector(G2, 1.0)
    H0, d0 = ob.closed_sector(G2, 0.0)
    assert (d1, d0) == (12, 9)
    for H in (H1, H0):
        assert np.abs(H - H.conj().T).max() < 1e-12


def test_vacuum_energy_and_first_moment():
    # <Omega|H|Omega> = 4 links * (g2/4) * r * (-4) ; <Omega|square|Omega> = 0
    H, _ = ob.closed_sector(G2, 1.0)
    assert abs(H[0, 0] - (-4.0 * G2)) < 1e-12
    H, _ = ob.closed_sector(G2, 0.0)
    assert abs(H[0, 0]) < 1e-12
    assert np.linalg.eigvalsh(ob.closed_sector(G2, 1.0)[0])[0] < -4.0 * G2


def test_t_zero_and_small_t():
    for r in (0.0, 1.0):
        assert abs(ob.plaquette_at_time(0.0, G2, r)) < 1e-12
        # <square>(t) = O(t): d/dt = i<[H, square]> = 0 at t=0, so O(t^2) in fact
        assert abs(ob.plaquette_at_time(1e-3, G2, r)) < 1e-4
        assert abs(ob.loschmidt([0.0], G2, r)[0] - 1) < 1e-12


def test_projected_matches_full_krylov_dynamics():
    # compare e^{-iHt}|Omega> from the invariant-subspace blocks with a direct dense-free Taylor expansion in 65536 dims
    t = 0.3
    r = 1.0
    k1, k2, W = ob.K1(), ob.K2(), ob.plaquette_row()

    def Hfull(v):
        v4 = v.reshape(16, 16, 16, 16)
        return (G2 / 4 * (ob._kin(k1, v4) + r * ob._kin(k2, v4)) - 2 / G2 * ob._square(W, v4)).reshape(-1)

    psi = ob._vacuum()
    term = psi.copy()
    for n in range(1, 60):
        term = (-1j * t / n) * Hfull(term)
        psi = psi + term
    Hs, _ = ob.closed_sector(G2, r)
    amp = expm(-1j * Hs * t)[0, 0]
    assert abs(np.vdot(ob._vacuum(), psi) - amp) < 1e-11
    s = ob._square(W, psi.reshape(16, 16, 16, 16)).reshape(-1)
    assert abs(np.real(np.vdot(psi, s)) - ob.plaquette_at_time(t, G2, r)) < 1e-11


def test_ks_block_and_loschmidt():
    ks = ob.ks_closed_sector(G2)
    assert np.allclose(ks, [[0, -2 / G2], [-2 / G2, 1.5 * G2]])
    ts = np.array([0.0, 0.7, 2.0])
    ref = [abs(expm(-1j * ks * t)[0, 0]) ** 2 for t in ts]
    assert np.allclose(ob.ks_loschmidt(ts, G2), ref, atol=1e-13)
    # KS plaquette: <sigma_x>(t) from the vacuum, small at small t, bounded
    assert abs(ob.ks_plaquette_at_time(0.0, G2)) < 1e-14
    assert abs(ob.ks_plaquette_at_time(0.5, G2)) <= 1.0


def test_one_step_identity():
    # order 1 = U_B U_K U_E: kinetic layers are phases on Omega and U_B commutes with square  =>  exactly 0
    for r in (0.0, 1.0):
        assert abs(ob.one_step_plaquette(0.37, 0.61, r, 1)) < 1e-12
    assert abs(ob.one_step_plaquette(0.91, 0.23, 1.0, 1)) < 1e-12


def test_one_step_order2_is_not_zero_but_second_order_small():
    # order 2 = U_EK U_B U_EK: U_B Omega is not a kinetic eigenvector, so the value is O(alpha beta) (quadratic scaling)
    a = abs(ob.one_step_plaquette(0.05, 0.05, 0.0, 2))
    b = abs(ob.one_step_plaquette(0.025, 0.025, 0.0, 2))
    assert 1e-4 < b < a < 0.05 and 3.0 < a / b < 5.0


def test_shared_table_schema():
    d = ob.shared_table()
    assert set(d["rows"]) == {"fuzzy_r1", "fuzzy_r0", "ks"}
    grids = {tuple(b for b, _ in r["plaquette_vs_beta"]) for r in d["rows"].values()}
    assert len(grids) == 1 and len(next(iter(grids))) >= 5
    assert 0.61 in next(iter(grids))
    import json
    json.dumps(d)  # JSON-serialisable

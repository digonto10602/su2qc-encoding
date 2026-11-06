"""M9-O1 — shared observables vs Kogut–Susskind (prompts/300 step 9.6; METHODS-fuzzy F7).  The fuzzy model is a different
theory; only these four quantities are compared: electric energy per link, closed-sector spectrum, <Re Tr U_P>(t) from the
vacuum, Loschmidt echo.  KS reference = the 2x2 closed sector [[0, -2/g^2], [-2/g^2, 3 g^2/2]] (METHODS §4), recomputed here."""
import json

import numpy as np
import pytest

from scipy.linalg import expm

from tests.acceptance.m9._fz import NOMINAL, api, ref_K1, ref_K2, ref_plaquette_row

TOL = 1e-10  # closed-sector eigh on <= 50-dim matrices: 1e-13


def _ks(g2):
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


def test_M9_O1_definitions_and_identities():
    """g2_of(alpha, beta) = sqrt(2 alpha / beta); electric_spectrum(g2) = {0, 3 g^2/8, g^2/2}; closed_sector(g2, r) is Hermitian,
    basis vector 0 = Omega, dimension 12 (r = 1) and 9 (r = 0) (the K2 term connects Omega to more states; both <= 50), vacuum
    energy <Omega|H|Omega> = H[0, 0] = -4 r g^2 (the K2 vacuum value, 4 inner links x (-g^2 r)), and the ground state is strictly
    below it for r = 1 (and <= 0 = vacuum for r = 0); ks_closed_sector equals the 2x2 above.  One-step identity: after one
    FIRST-order Trotter step U = U_B U_K U_E from the vacuum <Re Tr U_P> = 0 exactly at r = 1 and r = 0 (U_E, U_K are phases on
    the vacuum and U_B commutes with the plaquette).  For the symmetric order-2 step U_E(a/2) U_K(k/2) U_B U_K(k/2) U_E(a/2) the
    value is NOT zero: it is O(alpha beta) (measured 0.0348 at nominal r = 0, 0.0147 at (0.05, 0.05), 0.0037 at (0.025, 0.025);
    prompts/301), so the test checks it is nonzero and that halving both angles divides it by a factor in [3, 5] (4 at leading
    order, corrections O(alpha, beta)).  plaquette_at_time(t) starts at 0 and is small for t = 1e-3 (|value| <= 1e-2);
    loschmidt(0) = 1."""
    ob = api("su2plaq.fuzzy.observables")
    alpha, beta = NOMINAL
    g2 = ob.g2_of(alpha, beta)
    assert abs(g2 - np.sqrt(2 * alpha / beta)) <= 1e-12
    es = sorted(ob.electric_spectrum(g2))
    assert np.allclose(es, [0.0, 0.375 * g2, 0.5 * g2], atol=1e-12)
    H1, d1 = ob.closed_sector(g2, 1.0)
    H0, d0 = ob.closed_sector(g2, 0.0)
    assert H1.shape == (d1, d1) and H0.shape == (d0, d0) and d1 == 12 and d0 == 9
    assert np.abs(H1 - H1.conj().T).max() <= TOL and np.abs(H0 - H0.conj().T).max() <= TOL
    assert abs(H1[0, 0] + 4 * g2) <= TOL and abs(H0[0, 0]) <= TOL          # vacuum energy -4 r g^2 (prompts/301, verified)
    assert np.linalg.eigvalsh(H1)[0] < -4 * g2 - TOL and np.linalg.eigvalsh(H0)[0] <= TOL
    ks = ob.ks_closed_sector(g2)
    assert np.abs(ks - _ks(g2)).max() <= 1e-12
    # one-step identity (fuzzy, order 1): <Omega| U^dag W U |Omega> = <Omega|W|Omega> = 0 with U = U_B U_K U_E — 4 inner links
    W = ref_plaquette_row()
    vac1 = np.zeros(4, complex); vac1[[0, 3]] = 1 / np.sqrt(2)   # row part of Psi = 1/2 per link, traced over columns = |00>+|11>
    assert abs(ob.plaquette_at_time(0.0, g2, 1.0)) <= TOL and abs(ob.plaquette_at_time(0.0, g2, 0.0)) <= TOL
    assert abs(ob.one_step_plaquette(alpha, beta, 1.0, order=1)) <= TOL and abs(ob.one_step_plaquette(alpha, beta, 0.0, order=1)) <= TOL
    # order 2 is nonzero and O(alpha beta): halving both angles divides the value by ~4 (prompts/301: 0.0147 -> 0.0037 at r = 0)
    for r in (1.0, 0.0):
        v_nom = ob.one_step_plaquette(alpha, beta, r, order=2)
        assert abs(v_nom) > 1e-3
        v1 = ob.one_step_plaquette(0.05, 0.05, r, order=2)
        v2 = ob.one_step_plaquette(0.025, 0.025, r, order=2)
        assert abs(v1) > 1e-4 and abs(v2) > 1e-5
        assert 3.0 <= v1 / v2 <= 5.0
    assert abs(ob.plaquette_at_time(1e-3, g2, 1.0)) <= 1e-2
    L = ob.loschmidt(np.array([0.0, 0.5, 1.0]), g2, 1.0)
    assert L.shape == (3,) and abs(L[0] - 1) <= TOL and np.all((L >= -TOL) & (L <= 1 + TOL))
    # KS Loschmidt from the 2x2 block agrees with the closed-form used by the table
    e0 = np.array([1.0, 0.0])
    Lks = [abs(e0 @ expm(-1j * _ks(g2) * t) @ e0) ** 2 for t in (0.0, 0.5, 1.0)]
    assert np.allclose(ob.ks_loschmidt(np.array([0.0, 0.5, 1.0]), g2), Lks, atol=1e-12)


def test_M9_O1_shared_table_file(root):
    """results/fuzzy/shared_observables.json: rows for 'fuzzy_r1', 'fuzzy_r0', 'ks' with keys electric_per_link (list),
    closed_sector_dim (int), closed_sector_spectrum (sorted list), plaquette_vs_beta (list of [beta, value] at fixed g2),
    loschmidt (list of [t, value]); every number recomputed here from the production functions within 1e-10; provenance present."""
    p = root / "results" / "fuzzy" / "shared_observables.json"
    assert p.exists(), f"missing {p}"
    d = json.loads(p.read_text())
    ob = api("su2plaq.fuzzy.observables")
    assert set(d["rows"]) == {"fuzzy_r1", "fuzzy_r0", "ks"} and "provenance" in d and len(d["provenance"]["git_commit"]) >= 7
    g2 = d["g2"]
    assert abs(g2 - ob.g2_of(*NOMINAL)) <= 1e-12
    for name, r in {"fuzzy_r1": 1.0, "fuzzy_r0": 0.0}.items():
        row = d["rows"][name]
        H, dim = ob.closed_sector(g2, r)
        assert row["closed_sector_dim"] == dim
        assert np.allclose(sorted(row["closed_sector_spectrum"]), np.linalg.eigvalsh(H), atol=TOL)
        assert np.allclose(sorted(row["electric_per_link"]), sorted(ob.electric_spectrum(g2)), atol=1e-12)
        for b, val in row["plaquette_vs_beta"]:
            t = b * g2
            assert abs(val - ob.plaquette_at_time(t, g2, r)) <= TOL
        ts = np.array([t for t, _ in row["loschmidt"]])
        assert np.allclose([v for _, v in row["loschmidt"]], ob.loschmidt(ts, g2, r), atol=TOL)
    ks = d["rows"]["ks"]
    assert ks["closed_sector_dim"] == 2 and np.allclose(sorted(ks["closed_sector_spectrum"]), np.linalg.eigvalsh(_ks(g2)), atol=TOL)
    assert np.allclose(sorted(ks["electric_per_link"]), [0.0, 0.375 * g2], atol=1e-12)
    ts = np.array([t for t, _ in ks["loschmidt"]])
    assert np.allclose([v for _, v in ks["loschmidt"]], ob.ks_loschmidt(ts, g2), atol=TOL)
    # same beta grid and t grid in all rows
    grids = {tuple(b for b, _ in d["rows"][k]["plaquette_vs_beta"]) for k in d["rows"]}
    assert len(grids) == 1 and len(next(iter(grids))) >= 5

"""Unit tests of su2plaq.crosscheck.embed (prompts/009 §5.2): the KS link as a compression of the rishon / fuzzy link."""
from __future__ import annotations

import numpy as np
import pytest

from su2plaq.crosscheck import embed as E


@pytest.mark.parametrize("model", E.LINK_MODELS)
def test_isometry_and_phase(model):
    V, c = E.link_isometry(model)
    assert V.shape == (16, 5) and V.dtype == np.complex128
    assert np.abs(V.conj().T @ V - np.eye(5)).max() <= 1e-12
    assert abs(c - (1j if model == "rishon_minus" else 1.0)) <= 1e-15


def test_isometry_matches_independent_casimir_route():
    """V maps the KS Casimir j(j+1) onto the model link energy: H_E V = V diag(j(j+1)) holds on the embedded space only for the
    rishon link (H_E = (L^2 + R^2)/2 is exactly j(j+1) on the singlet and flux copy)."""
    from su2plaq.rishon.algebra import RishonLink
    from su2plaq.su2.algebra import LinkSpace

    rl = RishonLink()
    HE = 0.5 * (rl.casimir_L + rl.casimir_R)
    V, _ = E.link_isometry("rishon_plus")
    assert np.abs(HE @ V - V @ LinkSpace(0.5).casimir()).max() <= 1e-12


def test_link_models_rejected():
    with pytest.raises(ValueError):
        E.link_isometry("nope")
    with pytest.raises(ValueError):
        E.link_compression("nope")


def test_compression_residuals_and_leaks_rishon_plus():
    r = E.link_compression("rishon_plus")
    for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette"):
        assert 0.0 <= r[k] <= 1e-12, k
    assert abs(r["leak_U"] ** 2 - 0.5) <= 1e-9 and abs(r["leak_plaquette"] ** 2 - 15.0) <= 1e-6 and r["phase"] == 1.0


def test_compression_fuzzy_fplus_leaks():
    r = E.link_compression("fuzzy_fplus")
    for k in ("isometry", "U", "L", "R", "HE", "plaquette"):
        assert r[k] <= 1e-12, k
    assert abs(r["leak_U"] ** 2 - 1.0) <= 1e-9 and abs(r["leak_plaquette"] ** 2 - 4.0) <= 1e-6


def test_compressed_plaquette_shapes_and_hermitian_gram():
    V, _ = E.link_isometry("fuzzy_one")
    from su2plaq.fuzzy import link as fz

    U = [[fz.U_op(a, b) for b in range(2)] for a in range(2)]
    Wc, G = E.compressed_plaquette(U, V)
    assert Wc.shape == G.shape == (625, 625)
    assert np.abs(G - G.conj().T).max() <= 1e-10

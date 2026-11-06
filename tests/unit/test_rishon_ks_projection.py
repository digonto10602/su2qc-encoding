"""Unit tests for the projector construction of scripts/m5_ks_projection.py (exploratory rishon-vs-KS projection check).
Fast (< 30 s): single-link projector, the 433 groups, per-group verification on small groups, Gauss law on sampled images."""
from __future__ import annotations

import importlib.util
import pathlib

import numpy as np
import pytest

from su2plaq.exact.physical import physical_basis
from su2plaq.rishon import physical as rphys
from su2plaq.rishon.algebra import CODES_Q, RishonLink

_SPEC = importlib.util.spec_from_file_location("m5_ks_projection", pathlib.Path(__file__).resolve().parents[2] / "scripts" / "m5_ks_projection.py")
X = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(X)

VARIANTS = ("plus", "minus", "A")


@pytest.fixture(scope="module")
def basis():
    return rphys.rishon_basis()


@pytest.mark.parametrize("variant", VARIANTS)
def test_link_projector_is_projector_commuting_with_generators(variant):
    P = X.link_projector16(variant)
    rl = RishonLink()
    assert np.abs(P - P.conj().T).max() < 1e-15
    assert np.abs(P @ P - P).max() < 1e-15
    assert abs(np.trace(P).real - (len(CODES_Q) + 1)) < 1e-14           # P_Q (4) + one singlet combination
    for m in list(rl.L) + list(rl.R):
        assert np.abs(P @ m - m @ P).max() < 1e-14                      # gauge-invariant link operator


def test_sigma_vectors_are_eigenvectors_of_det_u_plus_dagger():
    rl = RishonLink()
    d = rl.det_U + rl.det_U.conj().T
    for variant, ev in (("plus", 2.0), ("minus", -2.0)):
        P = X.link_projector16(variant)
        v = P[:, 3] * np.sqrt(2.0)                                       # column of |sigma><sigma| on A: (|A> + s|B>)/sqrt2 * (1/sqrt2) -> rescale
        v = v / np.linalg.norm(v)
        assert np.abs(d @ v - ev * v).max() < 1e-14


def test_groups_are_the_433_ks_labels(basis):
    grp = X.rishon_groups(basis)
    ks = physical_basis()
    ks_keys = {(tuple(float(x) for x in l[0]), tuple(float(x) for x in l[1])) for l in ks.labels}
    assert set(grp) == ks_keys and len(grp) == 433
    assert sum(len(v) for v in grp.values()) == basis.dim == 38432
    for (j, _J), idx in grp.items():
        assert len(idx) == 2 ** sum(1 for x in j if x == 0.0)


@pytest.mark.parametrize("variant", VARIANTS)
def test_group_projector_rank_one_hermitian_idempotent(basis, variant):
    grp = X.rishon_groups(basis)
    small = sorted((idx for idx in grp.values() if len(idx) <= 16), key=lambda i: (len(i), i[0]))
    sel = small[:: max(1, len(small) // 24)]
    assert sel
    for idx in sel:
        r = X.group_projector(basis, idx, variant)
        w = X.analytic_vector(basis, idx, variant)
        w = w / np.linalg.norm(w)
        assert r["orthonormality"] < 1e-12
        assert r["hermitian"] < 1e-12
        assert r["idempotent"] < 1e-12
        assert r["closure"] < 1e-12                                      # P Psi stays in span of the group
        assert abs(r["trace"] - 1.0) < 1e-12                             # rank 1 per group
        assert np.abs(r["G"] - np.outer(w, w.conj())).max() < 1e-12


def test_rank_and_overlap_on_groups_up_to_1024(basis):
    ks = physical_basis()
    V = X.build_V(basis, ks.labels, "plus", check=True, max_group=1024)
    st = V["stats"]
    assert abs(st["rank"] - st["n_groups"]) < 1e-9 and st["n_groups"] >= 400
    assert max(st["hermitian"], st["idempotent"], st["closure"], st["range_residual"]) < 1e-12
    S = X.V_overlap(V)
    d = np.zeros(433)
    d[V["positions"]] = 1.0
    assert np.abs(S - np.diag(d)).max() < 1e-12                          # orthonormal columns
    assert X.V_gauss_residual(V) < 1e-12                                 # range vectors satisfy the Gauss law


def test_projector_image_of_sampled_states_satisfies_gauss(basis):
    ids = rphys.sample_indices(basis, n=24, seed=20261104) + rphys.closed_indices(basis)[:3]
    for variant in VARIANTS:
        for k in ids:
            col = np.zeros(len(basis.keys[k]), dtype=np.int64)
            c, key, amp = X.apply_projector(col, np.asarray(basis.keys[k], dtype=np.int64),
                                            np.asarray(basis.amps[k], dtype=np.complex128), variant)
            if len(key) == 0:
                continue
            assert rphys.gauss_residual(key, amp) < 1e-12


def test_reducer_electric_energy_matches_ks_on_range(basis):
    from su2plaq.exact import operators as kop
    from su2plaq.rishon import operators as rops

    ks = physical_basis()
    V = X.build_V(basis, ks.labels, "plus", check=False, max_group=64)
    red = X.Reducer(V["col"], V["key"], V["amp"], V["n_cols"], 16, rops.inner_codes())
    (HE,) = red.reduce([np.diag(rops.h_electric_inner()).astype(np.complex128)])
    HK = kop.h_electric_inner(ks)
    pos = np.array(V["positions"])
    assert np.abs(HE[np.ix_(pos, pos)] - np.diag(HK[pos])).max() < 1e-12

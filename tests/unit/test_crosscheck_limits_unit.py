"""Unit tests of su2plaq.crosscheck.limits (prompts/009 §5.3): rishon levels and KS limit, fuzzy isolated plaquette and flavour blocks."""
from __future__ import annotations

import importlib.util
import pathlib

import numpy as np
import pytest

from su2plaq.crosscheck import limits as Lm

ROOT = pathlib.Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------------------------- rishon
def test_closed_block_is_hermitian_linear_in_couplings_and_has_loop_entry():
    B = Lm.rishon_closed_block(0.5, 1.0, 0.2)
    assert B.shape == (17, 17) and np.abs(B - B.conj().T).max() <= 1e-12
    B0, B1 = Lm.rishon_closed_block(0.0, 0.0, 0.0), Lm.rishon_closed_block(1.3, -0.7, 0.4)
    assert np.abs(B0).max() <= 1e-12
    parts = [Lm.rishon_closed_block(*c) for c in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
    assert np.abs(B1 - (1.3 * parts[0] - 0.7 * parts[1] + 0.4 * parts[2])).max() <= 1e-12
    assert abs(parts[0][16, 16] - 3.0) <= 1e-12                         # H_E on the loop state: 4 links x 3/4


def test_closed_block_ks_limit_levels_converge():
    g2 = 1.0
    ks = np.linalg.eigvalsh(np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]]))
    errs = []
    for L in (64.0, 128.0):
        ev = np.linalg.eigvalsh(Lm.rishon_closed_block(g2 / 2 - 8 * L / 3, 1 / g2, -L)) + 8 * L
        errs.append(np.abs(ev[:2] - ks).max())
    assert errs[1] < 0.6 * errs[0] < 0.1


def test_rishon_blocks_and_levels_at_project_couplings():
    sz = Lm.rishon_block_sizes()
    assert len(sz) == 305 and sz.max() == 4352 and sz.sum() == 38432
    ev = Lm.rishon_levels(0.5, 1.0, 0.0)
    assert ev.shape == (38432,) and np.all(np.diff(ev) >= -1e-9)
    lo = 0.75 - np.sqrt(0.5625 + 32.0)
    assert abs(ev[0] - lo) <= 1e-10 and int(np.sum(np.abs(ev - lo) <= 1e-9)) == 256
    assert np.array_equal(Lm.rishon_levels(0.5, 1.0, 0.0, k=7), ev[:7])


def test_rishon_ks_limit_keys():
    r = Lm.rishon_ks_limit(1.0, 64.0)
    assert r["levels"].shape == (433,) and r["ks_levels"].shape == (433,)
    assert abs(r["max_dev"] - np.abs(r["levels"] - r["ks_levels"]).max()) <= 1e-12
    assert 4 * 64 - 12 <= r["gap_to_next_band"] <= 4 * 64 and r["max_dev"] < 0.2


# ----------------------------------------------------------------------------------------------- fuzzy
def test_isolated_plaquette_basis_moved_not_copied():
    spec = importlib.util.spec_from_file_location("m9_results_unit11", ROOT / "scripts" / "m9_results.py")
    m9 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m9)
    assert m9.isolated_plaquette_basis is Lm.isolated_plaquette_basis


def test_isolated_plaquette_levels():
    from su2plaq.fuzzy import gauss as gz

    vecs, _ = Lm.isolated_plaquette_basis()
    assert vecs.shape == (gz.isolated_plaquette_count(), 65536) == (50, 65536)
    assert np.abs(vecs.conj() @ vecs.T - np.eye(50)).max() <= 1e-12
    lv = Lm.fuzzy_isolated_levels(1.0, 1.0, 1.0)
    assert lv.shape == (50,) and np.all(np.diff(lv) >= -1e-9)
    ev = Lm.fuzzy_isolated_levels(1.0, 1.0, 0.0)
    assert ev[1] - ev[0] <= 1e-10                                       # K1 only: twofold ground level
    # weak coupling gap is tiny but positive
    ev = Lm.fuzzy_isolated_levels(0.2, 1.0, 1.0)
    assert 1e-10 < ev[1] - ev[0] < 1e-3


def test_flavour_block_dimensions_and_ks_block():
    for signs, d in (((1, 1, -1, -1), 2), ((1, -1, -1, 1), 4), ((1, 1, 1, 1), 3)):
        H = Lm.fuzzy_flavour_block(1.0, signs)
        assert H.shape == (d, d) and np.abs(H - H.conj().T).max() <= 1e-12 and abs(H[0, 0]) <= 1e-10
    H = Lm.fuzzy_flavour_block(2.0, (1, 1, -1, -1))
    assert np.abs(np.linalg.eigvalsh(H) - np.linalg.eigvalsh(np.array([[0.0, -1.0], [-1.0, 3.0]]))).max() <= 1e-10
    with pytest.raises(ValueError):
        Lm.fuzzy_flavour_block(1.0, (1, 1, 1))
    with pytest.raises(ValueError):
        Lm.fuzzy_flavour_block(1.0, (1, 1, 1, 2))


# ----------------------------------------------------------------------------------------------- hardening (tester 422)
def test_cached_helpers_are_read_only():
    HE, HB, HD, lab, _drops = Lm._rishon_phys_ops()
    for X in (HE, HB, HD):
        for arr in (X.data, X.indices, X.indptr):
            with pytest.raises(ValueError):
                arr[0] = arr[0]
    with pytest.raises(ValueError):
        lab[0] = 1
    for arr in Lm._flavour_blocks((1, 1, -1, -1)):
        with pytest.raises(ValueError):
            arr[0, 0] = 0.0
    # the public functions still return fresh, writable arrays and do not change the cache
    before = HB.data.copy()
    ev = Lm.rishon_levels(0.5, 1.0, 0.0, k=3)
    ev[0] = 99.0
    H = Lm.fuzzy_flavour_block(1.0, (1, 1, -1, -1))
    H[0, 0] = 99.0
    assert np.array_equal(HB.data, before) and abs(Lm.fuzzy_flavour_block(1.0, (1, 1, -1, -1))[0, 0]) <= 1e-10


def test_dropped_images_of_the_rishon_projection_are_counted():
    d = Lm.rishon_dropped_images()
    assert set(d) == {"HB", "HD"}
    for k in ("HB", "HD"):
        assert d[k]["images_outside_code"] == 0 and d[k]["outside_weight_max"] <= 1e-12
        assert 0 <= d[k]["tiny_max"] <= 1e-12 and d[k]["tiny_entries"] > 0          # entries below 1e-12 are rounding (~5e-16)
    assert d["HB"]["code_entries_below_1e-14"] == 0
    d["HB"]["images_outside_code"] = 5                                              # a copy: the cache is untouched
    assert Lm.rishon_dropped_images()["HB"]["images_outside_code"] == 0


def test_outside_record_weight_detects_non_cancelling_images():
    import scipy.sparse as sp

    nu = 3
    P = sp.csr_matrix(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]))         # physical vector 0 = e0 + e2, vector 1 = e1
    # an image outside the code reached from keys 0 and 2 with opposite amplitudes: cancels on physical vector 0
    rec = Lm._outside_record([np.array([99, 99])], [np.array([0, 2])], [np.array([1.0, -1.0])], P, nu)
    assert rec == {"images_outside_code": 2, "outside_weight_max": 0.0}
    # same keys, same sign: weight 2 on physical vector 0
    rec = Lm._outside_record([np.array([99, 99])], [np.array([0, 2])], [np.array([1.0, 1.0])], P, nu)
    assert rec["images_outside_code"] == 2 and abs(rec["outside_weight_max"] - 2.0) <= 1e-12
    assert Lm._outside_record([], [], [], P, nu) == {"images_outside_code": 0, "outside_weight_max": 0.0}

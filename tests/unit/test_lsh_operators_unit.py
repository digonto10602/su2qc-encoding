"""Unit tests for su2plaq.lsh.operators (prompts/400 steps 7.1-7.2): site rules, codes, Abelian Gauss law, ladder
factors, vertex table, plaquette operator, H_B / H_E.  Counts are recomputed here by loops that differ from the production
enumeration (spin triangles / raw loop numbers instead of site-code products)."""
import itertools
import pathlib

import numpy as np
import pytest

from su2plaq.lsh import operators as O


def _flux(s):
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    return l31 + l12, l12 + l23, l23 + l31


# ---- site rules ---------------------------------------------------------------------------------------------------
def test_site_rules_from_spin_triangles():
    """Valid site codes = images of the admissible spin triples (j1, j2 <= 1/2, J in {0, 1/2, 1}, triangle rule)."""
    codes = set()
    for j1, j2 in itertools.product((0.0, 0.5), repeat=2):
        for J in (0.0, 0.5, 1.0):
            if abs(j1 - j2) <= J <= j1 + j2 and abs((j1 + j2 + J) % 1.0) < 1e-12:
                codes.add(O.site_code(j1, j2, J))
    assert sorted(codes) == list(O.VALID_SITE) == [0, 1, 2, 4, 6]
    assert [s for s in range(8) if O.site_valid(s)] == [0, 1, 2, 4, 6]
    assert O.site_valid(-1) is False and O.site_valid(8) is False
    for s in range(8):
        assert O.site_flux(s) == _flux(s)
    assert len({O.site_flux(s) for s in range(8)}) == 8                 # loop numbers -> fluxes injective
    assert all(sum(O.site_flux(s)) % 2 == 0 for s in range(8))          # even total flux
    assert O.SITE_J1 == 6 and O.site_flux(6) == (1, 1, 2)
    with pytest.raises(ValueError):
        O.site_flux(8)


def test_site_code_rejects_non_loop_numbers():
    for args in [(0.5, 0.0, 0.0), (0.0, 0.0, 0.5), (1.0, 1.0, 0.0), (0.5, 0.5, 1.5), (0.25, 0.25, 0.5)]:
        with pytest.raises(ValueError):
            O.site_code(*args)
    assert O.site_code(0.5, 0.5, 1.0) == 6 and O.site_code(0.0, 0.5, 0.5) == 2 and O.site_code(0.5, 0.0, 0.5) == 4


# ---- counts (second loop) ----------------------------------------------------------------------------------------
def test_counts_second_loop():
    """5 site codes, 47 / 16 / 31 inner codes, 433 physical, 305 outer patterns, raw 82 / 5920 (without the flux cap)."""
    # raw loop numbers: every (l12, l23, l31) in {0,1}^3 per site, AGL only
    raw_inner = 0
    raw_states = 0
    n_out_by_nv = {v: sum(1 for s in range(8) if _flux(s)[2] == v) for v in range(3)}
    for ss in itertools.product(range(8), repeat=4):
        fl = [_flux(s) for s in ss]
        if all(fl[c][1] == fl[(c + 1) % 4][0] for c in range(4)):
            raw_inner += 1
            raw_states += int(np.prod([n_out_by_nv[f[2]] for f in fl]))
    assert (raw_inner, raw_states) == (82, 5920)
    # capped: brute force over all 24-bit codes whose 8 sites are valid
    valid = [s for s in range(8) if _flux(s)[0] <= 1 and _flux(s)[1] <= 1]
    inner, phys = [], []
    for ss in itertools.product(valid, repeat=4):
        fl = [_flux(s) for s in ss]
        if not all(fl[c][1] == fl[(c + 1) % 4][0] for c in range(4)):
            continue
        x = sum(s << (3 * c) for c, s in enumerate(ss))
        inner.append(x)
        outs = [[s for s in valid if _flux(s)[2] == fl[c][2]] for c in range(4)]
        phys += [x | sum(s << (12 + 3 * c) for c, s in enumerate(oo)) for oo in itertools.product(*outs)]
    assert len(valid) == 5 and len(inner) == 47 and len(phys) == 433
    assert np.array_equal(O.inner_codes(), np.sort(inner)) and np.array_equal(O.physical_codes(), np.sort(phys))
    bright = [x for x in inner if all(((x >> (3 * c)) & 7) != 6 for c in range(4))]
    assert len(bright) == 16 and len(inner) - len(bright) == 31
    assert len({p >> 12 for p in phys}) == 305
    assert O.inner_codes().dtype == np.int64 and O.physical_codes().dtype == np.int64


def test_is_physical_and_agl_violations():
    for code in O.physical_codes().tolist():
        assert O.is_physical_code(code) and O.agl_violations(code) == ()
    assert not O.is_physical_code(-1) and not O.is_physical_code(1 << 24)
    assert O.agl_violations(0) == ()
    assert set(O.agl_violations(0b001)) == {"b", "l"}                    # N_n = 1 at c0 vs N_p = 0 at c1, N_p = 1 vs N_n = 0
    assert set(O.agl_violations(0b010 << 12)) == {"v0"}
    # flux-cap violation with the AGL satisfied: site 111 (flux (2,2,2)) is not a valid site
    assert not O.site_valid(7) and not O.is_physical_code(0b111)


def test_code_of_label_roundtrip_and_errors():
    from su2plaq.exact.spinnet import labels
    labs = labels(jmax=0.5)
    codes = [O.code_of_label(lab) for lab in labs]
    assert sorted(codes) == O.physical_codes().tolist() and len(set(codes)) == 433
    # inner part of the code = inner_code_of of the inner spins
    for lab, code in zip(labs, codes):
        assert code & 0xFFF == O.inner_code_of(lab[0][:4], lab[1])
    with pytest.raises(ValueError):
        O.code_of_label(((0.0,) * 11, (0.0,) * 4))
    with pytest.raises(ValueError):                                      # (0.5, 0, 0) at corner 0: triangle violated
        O.inner_code_of((0.5, 0.0, 0.0, 0.0), (0.0,) * 4)


# ---- ladder factors, vertex table ---------------------------------------------------------------------------------
def test_ladder_amplitude_hand_values():
    assert O.ladder_amplitude((0, 0, 0), +1, +1) == ((1, 0, 0), pytest.approx(1.0))     # sqrt(2) / sqrt(1 * 2)
    assert O.ladder_amplitude((1, 0, 0), -1, -1) == ((0, 0, 0), pytest.approx(1.0))
    assert O.ladder_amplitude((0, 1, 0), +1, -1) == ((0, 0, 1), pytest.approx(-1.0))
    assert O.ladder_amplitude((0, 0, 1), -1, +1) == ((0, 1, 0), pytest.approx(-0.5))
    # loop numbers beyond {0, 1}: l = (2, 1, 3), S = 6: L++ -> sqrt(3 * 8) / sqrt((N_n' + 1)(N_p + 1)), N_p = 5, N_n' = 4
    (new, amp) = O.ladder_amplitude((2, 1, 3), +1, +1)
    assert new == (3, 1, 3) and amp == pytest.approx(np.sqrt(24) / np.sqrt(5 * 6))
    assert O.ladder_amplitude((0, 0, 0), -1, -1) is None and O.ladder_amplitude((1, 0, 0), +1, -1) is None
    assert O.ladder_amplitude((0, 0, 1), +1, -1) is None
    with pytest.raises(ValueError):
        O.ladder_amplitude((0, 0, 0), 0, 1)


def test_loop_ladder_matches_table_and_cap():
    assert O.loop_ladder(0, +1, +1) == (1, pytest.approx(1.0))
    assert O.loop_ladder(1, -1, -1) == (0, pytest.approx(1.0))
    assert O.loop_ladder(2, +1, -1) == (4, pytest.approx(-1.0))
    assert O.loop_ladder(4, -1, +1) == (2, pytest.approx(-0.5))
    assert O.loop_ladder(1, +1, +1) is None                              # l12 -> 2 leaves {0, 1}
    for s in range(8):
        for sp_, sn_ in itertools.product((1, -1), repeat=2):
            r = O.loop_ladder(s, sp_, sn_)
            a = O.ladder_amplitude((s & 1, (s >> 1) & 1, (s >> 2) & 1), sp_, sn_)
            assert (r is None) == (a is None or max(a[0]) > 1)


def test_vertex_table_shape():
    assert O.VERTEX_TYPES == ("LL", "RL", "RR", "LR") and len(O.VERTEX) == 4
    assert O.LINK_NAMES == ("b", "r", "t", "l")
    for c in range(4):
        for i, k in itertools.product(range(2), repeat=2):
            sgn, sp_, sn_ = O.VERTEX[c][i][k]
            assert sgn in (-1, 1) and sp_ in (-1, 1) and sn_ in (-1, 1)
    # every vertex matrix uses each of the four loop operators exactly once
    for c in range(4):
        used = {(O.VERTEX[c][i][k][1], O.VERTEX[c][i][k][2]) for i, k in itertools.product(range(2), repeat=2)}
        assert used == {(1, 1), (1, -1), (-1, 1), (-1, -1)}
    assert O.CORNER_PN == ((3, 0), (0, 1), (1, 2), (2, 3)) and O.CORNER_OUT == ((4, 5), (6, 7), (8, 9), (10, 11))


# ---- plaquette operator -------------------------------------------------------------------------------------------
def test_plaquette_and_K_structure():
    P, K, inner = O.plaquette_inner(), O.K_lsh(), O.inner_codes()
    assert P.shape == K.shape == (47, 47) and P.dtype == np.float64
    assert np.array_equal(K, -(P + P.T)) and np.array_equal(K, K.T)
    nz = np.flatnonzero(np.abs(K).sum(axis=1) > 0)
    bright = [k for k, x in enumerate(inner.tolist()) if all(((x >> (3 * c)) & 7) != 6 for c in range(4))]
    assert nz.tolist() == bright and len(nz) == 16                       # dark codes (a site in 110) are annihilated
    for k in nz:                                                         # matching: one partner per bright row
        assert np.count_nonzero(K[k]) == 1
    vals = sorted({round(float(v), 12) for v in K[K != 0]})
    assert vals == [-2.0, -0.5, 1.0]
    # partner = per-site flip 000 <-> 001, 010 <-> 100
    flip = {0: 1, 1: 0, 2: 4, 4: 2}
    pos = {int(x): k for k, x in enumerate(inner)}
    for k in nz:
        x = int(inner[k])
        y = sum(flip[(x >> (3 * c)) & 7] << (3 * c) for c in range(4))
        assert K[k, pos[y]] != 0
    # returned arrays are copies
    P[0, 0] = 99.0
    assert O.plaquette_inner()[0, 0] != 99.0


def test_h_magnetic_block_structure():
    codes = O.physical_codes()
    H = O.h_magnetic_lsh(codes)
    assert H.shape == (433, 433) and np.array_equal(H, H.T)
    pos = {int(x): k for k, x in enumerate(O.inner_codes())}
    K = O.K_lsh()
    rng = np.random.default_rng(20261110)
    for _ in range(300):
        a, b = rng.integers(0, 433, size=2)
        ca, cb = int(codes[a]), int(codes[b])
        want = K[pos[ca & 0xFFF], pos[cb & 0xFFF]] if ca >> 12 == cb >> 12 else 0.0
        assert H[a, b] == want
    with pytest.raises(ValueError):
        O.h_magnetic_lsh([0b001])


def test_h_electric():
    codes = O.physical_codes()
    HE = O.h_electric_lsh(codes)
    assert HE.shape == (433,) and HE.dtype == np.float64
    for k, code in enumerate(codes.tolist()):
        n_n = sum(_flux((code >> (3 * c)) & 7)[1] for c in range(4))     # number of spin-1/2 inner links
        assert HE[k] == pytest.approx(0.75 * n_n)
    # inner (12-bit) codes accepted, same values; include_outer adds 3/4 per spin-1/2 outer link
    inner = O.inner_codes()
    assert np.array_equal(O.h_electric_lsh(inner), O.h_electric_lsh(inner | (0 << 12)))
    HEo = O.h_electric_lsh(codes, include_outer=True)
    for k, code in enumerate(codes.tolist()):
        n_o = sum(f for c in range(4) for f in _flux((code >> (12 + 3 * c)) & 7)[:2])
        assert HEo[k] - HE[k] == pytest.approx(0.75 * n_o)
    assert O.h_electric_lsh([]).shape == (0,)


def test_operators_module_independent_of_exact_routes():
    src = pathlib.Path(O.__file__).read_text()
    for banned in ("su2plaq.exact", "wigner", "su2plaq.su2", "gauge_align"):
        assert f"import {banned}" not in src and f"from {banned}" not in src

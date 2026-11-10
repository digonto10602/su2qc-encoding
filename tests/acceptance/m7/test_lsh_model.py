"""M7-A1, K1, K2, X1 — the loop-string-hadron (LSH) model of the point-split plaquette (prompts/400 §1, §3 steps 7.1-7.2;
docs/METHODS-lsh.md L1-L4).

Model (Raychowdhury-Stryker arXiv:1912.06133 Sec. V; register rule of arXiv:1812.07554): 8 trivalent sites ((inner | outer)
pairing: 'in' site c = legs (p(c), n(c), v), 'out' site c = legs (outer 1, outer 2, v)), three loop numbers per site,
one qubit each at j_max = 1/2 -> 24 qubits.  Site code bits (l_12, l_23, l_31) = bits 0, 1, 2; fluxes N_1 = l_31 + l_12,
N_2 = l_12 + l_23, N_3 = l_23 + l_31.  Valid site codes = flux at most 1 on the two physical legs: {0, 1, 2, 4, 6}.
Abelian Gauss law (AGL) = the flux of a link read from its two ends agrees (4 inner + 4 virtual links).

Planner measurements (scratch/planner/proto_m7_lsh_model.py, reports/research/400): 433 AGL-valid codes = the 433 route-B
labels; 47 inner codes (16 bright, 31 dark); 305 outer-site patterns; raw register (no flux cap) 82 inner / 5920 states;
ladder factors vs the oscillator Fock space <= 1.2e-15; K_LSH = K_6j entry by entry (1.8e-15, no sign gauge needed);
spectra LSH vs route A / route B <= 1.0e-14.  Tolerances: 1e-12 for identities inside one construction (float64, fewer than
100 operations per entry), 1e-10 for comparisons with route A (corner-singlet eigh, as M0-X4/X6)."""
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api
from tests.acceptance.m7 import _ref

VALID_SITE = (0, 1, 2, 4, 6)
CORNER_PN = ((3, 0), (0, 1), (1, 2), (2, 3))        # (previous, next) inner link at corners c0..c3, links b r t l = 0 1 2 3
CORNER_OUT = ((4, 5), (6, 7), (8, 9), (10, 11))
SIGMAS = ((+1, +1), (+1, -1), (-1, +1), (-1, -1))


def _flux(s):
    l12, l23, l31 = s & 1, (s >> 1) & 1, (s >> 2) & 1
    return l31 + l12, l12 + l23, l23 + l31


def _violations(code):
    fl = [_flux((code >> (3 * k)) & 7) for k in range(8)]
    bad = []
    for c in range(4):
        if fl[c][1] != fl[(c + 1) % 4][0]:
            bad.append("brtl"[CORNER_PN[c][1]])
    for c in range(4):
        if fl[c][2] != fl[4 + c][2]:
            bad.append(f"v{c}")
    return tuple(bad)


def test_M7_A1_register_agl_counts():
    """Site rule, Abelian Gauss law and counts, all recomputed here by brute force: 5 valid site codes (= flux cap on the
    physical legs; the map loop numbers -> fluxes is injective and the three fluxes have even sum); of the 5^8 = 390 625
    site-valid register states exactly 433 obey the AGL on the 4 inner and 4 virtual links, and they are the codes of the
    433 route-B labels (code_of_label injective; label_of_code inverse); inner register: 47 of 5^4 (16 bright = no site in
    110, 31 dark); 305 distinct outer-site patterns with 1 or 2 states each; raw register without the flux cap: 82 inner
    patterns and 5920 AGL-valid states of 2^24 (the cap, not the AGL, removes the j = 1 states)."""
    O = api("su2plaq.lsh.operators")
    assert tuple(O.VALID_SITE) == VALID_SITE and O.SITE_J1 == 6
    assert tuple(map(tuple, O.CORNER_PN)) == CORNER_PN and tuple(map(tuple, O.CORNER_OUT)) == CORNER_OUT
    assert [s for s in range(8) if _flux(s)[0] <= 1 and _flux(s)[1] <= 1] == list(VALID_SITE)
    for s in range(8):
        assert tuple(O.site_flux(s)) == _flux(s) and O.site_valid(s) == (s in VALID_SITE) and sum(_flux(s)) % 2 == 0
    assert len({_flux(s) for s in range(8)}) == 8
    # spins <-> loop numbers
    for j1, j2 in itertools.product((0.0, 0.5), repeat=2):
        for J in (0.0, 0.5, 1.0):
            ls = (j1 + j2 - J, j2 + J - j1, J + j1 - j2)
            if min(ls) < 0 or any(abs(x - round(x)) > 1e-12 for x in ls):
                with pytest.raises(ValueError):
                    O.site_code(j1, j2, J)
                continue
            s = O.site_code(j1, j2, J)
            assert s == int(ls[0]) + 2 * int(ls[1]) + 4 * int(ls[2]) and s in VALID_SITE
            assert _flux(s) == (int(2 * j1), int(2 * j2), int(2 * J))
    # brute force over the site-valid register
    grid = np.array(np.meshgrid(*[VALID_SITE] * 8, indexing="ij"), dtype=np.int64).reshape(8, -1)
    assert grid.shape[1] == 5 ** 8
    l12, l23, l31 = grid & 1, (grid >> 1) & 1, (grid >> 2) & 1
    N1, N2, N3 = l31 + l12, l12 + l23, l23 + l31
    ok = np.ones(grid.shape[1], dtype=bool)
    for c in range(4):
        ok &= N2[c] == N1[(c + 1) % 4]
        ok &= N3[c] == N3[4 + c]
    codes = np.sort((grid[:, ok] << (3 * np.arange(8))[:, None]).sum(axis=0))
    assert len(codes) == 433
    assert np.array_equal(O.physical_codes(), codes) and O.physical_codes().dtype == np.int64
    labels = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    lab_codes = [O.code_of_label(lab) for lab in labels]
    assert len(set(lab_codes)) == 433 and sorted(lab_codes) == codes.tolist()
    label_of_code = api("su2plaq.encodings.lsh:label_of_code")
    for lab, code in zip(labels, lab_codes):
        j, J = lab
        for c in range(4):
            p, n = CORNER_PN[c]
            assert _flux((code >> (3 * c)) & 7) == (int(2 * j[p]), int(2 * j[n]), int(2 * J[c]))
            o1, o2 = CORNER_OUT[c]
            assert _flux((code >> (12 + 3 * c)) & 7) == (int(2 * j[o1]), int(2 * j[o2]), int(2 * J[c]))
        assert O.is_physical_code(code) and O.agl_violations(code) == () and label_of_code(code) == lab
    assert label_of_code(1 << 1) is None and not O.is_physical_code(1 << 1)
    # inner register
    inner = O.inner_codes()
    assert inner.dtype == np.int64 and len(inner) == 47 and np.array_equal(inner, np.sort(inner))
    assert inner.tolist() == sorted({c & 0xFFF for c in codes.tolist()})
    bright = [c for c in inner.tolist() if all(((c >> (3 * s)) & 7) != 6 for s in range(4))]
    assert len(bright) == 16
    per_outer: dict = {}
    for c in codes.tolist():
        per_outer.setdefault(c >> 12, []).append(c)
    assert len(per_outer) == 305 and {len(v) for v in per_outer.values()} == {1, 2}
    # AGL violations are named by link; cross-check on seeded random 24-bit codes
    assert set(O.agl_violations(0b001)) == {"b", "l"} and len(O.agl_violations(0b001)) == 2
    assert set(O.agl_violations(0b010)) == {"b", "v0"} and set(O.agl_violations(0b010 << 12)) == {"v0"}
    rng = np.random.default_rng(20261110)
    code_set = set(codes.tolist())
    for code in rng.integers(0, 1 << 24, size=2000).tolist() + codes.tolist()[::7]:
        assert set(O.agl_violations(code)) == set(_violations(code))
        valid = all(((code >> (3 * k)) & 7) in VALID_SITE for k in range(8)) and not _violations(code)
        assert O.is_physical_code(code) == valid == (code in code_set)
    # raw register (loop numbers 0/1, no flux cap)
    raw = np.array(np.meshgrid(*[np.arange(8)] * 4, indexing="ij"), dtype=np.int64).reshape(4, -1)
    r12, r23, r31 = raw & 1, (raw >> 1) & 1, (raw >> 2) & 1
    R1, R2, R3 = r31 + r12, r12 + r23, r23 + r31
    okr = np.ones(raw.shape[1], dtype=bool)
    for c in range(4):
        okr &= R2[c] == R1[(c + 1) % 4]
    n_out = np.array([sum(1 for s in range(8) if _flux(s)[2] == v) for v in range(3)])
    assert int(okr.sum()) == 82 and int(np.prod(n_out[R3[:, okr]], axis=0).sum()) == 5920


def test_M7_K1_ladder_factors_from_prepotentials(root):
    """The site-local LSH ladder factors are derived, not assumed: in the Schwinger-boson Fock space of a trivalent site
    (tests/acceptance/m7/_ref.py) the loop states of RS Eq. (lij) are orthonormal, and the production
    `ladder_amplitude(l, sigma_p, sigma_n)` equals <l'|(N_n+1)^(-1/2) L^{sigma_p sigma_n}_{pn} (N_p+1)^(-1/2)|l> for every
    l with l_12 + l_23 + l_31 <= 2 and all four sign pairs (1e-12; measured 1.2e-15).  The vertex-factor table VERTEX of the
    loop U_b U_r U_t^dag U_l^dag (traversal types LL, RL, RR, LR at corners c0..c3, derived here from the diagram's loop
    orientation) equals the operator products U_L^dag U_L, U_R U_L, U_R U_R^dag, U_L^dag U_R^dag of the Schwinger-boson
    link-end operators entry by entry (1e-12; measured 1.1e-16).  On the 5 valid site codes the modulus of every ladder
    factor equals the 6j recoupling coefficient F of route B (1e-12)."""
    O = api("su2plaq.lsh.operators")
    states = [l for l in itertools.product(range(4), repeat=3) if sum(l) <= 3]
    G = np.array([[_ref.loop_state(x) @ _ref.loop_state(y) for y in states] for x in states])
    assert np.abs(G - np.eye(len(states))).max() <= 1e-12
    n_checked = 0
    for l in [x for x in states if sum(x) <= 2]:
        for sp_, sn_ in SIGMAS:
            out = _ref.dressed_ladder(sp_, sn_) @ _ref.loop_state(l)
            r = O.ladder_amplitude(l, sp_, sn_)
            if r is None:
                assert np.abs(out).max() <= 1e-12, (l, sp_, sn_)
            else:
                new, amp = r
                assert min(new) >= 0 and np.abs(out - amp * _ref.loop_state(tuple(new))).max() <= 1e-12, (l, sp_, sn_)
            n_checked += 1
    assert n_checked == 40
    # traversal types from the loop orientation: arriving along +link = its R end, along -link = its L end (U^dag);
    # leaving along +link = its L end, along -link = its R end (U^dag)
    d = api("su2plaq.geometry:plaquette_diagram")()
    orient = dict(d.loop)
    types = tuple(("R" if orient[p] == +1 else "L") + ("L" if orient[n] == +1 else "R") for p, n in CORNER_PN)
    assert types == ("LL", "RL", "RR", "LR") == tuple(O.VERTEX_TYPES)
    P = _ref.safe_projector()
    for c, kind in enumerate(types):
        M = _ref.vertex_product(kind)
        for i in range(2):
            for k in range(2):
                sgn, sp_, sn_ = O.VERTEX[c][i][k]
                assert sgn in (+1, -1)
                assert abs((M[i][k] - sgn * _ref.dressed_ladder(sp_, sn_)) @ P).max() <= 1e-12, (c, kind, i, k)
        assert sorted((sp_, sn_) for row in O.VERTEX[c] for _s, sp_, sn_ in row) == sorted(SIGMAS)
    # 3-bit ladder vs the 6j F-symbols of route B (moduli)
    f_symbol = api("su2plaq.su2.wigner:f_symbol")
    for s in VALID_SITE:
        l = (s & 1, (s >> 1) & 1, (s >> 2) & 1)
        jp, jn, J = (l[2] + l[0]) / 2, (l[0] + l[1]) / 2, (l[1] + l[2]) / 2
        for sp_, sn_ in SIGMAS:
            jp2, jn2 = jp + sp_ / 2, jn + sn_ / 2
            r = O.loop_ladder(s, sp_, sn_)
            if min(jp2, jn2) < 0 or max(jp2, jn2) > 0.5:
                assert r is None or r[0] not in VALID_SITE
                continue
            F = f_symbol(J, jp, jn, 0.5, jn2, jp2)
            amp = 0.0 if r is None else r[1]
            assert abs(abs(amp) - abs(F)) <= 1e-12, (s, sp_, sn_, amp, F)
            if r is not None:
                assert _flux(r[0]) == (int(2 * jp2), int(2 * jn2), int(2 * J))


def test_M7_K2_plaquette_operator_vs_route_b_and_a():
    """LSH plaquette on the 47 inner codes, P = tr of the four vertex-factor matrices with the flux cap: real symmetric with
    16 non-zero entries; K_LSH = -(P + P^T) equals the 6j operator K_inner of route B entry by entry under the label map
    (1e-12, measured 1.8e-15; the Raychowdhury-Stryker signs reproduce the route-B sign gauge, no diagonal gauge needed);
    a matching: every bright code is moved to its per-site flip (000 <-> 001, 010 <-> 100), couplings -2 (all w = 0), -1/2
    (all w = 1), +1 (six classes with two w = 1), w_c = N_v mod 2; the 31 codes with a site in 110 (J = 1) are annihilated.
    On the 433 codes: H_B^LSH = H_B^6j (1e-12), = route A up to the real diagonal gauge (gauge_align residual <= 1e-10),
    multiplicities 16/96/16/177/16/96/16; H_E from the fluxes equals sum j(j+1) of the labels (inner and all 12 links)."""
    O = api("su2plaq.lsh.operators")
    codes = O.inner_codes().tolist()
    P = O.plaquette_inner()
    assert P.shape == (47, 47) and np.abs(P - P.T).max() <= 1e-12 and int(np.count_nonzero(np.abs(P) > 1e-12)) == 16
    K = O.K_lsh()
    assert np.abs(K + 2 * P).max() <= 1e-12
    il = api("su2plaq.exact.spinnet:inner_labels")(jmax=0.5)
    il_codes = [O.inner_code_of(j, J) for j, J in il]
    assert sorted(il_codes) == codes
    perm = [il_codes.index(c) for c in codes]
    K_B = api("su2plaq.exact.spinnet:K_inner")(jmax=0.5)[np.ix_(perm, perm)]
    assert np.abs(K - K_B).max() <= 1e-12
    flip = {0b000: 0b001, 0b001: 0b000, 0b010: 0b100, 0b100: 0b010}
    n_bright = 0
    for i, c in enumerate(codes):
        sites = [(c >> (3 * s)) & 7 for s in range(4)]
        nz = np.flatnonzero(np.abs(K[:, i]) > 1e-12)
        if 6 in sites:
            assert len(nz) == 0
            continue
        n_bright += 1
        partner = sum(flip[s] << (3 * k) for k, s in enumerate(sites))
        assert len(nz) == 1 and codes[nz[0]] == partner
        w = [_flux(s)[2] % 2 for s in sites]
        expect = -2.0 if sum(w) == 0 else (-0.5 if sum(w) == 4 else 1.0)
        assert sum(w) in (0, 2, 4) and abs(K[nz[0], i] - expect) <= 1e-12
    assert n_bright == 16
    # 433 states, label order
    labels = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    full = [O.code_of_label(lab) for lab in labels]
    HB = O.h_magnetic_lsh(full)
    HB_B = api("su2plaq.exact.spinnet:h_magnetic_phys_6j")(labels)
    assert HB.shape == (433, 433) and np.abs(HB - HB_B).max() <= 1e-12
    basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    assert basis.labels == labels
    HA, _leak = api("su2plaq.exact.operators:h_magnetic_phys")(basis)
    D, res = api("su2plaq.exact.compare:gauge_align")(HA, HB)
    assert D is not None and res <= 1e-10 and np.abs(D.imag).max() <= 1e-12
    vals, mult = np.unique(np.round(np.linalg.eigvalsh(HB), 9), return_counts=True)
    assert vals.tolist() == [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0] and mult.tolist() == [16, 96, 16, 177, 16, 96, 16]
    h6 = api("su2plaq.exact.spinnet:h_electric_6j")
    assert np.abs(O.h_electric_lsh(full) - np.diag(h6(labels))).max() <= 1e-12
    assert np.abs(O.h_electric_lsh(full, include_outer=True) - np.diag(h6(labels, inner_only=False))).max() <= 1e-12


def test_M7_X1_spectra_three_routes():
    """Same theory three ways: spectrum of (g^2/2) H_E + H_B / g^2 on the 433 states from the LSH operators, route A
    (electric basis, corner singlets) and route B (6j) agree to 1e-10 at g^2 in {0.5, 1, 2} (measured 1.0e-14); the closed
    sector (all 'out' sites empty) is the 2x2 block [[0, -2/g^2], [-2/g^2, 3 g^2/2]] of Paulo Eq. 37 (1e-12)."""
    O = api("su2plaq.lsh.operators")
    labels = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    full = [O.code_of_label(lab) for lab in labels]
    HE = O.h_electric_lsh(full)
    HB = O.h_magnetic_lsh(full)
    basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    HA, _leak = api("su2plaq.exact.operators:h_magnetic_phys")(basis)
    HEA = api("su2plaq.exact.operators:h_electric_inner")(basis)
    HB_B = api("su2plaq.exact.spinnet:h_magnetic_phys_6j")(labels)
    HE_B = api("su2plaq.exact.spinnet:h_electric_6j")(labels)
    spectra_match = api("su2plaq.exact.compare:spectra_match")
    assert spectra_match(HE, HB, HEA, HA) <= 1e-10
    assert spectra_match(HE, HB, HE_B, HB_B) <= 1e-10
    closed = sorted((c, k) for k, c in enumerate(full) if c >> 12 == 0)
    assert [c for c, _ in closed] == [0, 0b001001001001]
    ks = [k for _, k in closed]
    for g2 in (0.5, 1.0, 2.0):
        H = 0.5 * g2 * np.diag(HE) + HB / g2
        assert np.abs(H[np.ix_(ks, ks)] - np.array([[0.0, -2 / g2], [-2 / g2, 1.5 * g2]])).max() <= 1e-12

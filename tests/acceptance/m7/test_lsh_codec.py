"""M7-C1, C2 — loop-string-hadron encoding: 24-qubit codec and target (prompts/400 §2, §3 steps 7.3-7.4; METHODS-lsh L2, L5, L6).

Register: data d[0..11] = the four 'in' sites (site c at qubits 3c, 3c+1, 3c+2 = l_pn, l_nv, l_vp); outer o[0..11] = the four
'out' sites (site c at 12+3c.. = l_12, l_2v, l_v1), read-only.  The 433 physical states are computational-basis codes
(site-valid + Abelian Gauss law); the 47 valid data codes are the inner codes.  Target = the LSH operator of
su2plaq.lsh.operators (identical to the route-B target in label order); route A enters through the real diagonal gauge of
gauge_align.  Planner measurements (scratch/planner/proto_m7_lsh_circuit.py; reports/research/400 §4): gauge residual
8.9e-16 with 64 minus signs; |V_LSH - D^dag V_A D| <= 1.1e-15; 28 942 data-valid codes violate the Abelian Gauss law on a
virtual link and decode to orthogonal product states with Gauss residual in [0.5, 2.0]."""
import functools
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api

VALID_SITE = (0, 1, 2, 4, 6)
NOMINAL = (0.37, 0.61)
ALTS = ((0.91, 0.23), (1.70, 1.00))


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.lsh:LSH")()


def _vec(keys, amps):
    return dict(zip(keys.tolist(), amps.tolist()))


def _dot(a, b):
    return sum(np.conj(v) * b[k] for k, v in a.items() if k in b)


def test_M7_C1_codec_and_vectors():
    """Registers; 47 sorted inner codes; 433 distinct unit codes = code_of_label of the route-B labels in label order;
    decode = label index; decode_state: physical code -> gauge[k] x route-A state (unit norm, Gauss <= 1e-10, overlap
    gauge[k] to 1e-12), linear, empty input ok.  Every data-valid, outer-site-valid code that is not physical (28 942 codes:
    the two sites of some corner disagree on the virtual flux) decodes to a unit vector with Gauss residual >= 1/2 (all of
    them checked; analytic bound: such a corner has total G^z != 0, a multiple of 1/2), orthogonal to every physical state
    and to the other fallbacks (seeded sample of 150, 1e-12).  ValueError for a data part outside the 47 inner codes or an
    'out' site outside the flux cap.  gauge real +-1 with residual <= 1e-10 (as M0-X6, M3-C1)."""
    enc = _enc()
    O = api("su2plaq.lsh.operators")
    assert enc.name == "lsh" and enc.n_data == 12 and enc.n_outer == 12 and enc.is_basis_encoding
    assert enc.registers["d"] == list(range(12)) and enc.registers["o"] == list(range(12, 24))
    assert enc.registers["l_pn"] == [0, 3, 6, 9] and enc.registers["l_nv"] == [1, 4, 7, 10] and enc.registers["l_vp"] == [2, 5, 8, 11]
    assert enc.registers["site_in_0"] == [0, 1, 2] and enc.registers["site_in_3"] == [9, 10, 11]
    assert enc.registers["site_out_0"] == [12, 13, 14] and enc.registers["site_out_3"] == [21, 22, 23]
    labels = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    assert enc.basis.labels == labels and len(labels) == 433
    codes = enc.inner_codes()
    assert codes.dtype == np.int64 and len(codes) == 47 and np.array_equal(codes, np.sort(codes)) and codes.max() < 4096
    assert np.array_equal(codes, O.inner_codes())
    eb = enc.physical_vectors()
    assert eb.n_data == 12 and eb.n_outer == 12 and len(eb.codes) == 433 and len(eb.amps) == 433
    allc = []
    inner_set = set(codes.tolist())
    for k, (c, a) in enumerate(zip(eb.codes, eb.amps)):
        assert c.dtype == np.int64 and len(c) == 1 and len(a) == 1 and abs(a[0] - 1.0) <= 1e-15
        code = int(c[0])
        assert 0 <= code < 2 ** 24 and code == O.code_of_label(labels[k]) and (code & 0xFFF) in inner_set
        assert enc.decode(code) == k and O.is_physical_code(code)
        allc.append(code)
    assert len(set(allc)) == 433 and sorted(allc) == O.physical_codes().tolist()
    assert enc.decode(0b010) is None
    gauge = np.asarray(enc.gauge)
    assert gauge.shape == (433,) and np.abs(np.abs(gauge) - 1).max() <= 1e-12 and np.abs(np.imag(gauge)).max() <= 1e-12
    assert enc.gauge_residual <= 1e-10
    gauss_residual = api("su2plaq.exact.physical:gauss_residual")
    worst = 0.0
    for k, code in enumerate(allc):
        keys, amps = enc.decode_state(np.array([code], dtype=np.int64), np.array([1.0 + 0j]))
        assert abs(np.linalg.norm(amps) - 1) <= 1e-12
        worst = max(worst, gauss_residual(enc.basis, keys, amps))
        ref = _vec(enc.basis.keys[k], enc.basis.amps[k])
        assert abs(_dot(ref, _vec(keys, amps)) - gauge[k]) <= 1e-12
    assert worst <= 1e-10
    k0, a0 = enc.decode_state(np.array([allc[0], allc[1]], dtype=np.int64), np.array([0.6, 0.8j]))
    assert abs(np.linalg.norm(a0) - 1) <= 1e-12
    ke, ae = enc.decode_state(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.complex128))
    assert len(ke) == 0 and len(ae) == 0
    # data-valid, outer-site-valid, AGL-violating codes
    physical = set(allc)
    outer_valid = [sum(s << (3 * i) for i, s in enumerate(ss)) for ss in itertools.product(VALID_SITE, repeat=4)]
    bad = [c | (o << 12) for c in codes.tolist() for o in outer_valid if (c | (o << 12)) not in physical]
    assert len(bad) == 47 * 625 - 433 == 28942
    dec = [enc.decode_state(np.array([code], dtype=np.int64), np.array([1.0 + 0j])) for code in bad]
    assert max(abs(np.linalg.norm(a) - 1) for _k, a in dec) <= 1e-12
    res = api("su2plaq.exact.physical:gauss_residuals_coo")(enc.basis, [k for k, _a in dec], [a for _k, a in dec])
    assert res.shape == (len(bad),) and res.min() >= 0.5 - 1e-10
    rng = np.random.default_rng(20261110)
    pick = rng.choice(len(bad), size=150, replace=False)
    phys_vecs = [_vec(enc.basis.keys[k], enc.basis.amps[k]) for k in range(433)]
    fall = []
    for i in pick.tolist():
        code = bad[i]
        viol = O.agl_violations(code)
        assert enc.decode(code) is None and len(viol) >= 1 and set(viol) <= {"v0", "v1", "v2", "v3"}
        v = _vec(*dec[i])
        assert max(abs(_dot(p, v)) for p in phys_vecs) <= 1e-12
        fall.append(v)
    for i in range(len(fall)):
        for j in range(i):
            assert abs(_dot(fall[i], fall[j])) <= 1e-12
    with pytest.raises(ValueError):
        enc.decode_state(np.array([0b011], dtype=np.int64), np.array([1.0 + 0j]))          # 'in' site 0 = 011: not a data code
    with pytest.raises(ValueError):
        enc.decode_state(np.array([0b011 << 12], dtype=np.int64), np.array([1.0 + 0j]))    # 'out' site 0 breaks the flux cap
    desc = enc.describe()
    assert isinstance(desc, str) and "47" in desc and "433" in desc and "Abelian" in desc
    im = enc.import_map("spinnet")
    assert isinstance(im, dict) and im["kind"] == "UB" and im["fixed_angle"] is False and "general7" in im["skeletons"]
    assert isinstance(enc.import_map("paulo34"), str)
    with pytest.raises(ValueError):
        enc.import_map("no-such-source")


def test_M7_C2_target_lsh_equals_route_b_and_spinnet():
    """Target: U_B(beta) = expm(-i beta H_B^LSH) in label order (1e-12), = D^dag V_A D with the route-A target and the gauge
    D (1e-10), at the nominal and alternate angles; U_E = diag exp(-i alpha H_E) from the fluxes; step orders compose; the
    outer-electric variant matches route A.  LSH and the spin network are the same theory in the same label order: the 433x433
    targets of the two encodings are equal entry by entry (1e-12).  Block structure: the physical target restricted to any of
    the 305 outer-site patterns is the 47x47 inner target restricted (the circuit needs no outer information); nothing
    connects different patterns.  As in M3-K1 the sign of beta is a basis-sign convention at j_max = 1/2: U_B(-beta) =
    D' U_B(beta) D' with one -1 per bright pair (gauge_align residual <= 1e-10)."""
    enc = _enc()
    O = api("su2plaq.lsh.operators")
    expm = __import__("scipy.linalg", fromlist=["expm"]).expm
    eb = enc.physical_vectors()
    full = [int(c[0]) for c in eb.codes]
    HB = O.h_magnetic_lsh(full)
    HE = O.h_electric_lsh(full)
    assert np.abs(enc.h_magnetic() - HB).max() <= 1e-12 and np.abs(enc.h_electric() - HE).max() <= 1e-12
    assert np.abs(enc.h_electric(include_outer=True) - O.h_electric_lsh(full, include_outer=True)).max() <= 1e-12
    assert np.abs(np.asarray(enc.K_codes) - O.K_lsh()).max() <= 1e-12
    target_A = api("su2plaq.exact.operators:target")
    sn = api("su2plaq.encodings.spinnet:SpinNet")()
    assert sn.basis.labels == enc.basis.labels
    Dm = np.diag(enc.gauge)
    for alpha, beta in (NOMINAL,) + ALTS:
        VB = enc.target("UB", None, beta)
        assert VB.shape == (433, 433) and np.abs(VB - expm(-1j * beta * HB)).max() <= 1e-12
        assert np.abs(VB - Dm.conj().T @ target_A(enc.basis, "UB", beta=beta) @ Dm).max() <= 1e-10
        UE = enc.target("UE", alpha, None)
        assert np.abs(UE - np.diag(np.exp(-1j * alpha * HE))).max() <= 1e-12
        assert np.abs(enc.target("step", alpha, beta, 1) - VB @ UE).max() <= 1e-12
        UEh = enc.target("UE", alpha / 2, None)
        assert np.abs(enc.target("step", alpha, beta, 2) - UEh @ VB @ UEh).max() <= 1e-12
        for order in (1, 2):
            assert np.abs(enc.target("step", alpha, beta, order) - sn.target("step", alpha, beta, order)).max() <= 1e-12
        assert np.abs(VB - sn.target("UB", None, beta)).max() <= 1e-12
    UEo = enc.target("UE", 0.37, None, include_outer_electric=True)
    assert np.abs(UEo - target_A(enc.basis, "UE", alpha=0.37, include_outer_electric=True)).max() <= 1e-10
    assert np.abs(UEo - enc.target("UE", 0.37, None)).max() > 1e-3
    with pytest.raises(ValueError):
        enc.target("nope", 0.1, 0.1)
    # inner target and coupling table
    codes = enc.inner_codes().tolist()
    KI = enc.inner_target("UB", None, 0.61)
    assert KI.shape == (47, 47) and np.abs(KI - expm(-1j * 0.61 * O.K_lsh())).max() <= 1e-12
    hE_in = O.h_electric_lsh(codes)
    assert np.abs(enc.inner_target("UE", 0.37, None) - np.diag(np.exp(-0.37j * hE_in))).max() <= 1e-12
    assert np.abs(enc.inner_target("step", 0.37, 0.61, 1) - KI @ np.diag(np.exp(-0.37j * hE_in))).max() <= 1e-12
    W = api("su2plaq.lsh.walk")
    table = W.coupling_table(enc)
    assert set(table) == set(codes) and sorted(set(table.values())) == [-2.0, -0.5, 0.0, 1.0]
    assert sum(1 for v in table.values() if v != 0.0) == 16 and list(table.values()).count(1.0) == 12
    partner = W.partner_table(enc)
    assert set(partner) == {c for c, v in table.items() if v != 0.0}
    assert all(partner[partner[c]] == c and table[partner[c]] == table[c] for c in partner)
    assert table[0] == -2.0 and partner[0] == 0b001001001001
    # block structure in the outer-site pattern
    VB = enc.target("UB", None, 0.61)
    by_outer: dict = {}
    for k, c in enumerate(full):
        by_outer.setdefault(c >> 12, []).append(k)
    assert len(by_outer) == 305
    cidx = {c: i for i, c in enumerate(codes)}
    worst = 0.0
    off = VB.copy()
    for ks in by_outer.values():
        ii = [cidx[full[k] & 0xFFF] for k in ks]
        worst = max(worst, np.abs(VB[np.ix_(ks, ks)] - KI[np.ix_(ii, ii)]).max())
        off[np.ix_(ks, ks)] = 0.0
    assert worst <= 1e-12 and np.abs(off).max() <= 1e-12
    # sign of beta is a gauge at j_max = 1/2
    Dp, res = api("su2plaq.exact.compare:gauge_align")(enc.inner_target("UB", None, -0.61), KI)
    assert Dp is not None and res <= 1e-10 and np.abs(Dp.imag).max() <= 1e-12
    assert sum(1 for c in codes if Dp[cidx[c]].real < 0) == 8 and all(Dp[cidx[c]].real > 0 for c in codes if table[c] == 0.0)

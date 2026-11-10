"""M3-C1, M3-K1 — spin-network encoding: 16-qubit codec and the route-B target with the gauge (prompts/100 §2, §6;
docs/METHODS-spinnet.md §1-§3).

Encoding (Digonto, binding): 12 link qubits (j = 0 -> |0>, 1/2 -> |1>) and 4 corner qubits (J = 0 -> |0>, J = 1 -> |1>;
meaningful only when all four links at that corner are 1/2).  Data register d[0..7] = inner links b r t l, corners c0..c3;
outer register o[0..7] = outer links o0..o7.  The 433 physical states are computational-basis codes.  Target = route B
(6j), related to route A by the diagonal +-1 gauge D of gauge_align (audit 001 N5).  Numbers measured by the planner
(scratch/planner/proto_m3_spinnet.py, reports/research/100): gauge residual 2.7e-15, |V_B - D^dag V_A D| <= 2.4e-15."""
import functools
import itertools

import numpy as np
import pytest

from tests.acceptance._api import api

CORNER_INNER = ((0, 3), (0, 1), (1, 2), (2, 3))      # inner links (b r t l = 0 1 2 3) meeting at corners c0..c3
NOMINAL = (0.37, 0.61)
ALTS = ((0.91, 0.23), (1.70, 1.00))


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.spinnet:SpinNet")()


def _vec(keys, amps):
    return dict(zip(keys.tolist(), amps.tolist()))


def _dot(a, b):
    return sum(np.conj(v) * b[k] for k, v in a.items() if k in b)


def test_M3_C1_codec_and_vectors():
    """16-qubit codec: registers, 47 sorted inner codes (corner bit only with both inner links 1/2; 16 without a corner
    bit), 433 distinct unit codes consistent with the route-B labels (label order == route B), decode = label index,
    decode_state an isometry: physical code -> gauge[k] x route-A state (Gauss <= 1e-10, unit norm), inadmissible code ->
    a product state orthogonal to every physical state with Gauss residual >= 1/2 (analytic: a corner with k >= 1 aligned
    spin-1/2 ends has |G^z| = k/2), orthogonal to the other fallbacks.  gauge real +-1, residual <= 1e-10 (as M0-X6)."""
    enc = _enc()
    assert enc.name == "spinnet" and enc.n_data == 8 and enc.n_outer == 8 and enc.is_basis_encoding
    assert enc.registers["d"] == list(range(8)) and enc.registers["o"] == list(range(8, 16))
    assert enc.registers["links"] == [0, 1, 2, 3] and enc.registers["corners"] == [4, 5, 6, 7]
    assert enc.registers["link_b"] == [0] and enc.registers["link_l"] == [3] and enc.registers["corner_0"] == [4]
    assert enc.registers["outer_0"] == [8] and enc.registers["outer_7"] == [15]
    labels = api("su2plaq.exact.spinnet:labels")(jmax=0.5)
    assert enc.basis.labels == labels and len(labels) == 433
    code_of_label = api("su2plaq.encodings.spinnet:code_of_label")
    label_of_code = api("su2plaq.encodings.spinnet:label_of_code")
    # inner codes
    codes = enc.inner_codes()
    assert codes.dtype == np.int64 and len(codes) == 47 and np.array_equal(codes, np.sort(codes)) and codes.max() < 256
    for c in codes.tolist():
        for k, (a, b) in enumerate(CORNER_INNER):
            if (c >> (4 + k)) & 1:
                assert (c >> a) & 1 and (c >> b) & 1, f"corner bit {k} set without both inner links 1/2 in code {c:08b}"
    assert sum(1 for c in codes.tolist() if (c >> 4) == 0) == 16
    # physical vectors: unit codes
    eb = enc.physical_vectors()
    assert eb.n_data == 8 and eb.n_outer == 8 and len(eb.codes) == 433 and len(eb.amps) == 433
    allc = []
    for k, (c, a) in enumerate(zip(eb.codes, eb.amps)):
        assert c.dtype == np.int64 and len(c) == 1 and len(a) == 1 and abs(a[0] - 1.0) <= 1e-15
        code = int(c[0])
        assert 0 <= code < 2 ** 16 and code == code_of_label(labels[k]) and label_of_code(code) == labels[k]
        j, J = labels[k]
        for l in range(4):
            assert ((code >> l) & 1) == (j[l] == 0.5)
        for kk in range(8):
            assert ((code >> (8 + kk)) & 1) == (j[4 + kk] == 0.5)
        for cc in range(4):
            assert ((code >> (4 + cc)) & 1) == (J[cc] == 1.0)
        assert (code & 0xFF) in set(codes.tolist())
        assert enc.decode(code) == k
        allc.append(code)
    assert len(set(allc)) == 433
    assert enc.decode(0b1 << 4) is None and label_of_code(0b1 << 4) is None   # corner bit without links
    # gauge and decode_state on physical codes
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
    # linearity / empty input
    k0, a0 = enc.decode_state(np.array([allc[0], allc[1]], dtype=np.int64), np.array([0.6, 0.8j]))
    assert abs(np.linalg.norm(a0) - 1) <= 1e-12
    ke, ae = enc.decode_state(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.complex128))
    assert len(ke) == 0 and len(ae) == 0
    # inadmissible codes (valid inner code, outer pattern that does not fuse): isometric fallback, Gauss >= 1/2
    physical = set(allc)
    bad = [c | (o << 8) for c in codes.tolist() for o in range(256) if (c | (o << 8)) not in physical]
    assert len(bad) == 47 * 256 - 433
    rng = np.random.default_rng(20261104)
    sample = [bad[i] for i in rng.choice(len(bad), size=120, replace=False)]
    phys_vecs = [_vec(enc.basis.keys[k], enc.basis.amps[k]) for k in range(433)]
    fall = []
    for code in sample:
        assert enc.decode(code) is None
        keys, amps = enc.decode_state(np.array([code], dtype=np.int64), np.array([1.0 + 0j]))
        v = _vec(keys, amps)
        assert abs(np.linalg.norm(amps) - 1) <= 1e-12
        assert gauss_residual(enc.basis, keys, amps) >= 0.5 - 1e-10
        assert max(abs(_dot(p, v)) for p in phys_vecs) <= 1e-12
        fall.append(v)
    for i in range(0, len(fall) - 1, 2):
        assert abs(_dot(fall[i], fall[i + 1])) <= 1e-12
    desc = enc.describe()
    assert isinstance(desc, str) and "47" in desc and "433" in desc and "corner" in desc.lower()


def test_M3_K1_route_b_target_with_gauge():
    """Target = route B: U_B(beta) = expm(-i beta H_B^{6j}) in label order, equal to D^dag V_A D (1e-10; expm of a
    433x433 Hermitian matrix with ||H|| <= 2, measured 2e-15) at the nominal and alternate angles; U_E = diag(exp(-i alpha
    sum_inner j(j+1))); step orders compose; the outer-electric variant matches route A.  K structure (47 inner codes):
    16 bright codes paired by the four-link flip (code ^ 0b1111, corner bits unchanged), couplings K = -2 (vacuum pair
    0000/1111), -1/2 (alternating 0101/1010), +1 (six pairs); 31 dark rows (any corner bit set).  Fig. 2 claim: the
    physical target restricted to any outer pattern equals the 47x47 inner target (1e-12).  Physics finding: at
    j_max = 1/2 the sign of beta is a basis-sign convention in this encoding: U_B(-beta) = D' U_B(beta) D' with a real
    diagonal D' (one -1 per bright pair), gauge_align residual <= 1e-10."""
    enc = _enc()
    expm = __import__("scipy.linalg", fromlist=["expm"]).expm
    labels = enc.basis.labels
    HB = api("su2plaq.exact.spinnet:h_magnetic_phys_6j")(labels)
    HE = api("su2plaq.exact.spinnet:h_electric_6j")(labels)
    K = api("su2plaq.exact.spinnet:K_inner")(jmax=0.5)
    target_A = api("su2plaq.exact.operators:target")
    gauge_align = api("su2plaq.exact.compare:gauge_align")
    Dm = np.diag(enc.gauge)
    assert np.abs(enc.h_magnetic() - HB).max() <= 1e-12 and np.abs(enc.h_electric() - np.diag(HE)).max() <= 1e-12
    for alpha, beta in (NOMINAL,) + ALTS:
        VB = enc.target("UB", None, beta)
        assert VB.shape == (433, 433) and np.abs(VB - expm(-1j * beta * HB)).max() <= 1e-12
        assert np.abs(VB - Dm.conj().T @ target_A(enc.basis, "UB", beta=beta) @ Dm).max() <= 1e-10
        UE = enc.target("UE", alpha, None)
        assert np.abs(UE - np.diag(np.exp(-1j * alpha * np.diag(HE)))).max() <= 1e-12
        assert np.abs(enc.target("step", alpha, beta, 1) - VB @ UE).max() <= 1e-12
        UEh = enc.target("UE", alpha / 2, None)
        assert np.abs(enc.target("step", alpha, beta, 2) - UEh @ VB @ UEh).max() <= 1e-12
    UEo = enc.target("UE", 0.37, None, include_outer_electric=True)
    assert np.abs(UEo - target_A(enc.basis, "UE", alpha=0.37, include_outer_electric=True)).max() <= 1e-10
    assert np.abs(UEo - enc.target("UE", 0.37, None)).max() > 1e-3
    # K structure on the inner codes
    codes = enc.inner_codes().tolist()
    table = api("su2plaq.spinnet.walk:coupling_table")(enc)
    assert set(table) == set(codes)
    bright = {c: v for c, v in table.items() if v != 0.0}
    assert len(bright) == 16 and all((c >> 4) == 0 for c in bright)
    for c, v in bright.items():
        assert (c ^ 0b1111) in bright and abs(bright[c ^ 0b1111] - v) <= 1e-12
        expect = -2.0 if c in (0b0000, 0b1111) else (-0.5 if c in (0b0101, 0b1010) else 1.0)
        assert abs(v - expect) <= 1e-12, (c, v)
    KI = enc.inner_target("UB", None, 0.61)
    assert KI.shape == (47, 47)
    il = api("su2plaq.exact.spinnet:inner_labels")(jmax=0.5)
    code_of_label = api("su2plaq.encodings.spinnet:code_of_label")
    pos = {code_of_label((j + (0.0,) * 8, J)) & 0xFF: i for i, (j, J) in enumerate(il)}
    perm = [pos[c] for c in codes]
    assert np.abs(KI - expm(-1j * 0.61 * K[np.ix_(perm, perm)])).max() <= 1e-12
    assert np.abs(enc.K - K).max() <= 1e-12
    dark = [i for i in range(47) if np.abs(K[i]).max() <= 1e-12]
    assert len(dark) == 31
    # Fig. 2: every outer block of the physical target is the inner target restricted (independent of the outer pattern)
    VB = enc.target("UB", None, 0.61)
    eb = enc.physical_vectors()
    full = [int(c[0]) for c in eb.codes]
    by_outer: dict = {}
    for k, c in enumerate(full):
        by_outer.setdefault(c >> 8, []).append(k)
    assert len(by_outer) == 128
    cidx = {c: i for i, c in enumerate(codes)}
    worst = 0.0
    for ks in by_outer.values():
        ii = [cidx[full[k] & 0xFF] for k in ks]
        worst = max(worst, np.abs(VB[np.ix_(ks, ks)] - KI[np.ix_(ii, ii)]).max())
    assert worst <= 1e-12
    offblock = VB.copy()
    for ks in by_outer.values():
        offblock[np.ix_(ks, ks)] = 0.0
    assert np.abs(offblock).max() == 0.0
    # sign of beta is a gauge in this encoding at j_max = 1/2
    Dp, res = gauge_align(enc.inner_target("UB", None, -0.61), KI)
    assert Dp is not None and res <= 1e-10 and np.abs(Dp.imag).max() <= 1e-12
    assert sum(1 for c in codes if Dp[cidx[c]].real < 0) == 8 and all(Dp[cidx[c]].real > 0 for c in codes if (c >> 4) != 0)
    # regauge helper used by the external-circuit tests: D on the inner codes -> D on the 433 states
    Vg = enc.regauge(VB, Dp)
    assert np.abs(Vg - enc.target("UB", None, -0.61)).max() <= 1e-10

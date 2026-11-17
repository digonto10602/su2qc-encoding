"""M11-E / M11-F — what can be compared between DIFFERENT models (prompts/009 §4.2-§4.4, §6; docs/METHODS.md §13.2-§13.4).

The rishon encoding is the SU(2) quantum link model with a det term (38 432 physical states), the fuzzy encoding is fuzzy gauge
theory (arXiv:2308.05253); neither is Kogut-Susskind (KS) at j_max = 1/2 (433 states).  Exact relations that do hold:

E1: the KS j <= 1/2 link (5 states: U_ab, L_a, R_a, j(j+1)) is a COMPRESSION of the model link: an isometry V (16 x 5) with
    V^dag U_ab V = c U_ab^KS, V^dag L_a V = L_a^KS, V^dag R_a V = R_a^KS, V^dag H_E V = j(j+1), hence V^{(x)4 dag} W V^{(x)4} = W^KS
    for the plaquette; the leak (1 - P) U_ab V is NOT zero (that is the different physics): its squared norm is 1/2 or 1,
    for the plaquette 15, 33/8 or 4.
E2: rishon closed sector (17 x 17) with independent couplings, H = c_E H_E + c_B H_B + lam_D H_D: for lam_D = -L,
    c_E = g^2/2 - 8L/3, c_B = 1/g^2 the two lowest levels + 8L tend to the KS closed block [[0,-2/g^2],[-2/g^2,3g^2/2]] with
    L (lambda_k(L) - lambda_k^KS) -> -(13/4) g^-4 w_k, w_k = loop weight of KS eigenvector k (second-order perturbation theory:
    six states at 8L and one at 16L, each coupled with 2/g^2).
E3: the same limit on the full space: the 433 lowest of the 38 432 levels (+ 24 L) tend to the 433 KS levels, error ~ 1/L.
F1: fuzzy theory with the K1 kinetic term only (r = 0): each link has a conserved flavour sign; in the flavour sectors
    (b, r, t, l) = (+,+,-,-) and (-,-,+,+) the closed sector is exactly the KS 2 x 2 block; in the other 14 sectors it is not.
F2: isolated fuzzy plaquette (50 Gauss-law states): K1 only -> twofold degenerate ground level at every coupling; with K2 the
    gap closes as (g^2)^7 at weak coupling (arXiv:2308.05253 Sec. IV B and Fig. 3, slope 7), while the KS gap diverges as 4/g^2.
F3: K2 gives -4 to the singlet Psi = 1/2 and +2 to the flux copy U_ab Psi (and +4 / -2 to the Gamma_5 copy), and U has no matrix
    element between the two embeddings: no choice of (a K1 + b K2) makes a KS-like sector the low-energy sector (METHODS §13.4).

Tolerances.  Algebraic identities of 16 x 16 (5 x 5, 625 x 625) matrices with entries of modulus <= 2: 1e-12 (float64 rounding
measured <= 5.6e-16; the project's algebra tolerance, METHODS-fuzzy F6).  Leak norms formed from a difference of Gram matrices:
1e-6 on the square (rounding ~1e-13; the values are the exact numbers 1/2, 1, 15, 33/8, 4).  Limits: tolerances are stated at
each assert with the measured value (reports/research/006 §3, §4); all are convergence statements whose error terms are O(1/L)
or O(g^4) and were measured at 3 to 6 times below the tolerance.
Cost (one process, quiet core): E1 < 5 s per model; F3 < 1 s; E2 about 5 s; E3 about 20 s and 0.6 GB per coupling (g^2 = 1 runs in the
fast set, the other two and the 38 432-level test are slow); F1 about 2 s; F2 about 15 s (50-state basis built once).
"""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from tests.acceptance._api import api

TOL = 1e-10
ALG = 1e-12
G2S = (0.5, 1.0, 2.0)
PHASE = {"rishon_plus": 1.0, "rishon_minus": 1.0j, "fuzzy_one": 1.0, "fuzzy_gamma5": 1.0, "fuzzy_fplus": 1.0, "fuzzy_fminus": 1.0}
LEAK_U_SQ = {"rishon_plus": 0.5, "rishon_minus": 0.5, "fuzzy_one": 0.5, "fuzzy_gamma5": 0.5, "fuzzy_fplus": 1.0, "fuzzy_fminus": 1.0}
LEAK_W_SQ = {"rishon_plus": 15.0, "rishon_minus": 15.0, "fuzzy_one": 4.125, "fuzzy_gamma5": 4.125, "fuzzy_fplus": 4.0, "fuzzy_fminus": 4.0}
FLAVOUR_DIM = {(1, 1, -1, -1): 2, (-1, -1, 1, 1): 2, (1, -1, -1, 1): 4, (-1, 1, 1, -1): 4}     # the other twelve patterns: 3


def _embed():
    return api("su2plaq.crosscheck.embed")


def _limits():
    return api("su2plaq.crosscheck.limits")


def _model_ops(model):
    """Link operators of the model taken from its own (M5 / M9, locked) module: (U[a][b], L[a], R[a], H_E), 16 x 16."""
    if model.startswith("rishon"):
        rl = api("su2plaq.rishon.algebra:RishonLink")()
        return ([[rl.U(i, j) for j in range(2)] for i in range(2)], list(rl.L), list(rl.R), 0.5 * (rl.casimir_L + rl.casimir_R))
    fz = api("su2plaq.fuzzy.link")
    return ([[fz.U_op(a, b) for b in range(2)] for a in range(2)], [fz.calT_L(A) for A in range(3)],
            [fz.calT_R(A) for A in range(3)], 0.5 * fz.K1())


def _kron4(ms):
    return np.kron(ms[3], np.kron(ms[2], np.kron(ms[1], ms[0])))          # links (b, r, t, l), b least significant


def _compressed_plaquette(U, V):
    """(V^{(x)4})^dag W V^{(x)4} and (W V^{(x)4})^dag (W V^{(x)4}) from 5 x 5 factors; W = sum U_b[a,b] U_r[b,c] U_t[e,c]^dag U_l[a,e]^dag
    (the contraction of exact.operators._build_W, METHODS §3)."""
    Vd = V.conj().T
    idx = list(itertools.product(range(2), repeat=4))

    def factors(a, b, c, e):
        return [U[a][b], U[b][c], U[e][c].conj().T, U[a][e].conj().T]

    Wc = sum(_kron4([Vd @ X @ V for X in factors(*t)]) for t in idx)
    G = np.zeros((625, 625), dtype=np.complex128)
    for t in idx:
        Ft = factors(*t)
        for u in idx:
            G += _kron4([Vd @ Y.conj().T @ X @ V for X, Y in zip(factors(*u), Ft)])
    return Wc, G


def _ks_block(g2):
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


# ---------------------------------------------------------------------------------------------------- E1, F3: one link
@pytest.mark.parametrize("model", sorted(PHASE))
def test_M11_E1_ks_link_is_a_compression_of_the_model_link(model):
    E = _embed()
    assert set(E.LINK_MODELS) == set(PHASE)
    V, c = E.link_isometry(model)
    V = np.asarray(V, dtype=np.complex128)
    assert V.shape == (16, 5) and abs(complex(c) - PHASE[model]) <= ALG          # phase convention: arg c in [0, pi)
    ks = api("su2plaq.su2.algebra:LinkSpace")(0.5)
    UK = ks.U()
    LK, RK = ks.generators()
    U, L, R, HE = _model_ops(model)
    Vd = V.conj().T
    P = V @ Vd
    assert np.abs(Vd @ V - np.eye(5)).max() <= ALG
    for a in range(2):
        for b in range(2):
            assert np.abs(Vd @ U[a][b] @ V - c * UK[a][b]).max() <= ALG, (a, b)
    for a in range(3):
        assert np.abs(Vd @ L[a] @ V - LK[a]).max() <= ALG and np.abs(Vd @ R[a] @ V - RK[a]).max() <= ALG, a
        assert np.abs(P @ L[a] - L[a] @ P).max() <= ALG and np.abs(P @ R[a] - R[a] @ P).max() <= ALG, a
    assert np.abs(Vd @ HE @ V - ks.casimir()).max() <= ALG and np.abs(P @ HE - HE @ P).max() <= ALG
    # the model link operator leaves the embedded space: exact squared leak 1/2 (rishon, fuzzy 1 / Gamma_5) or 1 (flavour copies)
    leak = max(np.linalg.norm((np.eye(16) - P) @ U[a][b] @ V, 2) ** 2 for a in range(2) for b in range(2))
    assert abs(leak - LEAK_U_SQ[model]) <= ALG
    # plaquette: compression equals the KS plaquette of M0; squared leak of W V^{(x)4}: 15, 33/8, 4
    Wc, G = _compressed_plaquette(U, V)
    assert np.abs(Wc - api("su2plaq.exact.operators:plaquette_W")(convention="cg")).max() <= ALG
    leak_w = float(np.linalg.eigvalsh(G - Wc.conj().T @ Wc).max())
    assert abs(leak_w - LEAK_W_SQ[model]) <= 1e-6
    r = E.link_compression(model)
    for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette"):
        assert 0.0 <= r[k] <= ALG, k
    assert abs(r["leak_U"] ** 2 - LEAK_U_SQ[model]) <= 1e-9 and abs(r["leak_plaquette"] ** 2 - LEAK_W_SQ[model]) <= 1e-6
    assert abs(complex(r["phase"]) - PHASE[model]) <= ALG


def test_M11_E1_rishon_det_term_separates_the_two_singlets():
    """H_D = det U + h.c. is +2 on the 'plus' singlet, -2 on the 'minus' singlet, 0 on the four flux states, and commutes with both
    embedded projectors (METHODS-rishon R13): the det coupling is the knob of the limit E2 / E3."""
    E = _embed()
    rl = api("su2plaq.rishon.algebra:RishonLink")()
    D = rl.det_U + rl.det_U.conj().T
    for model, val in (("rishon_plus", 2.0), ("rishon_minus", -2.0)):
        V, _ = E.link_isometry(model)
        V = np.asarray(V)
        assert np.abs(D @ V - V @ np.diag([val, 0.0, 0.0, 0.0, 0.0])).max() <= ALG, model


def test_M11_F3_fuzzy_k2_orders_the_flux_copies_against_the_plaquette():
    E = _embed()
    fz = api("su2plaq.fuzzy.link")
    K1, K2 = fz.K1(), fz.K2()
    Vp = np.asarray(E.link_isometry("fuzzy_one")[0])
    Vm = np.asarray(E.link_isometry("fuzzy_gamma5")[0])
    assert np.abs(K2 @ Vp - Vp @ np.diag([-4.0, 2.0, 2.0, 2.0, 2.0])).max() <= ALG
    assert np.abs(K2 @ Vm - Vm @ np.diag([4.0, -2.0, -2.0, -2.0, -2.0])).max() <= ALG
    for V in (Vp, Vm):
        assert np.abs(K1 @ V - V @ np.diag([0.0, 1.5, 1.5, 1.5, 1.5])).max() <= ALG
    assert np.abs(Vp.conj().T @ Vm).max() <= ALG
    for a in range(2):
        for b in range(2):
            Uab = fz.U_op(a, b)
            assert np.abs(Vm.conj().T @ Uab @ Vp).max() <= ALG and np.abs(Vp.conj().T @ Uab @ Vm).max() <= ALG, (a, b)
    # consequence (arithmetic on the certified eigenvalues): for any b != 0 the lower singlet and the lower flux quartet of
    # a K1 + b K2 belong to different embeddings, between which U has no matrix element
    for a_, b_ in ((1.0, 0.5), (1.0, -0.5), (-3.0, 1.0), (5.0, -2.0)):
        h = a_ * K1 + b_ * K2
        e = {n: np.real(np.diag(V.conj().T @ h @ V)) for n, V in (("one", Vp), ("g5", Vm))}
        assert (e["one"][0] < e["g5"][0]) == (e["one"][1] > e["g5"][1]), (a_, b_)


# ---------------------------------------------------------------------------------------------------- E2, E3: rishon -> KS
def _closed_formula(c_e, c_b, lam_d):
    """METHODS-rishon R13 with independent couplings: basis = 16 electric vacua (bit l = type B on link l, links b, r, t, l) + loop;
    H = 3 c_e |loop><loop| - 4 c_b (|loop>(<vac_A| + <vac_B|) + h.c.) + 2 lam_d sum_l X_l,  vac_A = (A,A,B,B), vac_B = (B,B,A,A)."""
    H = np.zeros((17, 17))
    X, I = np.array([[0.0, 1.0], [1.0, 0.0]]), np.eye(2)
    for l in range(4):
        ops = [I, I, I, I]
        ops[l] = X
        H[:16, :16] += 2.0 * lam_d * _kron4(ops)
    H[16, 16] = 3.0 * c_e
    for v in (0b1100, 0b0011):
        H[16, v] = H[v, 16] = -4.0 * c_b
    return H


def test_M11_E2_rishon_closed_sector_reaches_the_ks_block():
    Lm = _limits()
    for (ce, cb, lam) in ((0.5, 1.0, 0.0), (1.0, 0.5, 0.2), (0.3, 0.7, -1.1), (-170.0, 2.0, -64.0)):
        B = np.asarray(Lm.rishon_closed_block(ce, cb, lam))
        assert B.shape == (17, 17) and np.abs(B - B.conj().T).max() <= ALG
        ref = np.linalg.eigvalsh(_closed_formula(ce, cb, lam))
        assert np.abs(np.linalg.eigvalsh(B) - ref).max() <= 1e-12 * (1.0 + np.abs(ref).max()), (ce, cb, lam)
    for g2 in G2S:
        ek, vk = np.linalg.eigh(_ks_block(g2))
        pred = -(13.0 / 4.0) / g2 ** 2 * vk[1, :] ** 2            # limit of L (lambda_k(L) - lambda_k^KS)
        d = {}
        for L in (128.0, 256.0):
            ev = np.linalg.eigvalsh(np.asarray(Lm.rishon_closed_block(g2 / 2 - 8 * L / 3, 1 / g2, -L))) + 8 * L
            d[L] = ev[:2] - ek
            assert abs((ev[2] - ev[1]) - (4 * L - ek[1])) <= 0.2, (g2, L)     # next band 4L above the vacuum; measured offset <= 0.055
        rel = np.abs(256.0 * d[256.0] - pred) / np.abs(pred)
        assert rel.max() <= 0.01, (g2, rel)                       # O(1/L) remainder: measured <= 0.0017 at L = 256
        slope = np.log(np.abs(d[256.0] / d[128.0])) / np.log(2.0)
        assert np.abs(slope + 1.0).max() <= 0.01, (g2, slope)     # measured |slope + 1| <= 0.0024


@pytest.mark.parametrize("g2", [pytest.param(0.5, marks=pytest.mark.slow), 1.0, pytest.param(2.0, marks=pytest.mark.slow)])
def test_M11_E3_rishon_433_lowest_levels_reach_the_ks_spectrum(g2):
    Lm = _limits()
    basis = api("su2plaq.exact.physical:physical_basis")(convention="cg")
    ks = np.linalg.eigvalsh(api("su2plaq.exact.operators:hamiltonian_phys")(basis, g2, include_outer_electric=True))
    out = {}
    for L in (64.0, 128.0):
        r = Lm.rishon_ks_limit(g2, L)
        lv = np.asarray(r["levels"], dtype=float)
        assert lv.shape == (433,) and np.all(np.diff(lv) >= -1e-9)
        assert np.abs(np.asarray(r["ks_levels"], dtype=float) - ks).max() <= TOL
        dev = float(np.abs(lv - ks).max())
        assert abs(dev - r["max_dev"]) <= 1e-12
        assert 4 * L - 12.0 <= r["gap_to_next_band"] <= 4 * L, (L, r["gap_to_next_band"])     # measured 4L - 9.6 .. 4L - 7.3
        out[L] = dev
    slope = np.log(out[128.0] / out[64.0]) / np.log(2.0)
    assert abs(slope + 1.0) <= 0.02, slope                          # measured -0.9973, -1.0010, -1.0043
    ek, vk = np.linalg.eigh(_ks_block(g2))
    pred = (13.0 / 4.0) / g2 ** 2 * vk[1, 1] ** 2                   # the slowest level is the upper closed-sector level (E2)
    assert abs(128.0 * out[128.0] - pred) / pred <= 0.01            # measured 0.0017, 0.0008, 0.0030


@pytest.mark.slow
def test_M11_E3_rishon_levels_at_the_project_couplings():
    """`rishon_levels(c_e, c_b, lam_d)` at lam_d = 0 contains the closed-sector levels of Report 5 with the right multiplicity:
    3 g^2/4 +- sqrt(9 g^4/16 + 32/g^4) once per choice of the 2^8 outer singlets, and the level count is 38 432."""
    Lm = _limits()
    g2 = 1.0
    ev = np.asarray(Lm.rishon_levels(g2 / 2, 1 / g2, 0.0), dtype=float)
    assert ev.shape == (38432,) and np.all(np.diff(ev) >= -1e-9)
    lo = 0.75 * g2 - np.sqrt(0.5625 * g2 ** 2 + 32.0 / g2 ** 2)
    assert abs(ev[0] - lo) <= TOL and int(np.sum(np.abs(ev - lo) <= 1e-9)) == 256
    assert np.array_equal(np.asarray(Lm.rishon_levels(g2 / 2, 1 / g2, 0.0, k=5)), ev[:5])


# ---------------------------------------------------------------------------------------------------- F1, F2: fuzzy
def test_M11_F1_fuzzy_flavour_sectors_at_r0():
    Lm = _limits()
    for signs in itertools.product((1, -1), repeat=4):
        d = FLAVOUR_DIM.get(signs, 3)
        for g2 in G2S:
            H = np.asarray(Lm.fuzzy_flavour_block(g2, signs))
            assert H.shape == (d, d) and np.abs(H - H.conj().T).max() <= ALG, (signs, g2)
            assert abs(H[0, 0]) <= TOL                               # basis vector 0 = the flavour vacuum: K1 = 0, <square> = 0
            ek = np.linalg.eigvalsh(_ks_block(g2))
            ev = np.linalg.eigvalsh(H)
            if d == 2:
                assert np.abs(ev - ek).max() <= TOL, (signs, g2)     # measured <= 1.8e-15
            else:
                assert max(np.abs(ev - x).min() for x in ek) >= 0.5, (signs, g2)     # measured >= 0.608


def test_M11_F2_fuzzy_isolated_plaquette_gap():
    Lm = _limits()
    lv = np.asarray(Lm.fuzzy_isolated_levels(1.0, 1.0, 1.0), dtype=float)
    assert lv.shape == (50,) and np.all(np.diff(lv) >= -1e-9)
    # K1 only (r = 0): twofold degenerate ground level, third level well above (measured 7.81, 3.60, 0.845)
    for g2 in G2S:
        ev = np.asarray(Lm.fuzzy_isolated_levels(g2, 1.0, 0.0), dtype=float)
        assert ev[1] - ev[0] <= TOL and ev[2] - ev[0] >= 0.5, g2
    # with K2: gap ~ (g^2)^7 at weak coupling; K2 alone: slope 7.0004; project model K1 + K2 (r = 1): 7.029 (correction ~ g^4)
    gap = {}
    for (a, b) in ((0.0, 1.0), (1.0, 1.0), (1.0, 2.0)):
        for g2 in (0.15, 0.2):
            ev = np.asarray(Lm.fuzzy_isolated_levels(g2, a, b), dtype=float)
            gap[(a, b, g2)] = float(ev[1] - ev[0])
            assert gap[(a, b, g2)] > 1e-10
    slope = lambda a, b: np.log(gap[(a, b, 0.2)] / gap[(a, b, 0.15)]) / np.log(0.2 / 0.15)
    assert abs(slope(0.0, 1.0) - 7.0) <= 0.02 and abs(slope(1.0, 1.0) - 7.0) <= 0.06
    # fourth order in the K2 coupling: doubling b multiplies the gap by 16 (measured 16.002)
    assert abs(gap[(1.0, 2.0, 0.15)] / gap[(1.0, 1.0, 0.15)] - 16.0) <= 0.32
    # strong coupling, r = 1: gap -> 2 g^2 (KS closed sector: 3 g^2 / 2); measured 0.9999973 at g^2 = 16
    ev = np.asarray(Lm.fuzzy_isolated_levels(16.0, 1.0, 1.0), dtype=float)
    assert abs((ev[1] - ev[0]) / 32.0 - 1.0) <= 1e-4

"""M11-K — the three encodings of the SAME model agree (prompts/009 §4.1, §6; docs/METHODS.md §13.1).

`twelve` (Paulo's 12-qubit code, route A), `spinnet` (route B, 6j symbols) and `lsh` (loop-string-hadron operators) encode the
Kogut-Susskind Hamiltonian at j_max = 1/2 on the same 433 physical states, listed in the label order of
`exact.physical.physical_basis(convention="cg")`.  Their bases differ only by signs: H_B(twelve) = D H_B(enc) D with D = diag(+-1).

K1: each encoding's own H_E and H_B (`crosscheck.ks.ks_operators`) have the right electric values, the Lean-certified H_B
    multiplicities (METHODS §11.3 b), and the spectra of H(g^2) = (g^2/2) H_E + H_B / g^2 agree pairwise.
K2: `transported_target(src, dst, ...)` (src's own step target, moved by the sign matrix) equals dst's own target.
K3: the GENERAL step circuit of one encoding passes the production evaluator against the target of ANOTHER encoding.
K4 (slow): the compressed HEADLINE circuit of one encoding passes the evaluator against the target of another encoding.

Tolerances: 1e-10 = the project's exact-angle tolerance for "two independent constructions of the same operator" (prompts/001 §1,
prompts/004); measured in the planner prototype (reports/research/006 §2): spectra 2.8e-14, transported targets 3.0e-15,
cross-verdicts 4.8e-15 .. 2.7e-13.  By the Bauer-Fike theorem (Numer. Math. 2 (1960) 137, doi:10.1007/BF01386217) every
eigenvalue of a circuit's physical block lies within `total_error` of an eigenphase of the (unitary, hence normal) target, so a
passing cross-verdict also certifies equal step spectra.  Negative control: a foreign target with beta off by 1e-6 must be
rejected with block error ||H_B|| * 1e-6 = 2e-6 (first order; window +-5 %).
Cost: K1, K2 < 20 s; K3 about 20 s for the twelve circuit (three evaluations of 6 s), < 5 s for the others; K4 about 30 s per
case once the headline cache exists; peak memory < 1 GB (prototype: 0.8 GB).
"""
from __future__ import annotations

import numpy as np
import pytest

from tests.acceptance._api import api

TOL = 1e-10
ENCS = ("twelve", "spinnet", "lsh")
ANGLES = ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))
G2S = (0.5, 1.0, 2.0)
HB_MULT = {-2.0: 16, -1.0: 96, -0.5: 16, 0.0: 177, 0.5: 16, 1.0: 96, 2.0: 16}       # METHODS §11.3 (b), Lean-certified


def _ks():
    return api("su2plaq.crosscheck.ks")


def _get(name):
    return api("su2plaq.compress.spec:get_encoding")(name)


def _evaluate():
    return api("su2plaq.evaluate.evaluator:evaluate")


@pytest.mark.parametrize("enc", ENCS)
def test_M11_K1_ks_operators_of_each_encoding(enc):
    """(he_inner, he_all, HB): electric values 3/4 per j = 1/2 link from the labels, H_B Hermitian with the certified spectrum."""
    K = _ks()
    he_in, he_all, HB = K.ks_operators(enc)
    labels = api("su2plaq.exact.physical:physical_basis")(convention="cg").labels
    j = np.array([lab[0] for lab in labels], dtype=float)
    assert j.shape == (433, 12)
    he_in, he_all, HB = np.asarray(he_in), np.asarray(he_all), np.asarray(HB)
    assert he_in.shape == (433,) and he_all.shape == (433,) and HB.shape == (433, 433)
    assert np.abs(he_in - 0.75 * (j[:, :4] == 0.5).sum(axis=1)).max() <= 1e-12
    assert np.abs(he_all - 0.75 * (j == 0.5).sum(axis=1)).max() <= 1e-12
    assert np.abs(HB - HB.conj().T).max() <= 1e-12
    vals, counts = np.unique(np.round(np.linalg.eigvalsh(HB), 9) + 0.0, return_counts=True)
    assert dict(zip(vals.tolist(), counts.tolist())) == HB_MULT
    H = np.asarray(K.ks_hamiltonian(enc, 1.3, include_outer_electric=True))
    assert np.abs(H - (0.65 * np.diag(he_all) + HB / 1.3)).max() <= 1e-12
    H = np.asarray(K.ks_hamiltonian(enc, 1.3, include_outer_electric=False))
    assert np.abs(H - (0.65 * np.diag(he_in) + HB / 1.3)).max() <= 1e-12


def test_M11_K1_spectra_agree_between_the_three_constructions():
    """All 433 levels of H(g^2), with and without the outer electric energy, agree pairwise; the closed-sector levels
    3 g^2/4 +- sqrt(9 g^4/16 + 4/g^4) (METHODS §4) are among them."""
    K = _ks()
    for g2 in G2S:
        for outer in (True, False):
            ev = {e: np.linalg.eigvalsh(np.asarray(K.ks_hamiltonian(e, g2, include_outer_electric=outer))) for e in ENCS}
            for a in ENCS:
                for b in ENCS:
                    assert np.abs(ev[a] - ev[b]).max() <= TOL, (g2, outer, a, b)
            for s in (+1.0, -1.0):
                lam = 0.75 * g2 + s * np.sqrt(0.5625 * g2 ** 2 + 4.0 / g2 ** 2)
                assert np.abs(ev["twelve"] - lam).min() <= TOL, (g2, outer, s)


def test_M11_K2_gauge_signs_and_transported_targets():
    """D is a vector of +-1 (all +1 for twelve, the reference); src's target conjugated by D_src D_dst is dst's own target, for
    every ordered pair, both step orders and the three locked angle pairs."""
    K = _ks()
    D = {e: np.asarray(K.gauge_signs(e), dtype=float) for e in ENCS}
    for e in ENCS:
        assert D[e].shape == (433,) and set(np.unique(D[e]).tolist()) <= {-1.0, 1.0}
    assert np.all(D["twelve"] == 1.0)
    own = {(e, a, b, o): np.asarray(_get(e).target("step", a, b, o)) for e in ENCS for (a, b) in ANGLES for o in (1, 2)}
    for (a, b) in ANGLES:
        for o in (1, 2):
            for src in ENCS:
                for dst in ENCS:
                    if src == dst:
                        continue
                    T = np.asarray(K.transported_target(src, dst, "step", a, b, o))
                    s = D[src] * D[dst]
                    assert np.abs(T - s[:, None] * own[(src, a, b, o)] * s[None, :]).max() <= 1e-12, (src, dst, a, b, o)
                    assert np.linalg.norm(T - own[(dst, a, b, o)], 2) <= TOL, (src, dst, a, b, o)
    for kind in ("UE", "UB"):
        T = np.asarray(K.transported_target("lsh", "spinnet", kind, 0.37, 0.61))
        assert np.linalg.norm(T - np.asarray(_get("spinnet").target(kind, 0.37, 0.61)), 2) <= TOL, kind


@pytest.mark.parametrize("circ,targ", [("twelve", "lsh"), ("spinnet", "twelve"), ("lsh", "spinnet")])
def test_M11_K3_general_circuit_against_another_encodings_target(circ, targ):
    """The general first-order step circuit of `circ` is exact on all 433 states against the step operator built by `targ`'s
    code; the same circuit is rejected against that operator at beta + 1e-6."""
    K = _ks()
    ev = _evaluate()
    qc, info = K.step_circuit(circ, "general", 0.37, 0.61, 1)
    assert info["which"] == "general" and info["entry"] is None
    v = ev(qc, _get(circ), np.asarray(K.transported_target(targ, circ, "step", 0.37, 0.61, 1)))
    assert v.ok and v.reason == "ok" and v.certified and v.n_inputs == 433
    assert v.total_error <= TOL and v.gauss_residual <= TOL
    w = K.cross_verdict(circ, targ, which="general", alpha=0.37, beta=0.61, order=1)
    assert w.ok and w.certified and abs(w.total_error - v.total_error) <= 1e-12
    bad = ev(qc, _get(circ), np.asarray(K.transported_target(targ, circ, "step", 0.37, 0.61 + 1e-6, 1)))
    assert not bad.ok and 1.9e-6 <= bad.block_error <= 2.1e-6


@pytest.mark.slow
@pytest.mark.parametrize("circ,targ", [("twelve", "spinnet"), ("spinnet", "lsh"), ("lsh", "twelve")])
def test_M11_K4_headline_circuit_against_another_encodings_target(circ, targ, root):
    """The compressed headline circuit (smallest robust key, METHODS §12.4) of `circ`, rebuilt from its program file at the nominal
    pair and at the alternate pair (0.91, 0.23), is exact against `targ`'s step operator; rejected at beta + 1e-6."""
    K = _ks()
    ev = _evaluate()
    RB = api("su2plaq.compress.robust")
    h = RB.headline(circ, "step", root=root, compute=False)
    if h is None or h.get("id") is None:
        pytest.fail(f"PENDING: no cached headline of the {circ} archive (results/compress/{circ}/robust.json; prompts/008 Phase C, "
                    f"for lsh the M8 loop of prompts/401)", pytrace=False)
    for (a, b) in ((0.37, 0.61), (0.91, 0.23)):
        qc, info = K.step_circuit(circ, "headline", a, b, 1)
        assert info["which"] == "headline" and info["entry"] == h["id"]
        v = ev(qc, _get(circ), np.asarray(K.transported_target(targ, circ, "step", a, b, 1)))
        assert v.ok and v.reason == "ok" and v.certified and v.n_inputs == 433, (a, b, v.reason)
        assert v.total_error <= TOL and v.gauss_residual <= TOL, (a, b, v.total_error)
    bad = ev(qc, _get(circ), np.asarray(K.transported_target(targ, circ, "step", 0.91, 0.23 + 1e-6, 1)))
    assert not bad.ok and 1.9e-6 <= bad.block_error <= 2.1e-6

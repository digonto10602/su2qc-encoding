"""M11-H — the headline rule of the fuzzy units and the meaning of "angle-linear" (prompts/010; docs/METHODS.md §12.4).

Decision of prompts/010: the generic rule is KEPT.  rho = 0 only if every rotation angle is c_alpha alpha + c_beta beta (no
constant term); a constant term is reported, not rewarded.  New, for information only: `robust.angle_offsets` classifies the
constant terms of a program:
    "linear"               no constant term (rho = 0);
    "clifford_offset"      affine, and every constant is a multiple of pi/2 on rz / p (or of pi on crz / crx / cp):
                           R_z(theta + k pi/2) = R_z(theta) S^k up to a global phase, a Clifford factor, no T gate;
    "non_clifford_offset"  affine with another constant (for example +pi/4: a hidden T gate);
    "non_affine"           not affine in (alpha, beta).
H1: the classification and the unchanged rho on small synthetic circuit families.
H2 (slow): on the real fuzzy archives every entry with rho = 1 is "clifford_offset", and the headline is the same entry whether
    Clifford offsets are counted as linear or not (so the open question of reports/tests/419 F2 changes no reported number).
H3 (slow): the fuzzy step composed from the HEADLINE units (`fuzzy.headline_step`) verifies as the M10 composed step does and is
    recorded in results/fuzzy/compressed_step_headline.json.

Tolerances: angle residuals 1e-9 (`robust.LINEAR_TOL`, the locked value of prompts/104 §11 E3); composed step 1e-10 with the M9
sampled composition check (METHODS-fuzzy F6, same call as the locked M10-G3); counts exact.
"""
from __future__ import annotations

import json

import numpy as np
import pytest
from qiskit import QuantumCircuit

from tests.acceptance._api import api

SEED = 20261104
TOL = 1e-10
PI = float(np.pi)


def _rb():
    return api("su2plaq.compress.robust")


def _family(RB, fill):
    pairs = [*RB.ANGLE_SET, (0.37, 0.61)]                # the 20 pairs of the locked set first, the nominal pair last
    circuits = []
    for a, b in pairs:
        qc = QuantumCircuit(2)
        fill(qc, a, b)
        circuits.append(qc)
    return circuits, pairs


def test_M11_H1_generic_rho_is_homogeneous_and_offsets_are_classified():
    RB = _rb()
    angle_offsets = api("su2plaq.compress.robust:angle_offsets")           # PENDING until prompts/010 step H.1
    assert RB.LINEAR_TOL == 1e-9 and len(RB.ANGLE_SET) == 20

    def linear(qc, a, b):
        qc.rz(a, 0); qc.cx(0, 1); qc.rz(-b / 2, 1); qc.p(3 * a - b, 0); qc.crz(2 * b, 0, 1)

    def clifford(qc, a, b):
        qc.rz(a - PI, 0); qc.cx(0, 1); qc.rz(b - 3 * PI / 2, 1); qc.p(a + PI / 2, 0); qc.s(1); qc.crz(2 * b + PI, 0, 1)

    def hidden_t(qc, a, b):
        qc.rz(a, 0); qc.cx(0, 1); qc.rz(b + PI / 4, 1)

    def controlled_half(qc, a, b):
        qc.rz(a, 0); qc.crz(b + PI / 2, 0, 1)             # crz(pi/2) is not a Clifford gate

    def constant(qc, a, b):
        qc.rz(a, 0); qc.rz(PI / 2, 1); qc.cx(0, 1); qc.rz(b, 1)

    def product(qc, a, b):
        qc.rz(a * b, 0); qc.cx(0, 1); qc.rz(b, 1)

    def tiny(qc, a, b):
        qc.rz(a + 1e-10, 0); qc.cx(0, 1); qc.rz(b, 1)     # below LINEAR_TOL

    cases = [(linear, True, "linear"), (clifford, False, "clifford_offset"), (hidden_t, False, "non_clifford_offset"),
             (controlled_half, False, "non_clifford_offset"), (constant, False, "clifford_offset"), (product, False, "non_affine"),
             (tiny, True, "linear")]
    for fill, is_linear, cls in cases:
        circuits, pairs = _family(RB, fill)
        ok, why = RB.generic_angle_linear(circuits, pairs)
        assert ok is is_linear, fill.__name__
        assert (why == "ok") if is_linear else why.startswith("non_linear_angle"), (fill.__name__, why)
        info = angle_offsets(circuits, pairs)
        assert info["class"] == cls, (fill.__name__, info["class"])
        assert len(info["offsets"]) == len(info["offset_units"]) == len(RB.rotation_angles(circuits[0]))
        if cls != "non_affine":
            assert info["affine_residual"] <= 1e-9, fill.__name__
    circuits, pairs = _family(RB, clifford)
    info = angle_offsets(circuits, pairs)
    assert info["offset_units"] == [-2, -3, 1, 2]          # constants in units of pi/2, in program order (rz, rz, p, crz)
    assert np.abs(np.array(info["offsets"]) - np.array([-PI, -1.5 * PI, 0.5 * PI, PI])).max() <= 1e-9
    circuits, pairs = _family(RB, linear)
    assert angle_offsets(circuits, pairs)["offset_units"] == [0, 0, 0, 0]
    circuits, pairs = _family(RB, hidden_t)
    info = angle_offsets(circuits, pairs)
    assert info["offset_units"] == [0, None] and abs(info["offsets"][1] - PI / 4) <= 1e-9
    assert angle_offsets([QuantumCircuit(1) for _ in range(21)], [*RB.ANGLE_SET, (0.37, 0.61)])["class"] == "linear"


def _cached_headline(RB, enc, kind, root):
    h = RB.headline(enc, kind, root=root, compute=False)
    if h is None or h.get("id") is None:
        pytest.fail(f"PENDING: no cached headline of the {enc} archive (results/compress/{enc}/robust.json with the offset classes; "
                    f"prompts/010 step H.2, after prompts/008 Phase C)", pytrace=False)
    return h


@pytest.mark.slow
@pytest.mark.parametrize("enc,kind", [("fuzzy_ub", "UB"), ("fuzzy_link", "UE")])
def test_M11_H2_fuzzy_headline_does_not_depend_on_the_offset_rule(enc, kind, root):
    RB = _rb()
    h = _cached_headline(RB, enc, kind, root)
    rows = [r for r in h["ranking"] if r["robust_key"] is not None]
    assert rows and all("offset_class" in r for r in rows)
    order = lambda r: (tuple(r["robust_key"]), tuple(r["laptop_key"]), r["id"])
    assert h["id"] == min(rows, key=order)["id"]
    for r in rows:
        assert r["angle_linear"] == (r["robust_key"][2] == 0) == (r["offset_class"] == "linear"), r["id"]
        assert r["offset_class"] in ("linear", "clifford_offset"), (r["id"], r["offset_class"])     # no hidden T, nothing non-affine

    def extended(r):                                       # the alternative rule: Clifford offsets counted as linear
        k = list(r["robust_key"])
        k[2] = 0 if r["offset_class"] in ("linear", "clifford_offset") else 1
        return (tuple(k), tuple(r["laptop_key"]), r["id"])

    assert min(rows, key=extended)["id"] == h["id"]
    # same CX and same summed T as the archive best: the two differ only in depth_CT and in the offsets
    best = next(r for r in rows if r["id"] == h["archive_best"])
    assert tuple(best["robust_key"][:2]) == tuple(h["robust_key"][:2])


@pytest.mark.slow
def test_M11_H3_fuzzy_step_composed_from_the_headline_units(root):
    RB = _rb()
    HS = api("su2plaq.fuzzy.headline_step")
    H = api("su2plaq.fuzzy.compress_hook")
    H.install()
    lm = api("su2plaq.metrics.logical:logical_metrics")
    vs = api("su2plaq.fuzzy.verify:verify_step_samples")
    hu = _cached_headline(RB, "fuzzy_ub", "UB", root)
    hl = _cached_headline(RB, "fuzzy_link", "UE", root)
    qc, info = HS.headline_step(root=root, order=1, with_outer=True)
    assert info["units"]["fuzzy_ub"]["entry"] == hu["id"] and info["units"]["fuzzy_link"]["entry"] == hl["id"]
    v = vs(qc, 0.37, 0.61, 0.5 * 0.37, 1, n_random=32, n_phys=8, seed=SEED)
    assert v["err"] <= TOL and v["gauss"] <= TOL and v["mode"] == "layers"
    m = lm(qc)
    g = H.step_metrics(H.general_link_fn, H.general_ub_fn, with_outer=True)
    row = lambda h: next(r for r in h["ranking"] if r["id"] == h["id"])
    assert m["cx"] == row(hu)["cx"] + 12 * row(hl)["cx"] <= g["cx"]            # U_B + 12 link blocks (4 inner + 8 outer)
    qi, _ = HS.headline_step(root=root, order=1, with_outer=False)
    assert lm(qi)["cx"] == row(hu)["cx"] + 4 * row(hl)["cx"]                   # the inner step of the cross-encoding table
    f = root / "results" / "fuzzy" / "compressed_step_headline.json"
    if not f.exists():
        pytest.fail("PENDING: results/fuzzy/compressed_step_headline.json missing (prompts/010 step H.3)", pytrace=False)
    d = json.loads(f.read_text())
    for k in ("rule", "order", "with_outer", "units", "composed", "inner", "general", "verification", "provenance"):
        assert k in d, k
    assert d["rule"] == "headline" and d["order"] == 1 and d["with_outer"] is True
    for enc, h in (("fuzzy_ub", hu), ("fuzzy_link", hl)):
        assert d["units"][enc]["entry"] == h["id"] and list(d["units"][enc]["robust_key"]) == list(h["robust_key"])
        assert abs(d["units"][enc]["t_mean"] - h["t_mean"]) <= 1e-9
    for k in ("cx", "t_fixed", "n_rot", "depth", "qubits"):
        assert d["composed"][k] == m[k] and d["general"][k] == g[k], k
    assert d["inner"]["cx"] == row(hu)["cx"] + 4 * row(hl)["cx"]
    assert abs(d["inner"]["t_mean"] - (hu["t_mean"] + 4 * hl["t_mean"])) <= 1e-9
    assert d["verification"]["err"] <= TOL and d["verification"]["gauss"] <= TOL and d["verification"]["seed"] == SEED
    assert len(d["provenance"]["git_commit"]) >= 7

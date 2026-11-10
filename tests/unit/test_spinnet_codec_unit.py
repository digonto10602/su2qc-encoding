"""Unit tests for the spin-network encoding (prompts/100 step 3.1): codec, decode_state (incl. the inadmissible-code
fallback), route-B targets with the gauge, helpers, and the step-3.0 stub surface of the other spin-network modules."""
import functools
import importlib

import numpy as np
import pytest
import scipy.sparse as sp
from qiskit import QuantumCircuit, QuantumRegister
from scipy.linalg import expm

from su2plaq.encodings.spinnet import (CORNER_LINKS, FUSE, SpinNet, align_inner_block, code_of_label, label_of_code)
from su2plaq.evaluate.evaluator import evaluate
from su2plaq.exact.compare import gauge_align
from su2plaq.exact.physical import gauss_residuals_coo
from su2plaq.exact.spinnet import labels as route_b_labels


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


@functools.lru_cache(maxsize=None)
def all_codes():
    e = enc()
    return np.array([int(c) | (o << 8) for c in e.inner_codes() for o in range(256)], dtype=np.int64)


@functools.lru_cache(maxsize=None)
def inadmissible():
    phys = set(int(c) for c in enc()._codes)
    return np.array([c for c in all_codes().tolist() if c not in phys], dtype=np.int64)


def test_stub_surface_importable():
    """Every module/name of prompts/100 §2 exists (steps 3.2+ fill the stubs)."""
    for mod, names in {
        "su2plaq.circuits.spinnet": ["build_UE", "build_UB", "build_step", "paulo_circuit", "trotter_v2_circuit", "N_DATA", "FRAME"],
        "su2plaq.spinnet.walk": ["coupling_table", "classical_slots", "solve_angles", "angle_fractions", "mirror", "build_walk"],
        "su2plaq.spinnet.paulo": ["parse_file", "load_circuit", "FILE_ALPHA_P"],
        "su2plaq.spinnet.lean_export": ["coupling_ints", "angle_ints", "lean_literals", "write_lean_tables",
                                        "export_certificate", "certify"],
    }.items():
        m = importlib.import_module(mod)
        for n in names:
            assert hasattr(m, n), (mod, n)


def test_fuse_table_and_corner_links():
    assert FUSE[(0.5, 0.5)] == frozenset({0.0, 1.0}) and FUSE[(0.0, 0.5)] == frozenset({0.5}) == FUSE[(0.5, 0.0)]
    assert FUSE[(0.0, 0.0)] == frozenset({0.0})
    # corner rule from the fusion table: J = 1 only with all four links 1/2 (inner and outer pair both 1/2 x 1/2)
    for (a, b), Js in FUSE.items():
        if 1.0 in Js:
            assert (a, b) == (0.5, 0.5)
    assert all(len(c) == 4 and set(c[:2]) <= {0, 1, 2, 3} and set(c[2:]) <= set(range(4, 12)) for c in CORNER_LINKS)
    assert tuple(tuple(i for i, _ in c.ends) for c in enc().basis.diagram.corners) == CORNER_LINKS


def test_codec_roundtrip_and_counts():
    labs = route_b_labels(jmax=0.5)
    codes = [code_of_label(lab) for lab in labs]
    assert len(set(codes)) == 433 and max(codes) < 2 ** 16
    assert all(label_of_code(c) == lab for c, lab in zip(codes, labs))
    e = enc()
    ic = e.inner_codes()
    assert len(ic) == 47 and (ic < 256).all() and np.array_equal(ic, np.sort(ic))
    assert sum(1 for c in ic if c >> 4 == 0) == 16
    # a corner bit without its four links is never a label
    assert label_of_code(1 << 4) is None and label_of_code(1 << 16) is None and label_of_code(0xFF) is None
    assert {int(c) & 0xFF for c in codes} == set(ic.tolist())
    vac = ((0.0,) * 12, (0.0,) * 4)
    assert code_of_label(vac) == 0
    with pytest.raises(ValueError):
        code_of_label(((0.0,) * 4, (0.0,) * 4))


def test_gauge_and_operators():
    e = enc()
    assert e.gauge.shape == (433,) and set(np.unique(e.gauge)) == {-1.0, 1.0} and int(np.sum(e.gauge < 0)) == 64
    assert e.gauge_residual <= 1e-10
    assert np.abs(e.h_magnetic() - e.h_magnetic().T).max() == 0.0
    # H_E counts 3/4 per spin-1/2 link; the outer variant adds the 8 outer links
    he, heo = e.h_electric(), e.h_electric(include_outer=True)
    nin = np.array([bin(int(c) & 0xF).count("1") for c in e._codes])
    nout = np.array([bin(int(c) >> 8).count("1") for c in e._codes])
    assert np.allclose(he, 0.75 * nin) and np.allclose(heo, 0.75 * (nin + nout))


def test_targets_unitary_and_consistent():
    e = enc()
    for a, b in ((0.37, 0.61), (0.91, 0.23)):
        UB = e.target("UB", None, b)
        assert np.abs(UB @ UB.conj().T - np.eye(433)).max() <= 1e-12
        assert np.abs(UB - expm(-1j * b * e.h_magnetic())).max() <= 1e-12
        assert np.abs(e.target("step", a, b, 1) - UB @ e.target("UE", a, None)).max() <= 1e-12
        assert np.abs(e.target("UE", a, None, include_outer_electric=True) - np.diag(np.exp(-1j * a * e.h_electric(True)))).max() <= 1e-15
    with pytest.raises(ValueError):
        e.target("bogus", 0.1, 0.1)
    with pytest.raises(ValueError):
        e.target("step", 0.1, 0.1, 3)


def test_inner_target_matches_blocks_and_steps():
    e = enc()
    codes = e.inner_codes().tolist()
    cidx = {c: i for i, c in enumerate(codes)}
    assert e.K_codes.shape == (47, 47) and np.abs(e.K_codes - e.K_codes.T).max() == 0
    for kind, order in (("UB", 1), ("UE", 1), ("step", 1), ("step", 2)):
        V = e.target(kind, 0.37, 0.61, order)
        W = e.inner_target(kind, 0.37, 0.61, order)
        assert W.shape == (47, 47)
        # restricted to the outer pattern 0 the 433 target equals the inner target on the codes with outer bits 0
        ks = [k for k, c in enumerate(e._codes) if int(c) >> 8 == 0]
        ii = [cidx[int(e._codes[k]) & 0xFF] for k in ks]
        assert np.abs(V[np.ix_(ks, ks)] - W[np.ix_(ii, ii)]).max() <= 1e-12
    W = e.inner_target("UB", None, 0.3)
    assert np.abs(W @ W.conj().T - np.eye(47)).max() <= 1e-12


def test_regauge():
    e = enc()
    V = e.target("UB", None, 0.4)
    ones = np.ones(47, dtype=complex)
    assert np.abs(e.regauge(V, ones) - V).max() == 0
    rng = np.random.default_rng(3)
    D = rng.choice([-1.0, 1.0], size=47).astype(complex)
    Vg = e.regauge(V, D)
    D433 = D[e._pos_of_k]
    assert np.abs(Vg - np.diag(D433) @ V @ np.diag(D433)).max() <= 1e-15
    assert np.abs(e.regauge(Vg, D) - V).max() <= 1e-15


def test_align_inner_block_recovers_gauge_and_phase():
    e = enc()
    V = e.inner_target("UB", None, 0.05)
    rng = np.random.default_rng(11)
    D = rng.choice([-1.0, 1.0], size=47)
    ph = np.exp(0.7j)
    M = ph * (D[:, None] * V * D[None, :])
    Dr, res, phase = align_inner_block(M, V)
    assert Dr is not None and res <= 1e-12 and abs(abs(phase) - 1) <= 1e-14
    assert np.abs(M / phase - Dr[:, None] * V * np.conj(Dr)[None, :]).max() <= 1e-12
    # different moduli (beta changed) -> (None, mismatch, phase)
    Dn, mism, _ = align_inner_block(e.inner_target("UB", None, 0.3), V)
    assert Dn is None and mism > 1e-3


def test_decode_state_physical_and_errors():
    e = enc()
    code = int(e._codes[5])
    keys, amps = e.decode_state(np.array([code]), np.array([1.0 + 0j]))
    assert abs(np.linalg.norm(amps) - 1) <= 1e-12
    assert e.decode(code) == 5 and e.decode(1 << 4) is None
    # data part outside the 47 inner codes -> ValueError
    bad = next(c for c in range(256) if c not in set(e.inner_codes().tolist()))
    with pytest.raises(ValueError):
        e.decode_state(np.array([bad]), np.array([1.0 + 0j]))
    with pytest.raises(ValueError):
        e.decode_state(np.array([1 << 16]), np.array([1.0 + 0j]))
    # coalescing: keys unique and sorted; duplicate codes add
    k2, a2 = e.decode_state(np.array([code, code]), np.array([0.5, 0.5j]))
    assert len(np.unique(k2)) == len(k2) and np.abs(a2 - (0.5 + 0.5j) * amps).max() <= 1e-15


def test_fallback_gauss_at_least_half_on_all_inadmissible_codes():
    """prompts/100 §1.4: all 11 599 inadmissible valid-data codes decode to unit product states with Gauss residual >= 1/2."""
    e = enc()
    bad = inadmissible()
    assert len(bad) == 47 * 256 - 433 == 11599
    ks, vs = [], []
    for c in bad.tolist():
        k, v = e.decode_state(np.array([c]), np.array([1.0 + 0j]))
        assert abs(np.linalg.norm(v) - 1) <= 1e-12 and len(k) == 1
        ks.append(k)
        vs.append(v)
    g = gauss_residuals_coo(e.basis, ks, vs)
    assert g.min() >= 0.5 - 1e-10, g.min()
    assert abs(g.min() - 0.5) <= 1e-10          # the bound is attained (one aligned end)


def test_decode_state_isometry_on_seeded_pairs():
    """<decode a | decode b> = delta_ab for 500 seeded pairs over the whole 12 032-code space (physical and fallback)."""
    e = enc()
    allc = all_codes()
    rng = np.random.default_rng(20261106)
    pairs = [(allc[i], allc[j]) for i, j in rng.integers(0, len(allc), size=(480, 2))]
    pairs += [(c, c) for c in allc[rng.integers(0, len(allc), size=20)]]
    assert len(pairs) == 500

    def vec(c):
        k, v = e.decode_state(np.array([c]), np.array([1.0 + 0j]))
        return dict(zip(k.tolist(), v.tolist()))
    for a, b in pairs:
        va, vb = vec(int(a)), vec(int(b))
        ov = sum(np.conj(x) * vb[k] for k, x in va.items() if k in vb)
        assert abs(ov - (1.0 if a == b else 0.0)) <= 1e-12, (int(a), int(b), ov)


def test_decode_state_isometry_gram_matrix_all_codes():
    """Full Gram matrix of the decoded vectors of all 12 032 valid-data codes is the identity (sparse)."""
    e = enc()
    allc = all_codes()
    rows, cols, vals = [], [], []
    for r, c in enumerate(allc.tolist()):
        k, v = e.decode_state(np.array([c]), np.array([1.0 + 0j]))
        rows.append(np.full(len(k), r))
        cols.append(k)
        vals.append(v)
    uk, inv = np.unique(np.concatenate(cols), return_inverse=True)
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), inv)), shape=(len(allc), len(uk)))
    G = (A @ A.conj().T).tocoo()
    off = G.data[G.row != G.col]
    assert (len(off) == 0) or np.abs(off).max() <= 1e-12
    assert np.abs(G.tocsr().diagonal() - 1).max() <= 1e-12


def test_layout_and_describe_and_import_map():
    e = enc()
    d, o, a = QuantumRegister(8, "d"), QuantumRegister(8, "o"), QuantumRegister(3, "a")
    lay = e.layout_of(QuantumCircuit(a, o, d))
    assert lay.data == list(range(11, 19)) and lay.outer == list(range(3, 11))
    assert lay.ancilla == [0, 1, 2]
    lay = e.layout_of(QuantumCircuit(d, a))
    assert lay.outer == [] and lay.ancilla == [8, 9, 10]
    with pytest.raises(ValueError):
        e.layout_of(QuantumCircuit(QuantumRegister(7, "d")))
    desc = e.describe()
    assert "47" in desc and "433" in desc and "corner" in desc.lower() and "gauge" in desc.lower()
    p = e.import_map("paulo15")
    assert len(p["qubit_map"]) == 15 and p["fixed_angle"] and p["kind"] == "UB" and p["angles"](0.3, 0.9)["beta"] == 0.05
    assert sorted(p["qubit_map"].values()) == list(range(4)) + list(range(4, 8)) + list(range(16, 23))
    assert sorted(p["qubit_map_open"].values()) == list(range(15))
    v2 = e.import_map("spinnet_v2")
    assert v2["kind"] == "UB" and not v2["fixed_angle"] and v2["angles"](0.3, 0.9) == {"kind": "UB", "beta": 0.9}
    assert all(isinstance(e.import_map(s), str) for s in ("paulo34", "lean22", "lean22_v2"))
    with pytest.raises(ValueError):
        e.import_map("nope")


def test_evaluator_accepts_identity_and_electric_circuits():
    e = enc()
    qc = QuantumCircuit(QuantumRegister(8, "d"))
    v = evaluate(qc, e, e.target("UE", 0.0, None))
    assert v.ok and v.op_norm_error <= 1e-12
    for q in range(4):
        qc.p(-0.75 * 0.37, q)
    v = evaluate(qc, e, e.target("UE", 0.37, None))
    assert v.ok and v.op_norm_error <= 1e-12 and v.gauss_residual <= 1e-10
    # a wrong target is rejected
    assert not evaluate(qc, e, e.target("UE", 0.9, None)).ok
    # an X on a corner qubit leaves the code space of physical states: rejected
    bad = QuantumCircuit(QuantumRegister(8, "d"))
    bad.x(4)
    assert not evaluate(bad, e, np.eye(433)).ok

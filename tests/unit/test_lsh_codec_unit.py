"""Unit tests for su2plaq.encodings.lsh (prompts/400 step 7.1: `label_of_code`) and the interface surface of the LSH
modules (step 7.0: every name of prompts/400 section 2 exists, whatever its build status)."""
import importlib

import pytest

from su2plaq.encodings.lsh import LSH, code_of_label, label_of_code
from su2plaq.exact.spinnet import labels
from su2plaq.lsh import operators as O

SURFACE = {
    "su2plaq.lsh.operators": ["VALID_SITE", "SITE_J1", "CORNER_PN", "CORNER_OUT", "LINK_NAMES", "VERTEX_TYPES", "VERTEX",
                              "site_flux", "site_valid", "site_code", "ladder_amplitude", "loop_ladder", "inner_code_of",
                              "code_of_label", "agl_violations", "is_physical_code", "inner_codes", "physical_codes",
                              "plaquette_inner", "K_lsh", "h_magnetic_lsh", "h_electric_lsh"],
    "su2plaq.lsh.walk": ["LINK", "CBIT", "WBIT", "TARGET", "J_HALF_PHASE", "TRANSCODE", "FRAME", "transcode_steps", "mirror",
                         "skeleton", "classical_run", "classical_slots", "coupling_table", "partner_table", "solve_angles",
                         "angle_fractions", "build"],
    "su2plaq.lsh.lean_export": ["coupling_ints", "partner_ints", "angle_ints", "lean_literals", "write_lean_tables",
                                "export_certificate", "certify", "write_pins"],
    "su2plaq.circuits.lsh": ["build_UE", "build_UB", "build_step", "wrap_spinnet"],
    "su2plaq.encodings.lsh": ["N_DATA", "N_OUTER", "code_of_label", "label_of_code", "LSH"],
}


@pytest.mark.parametrize("mod", sorted(SURFACE))
def test_interface_surface(mod):
    m = importlib.import_module(mod)
    missing = [n for n in SURFACE[mod] if not hasattr(m, n)]
    assert missing == []


def test_class_attributes():
    assert (LSH.name, LSH.n_data, LSH.n_outer, LSH.is_basis_encoding) == ("lsh", 12, 12, True)
    for meth in ("inner_codes", "physical_vectors", "decode", "decode_state", "target", "inner_target", "h_magnetic",
                 "h_electric", "layout_of", "describe", "import_map"):
        assert callable(getattr(LSH, meth))


def test_label_of_code_inverse_and_none():
    labs = labels(jmax=0.5)
    for lab in labs:
        code = code_of_label(lab)
        assert code == O.code_of_label(lab) and label_of_code(code) == lab
        assert label_of_code(int(code)) == lab
    physical = set(O.physical_codes().tolist())
    assert {code_of_label(lab) for lab in labs} == physical
    for code in (0b010, 1 << 1, 1 << 23, (1 << 24) - 1, 0b001):
        assert code not in physical and label_of_code(code) is None


# ---- step 7.3: codec and decoding ----------------------------------------------------------------------------------
import functools  # noqa: E402
import itertools  # noqa: E402

import numpy as np  # noqa: E402
from qiskit import QuantumCircuit, QuantumRegister  # noqa: E402
from scipy.linalg import expm  # noqa: E402

from su2plaq.exact.operators import target as target_A  # noqa: E402
from su2plaq.exact.physical import gauss_residual, gauss_residuals_coo  # noqa: E402
from su2plaq.lsh import walk as W  # noqa: E402


@functools.lru_cache(maxsize=1)
def enc():
    return LSH()


def test_label_order_equals_basis_and_route_b():
    e = enc()
    assert list(e.basis.labels) == list(labels(jmax=0.5)) == list(e.labels)
    assert [e.decode(code_of_label(lab)) for lab in e.labels] == list(range(433))


def test_registers_and_physical_vectors():
    e = enc()
    assert e.registers["d"] == list(range(12)) and e.registers["o"] == list(range(12, 24))
    for c in range(4):
        assert e.registers[f"site_in_{c}"] == [3 * c, 3 * c + 1, 3 * c + 2]
        assert e.registers[f"site_out_{c}"] == [12 + 3 * c, 13 + 3 * c, 14 + 3 * c]
    assert e.registers["l_pn"] == [0, 3, 6, 9] and e.registers["l_nv"] == [1, 4, 7, 10] and e.registers["l_vp"] == [2, 5, 8, 11]
    eb = e.physical_vectors()
    assert (eb.n_data, eb.n_outer, len(eb.codes)) == (12, 12, 433)
    assert [int(c[0]) for c in eb.codes] == [code_of_label(lab) for lab in e.labels]
    assert all(len(a) == 1 and a[0] == 1.0 for a in eb.amps)
    assert np.array_equal(e.inner_codes(), O.inner_codes())
    e.inner_codes()[0] = -5                                         # copy: no aliasing
    assert e.inner_codes()[0] >= 0
    assert e.decode(0b010) is None


def test_gauge_is_real_pm1():
    e = enc()
    assert e.gauge.shape == (433,) and set(np.unique(e.gauge).tolist()) <= {-1.0, 1.0}
    assert e.gauge_residual <= 1e-10 and int(np.sum(e.gauge < 0)) > 0


def test_decode_state_physical_and_linear():
    e = enc()
    codes = O.physical_codes()
    for k in (0, 17, 200, 432):
        code = code_of_label(e.labels[k])
        keys, amps = e.decode_state(np.array([code]), np.array([1.0 + 0j]))
        assert abs(np.linalg.norm(amps) - 1) < 1e-12 and gauss_residual(e.basis, keys, amps) < 1e-10
    c0, c1 = int(codes[0]), int(codes[1])
    k0, a0 = e.decode_state(np.array([c0]), np.array([1.0 + 0j]))
    k1, a1 = e.decode_state(np.array([c1]), np.array([1.0 + 0j]))
    ks, a = e.decode_state(np.array([c0, c1]), np.array([0.6, 0.8j]))
    full = dict(zip(ks.tolist(), a.tolist()))
    for key, v in zip(k0.tolist(), a0.tolist()):
        full[key] = full.get(key, 0) - 0.6 * v
    for key, v in zip(k1.tolist(), a1.tolist()):
        full[key] = full.get(key, 0) - 0.8j * v
    assert max(abs(v) for v in full.values()) < 1e-12
    ke, ae = e.decode_state(np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.complex128))
    assert len(ke) == 0 and len(ae) == 0


def test_decode_state_fallback_all_agl_violating_codes():
    """All 47 * 625 - 433 = 28942 data-valid, site-valid codes that are not physical: unit norm, Gauss residual >= 1/2,
    pairwise distinct electric keys, none in the support of a physical state."""
    e = enc()
    phys = set(O.physical_codes().tolist())
    outer = [sum(s << (3 * i) for i, s in enumerate(ss)) for ss in itertools.product(O.VALID_SITE, repeat=4)]
    bad = [int(c) | (o << 12) for c in O.inner_codes() for o in outer if (int(c) | (o << 12)) not in phys]
    assert len(bad) == 28942
    dec = [e.decode_state(np.array([c]), np.array([1.0 + 0j])) for c in bad]
    keys = [int(k[0]) for k, _ in dec]
    assert all(len(k) == 1 for k, _ in dec) and len(set(keys)) == len(bad)
    phys_keys = set(int(k) for ks in e.basis.keys for k in ks)
    assert not (set(keys) & phys_keys)
    res = gauss_residuals_coo(e.basis, [k for k, _ in dec], [a for _, a in dec])
    assert res.min() >= 0.5 - 1e-10
    assert all(abs(np.linalg.norm(a) - 1) < 1e-12 for _, a in dec)


def test_decode_state_errors():
    e = enc()
    with pytest.raises(ValueError):
        e.decode_state(np.array([0b011]), np.array([1.0 + 0j]))            # 'in' site 0 = 011: not a data code
    with pytest.raises(ValueError):
        e.decode_state(np.array([0b011 << 12]), np.array([1.0 + 0j]))      # 'out' site 0 breaks the flux cap
    with pytest.raises(ValueError):
        e.decode_state(np.array([1 << 24]), np.array([1.0 + 0j]))


def test_layout_of():
    e = enc()
    qc = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(12, "o"), QuantumRegister(3, "a"))
    lay = e.layout_of(qc)
    assert lay.data == list(range(12)) and lay.outer == list(range(12, 24)) and lay.ancilla == [24, 25, 26]
    lay = e.layout_of(QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(2, "a")))
    assert lay.outer == [] and lay.ancilla == [12, 13]
    assert e.layout_of(QuantumCircuit(14)).ancilla == [12, 13]
    with pytest.raises(ValueError):
        e.layout_of(QuantumCircuit(QuantumRegister(8, "d")))
    with pytest.raises(ValueError):
        e.layout_of(QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(8, "o")))
    with pytest.raises(ValueError):
        e.layout_of(QuantumCircuit(5))


def test_describe_and_import_map():
    e = enc()
    d = e.describe()
    assert isinstance(d, str) and "47" in d and "433" in d and "Abelian" in d
    im = e.import_map("spinnet")
    assert im["wrap"] == "su2plaq.circuits.lsh:wrap_spinnet" and im["kind"] == "UB" and im["fixed_angle"] is False
    assert (im["extra_cx"], im["extra_t"]) == (40, 32) and {"general7", "pairs9", "flags4"} <= set(im["skeletons"])
    assert e.import_map("paulo15")["fixed_angle"] is True
    for src in ("paulo34", "lean22", "lean22_v2"):
        assert isinstance(e.import_map(src), str)
    with pytest.raises(ValueError):
        e.import_map("nope")


# ---- step 7.4: targets ---------------------------------------------------------------------------------------------
def test_targets():
    e = enc()
    HB, HE = e.h_magnetic(), e.h_electric()
    a, b = 0.37, 0.61
    UB = expm(-1j * b * HB)
    UE = np.diag(np.exp(-1j * a * HE))
    assert np.abs(e.target("UB", None, b) - UB).max() < 1e-12
    assert np.abs(e.target("UE", a, None) - UE).max() < 1e-12
    assert np.abs(e.target("step", a, b, 1) - UB @ UE).max() < 1e-12
    UEh = np.diag(np.exp(-0.5j * a * HE))
    assert np.abs(e.target("step", a, b, 2) - UEh @ UB @ UEh).max() < 1e-12
    Do = e.target("UE", a, None, include_outer_electric=True)
    assert np.abs(Do - np.diag(np.exp(-1j * a * e.h_electric(include_outer=True)))).max() < 1e-12
    assert np.abs(Do - e.target("UE", a, None)).max() > 1e-3
    D = np.diag(e.gauge)
    assert np.abs(UB - D.T @ target_A(e.basis, "UB", beta=b) @ D).max() < 1e-10
    with pytest.raises(ValueError):
        e.target("nope", a, b)
    with pytest.raises(ValueError):
        e.target("step", a, b, 3)


def test_inner_target_and_tables():
    e = enc()
    codes = e.inner_codes()
    K = e.K_codes
    assert np.array_equal(K, O.K_lsh()) and K.shape == (47, 47)
    KI = e.inner_target("UB", None, 0.61)
    assert np.abs(KI - expm(-0.61j * K)).max() < 1e-12
    hE = O.h_electric_lsh(codes)
    assert np.abs(e.inner_target("step", 0.37, 0.61, 2)
                  - np.diag(np.exp(-0.185j * hE)) @ KI @ np.diag(np.exp(-0.185j * hE))).max() < 1e-12
    table, partner = W.coupling_table(e), W.partner_table(e)
    assert sorted(table) == codes.tolist() and sorted(partner) == [c for c in codes.tolist() if table[c] != 0.0]
    assert sorted(set(table.values())) == [-2.0, -0.5, 0.0, 1.0]
    for c, p in partner.items():
        assert partner[p] == c and table[p] == table[c] and K[codes.tolist().index(p), codes.tolist().index(c)] == table[c]
    assert len(partner) == 16
    # a non-matching K is rejected
    class Fake:
        K_codes = np.ones((2, 2))
        def inner_codes(self):
            return np.array([0, 1])
    with pytest.raises(ValueError):
        W.coupling_table(Fake())
    with pytest.raises(ValueError):
        W.partner_table(Fake())

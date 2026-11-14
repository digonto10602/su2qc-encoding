"""Unit tests for the det layer operators / targets and the rishon prune cap (prompts/204 steps D1, D2): small, cheap checks."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.encodings.rishon import RISHON_ALT_ETA, RISHON_NOMINAL_ETA, RishonEncoding
from su2plaq.evaluate.evaluator import PRUNE_FRACTION, Verdict
from su2plaq.rishon import operators as O
from su2plaq.rishon import verify as V


def _verdict(reason="pruning_bound", dropped=5e-12, leak=0.0, err=1e-13, dirty=0.0, max_leak=0.0):
    return Verdict(ok=reason == "ok", reason=reason, op_norm_error=err + dropped + leak, max_leak=max_leak, dirty_ancilla=dirty,
                   phase=1 + 0j, outer_bits_read=0, n_blocks=1, gauss_residual=float("nan"), method="inner_block", engine="sparse",
                   seconds=0.0, failing_inputs=[], n_inputs=1296, dropped_total=dropped, block_error=err, leak_amplitude=leak)


# ------------------------------------------------------------------------------------------------ D1: prune cap
def test_constants_and_cap_ordering():
    assert V.RISHON_PRUNE_FRACTION == 0.1 and PRUNE_FRACTION == 1e-2 and V.RISHON_PRUNE_FRACTION >= PRUNE_FRACTION


@pytest.mark.parametrize("kw,reason", [
    (dict(dropped=5e-12), "ok"),                                           # between the two caps, exact otherwise
    (dict(dropped=2e-11), "pruning_bound"),                                # above the rishon cap 1e-11
    (dict(dropped=5e-12, leak=2e-10, dirty=1.0, max_leak=1.0), "dirty_ancilla"),
    (dict(dropped=5e-12, leak=2e-10, dirty=0.1, max_leak=1.0), "leak"),
    (dict(dropped=5e-12, err=2e-10), "error"),
    (dict(dropped=5e-12, err=9.8e-11), "error"),                           # block + pruning together exceed the budget
])
def test_rejudge_cascade(kw, reason):
    got, failing = V._rejudge(_verdict(**kw), V.RISHON_PRUNE_FRACTION * 1e-10, 1e-10)
    assert got == reason
    assert (failing == []) == (reason == "ok")
    if reason == "pruning_bound":
        assert dict(failing) == {"dropped_total": 2e-11, "prune_cap": pytest.approx(1e-11, rel=1e-12)}


@pytest.mark.parametrize("field,reason", [("dropped_total", "pruning_bound"), ("leak_amplitude", "leak"), ("op_norm_error", "error")])
@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_rejudge_rejects_non_finite(field, reason, bad):
    v = _verdict(dropped=5e-12)
    setattr(v, field, bad)
    got, failing = V._rejudge(v, V.RISHON_PRUNE_FRACTION * 1e-10, 1e-10)
    assert got in ({"leak", "dirty_ancilla"} if reason == "leak" else {reason}) and failing != []     # leak vs dirty_ancilla is a label


def test_rejudge_cap_scales_with_fraction():
    v = _verdict(dropped=5e-12)
    assert V._rejudge(v, 1e-2 * 1e-10, 1e-10)[0] == "pruning_bound"        # the shared cap reproduces the shared verdict
    assert V._rejudge(v, 1e-1 * 1e-10, 1e-10)[0] == "ok"


def test_verify_refuses_fraction_below_shared_and_det_paths_pending():
    enc = RishonEncoding()
    qc = QuantumCircuit(QuantumRegister(16, "d"))
    with pytest.raises(ValueError):
        V.verify(qc, enc, "UE", 0.0, None, prune_fraction=1e-3, gauss=False)
    v = V.verify(qc, enc, "UE", 0.0, None, prune_fraction=0.5, gauss=False)
    assert v.ok and v.extra["prune_fraction"] == 0.5 and v.extra["prune_cap"] == pytest.approx(5e-11) and v.extra["laptop_reason"] == "ok"
    d = V.verify(qc, enc, "UE", 0.0, None, gauss=False)
    assert d.extra["prune_fraction"] == V.RISHON_PRUNE_FRACTION and d.inner_verdict.ok
    v = V.verify(qc, enc, "UD", None, None, eta=0.0, gauss=False)           # det layer of angle 0 is the identity
    assert v.ok and v.reason == "ok"


# ------------------------------------------------------------------------------------------------ D2: operators
def test_h_det_inner_and_hamiltonian():
    D = O.h_det_inner()
    assert D.shape == (1296, 1296) and D.dtype == np.float64 and np.array_equal(D, D.T)
    assert np.array_equal(D, O.det_term_inner().real) and set(np.unique(D).tolist()) == {0.0, 2.0}
    HE, HB = O.h_electric_inner(), O.h_magnetic_inner()
    H = O.hamiltonian_inner(1.3, 0.4)
    assert H.dtype == np.complex128 and np.abs(H - (0.65 * np.diag(HE) + HB / 1.3 + 0.4 * D)).max() <= 1e-13
    assert np.abs(O.hamiltonian_inner(1.3) - (0.65 * np.diag(HE) + HB / 1.3)).max() <= 1e-13


def test_ud_is_exp_of_h_det_and_unitary_group():
    D = O.h_det_inner()
    w, v = np.linalg.eigh(D)
    for eta in (0.29, 0.53):
        U = O.inner_target("UD", None, None, eta=eta)
        assert U.dtype == np.complex128 and np.abs(U - (v * np.exp(-1j * eta * w)) @ v.T).max() <= 1e-12
        assert np.abs(U.conj().T @ U - np.eye(1296)).max() <= 1e-12
    assert np.abs(O.inner_target("UD", None, None, eta=0.0) - np.eye(1296)).max() == 0.0
    a, b = O.inner_target("UD", None, None, eta=0.1), O.inner_target("UD", None, None, eta=0.19)
    assert np.abs(a @ b - O.inner_target("UD", None, None, eta=0.29)).max() <= 1e-12


def test_step_with_and_without_eta():
    a, b, e = 0.37, 0.61, 0.29
    UE, UB, UD = O.inner_target("UE", a, None), O.inner_target("UB", None, b), O.inner_target("UD", None, None, eta=e)
    two = O.inner_target("step", a, b)
    assert np.array_equal(two, O.inner_target("step", a, b, 1, eta=None)) and np.abs(two - UB @ UE).max() <= 1e-13
    assert np.abs(O.inner_target("step", a, b, 1, eta=e) - UB @ UD @ UE).max() <= 1e-12
    h = lambda x: O.inner_target("UD", None, None, eta=x)
    S2 = O.inner_target("step", a, b, 2, eta=e)
    assert np.abs(S2 - O.inner_target("UE", a / 2, None) @ h(e / 2) @ UB @ h(e / 2) @ O.inner_target("UE", a / 2, None)).max() <= 1e-12
    assert np.abs(O.inner_target("step", a, b, 2, eta=0.0) - O.inner_target("step", a, b, 2)).max() <= 1e-12
    assert np.linalg.norm(O.inner_target("step", a, b, 1, eta=e) - two, 2) > 1e-2


def test_target_errors():
    with pytest.raises(ValueError):
        O.inner_target("UD", None, None)
    with pytest.raises(ValueError):
        O.inner_target("UE", 0.3, None, eta=0.1)
    with pytest.raises(ValueError):
        O.inner_target("UB", None, 0.3, eta=0.1)
    with pytest.raises(ValueError):
        O.inner_target("step", 0.3, 0.3, 3, eta=0.1)


def test_closed_block_full_with_lam_d():
    B0 = O.closed_block_full(1.1)
    assert np.array_equal(B0, O.closed_block_full(1.1, 0.0)) and B0.shape == (17, 17)
    B = O.closed_block_full(1.1, 0.2)
    assert np.abs(B - B.conj().T).max() <= 1e-13
    X = np.zeros((17, 17))
    for k in range(16):
        for l in range(4):
            X[k, k ^ (1 << l)] = 1.0           # "link l is type B" bit, as in the acceptance model
    assert np.abs(B - B0 - 0.4 * X).max() <= 1e-12            # det acts as 2 lam_d X_l on the 16 vacua, loop untouched


def test_encoding_pass_through_and_constants():
    enc = RishonEncoding()
    assert (RISHON_NOMINAL_ETA, RISHON_ALT_ETA) == (0.29, (0.53, 1.07))
    assert np.array_equal(enc.inner_target("step", 0.37, 0.61), O.inner_target("step", 0.37, 0.61))
    assert np.array_equal(enc.inner_target("step", 0.37, 0.61, 1, eta=0.29), O.inner_target("step", 0.37, 0.61, 1, eta=0.29))
    ids = [0, 1, 5]
    T = enc.target("step", 0.37, 0.61, 1, states=ids)
    assert np.array_equal(T, enc.target("step", 0.37, 0.61, 1, states=ids, eta=None))
    T3 = enc.target("step", 0.37, 0.61, 1, states=ids, eta=0.29)
    assert T3.shape == (3, 3) and np.linalg.norm(T3, 2) <= 1.0 + 1e-9
    U = enc.target("UD", None, None, states=list(range(5)), eta=0.29)
    assert U.shape == (5, 5) and np.linalg.norm(U, 2) <= 1.0 + 1e-9


# ------------------------------------------------------------------------------------------------ D3: circuits
def test_build_UD_counts_registers_and_errors():
    from su2plaq.circuits.rishon import build_UD
    from su2plaq.metrics.logical import logical_metrics

    qc = build_UD(0.29)
    m = logical_metrics(qc)
    assert qc.num_qubits == 16 and [r.name for r in qc.qregs] == ["d"] and m["cx"] == 32 and m["n_rot"] == 8 and m["t_fixed"] == 0
    assert qc.metadata == {"kind": "UD", "eta": 0.29}
    assert [i.operation.name for i in qc.data] == [i.operation.name for i in build_UD(0.83).data]
    qo = build_UD(0.29, with_outer=True, include_outer_det=True)
    assert qo.num_qubits == 48 and logical_metrics(qo)["cx"] == 96 and logical_metrics(qo)["n_rot"] == 24
    with pytest.raises(ValueError):
        build_UD(0.29, include_outer_det=True)


def test_det_layer_exact_on_inner_codes_and_wrong_sign_rejected():
    enc = RishonEncoding()
    from su2plaq.circuits.rishon import build_UD

    v = V.verify(build_UD(0.29), enc, "UD", None, None, eta=0.29, gauss=False)
    assert v.ok and v.certified and v.op_norm_error <= 1e-12 and v.outer_bits_read == 0
    assert not V.verify(build_UD(-0.29), enc, "UD", None, None, eta=0.29, gauss=False).ok


@pytest.mark.parametrize("order", [1, 2])
def test_build_step_eta_structure(order):
    from su2plaq.circuits.rishon import build_step, build_UD
    from su2plaq.metrics.logical import logical_metrics

    two, three = build_step(0.37, 0.61, order), build_step(0.37, 0.61, order, eta=0.29)
    assert [(i.operation.name, tuple(two.find_bit(q).index for q in i.qubits)) for i in two.data] == \
           [(i.operation.name, tuple(two.find_bit(q).index for q in i.qubits)) for i in build_step(0.37, 0.61, order, eta=None).data]
    m2, m3, md = logical_metrics(two), logical_metrics(three), logical_metrics(build_UD(0.29))
    assert m3["cx"] == m2["cx"] + order * md["cx"] and m3["n_rot"] == m2["n_rot"] + order * md["n_rot"] and m3["qubits"] == m2["qubits"]
    assert three.metadata["eta"] == 0.29 and "eta" not in two.metadata


def test_prepend_det_layer():
    from qiskit import QuantumCircuit, QuantumRegister

    from su2plaq.circuits.rishon import build_step, build_UD, prepend_det_layer

    unit = build_step(0.37, 0.61, 1, with_outer=True)
    full = prepend_det_layer(unit, 0.29)
    ud = build_UD(0.29)
    assert full.num_qubits == unit.num_qubits and [r.name for r in full.qregs] == [r.name for r in unit.qregs]
    assert len(full.data) == len(unit.data) + len(ud.data) and [i.operation.name for i in full.data][-len(unit.data):] == [i.operation.name for i in unit.data]
    assert [i.operation.name for i in full.data][:len(ud.data)] == [i.operation.name for i in ud.data]
    assert len(unit.data) == len(build_step(0.37, 0.61, 1, with_outer=True).data)      # the input is not modified
    with pytest.raises(ValueError):
        prepend_det_layer(QuantumCircuit(QuantumRegister(8, "x")), 0.1)


def test_prepend_det_layer_rejects_non_first_order_units():
    """N4 (audit 304): [U_B U_E] U_D = U_B U_D U_E needs a first-order step; metadata that says otherwise is an error."""
    from su2plaq.circuits.rishon import build_step, build_UD, build_UE, prepend_det_layer

    for order in (2,):
        with pytest.raises(ValueError, match="order"):
            prepend_det_layer(build_step(0.37, 0.61, order, with_outer=True), 0.29)
    with pytest.raises(ValueError, match="kind"):
        prepend_det_layer(build_UE(0.37, with_outer=True), 0.29)
    with pytest.raises(ValueError, match="kind"):
        prepend_det_layer(build_UD(0.29, with_outer=True), 0.29)
    unit = build_step(0.37, 0.61, 1, with_outer=True)
    unit.metadata = {}                                   # program-built units carry no kind / order: accepted
    assert prepend_det_layer(unit, 0.29).num_qubits == unit.num_qubits


def test_outer_det_certify_basic():
    from su2plaq.circuits.rishon import build_UD
    from su2plaq.rishon.results import outer_det_certify

    enc = RishonEncoding()
    r = outer_det_certify(build_UD(0.29, with_outer=True, include_outer_det=True), enc, 0.29)
    assert r["certified"] and r["method"] == "outer_det_gadgets" and r["n_links"] == 12 and r["error_bound"] <= 1e-10
    assert abs(abs(r["phase"]) - 1.0) <= 1e-12 and r["gates_per_link"] == [14] * 12
    assert not outer_det_certify(build_UD(-0.29, with_outer=True, include_outer_det=True), enc, 0.29)["certified"]
    assert outer_det_certify(build_UD(0.29), enc, 0.29)["reason"] == "ancilla_register"
    assert outer_det_certify(build_UD(0.29, with_outer=True), enc, 0.29)["certified"] is False     # outer links lack their rotation


# ------------------------------------------------------------------------------------------------ D4: observables
def test_observables_eta_and_closed_spectra():
    from su2plaq.rishon import observables as Ob

    base = Ob.observables(0.37, 0.61)
    assert Ob.observables(0.37, 0.61, eta=None)["rishon"] == base["rishon"]
    z = Ob.observables(0.37, 0.61, eta=0.0)
    assert all(abs(z["rishon"][n][k] - base["rishon"][n][k]) <= 1e-12 for n in (1, 2) for k in ("E_link", "P", "echo"))
    d = Ob.observables(0.37, 0.61, eta=0.29)
    assert d["ks"] == base["ks"] and abs(d["rishon"][1]["P"]) <= 1e-12 and abs(d["rishon"][1]["echo"] - base["rishon"][1]["echo"]) > 1e-4
    s0 = Ob.closed_spectra((1.0,))["rishon"][1.0]
    assert s0 == Ob.closed_spectra((1.0,), lam_d=0.0)["rishon"][1.0] and s0["multiplicities"] == [1, 15, 1]
    s = Ob.closed_spectra((1.0,), lam_d=0.2)["rishon"][1.0]
    assert sum(s["multiplicities"]) == 17 and 15 not in s["multiplicities"]


def test_det_sector_structure_leaving_weight_is_a_residual():
    from su2plaq.rishon.physical import det_sector_structure

    d = det_sector_structure()
    assert d["dim"] == 38432 and d["blocks"] == {"lam0": 31870, "inner_det": 4976, "full_det": 305}
    assert d["leaving_weight"] <= 1e-20, d["leaving_weight"]          # residual form (~1e-25); the old difference showed 2^-32 ~ 2.3e-10
    assert d["leaving_weight"] != 2.0 ** -32


def test_det_sector_structure_counts_images_outside_the_code_union(monkeypatch):
    """N2 (audit 304): an operator that maps a physical code to a code that no physical state has must show up in leaving_weight
    (it used to be dropped silently).  Mutants: (a) the det nibble pair (5 <-> 10) instead of (3 <-> 12): the image of every
    quartet-code nibble is not a physical pattern; (b) H_B plus an extra column from one occupied inner code to all 1296 inner codes."""
    import scipy.sparse as sp

    from su2plaq.rishon import operators as O, physical as ph

    b0 = ph.rishon_basis()
    base = ph.det_sector_structure(b0)
    assert base["leaving_weight"] <= 1e-20
    kc = ph.closed_indices(b0)
    monkeypatch.setattr(ph, "closed_indices", lambda b: kc)            # (closed_indices itself reads CODE_A)
    monkeypatch.setattr(ph, "CODE_A", 5)                              # det_link: nibble 5 -> 10 (not a physical link pattern)
    a = ph.det_sector_structure(b0)                                   # basis built before the mutation
    assert a["leaving_weight"] > 1.0, a["leaving_weight"]
    monkeypatch.undo()
    codes = O.inner_codes()
    i0 = int(np.searchsorted(codes, int(b0.keys[0][0]) & 0xFFFF))
    M = sp.lil_matrix(O.h_magnetic_inner().shape, dtype=complex)
    M[:, i0] = 0.5
    M = M.tocsr()
    real = O.h_magnetic_inner
    monkeypatch.setattr(O, "h_magnetic_inner", lambda: real() + M.toarray())
    d = ph.det_sector_structure(b0)
    assert d["leaving_weight"] > 1e-3, d["leaving_weight"]

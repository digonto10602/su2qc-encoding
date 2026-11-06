"""Unit tests of su2plaq.fuzzy.verify (adapter, verdicts, layered step check, Gauss residual of outputs)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, RZGate, XGate

from su2plaq.circuits import fuzzy as cf
from su2plaq.fuzzy import targets as tg
from su2plaq.fuzzy import verify as vf


def test_adapter_layout_and_codes():
    enc = vf.FuzzyBlockEncoding(8, data_qubits=vf.ROW_QUBITS)
    qc = cf.build_UB(0.3)
    lay = enc.layout_of(qc)
    assert lay.data == list(vf.ROW_QUBITS) and lay.outer == [] and set(lay.ancilla) == set(range(qc.num_qubits)) - set(vf.ROW_QUBITS)
    ev = enc.physical_vectors()
    assert len(ev.codes) == 256 and enc.n_outer == 0 and list(enc.inner_codes()) == list(range(256))
    with pytest.raises(ValueError):
        enc.target("UB", 0.1, 0.1)


@pytest.mark.parametrize("alpha", [0.37, 1.1])
def test_verify_link_accepts_exact_and_rejects_wrong(alpha):
    v = vf.verify_link(cf.link_UE(alpha), tg.UE_link(alpha))
    assert v.ok and v.op_norm_error <= 1e-10 and v.max_leak <= 1e-20 and v.dirty_ancilla <= 1e-20
    bad = vf.verify_link(cf.link_UE(alpha), tg.UE_link(alpha * 1.01))
    assert not bad.ok and bad.op_norm_error > 1e-4


def test_verify_link_detects_dirty_ancilla():
    qc = QuantumCircuit(5)
    qc.compose(cf.link_UK(0.2), qubits=range(4), inplace=True)
    qc.cx(0, 4)                                  # leaves the ancilla entangled
    v = vf.verify_link(qc, tg.UK_link(0.2))
    assert not v.ok and v.reason in ("dirty_ancilla", "leak")


def test_verify_plaquette_flags_column_access_and_sign():
    beta = 0.23
    qc = cf.build_UB(beta)
    v = vf.verify_plaquette(qc, tg.UB_row(beta))
    assert v.ok and v.extra["touches_column"] is False and v.max_leak <= 1e-20
    assert not vf.verify_plaquette(qc, tg.UB_row(beta).conj().T).ok
    qc2 = QuantumCircuit(*qc.qregs)
    qc2.compose(qc, inplace=True)
    qc2.z(0)                                      # a column qubit (q4 of link b)
    assert vf.verify_plaquette(qc2, tg.UB_row(beta)).extra["touches_column"] is True


@pytest.mark.parametrize("order", [1, 2])
def test_verify_step_samples_small(order):
    alpha, beta = 0.37, 0.61
    k2 = tg.kappa2_of(alpha, 1.0)
    qc = cf.build_step(alpha, beta, k2, order)
    res = vf.verify_step_samples(qc, alpha, beta, k2, order, n_random=3, n_phys=2, seed=7)
    assert res["err"] <= 1e-10 and res["gauss"] <= 1e-10 and res["n_inputs"] == 5 and res["mode"] == "layers"
    other = vf.verify_step_samples(qc, alpha, beta, k2, 3 - order, n_random=3, n_phys=0, seed=7)
    assert other["err"] > 1e-3


def test_gauss_residual_outputs_sees_a_gauge_breaking_gate():
    from su2plaq.fuzzy import gauss as gz
    alpha, beta = 0.37, 0.61
    k2 = tg.kappa2_of(alpha, 1.0)
    states = gz.sample_physical_states(1, 20261104, max_components=1024)
    good = cf.build_step(alpha, beta, k2, 1, with_outer=True)
    assert vf.gauss_residual_outputs(good, states) <= 1e-10
    bad = cf.build_step(alpha, beta, k2, 1)
    a, b = bad.metadata["layers"][0][1:]
    from qiskit.circuit.library import RXGate
    for k in range(a, b):
        if bad.data[k].operation.name == "rz":
            bad.data[k] = bad.data[k].replace(operation=RXGate(0.7))
            break
    assert vf.gauss_residual_outputs(bad, states) > 1e-3


# --------------------------------------------------------------------------------------------------------------------
# NB-1: the layer metadata must partition the circuit and each range must touch only what it claims
# --------------------------------------------------------------------------------------------------------------------
ALPHA, BETA = 0.37, 0.61
K2 = tg.kappa2_of(ALPHA, 1.0)


def _step(order=1, with_outer=False):
    return cf.build_step(ALPHA, BETA, K2, order, with_outer=with_outer)


def test_validate_layers_accepts_delivered_circuits():
    for order in (1, 2):
        for wo in (False, True):
            qc = _step(order, wo)
            lay = vf.validate_layers(qc, qc.metadata["layers"], ALPHA, K2)
            assert lay[0][1] == 0 and lay[-1][2] == len(qc.data)


@pytest.mark.parametrize("tamper", ["append_rz", "append_cx"])
def test_tail_instructions_outside_the_layers_are_rejected(tamper):
    """The auditor's attack (A7): gates appended after the listed ranges, metadata untouched, must not pass."""
    qc = _step(1)
    if tamper == "append_rz":
        qc.rz(1.0, 0)
    else:
        qc.cx(3, 7)
    with pytest.raises(vf.LayerMetadataError):
        vf.verify_step_samples(qc, ALPHA, BETA, K2, 1, n_random=2, n_phys=0, seed=7)


def test_auditor_attack_both_gates_fails():
    qc = _step(1)
    qc.rz(1.0, 0)
    qc.cx(3, 7)
    with pytest.raises(vf.LayerMetadataError):
        vf.verify_step_samples(qc, ALPHA, BETA, K2, 1, n_random=2, n_phys=0, seed=7)
    with pytest.raises(vf.LayerMetadataError):
        vf.gauss_residual_outputs(qc, [])


def test_layer_gap_overlap_and_unknown_kind_are_rejected():
    qc = _step(1)
    lay = [tuple(x) for x in qc.metadata["layers"]]
    gap = [lay[0]] + [(lay[1][0], lay[1][1] + 1, lay[1][2])] + lay[2:]
    overlap = [lay[0], (lay[1][0], lay[1][1] - 1, lay[1][2])] + lay[2:]
    short = lay[:-1]
    reordered = [lay[1], lay[0]] + lay[2:]
    unknown = [("XX",) + lay[0][1:]] + lay[1:]
    for bad in (gap, overlap, short, reordered, unknown):
        with pytest.raises(vf.LayerMetadataError):
            vf.validate_layers(qc, bad)


def test_kinetic_range_must_stay_inside_one_inner_link():
    qc = _step(1)
    a, b = qc.metadata["layers"][0][1:]
    qc.data.insert(a, qc.data[a].replace(qubits=(qc.qubits[3], qc.qubits[7]), operation=CXGate()))
    qc.metadata["layers"] = [(k, x, y + 1) if (x, y) == (a, b) else ((k, x + 1, y + 1) if x >= b else (k, x, y)) for k, x, y in qc.metadata["layers"]]
    with pytest.raises(vf.LayerMetadataError):
        vf.validate_layers(qc, qc.metadata["layers"])


def test_ub_range_must_not_touch_outer_register():
    qc = _step(1, with_outer=True)
    kinds = [k for k, _, _ in qc.metadata["layers"]]
    a, b = qc.metadata["layers"][kinds.index("UB")][1:]
    qc.data[a] = qc.data[a].replace(qubits=(qc.qubits[20],), operation=XGate())
    with pytest.raises(vf.LayerMetadataError):
        vf.validate_layers(qc, qc.metadata["layers"])


def _outer_ranges(qc):
    return [(i, a, b) for i, (k, a, b) in enumerate(qc.metadata["layers"]) if k == "outer"]


def test_outer_range_with_inner_gate_is_rejected():
    """An inner gate hidden inside an 'outer' range (previously skipped silently, e.g. at r = 0)."""
    for k2 in (K2, 0.0):
        qc = cf.build_step(ALPHA, BETA, k2, 1, with_outer=True)
        i, a, b = _outer_ranges(qc)[0]
        qc.data[a] = qc.data[a].replace(qubits=(qc.qubits[0],), operation=RZGate(1.0))
        with pytest.raises(vf.LayerMetadataError):
            vf.verify_step_samples(qc, ALPHA, BETA, k2, 1, n_random=2, n_phys=0, seed=7)


def test_outer_block_with_wrong_angle_is_rejected():
    """An outer link block with a wrong angle (still gauge invariant, so the commutator would not see it) fails the per-link target."""
    wrong = cf.build_step(ALPHA * 1.05, BETA, K2, 1, with_outer=True)               # outer blocks at alpha * 1.05
    ok = cf.build_step(ALPHA, BETA, K2, 1, with_outer=True)
    assert len(wrong.data) == len(ok.data) and wrong.metadata["layers"] == ok.metadata["layers"]
    tam = ok.copy()
    a0 = _outer_ranges(ok)[0][1]
    for k in range(a0, len(ok.data)):                                               # inner part right, outer part wrong
        tam.data[k] = tam.data[k].replace(operation=wrong.data[k].operation)
    vf.validate_layers(ok, ok.metadata["layers"], ALPHA, K2)
    with pytest.raises(vf.LayerMetadataError, match="outer link"):
        vf.validate_layers(tam, tam.metadata["layers"], ALPHA, K2)
    with pytest.raises(vf.LayerMetadataError, match="outer link"):
        vf.verify_step_samples(tam, ALPHA, BETA, K2, 1, n_random=2, n_phys=0, seed=7)


def test_outer_range_spanning_two_links_or_partition_short_is_rejected():
    qc = _step(1, with_outer=True)
    lay = [tuple(x) for x in qc.metadata["layers"]]
    i0, a, b = _outer_ranges(qc)[0]
    merged = [x for j, x in enumerate(lay) if j != i0 + 1]
    merged[i0] = ("outer", a, lay[i0 + 1][2])                                      # two ranges (link 4 UE + link 4 UK) merged: still one link
    vf.validate_layers(qc, merged)                                                 # allowed: same link
    two_links = [x for j, x in enumerate(lay) if j not in (i0 + 1, i0 + 2)]
    two_links[i0] = ("outer", a, lay[i0 + 2][2])                                   # link 4 UE + link 4 UK + link 5 UE -> spans two links
    with pytest.raises(vf.LayerMetadataError):
        vf.validate_layers(qc, two_links)
    # last outer link dropped from the layers -> partition broken
    with pytest.raises(vf.LayerMetadataError):
        vf.validate_layers(qc, lay[:-2], ALPHA, K2)

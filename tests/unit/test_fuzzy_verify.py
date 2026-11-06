"""Unit tests of su2plaq.fuzzy.verify (adapter, verdicts, layered step check, Gauss residual of outputs)."""
import numpy as np
import pytest
from qiskit import QuantumCircuit

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

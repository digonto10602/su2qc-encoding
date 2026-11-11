"""Unit tests for su2plaq.circuits.lsh.build_UE (prompts/400 step 7.5): gates, registers, diagonal phases, outer row."""
import numpy as np
import pytest

from su2plaq.circuits.lsh import build_UE
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import operators as O


def test_build_UE_structure():
    qc = build_UE(0.37)
    assert [r.name for r in qc.qregs] == ["d"] and qc.num_qubits == 12
    ops = qc.count_ops()
    assert dict(ops) == {"p": 8} and qc.metadata["kind"] == "UE"
    assert sorted(qc.find_bit(i.qubits[0]).index for i in qc.data) == [0, 1, 3, 4, 6, 7, 9, 10]
    assert all(np.isclose(i.operation.params[0], -0.75 * 0.37) for i in qc.data)
    qo = build_UE(0.37, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o"] and qo.num_qubits == 24 and dict(qo.count_ops()) == {"p": 8}
    qr = build_UE(0.37, with_outer=True, include_outer_electric=True)
    assert dict(qr.count_ops()) == {"p": 20}
    outer = [i for i in qr.data if qr.find_bit(i.qubits[0]).index >= 12]
    assert len(outer) == 12
    phases = sorted((qr.find_bit(i.qubits[0]).index, round(i.operation.params[0] / (-0.75 * 0.37), 12)) for i in outer)
    assert phases == [(12 + 3 * c + k, 2.0 if k == 0 else 1.0) for c in range(4) for k in range(3)]
    with pytest.raises(ValueError):
        build_UE(0.1, with_outer=False, include_outer_electric=True)


def test_build_UE_matches_electric_energy_on_all_codes():
    """exp(-i alpha H_E) on the 433 physical codes, data-only and with the outer row (diagonal, evaluated per code)."""
    alpha = 0.91
    enc = LSH()
    codes = O.physical_codes()
    for outer, with_outer in ((False, False), (True, True)):
        qc = build_UE(alpha, with_outer=with_outer, include_outer_electric=outer)
        phase = np.zeros(len(codes))
        for inst in qc.data:
            q = qc.find_bit(inst.qubits[0]).index
            phase += inst.operation.params[0] * ((codes >> q) & 1)
        want = -alpha * O.h_electric_lsh(codes, include_outer=outer)
        assert np.abs(np.exp(1j * phase) - np.exp(1j * want)).max() < 1e-12
    assert enc.n_data == 12


# ---- step 7.8: wrap_spinnet ----------------------------------------------------------------------------------------
def test_wrap_spinnet_structure_and_overhead():
    from su2plaq.circuits import spinnet as CS
    from su2plaq.circuits.lsh import wrap_spinnet
    from su2plaq.evaluate.evaluator import evaluate
    from su2plaq.metrics.logical import logical_metrics
    enc = LSH()
    sn = CS.build_UB(0.61)
    qc = wrap_spinnet(sn)
    assert [r.name for r in qc.qregs] == ["d", "a"] and qc.qregs[0].size == 12 and qc.num_qubits == sn.num_qubits + 4
    a, b = logical_metrics(qc), logical_metrics(sn)
    assert (a["cx"], a["t_fixed"], a["n_rot"], a["ancilla"]) == (b["cx"] + 40, b["t_fixed"] + 32, b["n_rot"], b["ancilla"])
    assert qc.metadata["wrapped"] == "lsh transcoder"
    assert evaluate(qc, enc, enc.target("UB", None, 0.61)).ok
    qo = wrap_spinnet(sn, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o", "a"] and qo.num_qubits == sn.num_qubits + 16
    # ancillas of C are the ancillas of the wrapped circuit (same count, after the outer register)
    assert qo.qregs[2].size == sn.num_qubits - 8
    with pytest.raises(ValueError):
        wrap_spinnet(CS.build_UB(0.61, with_outer=True))
    from qiskit import QuantumCircuit
    with pytest.raises(ValueError):
        wrap_spinnet(QuantumCircuit(8))


def test_wrap_of_identity_is_identity_on_codes():
    """T^dag T = 1: wrapping an empty spin-network circuit acts trivially on every inner code."""
    from qiskit import QuantumCircuit, QuantumRegister
    from su2plaq.circuits.lsh import wrap_spinnet
    from su2plaq.lsh import walk as Wk
    qc = wrap_spinnet(QuantumCircuit(QuantumRegister(8, "d")))
    steps = [(inst.operation.name, *[qc.find_bit(q).index for q in inst.qubits]) for inst in qc.data]
    for code in O.inner_codes().tolist():
        assert Wk.classical_run(steps, code) == code

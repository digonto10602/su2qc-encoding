"""Unit tests for circuits/spinnet.py build_UE / build_UB / build_step (prompts/100 steps 3.3-3.5) and the rc3x skeleton path
of spinnet/walk.py (mirror / build_walk with rc3x, rc3x_dg)."""
import functools
from fractions import Fraction

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from su2plaq.circuits import spinnet as cs
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.evaluate.evaluator import evaluate
from su2plaq.spinnet import walk
from su2plaq.spinnet.walk import FRAME, TARGET, build_walk, mirror


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


def test_frame_and_target_single_definition():
    assert cs.FRAME is walk.FRAME and cs.TARGET == walk.TARGET == 0
    assert not hasattr(cs, "QUBIT_MAP")
    assert enc().import_map("paulo15")["qubit_map"] == cs.paulo.QUBIT_MAP


def test_build_UE_structure_and_errors():
    qc = cs.build_UE(0.37)
    assert [(i.operation.name, qc.find_bit(i.qubits[0]).index) for i in qc.data] == [("p", q) for q in range(4)]
    assert all(abs(i.operation.params[0] + 0.75 * 0.37) < 1e-15 for i in qc.data)
    assert qc.metadata == {"kind": "UE", "alpha": 0.37}
    qe = cs.build_UE(0.37, with_outer=True, include_outer_electric=True)
    assert [qe.find_bit(i.qubits[0]).index for i in qe.data] == list(range(4)) + list(range(8, 16))
    assert cs.build_UE(0.37, with_outer=True).size() == 4
    with pytest.raises(ValueError):
        cs.build_UE(0.37, include_outer_electric=True)


def test_build_UB_metadata_counts_and_angle_linearity():
    qc = cs.build_UB(0.61)
    ops = dict(qc.count_ops())
    assert ops["rz"] == 4 and qc.num_qubits == 15 and [r.name for r in qc.qregs] == ["d", "a"]
    md = qc.metadata
    assert md["kind"] == "UB" and md["skeleton"] == "general7" and md["beta"] == 0.61
    fr = [Fraction(s) for s in md["angle_fractions"]]
    assert len(fr) == 4 and all(abs(float(f) * 0.61 - a) < 1e-12 for f, a in zip(fr, md["angles"]))
    rz = [i.operation.params[0] for i in qc.data if i.operation.name == "rz"]
    assert np.allclose(rz, md["angles"], atol=1e-15)
    other = cs.build_UB(1.7)
    assert other.metadata["angle_fractions"] == md["angle_fractions"]          # fractions are beta independent
    assert [i.operation.name for i in other.data] == [i.operation.name for i in qc.data]


@pytest.mark.parametrize("order", [1, 2])
def test_build_step_structure_and_order(order):
    alpha, beta = 0.37, 0.61
    qc = cs.build_step(alpha, beta, order=order)
    names = [i.operation.name for i in qc.data]
    ps = [k for k, n in enumerate(names) if n == "p"]
    first_rz = names.index("rz")
    assert len(ps) == 4 * order and all(k < first_rz for k in ps[:4])             # electric layer first
    if order == 2:
        assert all(k > max(i for i, n in enumerate(names) if n == "rz") for k in ps[4:])
    assert qc.metadata["kind"] == "step" and qc.metadata["order"] == order
    assert abs(qc.global_phase) < 1e-15
    assert qc.num_qubits == 15 and cs.build_step(alpha, beta, order, with_outer=True).num_qubits == 23
    v = evaluate(qc, enc(), enc().target("step", alpha, beta, order=order))
    assert v.ok and v.op_norm_error <= 1e-10
    v = evaluate(qc, enc(), enc().target("step", alpha, beta, order=3 - order))
    assert not v.ok
    with pytest.raises(ValueError):
        cs.build_step(alpha, beta, order=3)


def test_mirror_swaps_rc3x_pair_in_toy_walk():
    """rc3x flag on corner bits 4,5,6 into ancilla 8, rotation behind cx(8, q0); checked against an mcx reference."""
    compute = [("rc3x", 4, 5, 6, 8)]
    steps = compute + [("cx", 8, 0), ("rz", 0), ("cx", 8, 0)] + mirror(compute)
    assert steps[-1] == ("rc3x_dg", 4, 5, 6, 8)
    table = {c: (-1.0 if (c >> 4) & 7 == 7 else 1.0) for c in range(256)}        # frame leaves bits 4..6 alone
    beta = 0.3
    qc = build_walk(steps, table, beta, 1)
    ops = qc.count_ops()
    assert sum(v for k, v in ops.items() if "c" in k and k != "cx") == 2          # the rc3x pair, nothing else of that kind
    ref = QuantumCircuit(9)
    for a, b in FRAME:
        ref.cx(a, b)
    ref.h(TARGET)
    ref.mcx([4, 5, 6], 8)
    ref.cx(8, 0)
    ref.rz(2 * beta, 0)
    ref.cx(8, 0)
    ref.mcx([4, 5, 6], 8)
    ref.h(TARGET)
    for a, b in reversed(FRAME):
        ref.cx(a, b)
    U, R = Operator(qc).data, Operator(ref).data
    clean = np.arange(256)                                                         # ancilla bit (bit 8) = 0 columns/rows
    assert np.abs(U[:, clean][256:]).max() < 1e-12                                 # ancilla returns to |0>
    assert np.abs(U[np.ix_(clean, clean)] - R[np.ix_(clean, clean)]).max() < 1e-12

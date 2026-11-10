"""Unit tests for spinnet/trotter_v2.py and circuits.spinnet.trotter_v2_circuit (prompts/100 step 3.6)."""
import functools
from fractions import Fraction

import numpy as np
import pytest
from qiskit.circuit.library import RC3XGate, RCCXGate
from qiskit.quantum_info import Operator

from su2plaq.circuits import spinnet as cs
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.evaluate.evaluator import evaluate, synth_tolerances
from su2plaq.metrics.cliffordt import synthesize, t_table
from su2plaq.metrics.logical import logical_metrics
from su2plaq.spinnet import trotter_v2
from su2plaq.spinnet.walk import FRAME, build_walk

NAMES = ("pairs9", "flags4", "flags5", "flags6")
ALLOWED = {"x", "h", "t", "tdg", "rz", "cx", "rccx"}


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


def test_source_and_skeleton_table():
    assert "su2qc-trotter" in trotter_v2.SOURCE and "spinnet_v2" in trotter_v2.SOURCE and "feadc42" in trotter_v2.SOURCE
    assert set(trotter_v2.SKELETONS) == set(NAMES)
    assert trotter_v2.FRAME_B == ((3, 1), (0, 3), (0, 2))
    for name, (steps, n_anc, frame) in trotter_v2.SKELETONS.items():
        assert frame == (trotter_v2.FRAME_B if name == "pairs9" else FRAME) and n_anc == 3
        assert {s[0] for s in steps} <= {"cx", "x", "rccx", "rc3x", "rc3x_dg", "rz"}      # rccx_dg is written rccx
        wires = {q for s in steps for q in (s[1:] if s[0] != "rz" else s[1:])}
        assert max(wires) == 10 and min(wires) == 0
    assert all(any(s[0] == "rc3x" for s in trotter_v2.SKELETONS[n][0]) for n in ("flags4", "flags5", "flags6"))
    assert not any(s[0].startswith("rc3x") for s in trotter_v2.SKELETONS["pairs9"][0])


def test_frame_b_maps_the_four_link_flip_to_x_on_q0():
    """The frame must leave q1..q3 invariant under the flip of the four link bits and move q0 only."""
    for frame in (FRAME, trotter_v2.FRAME_B):
        for x in range(16):
            def run(v):
                for a, b in frame:
                    if (v >> a) & 1:
                        v ^= 1 << b
                return v
            assert run(x ^ 0b1111) == run(x) ^ 1


def test_rccx_is_self_inverse_rc3x_is_not_and_expansion_matches():
    R = Operator(RCCXGate()).data
    assert np.abs(R @ R - np.eye(8)).max() < 1e-14
    C = Operator(RC3XGate()).data
    assert np.abs(C @ C - np.eye(16)).max() > 1.0                                     # not self-inverse (norm 2)
    assert np.abs(Operator(RC3XGate().inverse()).data @ C - np.eye(16)).max() < 1e-14
    for dg in (False, True):
        steps = [("rc3x_dg" if dg else "rc3x", 4, 5, 6, 8)]
        qc = build_walk(steps, {c: 0.0 for c in range(256)}, 0.1, 1, expand=True)
        assert {i.operation.name for i in qc.data} <= {"cx", "h", "t", "tdg"}
        plain = build_walk(steps, {c: 0.0 for c in range(256)}, 0.1, 1, expand=False)
        assert np.abs(Operator(qc).data - Operator(plain).data).max() < 1e-14


@pytest.mark.parametrize("skeleton", NAMES)
def test_exact_allowed_gates_and_angle_linearity(skeleton):
    last = None
    for beta in (0.23, 0.61, 1.0):
        qc = cs.trotter_v2_circuit(skeleton, beta)
        assert qc.num_qubits == 11 and [r.name for r in qc.qregs] == ["d", "a"] and qc.qregs[1].size == 3
        assert {i.operation.name for i in qc.data} <= ALLOWED
        v = evaluate(qc, enc(), enc().target("UB", None, beta))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.dirty_ancilla <= 1e-20
        md = qc.metadata
        assert md["kind"] == "UB" and md["beta"] == beta and md["skeleton"] == skeleton and md["source"] == trotter_v2.SOURCE
        fr = [Fraction(s) for s in md["angle_fractions"]]
        assert np.allclose([float(f) * beta for f in fr], md["angles"], atol=1e-12)
        sk = [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]
        assert last is None or sk == last                                             # skeleton independent of beta
        last = sk


@pytest.mark.parametrize("skeleton, cx, n_rot, t_fixed", [("pairs9", 34, 9, 24), ("flags4", 44, 4, 48),
                                                          ("flags5", 42, 5, 40), ("flags6", 36, 6, 32)])
def test_counts_of_the_sibling(skeleton, cx, n_rot, t_fixed):
    lm = logical_metrics(cs.trotter_v2_circuit(skeleton, 0.61))
    assert (lm["cx"], lm["n_rot"], lm["t_fixed"], lm["ancilla"]) == (cx, n_rot, t_fixed, 3)


def test_wrong_uncompute_with_plain_rc3x_is_rejected():
    """Replacing the true inverse by the same RC3X gate in the uncompute leaves a dirty ancilla / wrong block."""
    steps, n_anc, frame = trotter_v2.SKELETONS["flags4"]
    bad = [("rc3x",) + s[1:] if s[0] == "rc3x_dg" else s for s in steps]
    assert bad != steps
    qc = build_walk(bad, cs._table(), 0.61, n_anc, frame=frame, expand=True)
    v = evaluate(qc, enc(), enc().target("UB", None, 0.61))
    assert not v.ok


def test_outer_register_untouched_and_errors():
    qo = cs.trotter_v2_circuit("pairs9", 0.61, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o", "a"] and qo.num_qubits == 19
    assert not ({qo.find_bit(q).index for i in qo.data for q in i.qubits} & set(range(8, 16)))
    v = evaluate(qo, enc(), enc().target("UB", None, 0.61), method="physical")
    assert v.ok and v.outer_bits_read == 0
    with pytest.raises(ValueError):
        cs.trotter_v2_circuit("nope", 0.61)


@pytest.mark.parametrize("skeleton", ("pairs9", "flags4"))
def test_t_table_and_synthesised_reverification(skeleton):
    qc = cs.trotter_v2_circuit(skeleton, 0.61)
    lm = logical_metrics(qc)
    rows = t_table(qc, (1e-4, 1e-6))
    for r in rows:
        assert r["t_total"] == r["t_fixed"] + r["t_rot_pygridsynth"]
        assert abs(r["t_qiskit"] - r["t_total"]) <= 0.10 * r["t_total"]
    eps = 1e-6
    synth, info = synthesize(qc, eps)
    tol = synth_tolerances(lm["n_rot"], eps)
    v = evaluate(synth, enc(), enc().target("UB", None, 0.61), **tol)
    assert v.ok and v.engine == "sparse" and v.certified and v.op_norm_error <= tol["tol_err"]

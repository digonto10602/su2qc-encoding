"""M3-P1, M3-V1 — external spin-network circuits through our evaluator (prompts/100 §3 steps 3.2, 3.6; METHODS-spinnet §5).

M3-P1: Paulo's 15-qubit gate file refs/paulo/spin_network_plaquette3.gates.txt (exp(+i alpha_P Re Tr W), alpha_P = 0.1,
i.e. beta = 0.05; 68 CX, 64 fixed T, 4 exact p rotations, 7 ancillas; file qubits q0-3 = links, q12-15 = corners,
q16-22 = ancillas, q4-11 never touched) evaluated on the open 433 states.  Expected valid in the (inner|outer) pairing
up to a diagonal +-1 gauge of the code basis — the test decides.  Planner measurement (scratch/planner/
proto_m3_spinnet.py): gauge residual 2.9e-15 with one -1 per bright pair, full evaluator error 9.8e-15, leak 0,
Gauss 5e-16, outer_bits_read 0.  Its rotations are exact p gates, so the exact-angle tolerance 1e-10 applies.
M3-V1: su2qc-trotter spinnet_v2 skeletons pairs9 (34 CX, 9 rotations) and flags4 (44 CX, 4 rotations), vendored and
re-solved from our K (angle-linear), exact at the nominal and alternate angles (planner measurement 8e-15)."""
import functools
import re

import numpy as np
import pytest

from tests.acceptance._api import api, op_norm_after_phase

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}
GATES_FILE = "refs/paulo/spin_network_plaquette3.gates.txt"
PAULO_OPS = {"cx": 68, "h": 34, "t": 32, "tdg": 32, "x": 12, "p": 4}
PAULO_ALPHA_P = 0.1


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.spinnet:SpinNet")()


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


def test_M3_P1_paulo15_open_states(root):
    """Loads with the file's counts and angles (0.025, 0.05, 0.1, -0.2 = alpha_P x (1/4, 1/2, 1, -2)); 47x47 block on the
    inner codes: leak 0, equal to exp(-i beta K) (beta = alpha_P/2) up to one global phase and a real diagonal gauge D
    with exactly one -1 per bright pair and +1 on dark codes (gauge_align residual <= 1e-10); with the gauge-fixed target
    the full evaluator (433 states, outer register present) accepts at the exact-angle tolerance: error <= 1e-10,
    leak <= 1e-10, Gauss <= 1e-10, ancillas clean, outer_bits_read 0; without the gauge the raw route-B target is
    rejected (error > 0.1) — the recorded verdict goes to results/spinnet/UB.json (M3-R1)."""
    enc = _enc()
    paulo_circuit = api("su2plaq.circuits.spinnet:paulo_circuit")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    run_batch = api("su2plaq.evaluate.sparse_sim:run_batch")
    encoded_block = api("su2plaq.evaluate.sparse_sim:encoded_block")
    align = api("su2plaq.encodings.spinnet:align_inner_block")
    text = (root / GATES_FILE).read_text()
    n_lines = sum(1 for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#"))
    assert n_lines == sum(PAULO_OPS.values()) == 182
    qc = paulo_circuit()
    assert qc.num_qubits == 15 and [r.name for r in qc.qregs] == ["d", "a"] and qc.qregs[0].size == 8 and qc.qregs[1].size == 7
    assert dict(qc.count_ops()) == PAULO_OPS
    angles = [float(i.operation.params[0]) for i in qc.data if i.operation.name == "p"]
    assert np.allclose(np.array(angles) / PAULO_ALPHA_P, [0.25, 0.5, 1.0, -2.0], atol=1e-12)
    assert qc.metadata["alpha_P"] == PAULO_ALPHA_P and abs(qc.metadata["beta"] - 0.05) <= 1e-15 and qc.metadata["kind"] == "UB"
    lm = api("su2plaq.metrics.logical:logical_metrics")(qc)
    assert lm["cx"] == 68 and lm["t_fixed"] == 64 and lm["n_rot"] == 4 and lm["ancilla"] == 7 and lm["depth"] == 90
    beta = PAULO_ALPHA_P / 2
    codes = enc.inner_codes()
    M, leak = encoded_block(run_batch(qc, codes), codes, len(codes), code_mask=(1 << 8) - 1)
    assert leak.max() <= 1e-12
    V47 = enc.inner_target("UB", None, beta)
    D, res, phase = align(M, V47)
    assert D is not None and res <= 1e-10 and abs(abs(phase) - 1) <= 1e-12
    assert np.abs(D.imag).max() <= 1e-12 and np.abs(np.abs(D) - 1).max() <= 1e-12
    neg = [int(c) for c, d in zip(codes, D) if d.real < 0]
    assert len(neg) == 8 and all((c >> 4) == 0 for c in neg) and all((c ^ 0b1111) not in neg for c in neg)
    assert op_norm_after_phase(M, np.diag(D) @ V47 @ np.diag(D).conj().T) <= 1e-10
    # open 433 states, outer register present, gauge-fixed target
    qo = paulo_circuit(with_outer=True)
    assert qo.num_qubits == 23 and [r.name for r in qo.qregs] == ["d", "o", "a"]
    touched = {qo.find_bit(q).index for inst in qo.data for q in inst.qubits}
    assert not (touched & set(range(8, 16)))
    Vg = enc.regauge(enc.target("UB", None, beta), D)
    v = evaluate(qo, enc, Vg, method="physical", gauss=True)
    assert v.ok, (v.reason, v.op_norm_error, v.leak_amplitude, v.gauss_residual)
    assert v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.dirty_ancilla <= 1e-20 and v.gauss_residual <= 1e-10
    assert v.outer_bits_read == 0 and v.n_blocks == 1 and v.n_inputs == 433 and v.engine == "sparse" and v.certified
    v2 = evaluate(qo, enc, enc.target("UB", None, beta), method="physical")
    assert not v2.ok and v2.op_norm_error > 0.1
    imp = enc.import_map("paulo15")
    assert isinstance(imp, dict) and imp["fixed_angle"] and imp["kind"] == "UB" and imp["n_source_qubits"] == 15
    assert imp["angles"](0.37, 0.61)["beta"] == beta and len(imp["qubit_map"]) == 15
    assert isinstance(enc.import_map("paulo34"), str) and isinstance(enc.import_map("lean22_v2"), str)


@pytest.mark.parametrize("skeleton, cx, n_rot", [("pairs9", 34, 9), ("flags4", 44, 4)])
def test_M3_V1_trotter_spinnet_v2(skeleton, cx, n_rot):
    """Vendored su2qc-trotter spinnet_v2 skeleton (angles re-solved from our K in route-B gauge; rc3x expanded into its
    basis-gate definition and its true inverse used in the uncompute): allowed gates only, CX and rotation counts equal
    the sibling's published numbers (results_spinnet_v2.json / archive), exact (1e-10) at the nominal and the alternate
    angles with one skeleton, ancillas clean, outer register untouched."""
    enc = _enc()
    build = api("su2plaq.circuits.spinnet:trotter_v2_circuit")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    lm_f = api("su2plaq.metrics.logical:logical_metrics")
    skel = None
    for alpha, beta in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        qc = build(skeleton, beta)
        assert qc.qregs[0].name == "d" and qc.qregs[0].size == 8
        assert {i.operation.name for i in qc.data} <= ALLOWED
        v = evaluate(qc, enc, enc.target("UB", None, beta))
        assert v.ok, (skeleton, beta, v.reason, v.op_norm_error)
        assert v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.dirty_ancilla <= 1e-20
        sk = _skeleton(qc)
        assert skel is None or sk == skel
        skel = sk
    lm = lm_f(build(skeleton, 0.61))
    assert lm["cx"] == cx and lm["n_rot"] == n_rot and lm["ancilla"] == 3
    qo = build(skeleton, 0.61, with_outer=True)
    vo = evaluate(qo, enc, enc.target("UB", None, 0.61), method="physical")
    assert vo.ok and vo.outer_bits_read == 0 and vo.gauss_residual <= 1e-10
    imp = enc.import_map("spinnet_v2")
    assert isinstance(imp, dict) and not imp["fixed_angle"] and imp["kind"] == "UB" and skeleton in imp["skeletons"]
    src = api("su2plaq.spinnet.trotter_v2:SOURCE")
    assert isinstance(src, str) and "su2qc-trotter" in src and "spinnet_v2" in src

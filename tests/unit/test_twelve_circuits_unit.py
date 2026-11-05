"""Unit tests for su2plaq.circuits.twelve (electric step)."""
import numpy as np
import pytest

from su2plaq.circuits.twelve import OUTER_J_QUBITS, build_UE
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate import evaluator as ev
from su2plaq.exact.operators import target


@pytest.fixture(scope="module")
def enc():
    return TwelveQubit()


def test_build_UE_structure_and_metadata():
    qc = build_UE(0.37)
    assert qc.num_qubits == 12 and [r.name for r in qc.qregs] == ["d"]
    assert [(i.operation.name, qc.find_bit(i.qubits[0]).index) for i in qc.data] == [("p", q) for q in (2, 5, 8, 11)]
    assert all(abs(i.operation.params[0] + 0.75 * 0.37) < 1e-15 for i in qc.data)
    assert qc.metadata == {"kind": "UE", "alpha": 0.37}
    qo = build_UE(0.37, with_outer=True)
    assert qo.num_qubits == 28 and [r.name for r in qo.qregs] == ["d", "o"] and len(qo.data) == 4
    with pytest.raises(ValueError):
        build_UE(0.37, include_outer_electric=True)


def test_outer_qubits_are_the_j_qubits_of_the_outer_links():
    assert OUTER_J_QUBITS == (13, 15, 17, 19, 21, 23, 25, 27)


@pytest.mark.parametrize("alpha", [0.37, 1.7])
def test_UE_matches_target_inner_and_with_outer_row(enc, alpha):
    v = ev.evaluate(build_UE(alpha), enc, enc.target("UE", alpha, None))
    assert v.ok and v.certified and v.engine == "sparse" and v.op_norm_error <= 1e-10
    qo = build_UE(alpha, with_outer=True, include_outer_electric=True)
    assert len(qo.data) == 12
    full = target(enc.basis, "UE", alpha=alpha, include_outer_electric=True)
    vo = ev.evaluate(qo, enc, full)
    assert vo.ok and vo.outer_bits_read == 8 and vo.method == "physical" and vo.op_norm_error <= 1e-10
    # without the outer row the same circuit does not match the full target (outer electric energy is non-trivial)
    vn = ev.evaluate(build_UE(alpha, with_outer=True), enc, full)
    assert not vn.ok and vn.reason == "error"


# ---------------------------------------------------------------- magnetic step (port of Paulo's notebook)
ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


def _skeleton(qc):
    return [(i.operation.name, tuple(qc.find_bit(q).index for q in i.qubits)) for i in qc.data]


def test_build_UB_registers_gateset_and_beta_independent_skeleton():
    from su2plaq.circuits.twelve import build_UB

    qc = build_UB(0.61)
    assert [(r.name, len(r)) for r in qc.qregs] == [("d", 12), ("p", 4), ("e", 4), ("w", 7), ("g", 3), ("tmp", 3), ("h", 1)]
    assert {i.operation.name for i in qc.data} <= ALLOWED
    assert _skeleton(build_UB(0.4)) == _skeleton(build_UB(2.0)) == _skeleton(qc)
    qo = build_UB(0.61, with_outer=True)
    assert [r.name for r in qo.qregs] == ["d", "o", "p", "e", "w", "g", "tmp", "h"] and qo.num_qubits == 50
    assert all(qo.find_bit(q).index < 12 or qo.find_bit(q).index >= 28 for i in qo.data for q in i.qubits)  # outer never touched
    assert qc.metadata == {"kind": "UB", "beta": 0.61}


def test_build_UB_rotations_sit_on_one_qubit_and_costs():
    from su2plaq.circuits.twelve import build_UB
    from su2plaq.metrics.logical import logical_metrics

    m = logical_metrics(build_UB(0.61))
    assert m["cx"] == 294 and m["n_rot"] == 6 and m["qubits"] == 34 and m["ancilla"] == 22
    assert m["t_fixed"] == 296 + 16   # Paulo's 296 plus four rccx (2 x 4 T) replacing his two native mcrx
    import math
    from su2plaq.metrics.logical import lower

    low = lower(build_UB(0.61))
    rot_qubits = {low.find_bit(i.qubits[0]).index for i in low.data
                  if i.operation.name == "rz" and abs(i.operation.params[0] / (math.pi / 4) - round(i.operation.params[0] / (math.pi / 4))) > 1e-9}
    assert rot_qubits == {11}   # the single 'side' qubit j_3: after synthesis only one data qubit carries non-Clifford words


def test_build_UB_equals_inner_target_and_paulo_logical(enc):
    import numpy as np
    from su2plaq.circuits.twelve import build_UB, paulo_logical
    from su2plaq.evaluate.sparse_sim import encoded_block, run_batch

    codes = enc.inner_codes()
    blocks = []
    for qc in (build_UB(0.61), paulo_logical(0.61)):
        M, leak = encoded_block(run_batch(qc, codes), codes, 625, (1 << 12) - 1)
        assert leak.max() < 1e-12
        blocks.append(M)
    V = ev.inner_target(enc, "UB", None, 0.61)
    for M in blocks:
        ov = np.trace(V.conj().T @ M)
        assert np.linalg.norm(M - ov / abs(ov) * V, 2) < 1e-10

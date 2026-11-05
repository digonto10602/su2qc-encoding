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

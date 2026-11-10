"""M7-V1 — spin-network circuits wrapped by the LSH transcoder (prompts/400 §1.7, §3 step 7.8; METHODS-lsh L8).

For pure gauge the LSH loop numbers and the spin-network labels describe the same states; the in-place transcoder T (per
'in' site: cx, cx, rccx = 5 CX, 4 T) maps the 47 LSH inner codes one-to-one onto the 47 spin-network inner codes (links on
wires 0, 3, 6, 9; corner bits on 1, 4, 7, 10) and leaves w_c = N_v mod 2 on wires 2, 5, 8, 11.  Hence T^dag C T is a valid
LSH circuit for every valid spin-network U_B circuit C, at an overhead of exactly 40 CX and 32 T: the measured price of
the LSH register relative to the spin-network register.  Planner measurements (scratch/planner/proto_m7_lsh_wrap.py):
general7 94 CX / 4 rot / 88 T; pairs9 74 / 9 / 56; flags4 84 / 4 / 80; errors <= 1.4e-14, Gauss 5.4e-16."""
import functools

import pytest

from tests.acceptance._api import api

ALLOWED = {"x", "z", "h", "s", "sdg", "t", "tdg", "rz", "p", "cx", "cz", "ccx", "rccx", "ccz", "swap", "ch", "crz", "crx", "cp"}


@functools.lru_cache(maxsize=None)
def _enc():
    return api("su2plaq.encodings.lsh:LSH")()


def _skeleton(qc):
    return [(inst.operation.name, tuple(qc.find_bit(q).index for q in inst.qubits)) for inst in qc.data]


@pytest.mark.parametrize("skeleton", ["general7", "pairs9", "flags4"])
def test_M7_V1_wrapped_spinnet(skeleton):
    """wrap_spinnet(C) for C = the spin-network general circuit (general7) and the vendored su2qc-trotter skeletons pairs9,
    flags4 (M3-V1): registers d[12] + the ancillas of C; exact on the LSH target at the nominal and alternate beta (1e-10,
    Gauss 1e-10, clean ancillas), same skeleton at all beta; CX = CX(C) + 40, fixed T = T(C) + 32, rotations and ancillas
    unchanged; with_outer: 433 states, outer never read.  A circuit with an outer register or without d[8] is refused."""
    enc = _enc()
    CS = api("su2plaq.circuits.spinnet")
    wrap = api("su2plaq.circuits.lsh:wrap_spinnet")
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    lmf = api("su2plaq.metrics.logical:logical_metrics")

    def source(beta):
        return CS.build_UB(beta) if skeleton == "general7" else CS.trotter_v2_circuit(skeleton, beta)

    skel = None
    for beta in (0.61, 0.23, 1.00):
        sn = source(beta)
        qc = wrap(sn)
        assert qc.qregs[0].name == "d" and qc.qregs[0].size == 12 and qc.num_qubits == sn.num_qubits + 4
        assert {i.operation.name for i in qc.data} <= ALLOWED | {i.operation.name for i in sn.data}
        v = evaluate(qc, enc, enc.target("UB", None, beta))
        assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.dirty_ancilla <= 1e-20 and v.gauss_residual <= 1e-10
        sk = _skeleton(qc)
        assert skel is None or sk == skel
        skel = sk
    sn = source(0.61)
    a, b = lmf(wrap(sn)), lmf(sn)
    assert a["cx"] == b["cx"] + 40 and a["t_fixed"] == b["t_fixed"] + 32 and a["n_rot"] == b["n_rot"] and a["ancilla"] == b["ancilla"]
    qo = wrap(sn, with_outer=True)
    assert [r.name for r in qo.qregs][:2] == ["d", "o"] and qo.qregs[1].size == 12
    vo = evaluate(qo, enc, enc.target("UB", None, 0.61), method="physical")
    assert vo.ok and vo.outer_bits_read == 0 and vo.n_inputs == 433 and vo.gauss_residual <= 1e-10
    with pytest.raises(ValueError):
        wrap(CS.build_UB(0.61, with_outer=True))

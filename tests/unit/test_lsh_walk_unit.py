"""Unit tests for su2plaq.lsh.walk and circuits.lsh.build_UB / build_step (prompts/400 steps 7.6-7.7)."""
import functools
from fractions import Fraction

import numpy as np
import pytest

from su2plaq.circuits.lsh import build_UB, build_step
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import operators as O
from su2plaq.lsh import walk as W
from su2plaq.metrics.logical import logical_metrics


@functools.lru_cache(maxsize=1)
def enc():
    return LSH()


def test_constants_and_transcoder():
    assert W.LINK == (0, 3, 6, 9) and W.CBIT == (1, 4, 7, 10) and W.WBIT == (2, 5, 8, 11) and W.TARGET == 0
    assert len(W.TRANSCODE) == 12 and W.TRANSCODE == tuple(W.transcode_steps())
    assert W.FRAME == (("cx", 3, 9), ("cx", 0, 3), ("cx", 0, 6))
    steps = W.transcode_steps()
    assert steps[:3] == [("cx", 1, 2), ("cx", 1, 0), ("rccx", 2, 0, 1)]
    assert W.mirror(steps) == list(reversed(steps))
    assert W.mirror([("rz", 0), ("cx", 0, 1), ("p_alpha", 2)]) == [("cx", 0, 1)]


def test_transcoder_maps_inner_codes_into_spinnet_codes():
    """Transcoder (classical action): wires 0,3,6,9 = N_n (= 2 j), 1,4,7,10 = [J_c = 1], 2,5,8,11 = N_v mod 2; injective on
    the 47 inner codes."""
    images = set()
    for code in O.inner_codes().tolist():
        out = W.classical_run(W.transcode_steps(), code)
        images.add(out)
        for c in range(4):
            s = (code >> (3 * c)) & 7
            n1, n2, n3 = O.site_flux(s)
            assert (out >> (3 * c)) & 1 == n2 and (out >> (3 * c + 1)) & 1 == int(n3 == 2) and (out >> (3 * c + 2)) & 1 == n3 % 2
    assert len(images) == 47


def test_skeleton_variants():
    s0, n0 = W.skeleton(0)
    s1, n1 = W.skeleton(1)
    s2, n2 = W.skeleton(2)
    assert n0 == n1 == n2 == 7
    cnt = lambda st, k: sum(1 for x in st if x[0] == k)  # noqa: E731
    assert (cnt(s0, "rz"), cnt(s1, "rz"), cnt(s2, "rz")) == (4, 4, 4)
    assert (cnt(s0, "p_alpha"), cnt(s1, "p_alpha"), cnt(s2, "p_alpha")) == (0, 4, 8)
    assert (cnt(s0, "rccx"), cnt(s1, "rccx"), cnt(s2, "rccx")) == (22, 22, 22)       # 2 * (4 transcoder + 7 flag Toffolis)
    assert (cnt(s0, "cx"), cnt(s1, "cx"), cnt(s2, "cx")) == (28, 28, 28)           # 16 transcoder + 6 frame + 6 walk
    with pytest.raises(ValueError):
        W.skeleton(3)


def test_solved_angles_and_fractions():
    e = enc()
    steps, _ = W.skeleton(0)
    table = W.coupling_table(e)
    theta, res = W.solve_angles(steps, table, 0.61)
    assert res < 1e-12 and len(theta) == 4
    theta1, _ = W.solve_angles(steps, table, 1.0)
    assert np.allclose(theta, 0.61 * theta1)                         # angle-linear in beta
    fr = W.angle_fractions(steps, table)
    assert all(isinstance(f, Fraction) for f in fr) and max(f.denominator for f in fr) <= 4
    assert sorted(float(f) for f in fr) == pytest.approx(sorted([-3.5, -1.0, 3.0, 1.5]))
    with pytest.raises(ValueError):
        W.angle_fractions(steps, table, max_den=1)                  # (-7/2, 3/2) are not integers
    # a table the 4-rotation Walsh series cannot reproduce is rejected by build
    bad = dict(table)
    bad[min(bad)] += 0.123
    with pytest.raises(ValueError):
        W.build(steps, 7, bad, None, 0.5)


def test_classical_slots_independent_of_pair_member():
    """The walk slots of the two members of a bright pair agree (the target bit is cleared at the first h) and there is one
    slot per rotation."""
    steps, _ = W.skeleton(0)
    partner = W.partner_table(enc())
    for code in O.inner_codes().tolist():
        slots = W.classical_slots(steps, code)
        assert len(slots) == 4
        if code in partner:
            pre = W.classical_run(W.transcode_steps(), code)
            pre_p = W.classical_run(W.transcode_steps(), partner[code])
            assert pre != pre_p
            assert slots == W.classical_slots(steps, partner[code])


def test_build_UB_gate_counts_and_metadata():
    qc = build_UB(0.61)
    lm = logical_metrics(qc)
    assert (lm["cx"], lm["n_rot"], lm["t_fixed"], lm["ancilla"]) == (94, 4, 88, 7)
    assert qc.num_qubits == 19 and [r.name for r in qc.qregs] == ["d", "a"]
    ops = dict(qc.count_ops())
    assert ops.get("rz") == 4 and not (set(ops) & {"mcx", "mcrx", "cu", "unitary", "ccx"})
    md = qc.metadata
    assert md["kind"] == "UB" and md["beta"] == 0.61 and len(md["angles"]) == 4 and len(md["angle_fractions"]) == 4
    qo = build_UB(0.61, with_outer=True)
    assert qo.num_qubits == 31 and [r.name for r in qo.qregs] == ["d", "o", "a"]


def test_build_step_orders():
    q1, q2 = build_step(0.37, 0.61, 1), build_step(0.37, 0.61, 2)
    assert dict(q1.count_ops())["p"] == 4 and dict(q2.count_ops())["p"] == 8
    assert dict(q1.count_ops())["rz"] == dict(q2.count_ops())["rz"] == 4
    assert q1.metadata["order"] == 1 and q2.metadata["order"] == 2
    assert np.isclose(q1.data[[i for i, x in enumerate(q1.data) if x.operation.name == "p"][0]].operation.params[0], -0.75 * 0.37)
    p2 = [x.operation.params[0] for x in q2.data if x.operation.name == "p"]
    assert np.allclose(p2, -0.75 * 0.37 / 2)
    with pytest.raises(ValueError):
        build_step(0.37, 0.61, 3)
    with pytest.raises(ValueError):
        W.build(W.skeleton(1)[0], 7, W.coupling_table(enc()), None, 0.61)      # electric layer without alpha


# ---- step 7.7 mutants: the evaluator against the step target must reject a swapped or mis-wired electric layer ---------
def _mutant_step(kind):
    """Order-1 step with the electric layer (a) after the core instead of before, (b) on the corner-bit wires 1,4,7,10."""
    steps, n_anc = W.skeleton(0)
    n_t = len(W.TRANSCODE)
    pre, rest = steps[:n_t], steps[n_t:]
    post = rest[-n_t:]
    core = rest[:-n_t]
    wires = W.LINK if kind == "swap" else W.CBIT
    layer = [("p_alpha", q) for q in wires]
    mutated = pre + (layer + core if kind == "wires" else core + layer) + post
    return W.build(mutated, n_anc, W.coupling_table(enc()), 0.37, 0.61, 1, False, f"mutant_{kind}")


def test_step_electric_layer_position_and_wires():
    from qiskit import QuantumCircuit  # noqa: F401
    q1, q2 = build_step(0.37, 0.61, 1), build_step(0.37, 0.61, 2)
    for qc, n_layers in ((q1, 1), (q2, 2)):
        idx = lambda i: qc.find_bit(qc.data[i].qubits[0]).index  # noqa: E731
        names = [x.operation.name for x in qc.data]
        p_pos = [i for i, n in enumerate(names) if n == "p"]
        rz_pos = [i for i, n in enumerate(names) if n == "rz"]
        assert len(p_pos) == 4 * n_layers
        assert {idx(i) for i in p_pos} == {0, 3, 6, 9}                  # the link wires j_b j_r j_t j_l
        assert max(p_pos[:4]) < min(rz_pos)                               # first layer before every walk rotation
        if n_layers == 2:
            assert min(p_pos[4:]) > max(rz_pos)                           # second layer after the walk
        else:
            assert max(p_pos) < min(rz_pos)


@pytest.mark.parametrize("kind", ["swap", "wires"])
def test_step_mutants_are_rejected_by_the_evaluator(kind):
    from su2plaq.evaluate.evaluator import evaluate
    e = enc()
    V = e.target("step", 0.37, 0.61, 1)
    assert evaluate(build_step(0.37, 0.61, 1), e, V).ok
    bad = evaluate(_mutant_step(kind), e, V)
    assert not bad.ok

"""Unit tests for spinnet/walk.py (prompts/100 step 3.2): classical_slots, solve_angles, angle_fractions, mirror, build_walk."""
import functools
from fractions import Fraction

import numpy as np
import pytest

from su2plaq.encodings.spinnet import SpinNet
from su2plaq.evaluate.evaluator import evaluate
from su2plaq.spinnet.walk import (FRAME, GENERAL7, TARGET, angle_fractions, build_walk, classical_slots, coupling_table,
                                  mirror, solve_angles)


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


@functools.lru_cache(maxsize=None)
def table():
    return coupling_table(enc())


def test_classical_slots_toy_skeleton():
    """x(4); rccx(4,1 -> 8); rz(0); cx(8,0); rz(0); cx(8,0): slot 1 is the target bit after the controlled flip."""
    steps = [("x", 4), ("rccx", 4, 1, 8), ("rz", 0), ("cx", 8, 0), ("rz", 0), ("cx", 8, 0)]
    for code in range(256):
        x = code
        for a, b in FRAME:
            x ^= ((x >> a) & 1) << b
        x &= ~1
        flag = (1 - ((x >> 4) & 1)) & ((x >> 1) & 1)
        assert classical_slots(steps, code) == [0, flag]
    # the target bit is cleared before the first rz whatever the input; the frame is applied first
    assert classical_slots([("rz", 1)], 0b0010, frame=()) == [1]
    assert classical_slots([("rz", 3)], 0b0010) == [1]            # frame cx(1,3) first: q3 = j_r ^ j_l
    assert classical_slots([("rz", 3)], 0b0001) == [0]            # cx(0,1), cx(0,2) come after cx(1,3)
    with pytest.raises(ValueError):
        classical_slots([("h", 0)], 0)


def test_classical_slots_matches_frame_invariants():
    steps, _ = GENERAL7
    for code in enc().inner_codes():
        s = classical_slots(steps, int(code))
        assert len(s) == 4 and s[0] == 0                          # first rz: constant slot (theta_0)
        bright = int(code) >> 4 == 0
        assert s[1] == (1 if bright else 0)                       # second rz sits behind cx(F, q0): F = 1 on bright codes


def test_mirror_reverses_and_drops_rz():
    steps = [("x", 1), ("rc3x", 1, 2, 3, 9), ("rccx", 4, 5, 10), ("rz", 0), ("rc3x_dg", 1, 2, 3, 11)]
    assert mirror(steps) == [("rc3x", 1, 2, 3, 11), ("rccx", 4, 5, 10), ("rc3x_dg", 1, 2, 3, 9), ("x", 1)]
    assert mirror(mirror(steps)) == [s for s in steps if s[0] != "rz"]


def test_solve_angles_reproduces_K_phases():
    steps, _ = GENERAL7
    t = table()
    for beta in (0.05, 0.37, 1.3):
        th, res = solve_angles(steps, t, beta)
        assert res <= 1e-12 and len(th) == 4
        for c, k in t.items():
            phase = sum(a * (-1) ** s for a, s in zip(th, classical_slots(steps, c)))
            assert abs(phase - 2 * beta * k) <= 1e-12            # dark codes: exactly 0 rotation angle
        assert np.allclose(th, beta * np.array(solve_angles(steps, t, 1.0)[0]), atol=1e-14)   # linear in beta
    assert sum(1 for k in t.values() if k == 0.0) == 31


def test_angle_fractions_exact_rationals():
    steps, _ = GENERAL7
    fr = angle_fractions(steps, table())
    assert all(isinstance(f, Fraction) and f.denominator <= 2 for f in fr)
    th, _ = solve_angles(steps, table(), 1.0)
    assert np.allclose([float(f) for f in fr], th, atol=1e-12)
    with pytest.raises(ValueError):
        angle_fractions(steps, table(), max_den=1)


def test_solve_angles_inconsistent_skeleton_reports_residual():
    steps = [("rz", TARGET)]                                       # one constant angle cannot give three distinct values
    th, res = solve_angles(steps, table(), 0.5)
    assert res > 0.1
    with pytest.raises(ValueError):
        build_walk(steps, table(), 0.5, 0)


@pytest.mark.parametrize("with_outer", [False, True])
def test_build_walk_general7_is_exact(with_outer):
    steps, n_anc = GENERAL7
    beta = 0.61
    qc = build_walk(steps, table(), beta, n_anc, with_outer=with_outer)
    assert [r.name for r in qc.qregs] == (["d", "o", "a"] if with_outer else ["d", "a"])
    assert qc.num_qubits == 8 + 8 * with_outer + n_anc
    ops = dict(qc.count_ops())
    assert ops["rz"] == 4 and ops["rccx"] == 14 and set(ops) <= {"cx", "x", "h", "rz", "rccx"}
    v = evaluate(qc, enc(), enc().target("UB", None, beta), **({"method": "physical"} if with_outer else {}))
    assert v.ok and v.op_norm_error <= 1e-10 and v.leak_amplitude <= 1e-10 and v.dirty_ancilla <= 1e-20, (v.reason, v.op_norm_error)


def test_coupling_table_exact_half_integers():
    """Entries are exact multiples of 1/2 (K carries ~1e-15 noise, snapped); non-half-integer K raises."""
    t = table()
    assert all(2 * v == round(2 * v) for v in t.values())
    assert sorted(set(t.values())) == [-2.0, -0.5, 0.0, 1.0]

    class Fake:
        def __init__(self, scale):
            e = enc()
            self.K_codes = e.K_codes * scale
            self._e = e

        def inner_codes(self):
            return self._e.inner_codes()

    with pytest.raises(ValueError):
        coupling_table(Fake(1.01))

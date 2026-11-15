"""Unit tests for the B2 evaluator changes of prompts/008 §5: span leak, Verdict fields, reason order, prune_fraction,
extra["gauss"], inner_target dispatch.  Small systems (spin network: 47 inner codes, 433 states, 16 qubits)."""
import dataclasses
import functools
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit

from su2plaq.circuits import spinnet as CS
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.evaluate import evaluator as EV
from su2plaq.results.store import verdict_to_dict

ALPHA, BETA = 0.37, 0.61
THETA = 0.02


@functools.lru_cache(maxsize=None)
def _enc():
    return SpinNet()


def _perturbed(theta=THETA):
    qc = CS.build_UE(0.0, with_outer=True)          # identity circuit on the 8 + 8 register
    qc.ry(theta, 0)
    return qc


def _identity():
    return np.eye(433, dtype=complex)


def test_verdict_has_the_new_fields_with_safe_defaults():
    f = EV.Verdict.__dataclass_fields__
    assert math.isnan(f["span_leak"].default) and f["total_error"].default == math.inf
    names = list(f)
    assert names.index("span_leak") > names.index("extra") and names.index("total_error") == names.index("span_leak") + 1
    e = EV._early("bad_layout", 0.0, "inner_span", "sparse")
    assert not e.ok and math.isnan(e.span_leak) and e.total_error == math.inf          # an early failure judged nothing
    d = verdict_to_dict(e)
    assert "span_leak" in d and "total_error" in d


def test_exact_circuit_has_zero_span_leak_and_identities():
    enc = _enc()
    qc = CS.build_step(ALPHA, BETA, 1, with_outer=True)
    v = EV.evaluate(qc, enc, enc.target("step", ALPHA, BETA, 1), gauss=True)
    assert v.ok and v.reason == "ok" and 0.0 <= v.span_leak <= 1e-12
    assert v.total_error == v.op_norm_error + v.span_leak
    assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) <= 1e-15
    assert v.extra["gauss"] == "checked" and 0.0 <= v.gauss_residual <= 1e-10
    assert 0.0 <= v.extra["span_leak_max_state"] <= v.span_leak + 1e-15
    assert "max_span_leak" in v.extra


def test_gauss_not_checked_is_nan_and_labelled():
    enc = _enc()
    qc = CS.build_UE(ALPHA, with_outer=True)
    v = EV.evaluate(qc, enc, enc.target("UE", ALPHA, BETA, 1), gauss=False)
    assert v.ok and math.isnan(v.gauss_residual) and v.extra["gauss"] == "not_checked"


def test_span_leak_value_and_validity_rule():
    """ry(theta) on a data qubit of the identity circuit sends sin(theta/2) of every input out of its place: the exact operator
    norm of the leak outside the physical span (inside the code space) is that amplitude."""
    enc = _enc()
    v = EV.evaluate(_perturbed(), enc, _identity(), tol_err=1.0, tol_gauss=1.0, gauss=True, prune_fraction=1.0)
    assert v.ok and abs(v.span_leak - math.sin(THETA / 2)) <= 1e-9, v.span_leak
    assert v.total_error == pytest.approx(v.op_norm_error + v.span_leak, abs=1e-15)
    # tol_err between op_norm_error and total_error, Gauss tolerance wide: only the span leak can reject
    mid = v.op_norm_error * (1 + 1e-6)
    assert v.op_norm_error <= mid < v.total_error
    v1 = EV.evaluate(_perturbed(), enc, _identity(), tol_err=mid, tol_gauss=1.0, gauss=True, prune_fraction=1.0)
    assert not v1.ok and v1.reason == "span_leak" and dict(v1.failing_inputs)["total_error"] == pytest.approx(v1.total_error)
    # just above total_error: ok; a failing Gauss check keeps priority over the span leak
    v2 = EV.evaluate(_perturbed(), enc, _identity(), tol_err=v.total_error * (1 + 1e-6), tol_gauss=1.0, gauss=True, prune_fraction=1.0)
    assert v2.ok and v2.reason == "ok"
    v3 = EV.evaluate(_perturbed(), enc, _identity(), tol_err=mid, tol_gauss=1e-3, gauss=True, prune_fraction=1.0)
    assert v3.reason == "gauss"


def test_state_subsets_never_exceed_the_full_span_leak():
    enc = _enc()
    full = EV.evaluate(_perturbed(), enc, _identity(), tol_err=1.0, tol_gauss=1.0, gauss=True, prune_fraction=1.0)
    allst = EV.evaluate(_perturbed(), enc, _identity(), tol_err=1.0, gauss=False, prune_fraction=1.0, states=np.arange(433))
    assert abs(allst.span_leak - full.span_leak) <= 1e-12
    sub = np.sort(np.random.default_rng(3).choice(433, size=40, replace=False))
    vs = EV.evaluate(_perturbed(), enc, _identity(), tol_err=1.0, gauss=False, prune_fraction=1.0, states=sub)
    assert vs.n_inputs == 40 and 0.0 < vs.span_leak <= full.span_leak + 1e-12


def test_span_leak_is_the_direct_residual_not_a_gram_difference():
    """The exact circuit: the direct residual is at rounding level (a W - A^dag A route would give ~6e-8 on the twelve-qubit
    step); the span leak of an exact circuit must stay far below 1e-12 even for an order-2 step."""
    enc = _enc()
    v = EV.evaluate(CS.build_step(ALPHA, BETA, 2, with_outer=True), enc, enc.target("step", ALPHA, BETA, 2), gauss=False)
    assert v.ok and v.span_leak <= 1e-13


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.0000001, float("nan"), float("inf")])
def test_prune_fraction_must_be_in_unit_interval(bad):
    with pytest.raises(ValueError, match="prune_fraction"):
        EV.evaluate(QuantumCircuit(16), _enc(), _identity(), prune_fraction=bad)


def test_prune_fraction_default_is_the_module_constant_and_sets_the_cap():
    from su2plaq.evaluate.sparse_sim import PRUNE_REL

    enc = _enc()
    qc = QuantumCircuit(16)
    for _ in range(250):
        qc.u(2 * 0.5 * PRUNE_REL, 0.0, 0.0, 0)        # each gate drops an amplitude below the pruning threshold (as locked M1-V1)
    ref = EV.evaluate(qc, enc, _identity(), tol_err=1e-10, gauss=False)
    assert ref.dropped_total > 0.0 and ref.reason == "pruning_bound"
    assert dict(ref.failing_inputs)["prune_cap"] == pytest.approx(EV.PRUNE_FRACTION * 1e-10, abs=1e-25)
    ratio = ref.dropped_total / 1e-10
    above = EV.evaluate(qc, enc, _identity(), tol_err=1e-10, gauss=False, prune_fraction=min(1.0, 1.5 * ratio))
    assert above.reason != "pruning_bound" and above.dropped_total == pytest.approx(ref.dropped_total)
    below = EV.evaluate(qc, enc, _identity(), tol_err=1e-10, gauss=False, prune_fraction=0.5 * ratio)
    assert below.reason == "pruning_bound" and dict(below.failing_inputs)["prune_cap"] == pytest.approx(0.5 * ratio * 1e-10, abs=1e-25)


def test_inner_target_dispatch():
    sn = _enc()
    for kind in ("UE", "UB", "step"):
        assert np.array_equal(EV.inner_target(sn, kind, ALPHA, BETA, 1), sn.inner_target(kind, ALPHA, BETA, 1))

    class Own:
        name = "own"

        def inner_target(self, kind, alpha, beta, order=1):
            return np.full((2, 2), order * alpha)

    assert np.array_equal(EV.inner_target(Own(), "UE", 0.5, 0.1, 2), np.full((2, 2), 1.0))

    class Nothing:
        name = "nothing"

    with pytest.raises(NotImplementedError, match="nothing"):
        EV.inner_target(Nothing(), "UE", ALPHA, BETA, 1)

    class Twelve:
        name = "twelve"

    W = EV.inner_target(Twelve(), "UE", ALPHA, BETA, 1)            # the built-in 625 x 625 operator
    assert W.shape == (625, 625) and np.allclose(np.abs(np.diag(W)), 1.0)


def test_local_basis_handles_rank_deficient_blocks():
    d = {}
    P = np.zeros((6, 3), dtype=complex)
    P[0, 0] = 1.0
    P[1, 1] = 1.0
    P[:, 2] = P[:, 0] + P[:, 1]                    # rank 2 of 3 columns
    B, R = EV._local_basis(d, 7, P)
    assert B.shape[1] == 2 and np.allclose(B @ R, P) and np.allclose(B.conj().T @ B, np.eye(2))
    assert EV._local_basis(d, 7, P)[0] is B                    # cached

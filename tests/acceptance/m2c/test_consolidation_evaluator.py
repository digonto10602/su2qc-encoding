"""M2c-E — evaluator changes of the consolidation (prompts/008 §5; METHODS §6 "span leak", §12).

E1-E3: the span leak S (output amplitude inside the code space but outside the physical span; audit 100 N3, audit 002 R1) is
computed exactly as an operator norm, `Verdict.span_leak` = ||S||_2, formed directly (S = Om - Psi A; never as a difference of
Gram matrices, which loses half the digits), and enters validity through
    total_error = op_norm_error + span_leak <= tol_err          (reason `span_leak`, tested after every older reason),
while the locked identity op_norm_error = block_error + dropped_total + leak_amplitude (prompts/004) is unchanged.
E4: `evaluate(..., prune_fraction=f)` (rishon merge note M6-3).  E5: an encoding registered with `gauss_in_loop=False` reports the
Gauss residual as NaN / "not_checked", never 0.0 (audit 301 A1).  E6: `inner_target` dispatches to the encoding.

Tolerances: E1 compares with an independent dense reference built in the test (256 x 256 `qiskit.quantum_info.Operator` of the
data register): |difference| <= dropped_total + 1e-12 (the engine's certified pruning bound plus float64 rounding of ~1000 gate
applications, each <= 2.3e-16 relative on numbers <= 1).  E2: span_leak <= 1e-12 on an exact circuit (direct formation gives
3.3e-15, planner prototype; the difference-of-Grams route gives 6.4e-8 and must fail).  Identities: 1e-15, as the locked M1-V1.
"""
from __future__ import annotations

import functools
import math

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from tests.acceptance._api import api

ALPHA, BETA = 0.37, 0.61


def _verdict_cls():
    V = api("su2plaq.evaluate.evaluator:Verdict")
    if "span_leak" not in V.__dataclass_fields__ or "total_error" not in V.__dataclass_fields__:
        pytest.fail("PENDING: evaluator.Verdict has no fields span_leak / total_error (prompts/008 step B2)", pytrace=False)
    return V


@functools.lru_cache(maxsize=None)
def _spinnet():
    return api("su2plaq.encodings.spinnet:SpinNet")()


@functools.lru_cache(maxsize=None)
def _twelve():
    return api("su2plaq.encodings.twelve:TwelveQubit")()


@functools.lru_cache(maxsize=None)
def _spinnet_ue_synth(eps: float):
    qc = api("su2plaq.circuits.spinnet:build_UE")(ALPHA, with_outer=True)
    synth, info = api("su2plaq.metrics.cliffordt:synthesize")(qc, eps, word_fn=api("su2plaq.compress.synth:gridsynth_word"))
    return synth, info


def _reference_leaks(qc, enc):
    """(||S||_2, ||X||_2) of a circuit that acts on the data register only, for a basis encoding (every physical state is one
    code d + 2^n_data o): dense unitary U_d of the data register; for the states of one outer pattern o the columns U_d[:, d_k];
    S = rows on valid data codes that are not physical together with o, X = rows on invalid data codes.  Independent of the
    project's simulator and evaluator (only `layout_of`, `inner_codes`, `physical_vectors` are read)."""
    from qiskit.quantum_info import Operator

    lay = enc.layout_of(qc)
    pos = {q: i for i, q in enumerate(lay.data)}
    sub = QuantumCircuit(len(lay.data))
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        if inst.operation.name == "barrier":
            continue
        assert all(q in pos for q in qs), "reference construction needs a circuit on the data register only"
        sub.append(inst.operation, [pos[q] for q in qs])
    Ud = Operator(sub).data
    ev = enc.physical_vectors()
    assert all(len(c) == 1 for c in ev.codes), "reference construction needs a basis encoding"
    codes = np.array([int(c[0]) for c in ev.codes])
    data, outer = codes & ((1 << ev.n_data) - 1), codes >> ev.n_data
    valid = np.zeros(1 << ev.n_data, dtype=bool)
    valid[np.asarray(enc.inner_codes(), dtype=np.int64)] = True
    s_max = x_max = 0.0
    for o in np.unique(outer):
        dk = data[outer == o]
        cols = Ud[:, dk]
        phys = np.zeros(1 << ev.n_data, dtype=bool)
        phys[dk] = True
        S = cols[valid & ~phys]
        X = cols[~valid]
        s_max = max(s_max, float(np.linalg.norm(S, 2)) if S.size else 0.0)
        x_max = max(x_max, float(np.linalg.norm(X, 2)) if X.size else 0.0)
    return s_max, x_max


def test_M2C_E1_span_leak_exact_against_dense_reference():
    """Spin-network U_E synthesised with pygridsynth at eps = 1e-6 and 1e-4: `span_leak` and `leak_amplitude` equal the dense
    reference; the span leak is the 3.15e-7 / 1.92e-5 of audit 100 N3 (non-zero: the case is not vacuous); total_error is the sum
    and stays inside the synthesised tolerance N_rot eps + 1e-9 (the verdict is still ok)."""
    _verdict_cls()
    enc = _spinnet()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    tols = api("su2plaq.evaluate.evaluator:synth_tolerances")
    V = enc.target("UE", ALPHA, BETA, 1)
    for eps, lo, hi in ((1e-6, 1e-7, 1e-6), (1e-4, 1e-5, 1e-4)):
        synth, info = _spinnet_ue_synth(eps)
        tol = tols(info["n_rot"], eps)
        v = evaluate(synth, enc, V, **tol, gauss=True, engine="sparse")
        s_ref, x_ref = _reference_leaks(synth, enc)
        assert lo < s_ref < hi, s_ref                                   # audit 100 N3: 3.15e-7 (1e-6), 1.92e-5 (1e-4)
        slack = v.dropped_total + 1e-12
        assert abs(v.span_leak - s_ref) <= slack, (eps, v.span_leak, s_ref)
        assert abs(v.leak_amplitude - x_ref) <= slack, (eps, v.leak_amplitude, x_ref)
        assert abs(v.total_error - (v.op_norm_error + v.span_leak)) <= 1e-15
        assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) <= 1e-15      # prompts/004, unchanged
        assert v.ok and v.certified and v.reason == "ok" and v.total_error <= tol["tol_err"], (eps, v.reason, v.total_error)
        assert v.extra["span_leak_max_state"] <= v.span_leak + 1e-15       # operator norm >= every single-state norm (audit 002 R1)


def test_M2C_E2_span_leak_zero_on_exact_circuits_and_trial_subset():
    """Exact general circuits: span_leak <= 1e-12 on the spin network (basis encoding) AND on the twelve-qubit encoding, whose
    physical states are superpositions over several outer patterns (the projection is not block-local there); the same in trial
    mode (64 seeded states).  An encoding whose physical span is the whole code space (fuzzy unit) has span_leak == 0.0 exactly."""
    _verdict_cls()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    for enc, qc in ((_spinnet(), api("su2plaq.circuits.spinnet:build_step")(ALPHA, BETA, 1, with_outer=True)),
                    (_twelve(), api("su2plaq.circuits.twelve:build_step")(ALPHA, BETA, 1, with_outer=True))):
        V = enc.target("step", ALPHA, BETA, 1)
        v = evaluate(qc, enc, V, gauss=True)
        assert v.ok and v.certified and v.op_norm_error <= 1e-10 and 0.0 <= v.span_leak <= 1e-12, (enc.name, v.reason, v.span_leak)
        assert abs(v.total_error - (v.op_norm_error + v.span_leak)) <= 1e-15
        assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) <= 1e-15
        states = np.sort(np.random.default_rng(0).choice(V.shape[0], size=64, replace=False))
        vt = evaluate(qc, enc, V, gauss=False, engine="sparse", states=states)
        assert vt.ok and 0.0 <= vt.span_leak <= 1e-12 and vt.n_inputs == 64
    fz = api("su2plaq.compress.spec:get_encoding")("fuzzy_link")
    spec = api("su2plaq.compress.spec:default_spec")("fuzzy_link", "UE")
    vf = evaluate(api("su2plaq.compress.baselines:general_circuit")(spec), fz, api("su2plaq.compress.oracle:target")(spec), gauss=False)
    assert vf.ok and vf.span_leak == 0.0 and vf.total_error == vf.op_norm_error


def test_M2C_E3_span_leak_decides_validity():
    """The synthesised spin-network U_E judged with a hand-set tolerance between op_norm_error and total_error and a Gauss
    tolerance above its Gauss residual: the pre-consolidation rule accepted it (every older check passes), the consolidated
    rule rejects it with reason `span_leak`; with tol_err just above total_error it is ok.  Older reasons keep priority."""
    _verdict_cls()
    enc = _spinnet()
    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    V = enc.target("UE", ALPHA, BETA, 1)
    synth, _ = _spinnet_ue_synth(1e-6)
    v0 = evaluate(synth, enc, V, tol_err=1.0, tol_gauss=1.0, gauss=True, engine="sparse")
    assert v0.ok and v0.span_leak > 1e-7 and v0.gauss_residual > 0.0
    tg = 2.0 * v0.gauss_residual
    mid = v0.op_norm_error + 0.5 * v0.span_leak
    v1 = evaluate(synth, enc, V, tol_err=mid, tol_gauss=tg, gauss=True, engine="sparse")
    assert v1.op_norm_error <= mid < v1.total_error and v1.gauss_residual <= tg and v1.leak_amplitude <= mid
    assert not v1.ok and v1.reason == "span_leak", v1.reason
    v2 = evaluate(synth, enc, V, tol_err=v0.total_error * (1 + 1e-6), tol_gauss=tg, gauss=True, engine="sparse")
    assert v2.ok and v2.reason == "ok"
    v3 = evaluate(synth, enc, V, tol_err=mid, tol_gauss=0.5 * v0.gauss_residual, gauss=True, engine="sparse")
    assert not v3.ok and v3.reason == "gauss"                  # an older reason is reported first


def _drop_circuit(k: int, delta: float) -> QuantumCircuit:
    """The construction of the locked M1-V1 (tests/acceptance/m1/test_evaluator_prune.py): k gates u(2 delta, 0, 0) on d[0], each
    dropped by the sparse engine; certified bound dropped_total = 25 k sin(delta); the circuit is the identity to rounding."""
    d = QuantumRegister(12, "d")
    qc = QuantumCircuit(d)
    for _ in range(k):
        qc.u(2 * delta, 0.0, 0.0, d[0])
    return qc


def test_M2C_E4_prune_fraction_keyword():
    """`evaluate(..., prune_fraction=f)`: `pruning_bound` iff dropped_total > f * tol_err; None = PRUNE_FRACTION (1e-2, prompts/005).
    Circuit: dropped_total = 3.125e-11 at tol_err = 1e-10 -> rejected at the default (cap 1e-12) and at f = 0.1 (cap 1e-11, the
    rishon value of prompts/204), accepted at f = 0.5 (cap 5e-11; block error + dropped_total <= 1e-10)."""
    import inspect

    evaluate = api("su2plaq.evaluate.evaluator:evaluate")
    if "prune_fraction" not in inspect.signature(evaluate).parameters:
        pytest.fail("PENDING: evaluator.evaluate has no keyword prune_fraction (prompts/008 step B2)", pytrace=False)
    assert api("su2plaq.evaluate.evaluator:PRUNE_FRACTION") == 1e-2
    prune_rel = api("su2plaq.evaluate.sparse_sim:PRUNE_REL")
    k, delta = 250, 0.5 * prune_rel
    expected = 25.0 * k * math.sin(delta)
    assert 1e-11 < expected < 5e-11, "construction must sit between the caps tested (PRUNE_REL changed?)"
    qc, enc, I = _drop_circuit(k, delta), _twelve(), np.eye(433, dtype=complex)
    for f, ok in ((None, False), (1e-2, False), (0.1, False), (0.5, True)):
        v = evaluate(qc, enc, I, tol_err=1e-10, gauss=True, prune_fraction=f)
        assert abs(v.dropped_total - expected) <= 1e-6 * expected
        assert v.ok is ok and v.reason == ("ok" if ok else "pruning_bound"), (f, v.reason)
        if not ok:
            cap = dict(v.failing_inputs)["prune_cap"]
            assert abs(cap - (1e-2 if f is None else f) * 1e-10) <= 1e-25
    with pytest.raises(ValueError):
        evaluate(qc, enc, I, prune_fraction=-0.1)


def test_M2C_E5_gauss_not_checked_is_reported_as_such():
    """Audit 301 A1: for the fuzzy units (registered with gauss_in_loop = False) the loop's verdict has gauss_residual = NaN and
    extra['gauss'] == 'not_checked' -- never a measured-looking 0.0; for twelve the Gauss residual is measured (<= 1e-10)."""
    api("su2plaq.encodings.registry")
    E = api("su2plaq.compress.evaluate")
    BL = api("su2plaq.compress.baselines")
    S = api("su2plaq.compress.spec")
    for name, kind in (("fuzzy_link", "UE"), ("fuzzy_ub", "UB")):
        spec = S.default_spec(name, kind)
        r = E.evaluate_circuit(BL.general_circuit(spec), spec, mode="trial")
        assert r.valid and r.reason == "ok" and r.verdict.certified, (name, r.reason, r.message)
        assert math.isnan(r.verdict.gauss_residual) and r.verdict.extra.get("gauss") == "not_checked", name
        assert r.verdict.span_leak == 0.0
    tw = S.default_spec("twelve", "step")
    rt = E.evaluate_circuit(BL.general_circuit(tw), tw, mode="trial")
    assert rt.valid and 0.0 <= rt.verdict.gauss_residual <= 1e-10 and rt.verdict.extra.get("gauss") == "checked"


def test_M2C_E6_inner_target_dispatch():
    """`evaluator.inner_target(enc, ...)` returns the encoding's own inner operator when it defines one (spinnet merge note 2);
    twelve keeps the built-in 625 x 625 operator; an encoding without one raises NotImplementedError."""
    api("su2plaq.encodings.registry")
    inner_target = api("su2plaq.evaluate.evaluator:inner_target")
    sn = _spinnet()
    for kind in ("UE", "UB", "step"):
        assert np.array_equal(inner_target(sn, kind, ALPHA, BETA, 1), sn.inner_target(kind, ALPHA, BETA, 1))
    W = inner_target(_twelve(), "step", ALPHA, BETA, 1)
    assert W.shape == (625, 625) and np.abs(W.conj().T @ W - np.eye(625)).max() <= 1e-10

    class _NoInner:
        name = "nothing"

    with pytest.raises(NotImplementedError):
        inner_target(_NoInner(), "UE", ALPHA, BETA, 1)

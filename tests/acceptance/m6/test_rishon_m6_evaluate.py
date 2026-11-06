"""M6-E1..E4 — the rishon program/circuit evaluator of the compression loop (prompts/203 §2, §3.1 `rishon.compress.evaluate`;
METHODS-rishon R10).  Validity = inner-block certification on the 1296 codes + sampled Gauss + prune cap (prompts/003-005,
unchanged); the sensitivity cases are discrete separations as M0-E3 / M2; metrics are exact counts; the T band is METHODS §7."""
import functools
import json
import pathlib
import time

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import CircuitInstruction

from tests.acceptance._api import api, ross_selinger_band

ENC = "rishon"


@functools.lru_cache(maxsize=None)
def _spec(kind="step"):
    return api("su2plaq.rishon.compress.spec:rishon_spec")(kind)


@functools.lru_cache(maxsize=None)
def _general(kind="step"):
    BL = api("su2plaq.rishon.compress.baselines")
    return BL.general_circuit(_spec(kind)), pathlib.Path(BL.general_program_path(_spec(kind)))


def _perturb_first_rotation(qc: QuantumCircuit, delta: float) -> QuantumCircuit:
    """Copy with the first rotation angle shifted by delta (instruction rebuilt: prompts/006 §12)."""
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name in ("rz", "p", "crz", "crx", "cp") and inst.operation.params:
            op = inst.operation.copy()
            old = float(op.params[0])
            op.params = [old + delta]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            assert abs(float(out.data[i].operation.params[0]) - (old + delta)) <= 1e-15 and abs(float(qc.data[i].operation.params[0]) - old) <= 1e-15
            return out
    raise AssertionError("no rotation found")


def _with_extra(qc: QuantumCircuit, fn) -> QuantumCircuit:
    out = qc.copy()
    fn(out)
    return out


def test_M6_E1_evaluator_sensitivity():
    """On the general U_E circuit (16 data + 32 outer qubits, 12 gates; seconds): accepted as is and with a global phase;
    rejected for a disallowed gate, a dirty ancilla, a 1e-6 angle error (first order), a missing gadget, an outer write,
    an outer read, too many qubits, a skeleton change at an alternate pair, and the wrong task kind.  The verdict is a
    laptop `Verdict` (so archive / report / cache work unchanged) with method 'rishon_inner_block'."""
    spec = _spec("UE")
    ev = api("su2plaq.rishon.compress.evaluate")
    Verdict = api("su2plaq.evaluate.evaluator:Verdict")
    qc, _ = _general("UE")
    assert qc.num_qubits == 48 and [r.name for r in qc.qregs][:2] == ["d", "o"]
    r = ev.evaluate_circuit(qc, spec, mode="trial")
    assert r.valid and r.reason == "ok" and isinstance(r.verdict, Verdict) and r.verdict.certified and r.mode == "trial"
    assert r.verdict.method == "rishon_inner_block" and r.verdict.op_norm_error <= 1e-10 and r.verdict.outer_bits_read == 0
    assert r.metrics is not None and r.metrics["cx"] == 8 and r.metrics["n_rot"] == 4 and r.metrics["qubits"] == 48
    ph = qc.copy(); ph.global_phase += 0.3
    assert ev.evaluate_circuit(ph, spec, mode="trial").valid
    # disallowed gate (unitary)
    r = ev.evaluate_circuit(_with_extra(qc, lambda c: c.unitary(np.eye(2), [0])), spec, mode="trial")
    assert not r.valid and r.reason != "ok"
    # dirty ancilla
    out = qc.copy(); a = QuantumRegister(1, "anc_dirty"); out.add_register(a); out.cx(0, a[0])
    r = ev.evaluate_circuit(out, spec, mode="trial")
    assert not r.valid and ("ancilla" in r.reason or "leak" in r.reason)
    # angle error 1e-6 on the first rotation: first-order detection (prompts/203 §6)
    r = ev.evaluate_circuit(_perturb_first_rotation(qc, 1e-6), spec, mode="trial")
    assert not r.valid and r.reason == "error" and r.verdict is not None and r.verdict.op_norm_error >= 1e-7
    # missing gadget (last 3 gates dropped): a wrong operator
    part = qc.copy(); del part.data[-3:]
    r = ev.evaluate_circuit(part, spec, mode="trial")
    assert not r.valid and r.verdict.op_norm_error > 0.1
    # outer write / outer read
    r = ev.evaluate_circuit(_with_extra(qc, lambda c: c.x(16)), spec, mode="trial")
    assert not r.valid and r.reason == "writes_outer"
    r = ev.evaluate_circuit(_with_extra(qc, lambda c: c.cz(16, 0)), spec, mode="trial")
    assert not r.valid and r.reason == "outer_read_unsupported"
    # too many qubits (cap 80)
    big = QuantumCircuit(QuantumRegister(16, "d"), QuantumRegister(32, "o"), QuantumRegister(33, "anc"))
    big.compose(qc, qubits=list(range(48)), inplace=True)
    r = ev.evaluate_circuit(big, spec, mode="trial")
    assert not r.valid and r.reason == "max_qubits"
    # skeleton must be identical at the alternate pairs (full mode)
    BL = api("su2plaq.rishon.compress.baselines")
    alts = [BL.general_circuit(spec.with_angles(a, b)) for a, b in spec.alt_angles]
    alts[1] = _with_extra(alts[1], lambda c: c.x(0))
    r = ev.evaluate_circuit(qc, spec, mode="full", alt_circuits=alts)
    assert not r.valid and r.reason == "skeleton" and not r.skeleton_equal
    # wrong task kind: U_E alone against the step target
    r = ev.evaluate_circuit(qc, _spec("step"), mode="trial")
    assert not r.valid and r.verdict.op_norm_error > 0.1
    st = ev.trial_states(spec)
    assert len(st) == 64 and len(set(st.tolist())) == 64 and list(st) == sorted(st) and max(st) < 1296


def test_M6_E2_metrics_match_qiskit_and_T_band():
    """metrics() of the general step circuit (48 + 10 qubits) equals an independent level-0 lowering count; key / cell as
    prompts/002 §2.10; the T estimate formula; pygridsynth T in the Ross-Selinger band and deterministic."""
    spec = _spec("step")
    qc, _ = _general("step")
    M = api("su2plaq.compress.metrics")
    S = api("su2plaq.compress.synth")
    lower = api("su2plaq.metrics.logical:lower")
    m = M.metrics(qc, spec, measured=False)
    low = lower(qc)
    ops = low.count_ops()
    assert m["cx"] == ops.get("cx", 0) and m["depth"] == low.depth() and m["qubits"] == qc.num_qubits == 48 + 10
    odd_pi4 = sum(1 for i in low.data if i.operation.name == "rz" and abs(float(i.operation.params[0]) / (np.pi / 4) - round(float(i.operation.params[0]) / (np.pi / 4))) < 1e-9
                  and round(float(i.operation.params[0]) / (np.pi / 4)) % 2 == 1)
    assert m["t_fixed"] == ops.get("t", 0) + ops.get("tdg", 0) + odd_pi4
    # the M5 general step (Report 5 §3.2, reports/tests/204-205, recounted by the tester from the stored QPY): the ladder
    # parameter and the Casimir hardening of step 6.0 must not change the default circuit
    assert (m["cx"], m["t_fixed"], m["n_rot"]) == (10102, 10218, 166)
    for eps in (1e-6, 1e-10):
        assert abs(m["t_estimate"][eps] - (m["t_fixed"] + m["n_rot"] * 3 * np.log2(1 / eps))) <= 1e-6
    key, cell = M.key(m), M.cell(m, 8)
    assert len(key) == 4 and key[0] == m["cx"] and key[3] == 58 and cell[0] == int(np.floor(8 * np.log2(m["cx"] + 1)))
    for eps in (1e-4, 1e-6, 1e-8):
        lo, hi = ross_selinger_band(eps)
        for th in (2 * 0.61, 4 * 0.61, 8 * np.sqrt(2) * 0.61, -0.75 * 0.37):
            T = S.gridsynth_T(th, eps)
            assert lo <= T <= hi
    assert S.gridsynth_T(2 * 0.61, 1e-6) == S.gridsynth_T(2 * 0.61, 1e-6) == api("su2plaq.metrics.cliffordt:pygridsynth_tcount")(2 * 0.61, 1e-6)


def test_M6_E3_full_mode_ue_program_and_cache(tmp_path):
    """evaluate_program on the generated U_E seed program: full mode valid with two alternate verdicts and an identical
    skeleton; the result cache under a temporary root is keyed by the rishon code hash and replays the result."""
    spec = _spec("UE")
    ev = api("su2plaq.rishon.compress.evaluate")
    _, path = _general("UE")
    mod = ev.load_program(str(path)) if hasattr(ev, "load_program") else api("su2plaq.compress.evaluate:load_program")(str(path))
    s1 = api("su2plaq.compress.evaluate:skeleton")(mod.build(spec).circuit())
    s2 = api("su2plaq.compress.evaluate:skeleton")(mod.build(spec.with_angles(*spec.alt_angles[0])).circuit())
    assert s1 == s2 and len(s1) == 12
    r = ev.evaluate_program(str(path), spec, mode="full")
    assert r.valid and r.reason == "ok" and r.skeleton_equal and len(r.verdicts_alt) == 2 and all(v.ok and v.certified for v in r.verdicts_alt)
    assert r.verdict.op_norm_error <= 1e-10 and r.verdict.dropped_total <= 1e-12 and r.verdict.gauss_residual <= 1e-10
    assert r.metrics["measured"] is True and r.metrics["t_eps"] >= r.metrics["t_fixed"] and len(r.program_sha256) == 64
    t0 = time.time()
    r1 = ev.evaluate_program(str(path), spec, mode="full", cache=True, root=tmp_path)
    h = api("su2plaq.rishon.compress:code_hash")()
    cdir = tmp_path / "compress" / "cache" / h
    assert cdir.is_dir() and any(cdir.glob("*.json")) and len(h) == 64
    r2 = ev.evaluate_program(str(path), spec, mode="full", cache=True, root=tmp_path)
    assert r2.valid and r2.program_sha256 == r1.program_sha256 and tuple(api("su2plaq.compress.metrics:key")(r2.metrics)) == tuple(api("su2plaq.compress.metrics:key")(r1.metrics))
    assert time.time() - t0 <= 300


@pytest.mark.slow
def test_M6_E4_full_mode_general_step():
    """The general step program (round-0 seed) is valid in full mode: 1296 codes x 3 angle pairs, Gauss sample, measured
    T; its Clifford+T synthesis at eps = 1e-6 is re-verified within N_rot eps + 1e-9 (prompts/003)."""
    spec = _spec("step")
    ev = api("su2plaq.rishon.compress.evaluate")
    qc, path = _general("step")
    r = ev.evaluate_program(str(path), spec, mode="full")
    assert r.valid and r.skeleton_equal and len(r.verdicts_alt) == 2, (r.reason, r.message)
    assert r.verdict.op_norm_error <= 1e-10 and r.verdict.dropped_total <= 1e-12 and r.verdict.gauss_residual <= 1e-10
    m = r.metrics
    assert m["measured"] and m["t_eps"] == m["t_measured"][1e-6] and m["qubits"] == 58
    sv = ev.verify_synthesised(qc, spec)
    assert sv["ok"] and sv["verdict"].op_norm_error <= sv["tolerances"]["tol_err"] and sv["t_total"] == m["t_eps"]

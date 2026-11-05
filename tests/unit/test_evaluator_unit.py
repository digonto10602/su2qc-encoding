"""Unit tests for su2plaq.evaluate.evaluator, the twelve-qubit codec and the sparse-simulator mcx guard."""
import functools

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Operator

from su2plaq.encodings.base import Layout
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate import evaluator as ev
from su2plaq.evaluate import sparse_sim as ss


@functools.lru_cache(maxsize=None)
def _enc():
    return TwelveQubit()


def _circ(n_anc=0, with_outer=False):
    regs = [QuantumRegister(12, "d")]
    if with_outer:
        regs.append(QuantumRegister(16, "o"))
    if n_anc:
        regs.append(QuantumRegister(n_anc, "a"))
    qc = QuantumCircuit(*regs)
    return qc, {r.name: r for r in regs}


def test_codec_roundtrip_decode_state_matches_route_a():
    enc = _enc()
    eb = enc.physical_vectors()
    for k in range(0, 433, 37):
        keys, amps = enc.decode_state(eb.codes[k], eb.amps[k])
        o1, o2 = np.argsort(keys), np.argsort(enc.basis.keys[k])
        assert np.array_equal(keys[o1], enc.basis.keys[k][o2])
        assert np.abs(amps[o1] - enc.basis.amps[k][o2]).max() < 1e-14
    assert len(enc.inner_codes()) == 625 and enc.decode(0b01 << 12) is None
    assert enc.layout_of(_circ(2, True)[0]) == Layout(list(range(12)), list(range(12, 28)), [28, 29])


def test_classify_outer_gates_and_writes():
    qc = QuantumCircuit(6)
    qc.cz(3, 0)
    qc.cx(4, 1)
    qc.p(0.3, 3)
    lay = Layout([0, 1, 2], [3, 4], [5])
    assert ev.classify_outer_gates(qc, lay) == {3, 4}
    bad = QuantumCircuit(6)
    bad.cx(0, 3)
    with pytest.raises(ev.OuterWriteError):
        ev.classify_outer_gates(bad, lay)
    bad2 = QuantumCircuit(6)
    bad2.h(4)
    with pytest.raises(ev.OuterWriteError):
        ev.classify_outer_gates(bad2, lay)
    ok = QuantumCircuit(6)  # a 2-qubit unitary diagonal on the outer qubit is a read, not a write
    ok.unitary(np.kron(np.diag([1, np.exp(0.4j)]), np.array([[0, 1], [1, 0]])), [0, 3])
    assert ev.classify_outer_gates(ok, lay) == {3}


def test_specialise_equals_operator_columns():
    qc = QuantumCircuit(6, global_phase=0.2)
    qc.h(0)
    qc.cz(3, 0)
    qc.cx(4, 1)
    qc.ccx(3, 4, 2)
    qc.cp(0.4, 3, 1)
    qc.rz(0.7, 4)
    qc.t(3)
    qc.ccz(3, 4, 5)
    qc.cx(3, 5)
    qc.unitary(np.kron(np.diag([1, np.exp(0.4j)]), np.array([[0, 1], [1, 0]])), [2, 4])
    U = Operator(qc).data
    for pat in range(4):
        Us = Operator(ev.specialise(qc, {3, 4}, pat)).data
        cols = [i for i in range(64) if ((i >> 3) & 1) == (pat & 1) and ((i >> 4) & 1) == ((pat >> 1) & 1)]
        assert np.abs(U[:, cols] - Us[:, cols]).max() < 1e-13


def test_native_mcx_inside_custom_gate_is_rejected():
    inner = QuantumCircuit(5)
    inner.mcx([0, 1, 2], 3)
    outer = QuantumCircuit(7)  # idle qubits
    outer.append(inner.to_gate(), [0, 1, 2, 3, 4])
    with pytest.raises(ValueError, match="mcx"):
        ss.run_batch(outer, np.array([0], dtype=np.int64))
    # nested twice
    mid = QuantumCircuit(5)
    mid.append(inner.to_gate(), range(5))
    top = QuantumCircuit(7)
    top.append(mid.to_gate(), range(5))
    with pytest.raises(ValueError, match="mcx"):
        ss.run_batch(top, np.array([0], dtype=np.int64))


def test_identity_and_z_verdicts_and_budget_fields():
    enc = _enc()
    I = np.eye(433, dtype=complex)
    qc, r = _circ()
    v = ev.evaluate(qc, enc, I, gauss=False)
    assert v.ok and v.engine == "sparse" and v.dropped_total == 0.0 and v.engine_accuracy == 0.0 and v.certified
    qc.z(r["d"][2])
    v = ev.evaluate(qc, enc, I, gauss=False)
    assert not v.ok and v.reason == "error" and v.failing_inputs and v.op_norm_error >= 0.5


def test_disallowed_gate_reason():
    qc, r = _circ(5)
    qc.mcx([0, 1, 2], 12)
    v = ev.evaluate(qc, _enc(), np.eye(433, dtype=complex), gauss=False)
    assert not v.ok and v.reason == "disallowed_gate"


def test_pruning_bound_reason(monkeypatch):
    monkeypatch.setattr(ss, "PRUNE_REL", 1.5)  # force dropping every amplitude
    qc, r = _circ(1)
    qc.h(r["a"][0])
    qc.h(r["d"][0])
    v = ev.evaluate(qc, _enc(), np.eye(433, dtype=complex), gauss=False)
    assert not v.ok and v.reason == "pruning_bound" and v.dropped_total > 1e-12


def test_aer_mps_verdict_is_flagged_uncertified():
    enc = _enc()
    alpha = 0.37
    qc, r = _circ()
    for q in (2, 5, 8, 11):
        qc.p(-0.75 * alpha, r["d"][q])
    v = ev.evaluate(qc, enc, enc.target("UE", alpha, 0.0), gauss=False, engine="aer_mps")
    assert v.ok and v.engine == "aer_mps" and v.engine_accuracy >= 1e-10 and not v.certified


def test_inner_target_realises_physical_target():
    enc = _enc()
    d = ev._phys_data(enc)
    for kind, kw in (("UE", dict(alpha=0.37, beta=0.0)), ("UB", dict(alpha=0.0, beta=0.61))):
        Vin = ev.inner_target(enc, kind, **kw)
        A = np.zeros((433, 433), complex)
        for ks, P in zip(d["ks"], d["Psi"]):
            A[np.ix_(ks, ks)] += P.conj().T @ Vin @ P
        assert np.abs(A - enc.target(kind, **kw)).max() < 1e-12


# ---------------------------------------------------------------- register orders (layout mapping must not assume d, o, a)
@pytest.mark.parametrize("order", [("d", "a", "o"), ("o", "d"), ("a", "d", "o"), ("d", "o", "a")])
def test_register_order_does_not_change_verdicts(order):
    enc = _enc()
    sizes = {"d": 12, "o": 16, "a": 2}
    regs = {n: QuantumRegister(sizes[n], n) for n in order}
    theta, alpha = 0.3, 0.37
    labels = enc.basis.labels
    j_o0 = np.array([lab[0][4] for lab in labels])
    j_b = np.array([lab[0][0] for lab in labels])

    def circ():
        return QuantumCircuit(*[regs[n] for n in order])

    lay = enc.layout_of(circ())
    assert lay.data == [circ().find_bit(q).index for q in regs["d"]]
    assert lay.outer == [circ().find_bit(q).index for q in regs["o"]]
    # (1) p on the j-qubit of outer link 0 (o[1]) reads the outer register: phase e^{i theta} when j(o0) = 1/2
    qc = circ()
    qc.p(theta, regs["o"][1])
    good = np.diag(np.exp(1j * theta * (j_o0 == 0.5)))
    v = ev.evaluate(qc, enc, good, gauss=False)
    assert v.ok and v.outer_bits_read == 1 and v.method == "physical", (order, v)
    v = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False)
    assert not v.ok and v.reason == "error" and v.op_norm_error > 0.1
    # (2) p on the j-qubit of the data link b implements exp(-i alpha j(j+1)) on that link (outer-blind)
    qc = circ()
    qc.p(-0.75 * alpha, regs["d"][2])
    Vb = np.diag(np.exp(-1j * alpha * j_b * (j_b + 1)))
    v = ev.evaluate(qc, enc, Vb, gauss=False)
    assert v.ok and v.outer_bits_read == 0, (order, v)
    # (3) a gate writing the outer register is rejected wherever the register sits
    qc = circ()
    qc.cx(regs["d"][2], regs["o"][1])
    assert ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False).reason == "writes_outer"
    # (4) a dirty ancilla is reported with a non-empty failing list
    if "a" in regs:
        qc = circ()
        qc.x(regs["a"][0])
        v = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False)
        assert not v.ok and v.reason == "dirty_ancilla" and v.failing_inputs and v.dirty_ancilla >= 1 - 1e-12


def test_layout_of_errors():
    enc = _enc()
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(11, "d")))
    with pytest.raises(ValueError):
        enc.layout_of(QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(15, "o")))


def test_aer_mps_dirty_ancilla_labelled_like_sparse():
    enc = _enc()
    qc, r = _circ(1)
    qc.x(r["a"][0])
    vs = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False, engine="sparse")
    vm = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False, engine="aer_mps")
    assert vs.reason == vm.reason == "dirty_ancilla" and vm.failing_inputs
    # aer_mps: dirty_ancilla is the per-outer-block weight bound W_o (sum over the <= ~17 inner inputs in the support of a block): 1 <= W_o <= 17
    assert 1 - 1e-8 <= vm.dirty_ancilla <= 17 + 1e-8 and 1 - 1e-8 <= vm.leak_amplitude <= 5 + 1e-8 and vs.leak_amplitude > 1 - 1e-8
    # invalid data code only (no ancilla): X on q_m' of link b maps code 000 to 001 (invalid): reason 'leak'
    qc, r = _circ()
    qc.x(r["d"][0])
    vs = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False, engine="sparse")
    vm = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False, engine="aer_mps")
    assert vs.dirty_ancilla == 0.0 and vm.dirty_ancilla < 1e-8
    assert vs.reason == "leak" == vm.reason


# ---------------------------------------------------------------- prompts/003 §4: tolerances and certification
def test_synth_tolerances_formula():
    t = ev.synth_tolerances(14, 1e-6)
    assert t == {"tol_err": 14e-6 + 1e-9, "tol_gauss": 14e-6 + 1e-9}  # prompts/004: no tol_leak
    with pytest.raises(TypeError):
        ev.evaluate(QuantumCircuit(12), _enc(), np.eye(433, dtype=complex), tol_leak=1e-12)


def test_tolerances_recorded_and_gauss_tolerance_effective():
    enc = _enc()
    I = np.eye(433, dtype=complex)
    qc, r = _circ()
    qc.swap(r["d"][0], r["d"][1])  # code-preserving, gauge-violating: Gauss residual ~ O(1), error O(1)
    v = ev.evaluate(qc, enc, I)
    assert v.tolerances == {"tol_err": 1e-10, "tol_gauss": ev.TOL_GAUSS}
    # a huge Gauss tolerance moves the failure to the error check, a tiny error budget stays an error
    v2 = ev.evaluate(qc, enc, I, tol_gauss=10.0)
    assert v2.tolerances["tol_gauss"] == 10.0 and v2.reason == "error"
    qc, r = _circ()
    qc.p(1e-4, r["d"][2])  # small deviation from the identity target
    v3 = ev.evaluate(qc, enc, I, gauss=True, **ev.synth_tolerances(1, 1e-2))
    assert v3.ok and v3.tolerances["tol_err"] == 1e-2 + 1e-9
    # Gauss failure uses the effective tolerance in failing_inputs
    qc, r = _circ()
    qc.swap(r["d"][0], r["d"][1])
    v4 = ev.evaluate(qc, enc, I, tol_err=10.0)
    assert v4.reason == "gauss" and v4.failing_inputs and all(x[1] > ev.TOL_GAUSS for x in v4.failing_inputs)
    # early exits fill tolerances too
    qc, r = _circ(0, True)
    qc.cx(r["d"][2], r["o"][1])
    v5 = ev.evaluate(qc, enc, I, tol_gauss=1e-6)
    assert v5.reason == "writes_outer" and v5.tolerances["tol_gauss"] == 1e-6


def test_certified_follows_engine_accuracy_against_tolerances():
    enc = _enc()
    alpha = 0.37
    V = enc.target("UE", alpha, 0.0)
    qc, r = _circ()
    for q in (2, 5, 8, 11):
        qc.p(-0.75 * alpha, r["d"][q])
    # exact-angle tolerances: MPS (2e-10) is not certified; sparse is
    assert not ev.evaluate(qc, enc, V, engine="aer_mps").certified
    assert ev.evaluate(qc, enc, V, engine="sparse").certified
    # synthesised-circuit budget (prompts/004: certified = engine_accuracy <= min(tol_err, tol_gauss)): both >= 1e-9, certified
    vs = ev.evaluate(qc, enc, V, engine="aer_mps", **ev.synth_tolerances(4, 1e-6))
    assert vs.ok and vs.certified and vs.engine_accuracy == ev.MPS_ACCURACY
    assert ev.evaluate(qc, enc, V, engine="aer_mps", tol_err=1e-8, tol_gauss=1e-8).certified
    # with gauss=False the Gauss tolerance does not enter the minimum
    assert ev.evaluate(qc, enc, V, engine="aer_mps", gauss=False, tol_err=1e-8, tol_gauss=1e-12).certified
    assert not ev.evaluate(qc, enc, V, engine="aer_mps", gauss=True, tol_err=1e-8, tol_gauss=1e-12).certified


# ---------------------------------------------------------------- audit 001 notes N2, N3, N4, N7, N8
def test_inner_span_error_never_replaces_physical_error():
    """A target that depends on the outer spins: the verdict error is max(inner_span, physical), i.e. >= physical."""
    from su2plaq.exact.operators import h_electric_outer

    enc = _enc()
    V = np.diag(np.exp(-1j * 1.0 * h_electric_outer(enc.basis)))
    qc, _ = _circ()
    v = ev.evaluate(qc, enc, V, gauss=False)
    assert v.method == "inner_span" and not v.ok
    phys, inner = v.extra["op_norm_error_physical"], v.extra["op_norm_error_inner_span"]
    assert phys > 0.5 and v.op_norm_error >= phys - 1e-12 and v.op_norm_error >= inner - 1e-12
    assert abs(v.op_norm_error - max(phys, inner)) < 1e-12


def test_aer_mps_leak_bound_is_sqrt_of_block_weight_and_consistent():
    enc = _enc()
    qc, r = _circ(1)
    qc.x(r["a"][0])
    v = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False, engine="aer_mps")
    assert v.reason == "dirty_ancilla" and v.max_leak <= v.leak_amplitude ** 2 + 1e-30
    assert abs(v.leak_amplitude - np.sqrt(v.max_leak)) < 1e-12
    assert all(isinstance(f[0], str) and f[0].startswith("inner_code_index") for f in v.failing_inputs) and len(v.failing_inputs) == 10
    assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) < 1e-15


def test_bad_layout_has_its_own_reason():
    enc = _enc()
    qc = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(15, "o"))
    v = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False)
    assert not v.ok and v.reason == "bad_layout" and v.failing_inputs and v.tolerances
    v = ev.evaluate(QuantumCircuit(QuantumRegister(11, "d")), enc, np.eye(433, dtype=complex), gauss=False)
    assert v.reason == "bad_layout"


def test_verdict_extra_is_persisted():
    from su2plaq.results.store import verdict_to_dict

    enc = _enc()
    qc, _ = _circ()
    v = ev.evaluate(qc, enc, np.eye(433, dtype=complex), gauss=False)
    d = verdict_to_dict(v)
    assert d["extra"]["max_span_leak"] == v.extra["max_span_leak"] and "op_norm_error_physical" in d["extra"]
    import json

    json.dumps(d)


def test_idle_qubits_are_not_assumed_clean_by_the_translation():
    """Qiskit's transpile uses idle qubits as clean ancillas by default (MCXGate(4) came out wrong by 1.0)."""
    from qiskit import transpile
    from qiskit.circuit.library import C3SXGate, MCXGate

    qc = QuantumCircuit(8)
    qc.append(MCXGate(4), [0, 1, 2, 3, 4])
    default = transpile(qc, basis_gates=["x", "h", "t", "tdg", "cx"], optimization_level=0)
    safe = transpile(qc, basis_gates=["x", "h", "t", "tdg", "cx"], optimization_level=0, qubits_initially_zero=False)
    U = Operator(qc).data
    assert np.abs(Operator(safe).data - U).max() < 1e-12
    assert np.abs(Operator(default).data - U).max() > 0.5  # documents the default-behaviour hazard
    # the allowed multi-controlled gates, with 3 idle qubits, through the simulator translation and the logical lowering
    from su2plaq.metrics.logical import lower

    allowed = QuantumCircuit(8)
    allowed.mcp(0.37, [0, 1, 2], 3)
    allowed.append(C3SXGate(), [4, 5, 6, 3])
    allowed.mcrx(0.5, [0, 1, 2], 7)
    Uf = Operator(allowed).data
    assert np.abs(_dense_cols(allowed) - Uf).max() < 1e-12
    Ul = Operator(lower(allowed)).data
    ov = np.trace(Ul.conj().T @ Uf)
    assert np.abs(Uf - ov / abs(ov) * Ul).max() < 1e-12


def _dense_cols(qc):
    b = ss.run_batch(qc, np.arange(2 ** qc.num_qubits, dtype=np.int64))
    out = np.zeros((2 ** qc.num_qubits,) * 2, complex)
    np.add.at(out, (b.keys, b.cols), b.amps)
    return out


# ---------------------------------------------------------------- prompts/004: leak as an amplitude
def test_sparse_leak_amplitude_is_exact_and_combined_error_adds_up():
    enc = _enc()
    I = np.eye(433, dtype=complex)
    th = 1e-3
    qc, r = _circ(1)
    qc.cry(th, r["d"][2], r["a"][0])
    v = ev.evaluate(qc, enc, I, gauss=False)
    assert abs(v.leak_amplitude - np.sin(th / 2)) < 1e-12 * np.sin(th / 2) + 1e-15
    assert v.max_leak <= v.leak_amplitude ** 2 + 1e-30 and v.max_leak > 0.9 * v.leak_amplitude ** 2   # one coherent direction
    assert abs(v.op_norm_error - (v.block_error + v.dropped_total + v.leak_amplitude)) < 1e-15
    assert not v.ok and v.reason in ("leak", "dirty_ancilla") and len(v.failing_inputs) == 10   # unfiltered, never empty
    assert v.failing_inputs[0][1] >= v.failing_inputs[-1][1]


def test_sparse_and_aer_leak_amplitude_agree_within_the_certified_factor():
    enc = _enc()
    th = 1e-3
    qc, r = _circ(1)
    qc.cry(th, r["d"][2], r["a"][0])
    I = np.eye(433, dtype=complex)
    vs = ev.evaluate(qc, enc, I, gauss=False, engine="sparse")
    va = ev.evaluate(qc, enc, I, gauss=False, engine="aer_mps")
    s = np.sin(th / 2)
    assert abs(vs.leak_amplitude - s) < 1e-9 * s
    assert s * (1 - 1e-6) <= va.leak_amplitude <= 4 * s * (1 + 1e-6)   # certified bound, up to 4x pessimistic


def _synthetic_exact(seed=20261104, n_anc=22, layers=6):
    """34-qubit exact-angle code-preserving circuit with compute / phase / uncompute use of the ancillas (true leak 0)."""
    r = np.random.default_rng(seed)
    qc = QuantumCircuit(QuantumRegister(12, "d"), QuantumRegister(n_anc, "a"))
    A = list(range(12, 12 + n_anc))
    for _ in range(layers):
        l = int(r.integers(4))
        qj, qm, qmp = 3 * l + 2, 3 * l + 1, 3 * l
        qc.ch(qj, qm), qc.cx(qj, qmp), qc.ccx(qj, qm, qmp)
        a1, a2, a3 = [int(x) for x in r.choice(A, size=3, replace=False)]
        l2 = int(r.integers(4))
        qj2, qm2 = 3 * l2 + 2, 3 * l2 + 1
        comp = [(qj, qm, a1), (qj2, qm2, a2), (a1, a2, a3)]
        for c in comp:
            qc.ccx(*c)
        qc.crz(float(r.uniform(0.1, 1.5)), a3, qmp), qc.cp(float(r.uniform(0.1, 1.5)), a1, qj2), qc.rz(float(r.uniform(0.1, 1.5)), a2)
        for c in reversed(comp):
            qc.ccx(*c)
        qc.ccx(qj, qm, qmp), qc.cx(qj, qmp), qc.ch(qj, qm)
    return qc


def test_aer_mps_direct_weights_on_exact_circuit_are_at_noise_floor():
    from su2plaq.evaluate.aer_check import aer_mps_block

    enc = _enc()
    qc = _synthetic_exact()
    inner = enc.inner_codes()
    sel = inner[::40][:16]
    M, leak, info = aer_mps_block(qc, sel, inner, (1 << 12) - 1)
    assert leak.max() <= 1e-19 and info["w_anc"].max() <= 1e-19 and info["w_inv"].max() <= 1e-19
    assert np.allclose(leak, info["w_anc"] + info["w_inv"], atol=0)
    assert info["leak_derived"].shape == leak.shape   # the old subtraction value stays as a diagnostic
    with pytest.raises(ValueError):
        aer_mps_block(QuantumCircuit(20), sel[:1], np.array([0]), (1 << 17) - 1)

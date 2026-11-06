"""Unit tests for the exact certificate layer (prompts/006 step 2.L4): K / Laurent arithmetic, exact basis and targets,
export -> Lean checker accept / reject / n_a, and the checker's gate semantics against the float simulator."""
import json
import pathlib
from fractions import Fraction

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister

from su2plaq.circuits.twelve import build_UE
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.evaluate import sparse_sim as ss
from su2plaq.lean import certify as C
from su2plaq.lean import exact as E


@pytest.fixture(scope="module")
def enc():
    return TwelveQubit()


# ---------------------------------------------------------------------------------------------- K and Laurent
def _rand_k(rng):
    return E.KNum(*[Fraction(int(rng.integers(-5, 6)), int(rng.integers(1, 5))) for _ in range(8)])


def test_knum_arithmetic_matches_complex():
    rng = np.random.default_rng(20261104)
    for _ in range(40):
        x, y = _rand_k(rng), _rand_k(rng)
        assert abs((x * y).to_complex() - x.to_complex() * y.to_complex()) < 1e-9
        assert abs((x + y).to_complex() - (x.to_complex() + y.to_complex())) < 1e-12
        assert abs(x.conj().to_complex() - np.conj(x.to_complex())) < 1e-12
        if not x.is_zero():
            assert (x * x.inv()) == E.KNum(1)
    assert E.omega_power(8) == E.KNum(1) and E.omega_power(2) == E.K_I
    assert E.K_OMEGA.to_complex() == pytest.approx(np.exp(1j * np.pi / 4), abs=1e-15)


def test_knum_recognise_and_sqrt():
    z = E.KNum(Fraction(1, 3), Fraction(-1, 2), 0, Fraction(1, 4), Fraction(1, 6), 0, Fraction(-1, 2), 0)
    assert E.KNum.recognise(z.to_complex()) == z
    assert E.KNum.recognise(0.1234567) is None
    assert E.sqrt_rational(Fraction(1, 6)) * E.sqrt_rational(Fraction(1, 6)) == E.KNum(Fraction(1, 6))
    assert E.sqrt_rational(Fraction(8, 3)) * E.sqrt_rational(Fraction(8, 3)) == E.KNum(Fraction(8, 3))
    with pytest.raises(E.ExactError):
        E.sqrt_rational(Fraction(5))


def test_laurent_arithmetic_and_json():
    a = E.Laurent.mono((1, -2), E.KNum(2)) + E.Laurent.mono((0, 0), E.K_I)
    b = E.Laurent.mono((-1, 2), E.KNum(Fraction(1, 2)))
    prod = a * b
    assert prod == E.Laurent.mono((0, 0), E.KNum(1)) + E.Laurent.mono((-1, 2), E.KNum(0, Fraction(1, 2)))
    th = (0.3, 0.7)
    assert prod.evaluate(*th) == pytest.approx(a.evaluate(*th) * b.evaluate(*th), abs=1e-13)
    assert E.Laurent.from_json(json.loads(json.dumps(prod.to_json()))) == prod
    assert (a + a.scale(E.KNum(-1))) == E.Laurent()


def test_rational_multiple():
    assert E.rational_multiple(3 * 0.37 / 4, 0.37) == Fraction(3, 4)
    assert E.rational_multiple(0.123, 0.37) is None
    assert E.rational_multiple(0.0, 0.37) == 0


# ---------------------------------------------------------------------------------------------- exact data
def test_exact_basis_targets_and_states(enc):
    basis = E.exact_physical_basis("cg")
    assert len(basis) == 433                              # cross-checks against the float basis run inside
    states = E.exact_encoded_states(enc)
    assert len(states) == 433 and sum(len(s["codes"]) for s in states) == 33425
    blocks = E.beta_blocks_summary() if hasattr(E, "beta_blocks_summary") else E._beta_blocks()
    sizes = sorted(len(ks) for ks, _ in blocks)
    assert sum(sizes) == 433 and max(sizes) <= 17
    for kind, order, base in (("UE", 1, (4, 2)), ("UB", 1, (4, 2)), ("step", 1, (4, 2)), ("step", 2, (8, 2))):
        assert E.target_base(kind, order) == base
        tb = E.exact_target_blocks(kind, order)           # float cross-check <= 1e-12 inside
        assert sorted(k for b in tb for k in b["ks"]) == list(range(433))


# ---------------------------------------------------------------------------------------------- export and check
def _ue_variant(alpha, first_angle=None):
    """build_UE(alpha, with_outer=True) with the angle of the first p gate replaced (rebuilt circuit: Qiskit 2 returns copies
    of circuit instructions, so editing `inst.operation.params` in place has no effect)."""
    base = build_UE(alpha, with_outer=True)
    out = QuantumCircuit(*base.qregs, name="UE")
    done = False
    for inst in base.data:
        ang = inst.operation.params[0]
        if not done and first_angle is not None:
            ang, done = first_angle, True
        out.p(ang, base.find_bit(inst.qubits[0]).index)
    return out


def test_ue_certified_tampered_rejected_nonlinear_na(enc, tmp_path):
    alpha, beta = 0.37, 0.61
    ok = C.certify_circuit_kind(build_UE(alpha, with_outer=True), enc, "UE", alpha, beta, 1, out_dir=tmp_path)
    assert ok.status == "certified", (ok.status, ok.reason)
    d = json.loads(pathlib.Path(ok.cert_path).read_text())
    assert d["schema"] == "su2plaq-cert-1" and len(d["states"]) == 433 and d["n_data"] == 12 and d["n_outer"] == 16
    assert d["base"] == {"d_alpha": 4, "d_beta": 2} and d["phase"]["m"] == [0, 0]
    assert [g["m"] for g in d["gates"]] == [[-3, 0]] * 4
    # gate angle wrong by a rational multiple of alpha: exactly rejected
    bad = C.certify_circuit_kind(_ue_variant(alpha, -alpha / 2), enc, "UE", alpha, beta, 1, out_dir=tmp_path / "bad")
    assert bad.status == "rejected", (bad.status, bad.reason)
    # not a rational multiple of alpha or beta: not certifiable
    na = C.certify_circuit_kind(_ue_variant(alpha, 0.123), enc, "UE", alpha, beta, 1, out_dir=tmp_path / "na")
    assert na.status == "n_a" and na.reason.startswith("non_linear_angle:p:"), (na.status, na.reason)
    # corrupted certificate data: a state term moved to another electric sector / a target exponent changed
    d["states"][5]["terms"][0]["code"] ^= 4              # flips q_j of link b: other electric phase
    p2 = tmp_path / "tampered-state.json"
    p2.write_text(json.dumps(d))
    r = C.check_certificate(p2)
    assert r.status == "rejected", (r.status, r.reason)
    d = json.loads(pathlib.Path(ok.cert_path).read_text())
    d["target"]["blocks"][0]["entries"][0][2][0][0][0] += 1
    p2b = tmp_path / "tampered-target.json"
    p2b.write_text(json.dumps(d))
    assert C.check_certificate(p2b).status == "rejected"
    # wrong claimed phase: rejected
    d2 = json.loads(pathlib.Path(ok.cert_path).read_text())
    d2["phase"]["m"] = [1, 0]
    p3 = tmp_path / "tampered-phase.json"
    p3.write_text(json.dumps(d2))
    assert C.check_certificate(p3).status == "rejected"
    # structure problems are rejected, not crashes
    d3 = json.loads(pathlib.Path(ok.cert_path).read_text())
    d3["gates"].append({"g": "cx", "q": [0, 99]})
    p4 = tmp_path / "bad-qubit.json"
    p4.write_text(json.dumps(d3))
    r4 = C.check_certificate(p4)
    assert r4.status == "rejected" and "out of range" in r4.reason


def test_not_certifiable_reasons(enc, tmp_path):
    u = QuantumCircuit(12)
    u.unitary(np.eye(2), [0])
    assert C.export_certificate(u, enc, "UE", 0.37, 0.61, 1, tmp_path / "u.json") == "unitary_gate"
    big = QuantumCircuit(70)
    assert C.export_certificate(big, enc, "UE", 0.37, 0.61, 1, tmp_path / "b.json") == "too_many_qubits"
    wrong = QuantumCircuit(12)           # the identity is not U_E: rejected, not n_a
    res = C.certify_circuit_kind(wrong, enc, "UE", 0.37, 0.61, 1, out_dir=tmp_path)
    assert res.status == "rejected"


def test_ue_without_outer_register_and_permuted_registers(enc, tmp_path):
    """The outer bits are spectators when the circuit has no outer register; qubit order of the registers is irrelevant."""
    alpha, beta = 0.37, 0.61
    r = C.certify_circuit_kind(build_UE(alpha, with_outer=False), enc, "UE", alpha, beta, 1, out_dir=tmp_path)
    assert r.status == "certified", (r.status, r.reason)
    o, d = QuantumRegister(16, "o"), QuantumRegister(12, "d")
    qc = QuantumCircuit(o, d)
    for q in (2, 5, 8, 11):
        qc.p(-0.75 * alpha, d[q])
    r2 = C.certify_circuit_kind(qc, enc, "UE", alpha, beta, 1, out_dir=tmp_path / "perm")
    assert r2.status == "certified", (r2.status, r2.reason)


# ---------------------------------------------------------------------------------------------- gate semantics
def _all_gates_circuit():
    qc = QuantumCircuit(5)
    a, b = 0.37, 0.61
    qc.h(0); qc.sx(1); qc.x(2); qc.z(3); qc.s(4); qc.sdg(0); qc.t(1); qc.tdg(2)
    qc.rz(3 * a / 2, 3); qc.rz(-b, 4); qc.p(5 * a / 4, 0); qc.p(-b / 2, 1)
    qc.cx(0, 1); qc.cz(1, 2); qc.cp(3 * b / 2, 2, 3); qc.swap(3, 4); qc.ccx(0, 1, 2); qc.ccz(2, 3, 4)
    qc.h(4); qc.sx(0); qc.cx(4, 0)
    return qc


def test_checker_semantics_every_gate_kind(tmp_path):
    qc = _all_gates_circuit()
    path = C.export_raw_circuit(qc, tmp_path / "all.json", alpha=0.37, beta=0.61)
    assert isinstance(path, pathlib.Path)
    base = json.loads(path.read_text())["base"]
    th = (0.37 / base["d_alpha"], 0.61 / base["d_beta"])
    batch = ss.run_batch(qc, np.arange(32, dtype=np.int64))
    for col in (0, 7, 19, 31):
        vec = np.zeros(32, dtype=complex)
        for key, lp in C.checker_eval(path, col):
            vec[key] += lp.evaluate(*th)
        ref = np.zeros(32, dtype=complex)
        sel = batch.cols == col
        np.add.at(ref, batch.keys[sel], batch.amps[sel])
        ph = np.vdot(ref, vec)
        ph /= abs(ph)
        assert np.abs(vec - ph * ref).max() < 1e-12


def test_raw_export_reasons(tmp_path):
    qc = QuantumCircuit(2)
    qc.p(0.123, 0)
    assert C.export_raw_circuit(qc, tmp_path / "x.json", alpha=0.37, beta=0.61).startswith("non_linear_angle:p:")
    qc = QuantumCircuit(2)
    qc.unitary(np.eye(4), [0, 1])
    assert C.export_raw_circuit(qc, tmp_path / "y.json", alpha=0.37, beta=0.61) == "unitary_gate"

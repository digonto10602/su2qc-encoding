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


# ---------------------------------------------------------------------------------------------- hardening (tester N1-N4)
@pytest.fixture(scope="module")
def ue_cert(enc, tmp_path_factory):
    out = tmp_path_factory.mktemp("ue")
    r = C.certify_circuit_kind(build_UE(0.37, with_outer=True), enc, "UE", 0.37, 0.61, 1, out_dir=out)
    assert r.status == "certified", (r.status, r.reason)
    return json.loads(pathlib.Path(r.cert_path).read_text())


def _lean_only(d, tmp_path, name):
    """Run the Lean checker alone (no Python-side pinning) on a doctored certificate; (verdict line, stderr)."""
    p = tmp_path / name
    p.write_text(json.dumps(d))
    r = C._run_checker(["check", str(p)], 300)
    return r.stdout.strip(), r.stderr


def test_n1_state_set_is_pinned(ue_cert, tmp_path):
    d = json.loads(json.dumps(ue_cert))
    # (a) 164-state subset with its blocks: Lean rejects on the count, the Python pinning too
    cut = json.loads(json.dumps(d))
    cut["states"] = cut["states"][:164]
    cut["target"]["blocks"] = [b for b in cut["target"]["blocks"] if max(b["ks"]) < 164]
    line, _ = _lean_only(cut, tmp_path, "cut.json")
    assert line.startswith("REJECT") and "433" in line, line
    (tmp_path / "cut-py.json").write_text(json.dumps(cut))
    assert C.check_certificate(tmp_path / "cut-py.json").status == "rejected"
    # (b) duplicate state index
    dup = json.loads(json.dumps(d))
    dup["states"][7]["k"] = 6
    line, _ = _lean_only(dup, tmp_path, "dup.json")
    assert line.startswith("REJECT") and "duplicate state index" in line, line
    # (c) coefficient changed: not normalised
    alt = json.loads(json.dumps(d))
    alt["states"][5]["terms"][0]["c"][0] = "7/5"
    line, _ = _lean_only(alt, tmp_path, "alt.json")
    assert line.startswith("REJECT") and "normalised" in line or "orthogonal" in line, line
    # (d) a sign flip keeps the norm of this state: the Python pinning against the exact basis catches it
    flip = json.loads(json.dumps(d))
    t = flip["states"][5]["terms"][0]["c"]
    flip["states"][5]["terms"][0]["c"] = [("-" + x if x != "0" else x) for x in t]
    (tmp_path / "flip.json").write_text(json.dumps(flip))
    r = C.check_certificate(tmp_path / "flip.json")
    assert r.status == "rejected" and "exact physical basis" in r.reason, (r.status, r.reason)
    # (e) empty state, (f) a basis state listed twice
    emp = json.loads(json.dumps(d))
    emp["states"][3]["terms"] = []
    line, _ = _lean_only(emp, tmp_path, "emp.json")
    assert line.startswith("REJECT") and "empty" in line, line
    twice = json.loads(json.dumps(d))
    twice["states"][3]["terms"].append(dict(twice["states"][3]["terms"][0]))
    line, _ = _lean_only(twice, tmp_path, "twice.json")
    assert line.startswith("REJECT") and ("twice" in line or "normalised" in line), line


def test_n2_out_of_range_target_row_rejects(ue_cert, tmp_path):
    d = json.loads(json.dumps(ue_cert))
    d["target"]["blocks"][0]["entries"][0][0] = 5            # row 5 in a block of one state
    line, err = _lean_only(d, tmp_path, "row.json")
    assert line.startswith("REJECT") and "outside a block" in line, line
    assert "panic" not in err.lower() and "out of bounds" not in err.lower()
    d = json.loads(json.dumps(ue_cert))
    d["target"]["blocks"][0]["entries"][0][1] = 1000
    line, err = _lean_only(d, tmp_path, "col.json")
    assert line.startswith("REJECT") and "outside a block" in line


def test_n3_angle_preference_follows_the_target(enc, tmp_path):
    f = C._classify_angle
    assert f(-0.375, 0.5, 0.25, "a") == (Fraction(-3, 4), 0)          # alpha/beta = 2: the angle is -3a/4 = -3b/2
    assert f(-0.375, 0.5, 0.25, "b") == (0, Fraction(-3, 2))
    assert f(-0.375, 0.5, 0.25, "ab") == (0, Fraction(-3, 2))         # step: both are target variables, smaller denominator
    r = C.certify_circuit_kind(build_UE(0.5, with_outer=True), enc, "UE", 0.5, 0.25, 1, out_dir=tmp_path)
    assert r.status == "certified", (r.status, r.reason)


def test_n4_crx_family_is_lowered_exactly(tmp_path):
    """crx / crz / rx lower to h, rz, cx (no u gate); the lowered gate list equals Qiskit's gate EXACTLY (no phase freedom)."""
    a, b = 0.37, 0.61
    qc = QuantumCircuit(4)
    qc.h(0); qc.h(1); qc.sx(2)
    qc.crx(2 * b, 0, 3); qc.crx(-b / 2, 1, 3); qc.crz(3 * a / 4, 2, 0); qc.rx(b, 2); qc.crx(a, 3, 1)
    path = C.export_raw_circuit(qc, tmp_path / "crx.json", alpha=a, beta=b)
    assert isinstance(path, pathlib.Path)
    d = json.loads(path.read_text())
    assert {g["g"] for g in d["gates"]} <= {"h", "sx", "rz", "cx"}
    th = (a / d["base"]["d_alpha"], b / d["base"]["d_beta"])
    batch = ss.run_batch(qc, np.arange(16, dtype=np.int64))
    for col in range(16):
        vec = np.zeros(16, dtype=complex)
        for key, lp in C.checker_eval(path, col):
            vec[key] += lp.evaluate(*th)
        ref = np.zeros(16, dtype=complex)
        sel = batch.cols == col
        np.add.at(ref, batch.keys[sel], batch.amps[sel])
        assert np.abs(vec - ref).max() < 1e-12


def test_theorem_file_for_small_certificate(ue_cert, tmp_path):
    """write_theorem_file -> `lake env lean` elaborates; axioms = standard + exactly one native_decide axiom, printed on ONE line
    (the locked general-circuit test parses that line); a tampered certificate makes native_decide fail."""
    from su2plaq.lean import project as P

    cert = tmp_path / "ue.json"
    cert.write_text(json.dumps(ue_cert, separators=(",", ":")))
    f = C.write_theorem_file(cert, "ue_ok", tmp_path / "ue.lean")
    text = f.read_text()
    assert "native_decide" in text and "sorry" not in text
    r = P.lake(["env", "lean", str(f)], timeout=900)
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-1500:]
    lines = [ln for ln in r.stdout.splitlines() if "depends on axioms" in ln]
    assert len(lines) == 1
    ax = {a.strip(" ,[]'\"") for a in lines[0].split("axioms:")[1].split(",")} - {""}
    extra = ax - P.STANDARD_AXIOMS
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra), ax
    bad = json.loads(json.dumps(ue_cert))
    bad["phase"]["m"] = [1, 0]
    cert.write_text(json.dumps(bad, separators=(",", ":")))
    f2 = C.write_theorem_file(cert, "ue_bad", tmp_path / "ue_bad.lean")
    r2 = P.lake(["env", "lean", str(f2)], timeout=900)
    assert r2.returncode != 0
    with pytest.raises(ValueError):
        C.write_theorem_file(cert, "a_far_too_long_theorem_name", tmp_path / "x.lean")


# ---------------------------------------------------------------------------------------------- N5, N6: pinned data
def _fake_identity_cert(ue_cert):
    """433 fake orthonormal states (one basis state each) with the identity circuit and the identity target."""
    d = json.loads(json.dumps(ue_cert))
    d["gates"] = []
    d["states"] = [{"k": k, "label": "fake", "terms": [{"code": 1 + k, "c": ["1"] + ["0"] * 7}]} for k in range(433)]
    d["target"]["blocks"] = [{"ks": [k], "entries": [[0, 0, [[[0, 0], ["1"] + ["0"] * 7]]]]} for k in range(433)]
    d["phase"]["m"] = [0, 0]
    return d


def test_n5_fake_states_and_theorem_files_are_refused(ue_cert, tmp_path):
    fake = _fake_identity_cert(ue_cert)
    line, _ = _lean_only(fake, tmp_path, "fake.json")          # Lean alone: pinned fingerprint
    assert line.startswith("REJECT") and "pinned exact physical basis" in line, line
    p = tmp_path / "fake2.json"
    p.write_text(json.dumps(fake))
    assert C.check_certificate(p).status == "rejected"
    with pytest.raises(ValueError, match="differs from the exporter"):
        C.write_theorem_file(p, "fake_ok", tmp_path / "fake.lean")
    assert not (tmp_path / "fake.lean").exists()
    # right states, wrong target (identity instead of U_E): Lean alone rejects on the target fingerprint
    d = json.loads(json.dumps(ue_cert))
    d["gates"] = []
    d["target"]["blocks"] = [{"ks": [k], "entries": [[0, 0, [[[0, 0], ["1"] + ["0"] * 7]]]]} for k in range(433)]
    line, _ = _lean_only(d, tmp_path, "wrongtarget.json")
    assert line.startswith("REJECT") and "pinned exact" in line, line
    # unknown target kind
    d = json.loads(json.dumps(ue_cert))
    d["target"]["kind"] = "nonsense"
    line, _ = _lean_only(d, tmp_path, "kind.json")
    assert line.startswith("REJECT") and "unknown target kind" in line


def test_pins_file_and_fingerprint_agree_with_exporter(ue_cert, tmp_path):
    from su2plaq.lean import pins as Pn

    assert Pn.PINS_FILE.read_text() == Pn.render_lean(Pn.compute_pins()), "run: python -m su2plaq.lean.pins"
    p = tmp_path / "ue.json"
    p.write_text(json.dumps(ue_cert))
    r = C._run_checker(["fingerprint", str(p)], 120)
    got = dict(ln.split() for ln in r.stdout.strip().splitlines())
    want = Pn.compute_pins()
    assert got["states"] == want["states"] and got["target"] == want["targets"]["UE:1"]


@pytest.mark.parametrize("n", [0, 1, 55, 56, 63, 64, 119, 120, 1000])
def test_lean_sha256_matches_hashlib(n, tmp_path):
    import hashlib

    data = bytes((7 * i + 3) % 256 for i in range(n))
    f = tmp_path / "d.bin"
    f.write_bytes(data)
    r = C._run_checker(["sha256", str(f)], 60)
    assert r.stdout.strip() == hashlib.sha256(data).hexdigest()


def test_n6_zero_denominator_is_rejected_not_raised(ue_cert, tmp_path):
    for where in ("state", "target", "phase"):
        d = json.loads(json.dumps(ue_cert))
        if where == "state":
            d["states"][4]["terms"][0]["c"][0] = "1/0"
        elif where == "target":
            d["target"]["blocks"][0]["entries"][0][2][0][1][0] = "1/0"
        else:
            d["phase"]["k"][0] = "1/0"
        p = tmp_path / f"zero-{where}.json"
        p.write_text(json.dumps(d))
        r = C.check_certificate(p)
        assert r.status == "rejected", (where, r.status, r.reason)

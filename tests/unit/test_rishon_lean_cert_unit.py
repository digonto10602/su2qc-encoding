"""Steps 6.L2-6.L4 (prompts/203 section 3.2, prompts/204 section 6.4): the rishon three-angle certificate exporter
(`su2plaq.rishon.lean_cert`) and the Lean checker `su2plaq_rishon_cert` it drives.  Small systems only: the 12-gate U_E and the
det layer U_D circuits (about 1 s each in the checker); the general circuits are in the acceptance tests."""
import copy
import hashlib
import json
import math
import pathlib
import subprocess

import numpy as np
import pytest
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import CircuitInstruction

from su2plaq.circuits.rishon import build_UD, build_UE
from su2plaq.lean import exact as E
from su2plaq.lean import project as P
from su2plaq.rishon import lean_cert as L
from su2plaq.rishon import operators as O

ALPHA, BETA, ETA = 0.37, 0.61, 0.29
SQ2 = math.sqrt(2.0)


def _first(qc, name, angle):
    out = qc.copy()
    for i, inst in enumerate(out.data):
        if inst.operation.name == name:
            op = inst.operation.copy()
            op.params = [angle]
            out.data[i] = CircuitInstruction(op, inst.qubits, inst.clbits)
            return out
    raise AssertionError(name)


@pytest.fixture(scope="module")
def ue_cert(tmp_path_factory):
    d = tmp_path_factory.mktemp("ue")
    c = L.certify_circuit_kind(build_UE(ALPHA), "UE", ALPHA, BETA, 1, out_dir=d, timeout=300)
    assert c.status == "certified", (c.status, c.reason)
    return pathlib.Path(c.cert_path)


@pytest.fixture(scope="module")
def ud_cert(tmp_path_factory):
    d = tmp_path_factory.mktemp("ud")
    c = L.certify_det_layer(build_UD(ETA), ETA, out_dir=d, timeout=300)
    assert c.status == "certified", (c.status, c.reason)
    return pathlib.Path(c.cert_path)


# ----------------------------------------------------------------------------------------------------- Laurent3 and angles
def test_laurent3_arithmetic_and_json():
    h = E.KNum(E.Fraction(1, 2)) if hasattr(E, "Fraction") else E.KNum(0.5)
    a = L.Laurent3.mono((1, 0, -2), E.K_ONE) + L.Laurent3.mono((0, 3, 0), E.K_I)
    assert not (a + L.Laurent3.mono((1, 0, -2), E.KNum(-1)) + L.Laurent3.mono((0, 3, 0), -E.K_I))      # cancels to the empty polynomial
    b = L.Laurent3.mono((0, 1, 1), h)
    prod = a * b
    assert set(prod) == {(1, 1, -1), (0, 4, 1)}
    th = (0.31, 0.47, SQ2 * 0.47)
    assert abs(prod.evaluate(*th) - a.evaluate(*th) * b.evaluate(*th)) <= 1e-14
    assert L.Laurent3.from_json(json.loads(json.dumps(prod.to_json()))) == prod
    assert prod.shift((2, 0, 0)).evaluate(*th) == pytest.approx(prod.evaluate(*th) * np.exp(1j * 2 * th[0]), abs=1e-14)
    assert not a.scale(E.KNum(0))


def test_recognise_angle_single():
    s = L.recognise_angle_single
    assert s(2 * ETA, ETA) == (2, 1) and s(-0.75 * ETA, ETA) == (-3, 4) and s(0.0, ETA) == (0, 1)
    assert s(0.123, ETA) is None and s(ETA / 64, ETA) == (1, 64) and s(ETA / 65, ETA) is None
    assert s(6 * ETA / 4, ETA) == (3, 2)                      # smallest denominator, gcd-reduced
    with pytest.raises(ValueError):
        s(1.0, 0.0)


# ----------------------------------------------------------------------------------------------------- exact targets and pins
@pytest.mark.parametrize("kind,order", [("UE", 1), ("UB", 1), ("step", 1), ("step", 2)])
def test_exact_target_matches_float_at_other_angles(kind, order):
    base, ents = L.exact_target(kind, order)
    a, b = 0.91, 0.23
    th = (a / base[0], b / base[1], SQ2 * b / base[2])
    got = np.zeros((1296, 1296), dtype=complex)
    for (i, j), lp in ents.items():
        got[i, j] = lp.evaluate(*th)
    assert np.abs(got - O.inner_target(kind, a, b, order)).max() <= 1e-12
    assert np.abs(got.conj().T @ got - np.eye(1296)).max() <= 1e-12            # unitary at an angle pair the exporter never cross-checked


def test_exact_det_target_matches_float_at_other_eta():
    base, ents = L.exact_target("UD")
    assert base == (1, 1, 1)
    got = np.zeros((1296, 1296), dtype=complex)
    for (i, j), lp in ents.items():
        got[i, j] = lp.evaluate(0.53, 0.0, 0.0)
    assert np.abs(got - O.inner_target("UD", None, None, eta=0.53)).max() <= 1e-12
    assert len(ents) == 8 ** 4                                    # 8 nonzero entries per link, 4 links


def test_ub_target_exponents_use_beta_and_gamma_slots():
    _, ents = L.exact_target("UB")
    slots = {(a, b, g) for lp in ents.values() for (a, b, g) in lp}
    assert {(0, 1, 0), (0, 2, 0), (0, 0, 4)} <= slots and not any(a for a, _, _ in slots)       # kappa = 1, 2, 4 sqrt2 -> z_b, z_b^2, z_g^4


def test_shipped_pins_equal_a_fresh_render():
    assert L.render_pins_lean(L.compute_pins()) == L.PINS_FILE.read_text()
    assert L.compute_pins()["step:1"]["base"] == [4, 1, 1] and L.compute_pins()["UD:1"]["base"] == [1, 1, 1]


def test_lean_fingerprint_equals_python_target_text(ue_cert):
    r = subprocess.run([str(L._checker_exe()), "fingerprint", str(ue_cert)], capture_output=True, text=True, timeout=300)
    want = hashlib.sha256(L.target_text(L.exact_target("UE")[1]).encode()).hexdigest()
    assert r.stdout.strip() == f"target {want}"


# ----------------------------------------------------------------------------------------------------- exporter and checker
def test_phase_fit_recovers_known_exponents():
    base = (4, 2, 1)
    pairs = [(0.37, 0.61), (0.91, 0.23), (1.70, 1.00)]
    slots = [(a, b, SQ2 * b) for a, b in pairs]
    for j, ex in [(3, (2, -1, 0)), (0, (0, 0, 0)), (7, (-5, 3, 2))]:
        cs = [np.exp(1j * (ex[0] * s[0] / base[0] + ex[1] * s[1] / base[1] + ex[2] * s[2] / base[2] + j * np.pi / 4)) for s in slots]
        assert L._fit_phase3(cs, slots, base) == (j, *ex)
    assert L._fit_phase3([1.0, 1j, 1.0], slots, base) is None


def test_ue_certificate_shape_and_ancilla_free_layout(ue_cert):
    d = json.loads(ue_cert.read_text())
    assert d["schema"] == L.SCHEMA and d["n_qubits"] == 16 and d["n_data"] == 16 and d["n_outer"] == 0 and d["outer_dropped"] == 0
    assert d["base"] == {"d_alpha": 4, "d_beta": 1, "d_gamma": 1} and d["states"] == [int(c) for c in O.inner_codes()]
    assert all(len(g["m"]) == 3 and g["m"][1:] == [0, 0] for g in d["gates"] if "m" in g) and d["phase"]["m"] == [0, 0, 0]
    assert d["provenance"]["kind"] == "UE" and d["provenance"]["angle_slots"]["gamma"] == "sqrt2*beta"
    assert len(d["target"]["entries"]) == 1296


def test_checker_rejects_tampered_certificates(ud_cert, tmp_path):
    d = json.loads(ud_cert.read_text())
    assert d["provenance"]["angle_slots"] == {"alpha": "eta"}

    def verdict(dd):
        p = tmp_path / "t.json"
        p.write_text(json.dumps(dd))
        r = subprocess.run([str(L._checker_exe()), "check", str(p)], capture_output=True, text=True, timeout=300)
        return r.stdout.strip()

    assert verdict(d) == "ACCEPT"
    x = copy.deepcopy(d); x["phase"]["m"] = [1, 0, 0]
    assert verdict(x).startswith("REJECT state 0 differs")                                 # wrong global phase
    x = copy.deepcopy(d); x["gates"] = x["gates"][:-1]
    assert verdict(x).startswith("REJECT state")                                             # dropped gate
    x = copy.deepcopy(d); x["target"]["entries"][3][2][0][1][0] = "1/3"
    assert "pinned exact UD target" in verdict(x)                                           # target differs from the pin
    x = copy.deepcopy(d); x["states"][0], x["states"][1] = x["states"][1], x["states"][0]
    assert "states differ" in verdict(x)
    x = copy.deepcopy(d); x["n_outer"] = 32
    assert verdict(x).startswith("REJECT")
    x = copy.deepcopy(d); x["gates"][0]["q"] = [99, 100]
    assert "out of range" in verdict(x)
    x = copy.deepcopy(d); x["base"]["d_alpha"] = 2                                           # base multiple but exponents not rescaled
    assert verdict(x).startswith("REJECT")
    x = copy.deepcopy(d); x["schema"] = "su2plaq-cert-1"
    assert "unknown schema" in verdict(x)


def test_checker_accepts_a_rescaled_base(ud_cert, tmp_path):
    d = json.loads(ud_cert.read_text())
    d["base"]["d_alpha"] = 2
    for g in d["gates"]:
        if "m" in g:
            g["m"][0] *= 2
    for e in d["target"]["entries"]:
        for t in e[2]:
            t[0][0] *= 2
    d["gates_sha256"] = hashlib.sha256(json.dumps(d["gates"]).encode()).hexdigest()
    p = tmp_path / "r.json"
    p.write_text(json.dumps(d))
    assert L.check_inner_certificate(p, timeout=300).status == "certified"
    d["gates"][0]["q"] = d["gates"][0]["q"][::-1]                    # a gate list that no longer matches its recorded hash is refused before Lean
    p.write_text(json.dumps(d))
    r = L.check_inner_certificate(p, timeout=300)
    assert r.status == "rejected" and "gates_sha256" in r.reason


def test_certify_statuses_and_na_reasons(tmp_path):
    qc = build_UE(ALPHA)
    assert L.certify_circuit_kind(_first(qc, "p", -ALPHA / 2), "UE", ALPHA, BETA, 1, out_dir=tmp_path / "a", timeout=300).status == "rejected"
    na = L.certify_circuit_kind(_first(qc, "p", 0.123), "UE", ALPHA, BETA, 1, out_dir=tmp_path / "b", timeout=300)
    assert (na.status, na.reason) == ("n_a", "non_linear_angle:p:0.123")
    u = qc.copy()
    u.unitary(np.array([[0, 1], [1, 0]]), [0])
    assert L.certify_circuit_kind(u, "UE", ALPHA, BETA, 1, out_dir=tmp_path / "c", timeout=300).status in ("n_a", "certified")
    d = build_UD(ETA)
    wrong = L.certify_det_layer(_first(d, "rz", -2 * ETA), ETA, out_dir=tmp_path / "d", timeout=300)
    assert wrong.status == "rejected"
    assert L.certify_det_layer(_first(d, "rz", 0.123), ETA, out_dir=tmp_path / "e", timeout=300).reason.startswith("non_linear_angle:rz")
    with pytest.raises(ValueError):
        L.export_inner_certificate(d, "UD", ETA, 0.0, 1, tmp_path / "f.json")


def test_outer_qubit_touched_is_na(tmp_path):
    d, o = QuantumRegister(16, "d"), QuantumRegister(32, "o")
    qc = QuantumCircuit(d, o)
    qc.cx(0, 1)
    qc.cx(16, 0)                                                  # reads an outer qubit
    c = L.certify_circuit_kind(qc, "UE", ALPHA, BETA, 1, out_dir=tmp_path, timeout=60)
    assert (c.status, c.reason) == ("n_a", "outer_read")
    clean = QuantumCircuit(d, o)                                  # untouched outer register: dropped and recorded
    for l in range(4):
        clean.cx(4 * l, 4 * l + 1)
        clean.p(-0.75 * ALPHA, 4 * l + 1)
        clean.cx(4 * l, 4 * l + 1)
    c = L.certify_circuit_kind(clean, "UE", ALPHA, BETA, 1, out_dir=tmp_path / "ok", timeout=300)
    assert c.status == "certified" and json.loads(pathlib.Path(c.cert_path).read_text())["outer_dropped"] == 32


def test_checker_eval_matches_simulator_on_a_small_circuit(tmp_path):
    from su2plaq.evaluate import sparse_sim as ss

    qc = QuantumCircuit(3)
    qc.h(0); qc.cx(0, 1); qc.p(ALPHA / 4 * 3, 1); qc.rz(2 * BETA, 2); qc.cp(SQ2 * BETA / 2, 1, 2); qc.ccx(0, 1, 2); qc.h(2)
    path = L.export_raw_circuit(qc, tmp_path / "raw.json", alpha=ALPHA, beta=BETA)
    assert isinstance(path, pathlib.Path)
    base = json.loads(path.read_text())["base"]
    th = (ALPHA / base["d_alpha"], BETA / base["d_beta"], SQ2 * BETA / base["d_gamma"])
    batch = ss.run_batch(qc, np.arange(8, dtype=np.int64))
    for col in (0, 5):
        vec = np.zeros(8, dtype=complex)
        for key, lp in L.checker_eval(path, col, timeout=60):
            vec[key] += lp.evaluate(*th)
        ref = np.zeros(8, dtype=complex)
        sel = batch.cols == col
        np.add.at(ref, batch.keys[sel], batch.amps[sel])
        ph = np.vdot(ref, vec)
        assert np.abs(vec - ph / abs(ph) * ref).max() <= 1e-12
    assert L.export_raw_circuit(_first(qc, "p", 0.123), tmp_path / "bad.json", alpha=ALPHA, beta=BETA).startswith("non_linear_angle:p")


# ----------------------------------------------------------------------------------------------------- the exporter rule, theorem file
def test_angle_fit_rule_gates_the_status(tmp_path):
    from su2plaq.rishon.compress.spec import rishon_spec

    spec = rishon_spec("UE")
    qc = build_UE(ALPHA)
    fits = L.rotation_fits(qc, ALPHA, BETA)
    assert fits == [(-3, 0, 0, 4)] * 4
    ok = L.certify_circuit(qc, spec, out_dir=tmp_path / "ok", timeout=300, angle_fit={"confirmed": True, "angle_fit": fits, "reason": ""})
    assert ok.status == "certified"
    no = L.certify_circuit(qc, spec, out_dir=tmp_path / "no", timeout=300,
                           angle_fit={"confirmed": False, "angle_fit": fits, "reason": "the gate skeleton changes over the angle set"})
    assert no.status == "n_a" and no.reason.startswith("angle_fit_not_confirmed") and no.cert_path is None
    diff = L.certify_circuit(qc, spec, out_dir=tmp_path / "diff", timeout=300,
                             angle_fit={"confirmed": True, "angle_fit": [(-3, 0, 0, 4)] * 3 + [(-1, 0, 0, 2)], "reason": ""})
    assert diff.status == "n_a" and diff.reason.startswith("angle_fit_not_confirmed")


def test_confirm_angle_fit_on_the_general_ue_program():
    from su2plaq.rishon.compress import baselines as BL
    from su2plaq.rishon.compress.spec import rishon_spec

    spec = rishon_spec("UE")
    r = L.confirm_angle_fit(BL.general_program_path(spec), spec)
    assert r["confirmed"] is True and r["angle_fit"] == [(-3, 0, 0, 4)] * 4 and r["reason"] == ""


def test_theorem_file_writer_and_elaboration(ue_cert, tmp_path):
    out = L.write_theorem_file(ue_cert, "rishon_cert_unit_ue", tmp_path / "t.lean")
    src = out.read_text()
    assert src.startswith("import Su2PlaqCert.Rishon.Check3") and "native_decide" in src and "sorry" not in src
    assert "#print axioms rishon_cert_unit_ue" in src and src.count("\n") < 20
    r = L.check_theorem_file(out, timeout=600)
    assert r["status"] == "certified", r
    extra = set(r["axioms"]) - {"propext", "Classical.choice", "Quot.sound"}
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra)
    bad = json.loads(ue_cert.read_text())
    bad["target"]["entries"][0][2][0][1][0] = "2"
    badp = tmp_path / "bad.json"
    badp.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="refusing"):
        L.write_theorem_file(badp, "rishon_cert_bad", tmp_path / "bad.lean")
    with pytest.raises(ValueError, match="bad theorem name"):
        L.write_theorem_file(ue_cert, "not a name", tmp_path / "x.lean")


def test_theorem_file_of_a_false_statement_is_rejected(ue_cert, tmp_path):
    d = json.loads(ue_cert.read_text())
    d["phase"]["m"] = [1, 0, 0]                                      # exporter data are right, the claimed phase is not: the statement is false
    p = tmp_path / "false.json"
    p.write_text(json.dumps(d))
    out = L.write_theorem_file(p, "rishon_cert_false", tmp_path / "f.lean")
    r = L.check_theorem_file(out, timeout=600)
    assert r["status"] == "rejected", r


def test_round_certify_applies_the_angle_fit_rule_only_to_program_entries(monkeypatch):
    """`round._certify` (round integration, `run_round` and `certify_best`): an entry with a program file goes through
    `confirm_angle_fit` and passes its result to `certify_circuit`; a circuit-valued baseline (`*.circuit`) does not."""
    from su2plaq.compress.archive import Entry  # noqa: F401  (import check only)
    from su2plaq.lean.certify import LeanCert
    from su2plaq.rishon.compress import round as R

    calls = []
    monkeypatch.setattr(L, "confirm_angle_fit", lambda path, spec, root=None: calls.append(("confirm", str(path))) or {"confirmed": False, "angle_fit": None, "reason": "x"})
    monkeypatch.setattr(L, "certify_circuit", lambda qc, spec, out_dir=None, timeout=900.0, angle_fit=None: calls.append(("certify", angle_fit)) or LeanCert("n_a", "r", None, 0.0, ""))
    out, _sec = R._certify("circ", "spec", "compress/programs/rishon/F1/001-x.py", None)
    assert out["status"] == "n_a" and calls == [("confirm", "compress/programs/rishon/F1/001-x.py"), ("certify", {"confirmed": False, "angle_fit": None, "reason": "x"})]
    calls.clear()
    R._certify("circ", "spec", "compress/programs/rishon/seed/general.circuit", None)
    R._certify("circ", "spec")
    assert calls == [("certify", None), ("certify", None)]
    monkeypatch.setattr(L, "confirm_angle_fit", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    out, _sec = R._certify("circ", "spec", "compress/programs/rishon/F1/001-x.py", None)
    assert out["status"] == "failed" and "boom" in out["reason"]

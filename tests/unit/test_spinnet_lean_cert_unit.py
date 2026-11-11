"""Unit tests for the native certificate of the spin-network circuits (prompts/100 step 3.L3): exact Laurent targets vs
enc.target, pins vs the checked-in Lean file, certified circuits, and tampered certificates rejected by the Lean checker."""
import functools
import json
import re
import subprocess

import numpy as np
import pytest

from su2plaq.circuits.spinnet import build_UB, build_UE, build_step
from su2plaq.encodings.base import ALT_ANGLES
from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import lean_export as LE

PAIRS = [(0.37, 0.61)] + [tuple(p) for p in ALT_ANGLES]


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


def test_angle_pairs_are_three():
    assert len(PAIRS) == 3 and PAIRS[0] == (0.37, 0.61)


@pytest.mark.parametrize("kind,order", [("UE", 1), ("UB", 1), ("step", 1), ("step", 2)])
def test_exported_laurent_target_matches_enc_target(kind, order):
    """The exact Laurent-K blocks evaluated at the nominal and the two alternate angle pairs equal enc.target <= 1e-12."""
    for al, be in PAIRS:
        V = LE.laurent_target_matrix(enc(), kind, al, be, order)
        ref = enc().target(kind, al, be, order)
        assert np.abs(V - ref).max() <= 1e-12, (kind, order, al, be)


def test_target_block_structure():
    blocks = LE.exact_target_blocks(enc(), "UB", 1)
    sizes = sorted(len(b["ks"]) for b in blocks)
    assert sizes.count(1) == 177 and sizes.count(2) == 128 and len(sizes) == 305
    assert sorted(k for b in blocks for k in b["ks"]) == list(range(433))
    assert LE.target_base("step", 2) == (8, 4) and LE.target_base("UB") == (4, 4)


def test_pins_file_matches_exporter():
    p = LE.compute_pins(enc())
    assert LE.render_pins_lean(p) == LE.SPIN_PINS_FILE.read_text()


@pytest.fixture(scope="module")
def lean_ready():
    LE.checker_exe()
    return True


@pytest.fixture(scope="module")
def ub_cert(tmp_path_factory, lean_ready):
    d = tmp_path_factory.mktemp("certs")
    r = LE.certify(build_UB(0.61, with_outer=True), enc(), "UB", 0.37, 0.61, 1, out_dir=d)
    return r


def test_UB_certified_and_schema(ub_cert):
    r = ub_cert
    assert r["status"] == "certified", r
    d = json.loads(open(r["cert_path"]).read())
    assert d["schema"] == "su2plaq-cert-1" and d["n_data"] == 8 and d["n_outer"] == 8 and len(d["states"]) == 433
    assert d["base"] == {"d_alpha": 4, "d_beta": 4} and d["target"]["kind"] == "UB"
    assert all(len(s["terms"]) == 1 and s["terms"][0]["c"] == ["1"] + ["0"] * 7 for s in d["states"])
    assert len(d["target"]["blocks"]) == 305


def test_UE_and_step_certified(tmp_path, lean_ready):
    assert LE.certify(build_UE(0.37, with_outer=True), enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path)["status"] == "certified"
    r = LE.certify(build_step(0.37, 0.61, 1, with_outer=True), enc(), "step", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "certified", r


def test_lean_fingerprints_equal_python_pins(ub_cert):
    exe = LE.checker_exe()
    out = subprocess.run([str(exe), "fingerprint", ub_cert["cert_path"]], capture_output=True, text=True).stdout.split()
    pins = LE.compute_pins(enc())
    assert out == ["states", pins["states"], "target", pins["targets"]["UB:1"]]


def _rewrite(path, tmp_path, edit):
    d = json.loads(open(path).read())
    edit(d)
    out = tmp_path / "tampered.json"
    out.write_text(json.dumps(d, separators=(",", ":")))
    return out


@pytest.mark.parametrize("name", ["gate_angle", "drop_gate", "extra_x", "phase", "target_entry", "state_code",
                                  "wrong_kind", "wrong_base"])
def test_tampered_certificate_is_rejected(ub_cert, tmp_path, name):
    def edit(d):
        g = d["gates"]
        if name == "gate_angle":
            i = next(i for i, x in enumerate(g) if x["g"] == "rz")
            g[i]["m"][1] += 2
        elif name == "drop_gate":
            del g[next(i for i, x in enumerate(g) if x["g"] == "rz")]
        elif name == "extra_x":
            g.append({"g": "x", "q": [0]})
        elif name == "phase":
            d["phase"]["m"][1] += 1
        elif name == "target_entry":
            e = d["target"]["blocks"][0]["entries"][0]
            e[2][0][1][0] = "2"
        elif name == "state_code":
            d["states"][0]["terms"][0]["code"] ^= 1
        elif name == "wrong_kind":
            d["target"]["kind"] = "UE"
        elif name == "wrong_base":
            d["base"]["d_beta"] = 8
        d["program_sha256"] = "tampered"

    out = _rewrite(ub_cert["cert_path"], tmp_path, edit)
    r = LE.check_certificate(out)
    assert r["status"] == "rejected", (name, r)
    if name in ("gate_angle", "drop_gate", "extra_x", "phase"):
        assert "differs from the target" in r["reason"], r


def test_wrong_circuit_for_the_kind_is_rejected(tmp_path, lean_ready):
    """A U_E circuit against the U_B target: the export fits no phase and the exact checker rejects (not n_a)."""
    r = LE.certify(build_UE(0.37, with_outer=True), enc(), "UB", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "rejected" and "differs from the target" in r["reason"], r


def test_non_linear_angle_is_n_a(tmp_path, lean_ready):
    r = LE.certify(build_UB(0.61 * (1 + 1e-6), with_outer=True), enc(), "UB", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "n_a" and r["reason"].startswith("non_linear_angle"), r


def test_unitary_gate_is_n_a(tmp_path, lean_ready):
    from qiskit import QuantumCircuit
    from qiskit.circuit.library import UnitaryGate

    qc = QuantumCircuit(16)
    qc.append(UnitaryGate(np.array([[0, 1], [1, 0]], dtype=complex)), [0])
    r = LE.certify(qc, enc(), "UB", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "n_a", r


# ----------------------------------------------------------------------------------------- 4.L1: theorem file
def test_theorem_file_of_UE_elaborates_with_one_native_axiom(tmp_path, lean_ready):
    """write_theorem_file -> `lake env lean` exits 0; axioms = standard + exactly one native_decide axiom on ONE line; a
    certificate with a wrong phase gives a theorem that fails; a tampered state / bad name is refused by the writer."""
    from su2plaq.lean import project as P

    r = LE.certify(build_UE(0.37, with_outer=True), enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "certified", r
    f = LE.write_theorem_file(r["cert_path"], "spin_ue_ok", tmp_path / "ue.lean", comment="entry test, program sha256 abc")
    text = f.read_text()
    assert text.startswith("-- entry test, program sha256 abc\nimport Su2PlaqCert.SpinNet.Check\n")
    assert "Su2PlaqCert.SpinNet.checkJsonString certJson = true := by native_decide" in text and "sorry" not in text
    p = P.lake(["env", "lean", str(f)], timeout=900)
    assert p.returncode == 0, p.stdout[-1500:] + p.stderr[-1500:]
    lines = [ln for ln in p.stdout.splitlines() if "depends on axioms" in ln]
    assert len(lines) == 1
    ax = {a.strip(" ,[]'\"") for a in lines[0].split("axioms:")[1].split(",")} - {""}
    extra = ax - P.STANDARD_AXIOMS
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra), ax
    # wrong phase: still a valid-looking certificate (states and target are the exact ones), but the theorem is false
    d = json.loads(open(r["cert_path"]).read())
    d["phase"]["m"][0] += 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(d, separators=(",", ":")))
    f2 = LE.write_theorem_file(bad, "spin_ue_bad", tmp_path / "bad.lean")
    assert P.lake(["env", "lean", str(f2)], timeout=900).returncode != 0
    # writer refusals: tampered state, tampered target, bad name
    d = json.loads(open(r["cert_path"]).read())
    d["states"][0]["terms"][0]["code"] ^= 1
    bad.write_text(json.dumps(d, separators=(",", ":")))
    with pytest.raises(ValueError, match="state 0 differs"):
        LE.write_theorem_file(bad, "spin_x", tmp_path / "x.lean")
    d = json.loads(open(r["cert_path"]).read())
    d["target"]["blocks"][0]["entries"][0][2][0][1][0] = "2"
    bad.write_text(json.dumps(d, separators=(",", ":")))
    with pytest.raises(ValueError, match="target blocks differ"):
        LE.write_theorem_file(bad, "spin_x", tmp_path / "x.lean")
    with pytest.raises(ValueError, match="bad theorem name"):
        LE.write_theorem_file(r["cert_path"], "a_far_too_long_theorem_name", tmp_path / "x.lean")


def test_exporter_mismatch_accepts_the_exporters_own_certificate(ub_cert):
    assert LE._exporter_mismatch(ub_cert["cert_path"]) is None

"""Unit tests for su2plaq.lsh.lean_export (prompts/400 step 7.L2): integer tables, circuit segments, generated block of
lean/Su2Plaq/LSH/Circuit.lean equals the Python objects, source hygiene of the Lean files."""
import functools
import json
import pathlib
import shutil
import subprocess

import numpy as np
import pytest

from su2plaq.circuits.lsh import build_UB
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import lean_export as LE
from su2plaq.lsh import walk as W
from su2plaq.metrics.logical import logical_metrics

ROOT = pathlib.Path(__file__).resolve().parents[2]
CIRCUIT = ROOT / "lean" / "Su2Plaq" / "LSH" / "Circuit.lean"
COUNTS = ROOT / "lean" / "Su2Plaq" / "LSH" / "Counts.lean"


@functools.lru_cache(maxsize=1)
def enc():
    return LSH()


def test_integer_tables():
    e = enc()
    codes = e.inner_codes().tolist()
    cp, pt, an = LE.coupling_ints(e), LE.partner_ints(e), LE.angle_ints(e)
    assert len(cp) == len(pt) == 47 and sorted(set(cp)) == [-4, -1, 0, 2]
    assert [cp.count(v) for v in (-4, -1, 2, 0)] == [2, 2, 12, 31]
    table, ptab = W.coupling_table(e), W.partner_table(e)
    assert all(2 * table[c] == x for c, x in zip(codes, cp)) and pt == [ptab.get(c, c) for c in codes]
    assert all(pt[codes.index(p)] == c for c, p in zip(codes, pt))      # involution
    assert an == [-7, -2, 6, 3]
    lm = logical_metrics(build_UB(0.61))
    assert np.allclose(sorted(np.array(an) * 0.61 / 2), sorted(lm["rz_angles"]), atol=1e-9)


def test_literals_format():
    lit = LE.lean_literals(enc())
    assert set(lit) == {"codes", "coupling", "partner", "angles"}
    assert lit["codes"] == "[" + ", ".join(str(c) for c in enc().inner_codes().tolist()) + "]"
    assert lit["angles"] == "[-7, -2, 6, 3]"


def test_segments_cover_skeleton():
    seg = LE.circuit_segments()
    steps, _ = W.skeleton(0)
    assert seg["trans"] == list(W.TRANSCODE) and seg["frame"] == list(W.FRAME)
    assert len(seg["flags"]) == 15 and [s[0] for s in seg["walk"]].count("rz") == 4
    n = len(seg["trans"]) + len(seg["frame"]) + 1 + len(seg["flags"]) + len(seg["walk"])
    assert steps[:n] == seg["trans"] + seg["frame"] + [("h", 0)] + seg["flags"] + seg["walk"]


def test_generated_block_equals_python(tmp_path):
    """The block in the committed Circuit.lean is what write_lean_tables writes now (drift detector); the writer is idempotent
    and refuses a file without markers."""
    copy = tmp_path / "Circuit.lean"
    shutil.copy(CIRCUIT, copy)
    LE.write_lean_tables(copy)
    assert copy.read_text() == CIRCUIT.read_text()
    text = CIRCUIT.read_text()
    block = text[text.index("-- BEGIN generated"):text.index("-- END generated")]
    for key, lit in LE.lean_literals(enc()).items():
        assert lit in block, key
    seg = LE.circuit_segments()
    for name, ops in (("transOps", seg["trans"]), ("frameOps", seg["frame"]), ("flagOps", seg["flags"]), ("walkOps", seg["walk"])):
        line = next(ln for ln in block.splitlines() if ln.startswith(f"def {name} "))
        assert line == f"def {name} : List Op := " + LE._ops(ops)
    # a tampered table is repaired by the writer
    tampered = tmp_path / "T.lean"
    tampered.write_text(text.replace("[-7, -2, 6, 3]", "[-7, -2, 6, 4]"))
    LE.write_lean_tables(tampered)
    assert tampered.read_text() == text
    nomark = tmp_path / "N.lean"
    nomark.write_text("def x := 1\n")
    with pytest.raises(ValueError):
        LE.write_lean_tables(nomark)


def test_op_rendering():
    assert LE._op(("cx", 1, 2)) == ".cx 1 2" and LE._op(("x", 3)) == ".x 3"
    assert LE._op(("rccx", 2, 0, 1)) == ".ccx 2 0 1" and LE._op(("rz", 0)) == ".rz 0"
    with pytest.raises(ValueError):
        LE._op(("h", 0))


def test_lean_sources_hygiene():
    for p in (COUNTS, CIRCUIT):
        src = p.read_text()
        assert "native_decide" not in src and "sorry" not in src and "admit" not in src
        assert "namespace Su2Plaq.LSH" in src and "end Su2Plaq.LSH" in src
    assert "import Su2Plaq.SpinNet.Circuit" in CIRCUIT.read_text()
    root = (ROOT / "lean" / "Su2Plaq.lean").read_text()
    assert "import Su2Plaq.LSH.Counts" in root and "import Su2Plaq.LSH.Circuit" in root
    # the count theorems carry the locked values
    src = COUNTS.read_text()
    for name, v in (("card_site_codes", 5), ("card_inner_codes", 47), ("card_bright_codes", 16), ("card_dark_codes", 31),
                    ("card_states_lsh", 433), ("card_bright_states", 256), ("card_raw_inner", 82), ("card_raw_states", 5920)):
        assert f"= {v}" in src.split(f"theorem {name}", 1)[1].split("\n", 1)[0]


# ---- step 7.L3: native certificate -----------------------------------------------------------------------------------
from su2plaq.circuits.lsh import build_UE, build_step  # noqa: E402
from su2plaq.lsh import operators as O  # noqa: E402


@pytest.mark.parametrize("kind,order", LE.LSH_TARGETS)
def test_exact_target_equals_float_target(kind, order):
    """Exact Laurent target evaluated at the three angle pairs equals `enc.target` (1e-12)."""
    e = enc()
    for a, b in ((0.37, 0.61), (0.91, 0.23), (1.70, 1.00)):
        assert np.abs(LE.laurent_target_matrix(e, kind, a, b, order) - e.target(kind, a, b, order)).max() <= 1e-12


def test_exact_states_and_electric_weight():
    e = enc()
    st = LE.exact_states(e)
    assert len(st) == 433 and all(len(s["codes"]) == 1 for s in st)
    assert sorted(int(s["codes"][0]) for s in st) == O.physical_codes().tolist()
    nel = LE._n_inner_half(e)
    assert np.abs(e.h_electric() - 0.75 * np.array(nel)).max() < 1e-12 and set(nel) == {0, 1, 2, 3, 4}
    assert LE.target_base("UB") == (4, 4) and LE.target_base("step", 2) == (8, 4) and LE.target_base("step", 1) == (4, 4)
    with pytest.raises(ValueError):
        LE.exact_target_blocks(e, "nope")
    with pytest.raises(ValueError):
        LE.exact_target_blocks(e, "step", 3)


def test_pins_file_is_current(tmp_path):
    out = LE.write_pins(tmp_path / "Pins.lean")
    assert out.read_text() == LE.LSH_PINS_FILE.read_text()
    p = LE.compute_pins(enc())
    assert len(p["states"]) == 64 and set(p["targets"]) == {"UE:1", "UB:1", "step:1", "step:2"}
    assert len(set(p["targets"].values())) == 4


def test_certify_certified_rejected_n_a(tmp_path):
    e = enc()
    ok = LE.certify(build_step(0.37, 0.61, 1, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)
    assert ok["status"] == "certified" and ok["axioms"] == [] and pathlib.Path(ok["cert_path"]).exists()
    cert = json.loads(pathlib.Path(ok["cert_path"]).read_text())
    assert cert["n_data"] == 12 and cert["n_outer"] == 12 and cert["n_qubits"] == 31 and len(cert["states"]) == 433
    assert cert["circuit_id"].startswith("lsh-step-o1-") and cert["provenance"]["exporter"] == "su2plaq.lsh.lean_export"
    for qc, kind, order in ((build_step(0.37, 0.61, 2, with_outer=True), "step", 2), (build_step(0.37, 0.61, 1), "step", 1),
                            (build_UE(0.37, with_outer=True), "UE", 1)):
        assert LE.certify(qc, e, "UE" if kind == "UE" else kind, 0.37, 0.61, order, out_dir=tmp_path)["status"] == "certified"
    from su2plaq.circuits.lsh import build_UB
    assert LE.certify(build_UB(0.61, with_outer=True), e, "UB", 0.37, 0.61, 1, out_dir=tmp_path)["status"] == "certified"
    # wrong target kind, wrong sign of beta: rejected by the exact checker
    r = LE.certify(build_UB(0.61, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "rejected" and "differs from the target" in r["reason"]
    assert LE.certify(build_step(0.37, -0.61, 1, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)["status"] == "rejected"
    # an angle that is not a rational multiple of alpha / beta is not representable: n_a
    r = LE.certify(build_step(0.37, 0.61 * (1 + 1e-6), 1, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)
    assert r["status"] == "n_a" and r["reason"].startswith("non_linear_angle") and r["cert_path"] is None
    # too many qubits / bad layout / unknown kind
    from qiskit import QuantumCircuit
    assert LE.export_certificate(QuantumCircuit(63), e, "UB", 0.37, 0.61, 1, tmp_path / "x.json") == "too_many_qubits"
    assert LE.export_certificate(QuantumCircuit(5), e, "UB", 0.37, 0.61, 1, tmp_path / "x.json").startswith("bad_layout")
    with pytest.raises(ValueError):
        LE.export_certificate(build_UE(0.37), e, "nope", 0.37, 0.61, 1, tmp_path / "x.json")


def test_checker_rejects_tampered_certificates(tmp_path):
    """Changing a pinned state, a target entry or the register size makes the Lean checker REJECT (pins / validation)."""
    e = enc()
    res = LE.certify(build_step(0.37, 0.61, 1, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)
    path = pathlib.Path(res["cert_path"])
    base = json.loads(path.read_text())

    def check(d):
        q = tmp_path / "t.json"
        q.write_text(json.dumps(d, separators=(",", ":")))
        return LE.check_certificate(q)

    assert LE.check_certificate(path)["status"] == "certified"
    d = json.loads(json.dumps(base))
    d["states"][5]["terms"][0]["code"] = (1 << 24) - 1                 # a basis state no physical state uses
    r = check(d)
    assert r["status"] == "rejected" and "pinned" in r["reason"]
    d = json.loads(json.dumps(base))
    d["n_data"], d["n_outer"] = 8, 8
    r = check(d)
    assert r["status"] == "rejected" and "12 data and 12 outer" in r["reason"]
    d = json.loads(json.dumps(base))
    ents = [en for b in d["target"]["blocks"] for en in b["entries"]]
    other = next(en[2] for en in ents if en[2] != ents[0][2])
    ents[0][2] = other                                                   # a different Laurent polynomial in one entry
    r = check(d)
    assert r["status"] == "rejected"
    d = json.loads(json.dumps(base))
    d["gates"][len(d["gates"]) // 2] = d["gates"][0]                   # one gate replaced
    assert check(d)["status"] == "rejected"
    bad = tmp_path / "garbage.json"
    bad.write_text("{not json")
    assert LE.check_certificate(bad)["status"] == "rejected"


def test_fingerprint_matches_pins(tmp_path):
    e = enc()
    res = LE.certify(build_step(0.37, 0.61, 1, with_outer=True), e, "step", 0.37, 0.61, 1, out_dir=tmp_path)
    out = subprocess.run([str(LE.checker_exe()), "fingerprint", res["cert_path"]], capture_output=True, text=True, check=True).stdout
    p = LE.compute_pins(e)
    assert f"states {p['states']}" in out and f"target {p['targets']['step:1']}" in out

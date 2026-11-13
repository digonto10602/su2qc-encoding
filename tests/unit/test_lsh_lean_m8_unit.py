"""Unit tests of the M8 step 8.A2 / 8.L additions to su2plaq.lsh.lean_export (prompts/401): binding fields, git_dirty,
gates_sha256, the no-rewrite rule of `certify`, and the theorem-file writer (text and refusals; elaboration is M8-L3)."""
import functools
import hashlib
import json
import pathlib

import pytest

from su2plaq.circuits.lsh import build_UE
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import lean_export as LE

ROOT = pathlib.Path(__file__).resolve().parents[2]
BIND = {"entry_id": "r00-seed-000", "program_file_sha256": "ab" * 32}


@functools.lru_cache(maxsize=1)
def enc():
    return LSH()


def _export(tmp_path, name="c.json", **kw):
    out = LE.export_certificate(build_UE(0.37, with_outer=True), enc(), "UE", 0.37, 0.61, 1, tmp_path / name, **kw)
    assert not isinstance(out, str), out
    return json.loads(pathlib.Path(out).read_text())


def test_export_binding_dirty_and_gates_sha(tmp_path):
    c = _export(tmp_path, extra_provenance=BIND)
    assert c["provenance"]["entry_id"] == BIND["entry_id"] and c["provenance"]["program_file_sha256"] == BIND["program_file_sha256"]
    assert isinstance(c["provenance"]["git_dirty"], bool) and len(c["provenance"]["git_commit"]) >= 7
    h = hashlib.sha256(json.dumps(c["gates"]).encode()).hexdigest()
    assert c["gates_sha256"] == c["program_sha256"] == h and c["circuit_id"].endswith(h[:12])
    plain = _export(tmp_path, "p.json")
    assert "entry_id" not in plain["provenance"] and plain["circuit_id"] == c["circuit_id"]


def test_same_up_to_volatile():
    a = {"provenance": {"git_commit": "a", "git_dirty": True, "export_seconds": 1.0, "float_phase_spread": 1e-16,
                                       "x": 1}, "gates": [1]}
    b = json.loads(json.dumps(a))
    b["provenance"].update({"git_commit": "b", "git_dirty": False, "export_seconds": 9.0, "float_phase_spread": 3e-16})
    assert LE.VOLATILE_PROVENANCE == ("git_commit", "git_dirty", "export_seconds")
    assert LE._same_up_to_volatile(a, b)
    b["provenance"]["x"] = 2
    assert not LE._same_up_to_volatile(a, b)
    b["provenance"]["x"] = 1
    b["gates"] = [2]
    assert not LE._same_up_to_volatile(a, b)
    b["gates"] = [1]
    b["provenance"]["float_phase_spread"] = 1e-3
    assert not LE._same_up_to_volatile(a, b)


def test_certify_no_rewrite_and_binding_change(tmp_path, monkeypatch):
    """`certify` with a stubbed checker: unchanged certificate keeps its bytes (also when only commit/dirty/time differ),
    a changed binding rewrites it, no temporary file is left behind."""
    monkeypatch.setattr(LE, "check_certificate", lambda p, timeout=0: {"status": "certified", "reason": "", "seconds": 0.0,
                                                                         "checker_sha256": "x"})
    qc = build_UE(0.37, with_outer=True)
    r1 = LE.certify(qc, enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path, extra_provenance=BIND)
    f = pathlib.Path(r1["cert_path"])
    d = json.loads(f.read_text())
    d["provenance"].update({"git_commit": "0000000", "git_dirty": True, "export_seconds": 123.0})
    f.write_text(json.dumps(d, separators=(",", ":")))
    b1 = f.read_bytes()
    r2 = LE.certify(build_UE(0.37, with_outer=True), enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path, extra_provenance=dict(BIND))
    assert pathlib.Path(r2["cert_path"]) == f and f.read_bytes() == b1
    LE.certify(qc, enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path, extra_provenance={**BIND, "entry_id": "r01"})
    assert json.loads(f.read_text())["provenance"]["entry_id"] == "r01"
    LE.certify(qc, enc(), "UE", 0.37, 0.61, 1, out_dir=tmp_path)
    assert "entry_id" not in json.loads(f.read_text())["provenance"]
    assert [p.name for p in tmp_path.iterdir()] == [f.name]


def test_theorem_file_text_and_refusals(tmp_path):
    c = _export(tmp_path)
    cp = tmp_path / "cert.json"
    cp.write_text(json.dumps(c, separators=(",", ":")))
    out = LE.write_theorem_file(cp, "lsh_ue", tmp_path / "t.lean", comment="entry e, program sha256 " + "0" * 64)
    text = out.read_text()
    assert text.startswith("-- entry e, program sha256 ") and "import Su2PlaqCert.LSH.Check\n" in text
    assert "theorem lsh_ue : Su2PlaqCert.LSH.checkJsonString certJson = true := by native_decide" in text
    assert "#print axioms lsh_ue" in text and text.count("def certJson") == 1
    lit = text.split('def certJson : String := "', 1)[1].split('"\n\ntheorem', 1)[0]
    assert json.loads(lit.replace('\\"', '"').replace("\\\\", "\\")) == c           # the literal is the certificate
    with pytest.raises(ValueError):
        LE.write_theorem_file(cp, "bad name!", tmp_path / "x.lean")
    with pytest.raises(ValueError):
        LE.write_theorem_file(cp, "lsh_ue", tmp_path / "x.lean", comment="two\nlines")
    c["states"][0]["terms"][0]["code"] = int(c["states"][0]["terms"][0]["code"]) ^ 1
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(c, separators=(",", ":")))
    with pytest.raises(ValueError):
        LE.write_theorem_file(bad, "lsh_bad", tmp_path / "bad.lean")
    c2 = _export(tmp_path, "d.json")
    c2["n_data"] = 8
    nb = tmp_path / "nb.json"
    nb.write_text(json.dumps(c2))
    with pytest.raises(ValueError):
        LE.write_theorem_file(nb, "lsh_nb", tmp_path / "nb.lean")

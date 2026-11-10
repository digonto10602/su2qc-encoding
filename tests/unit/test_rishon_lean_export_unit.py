"""Unit tests for su2plaq.rishon.lean_export HB certificate (step 5.L3): export values computed from the code,
exact Python mirror of the Lean checker, Lean text generation, and (fast, ~3 s each) real Lean runs."""
import collections
import json
import pathlib

import numpy as np
import pytest

from su2plaq.rishon import lean_export as LE
from su2plaq.rishon import operators as O


@pytest.fixture(scope="module")
def cert(tmp_path_factory):
    path = LE.export_hb_certificate(tmp_path_factory.mktemp("hb") / "hb.json")
    return json.loads(pathlib.Path(path).read_text())


def val(z):
    return z[0] + z[1] * np.sqrt(2.0)


def test_export_structure_and_values(cert):
    assert cert["schema"] == LE.HB_SCHEMA and cert["n_codes"] == 1296 and len(cert["pairs"]) == 81
    assert [op["name"] for op in cert["link_ops"]] == ["U00", "U01", "U10", "U11", "Ud00", "Ud01", "Ud10", "Ud11"]
    assert all(len(op["entries"]) == 2 for op in cert["link_ops"])
    kap = collections.Counter(tuple(p["kappa"]) for p in cert["pairs"])
    assert kap == {(1, 0): 32, (2, 0): 48, (0, 4): 1}
    # the integer pairs reproduce the numerical bright pairs of the code (4u, 4v, kappa)
    for p, (u, v, k) in zip(cert["pairs"], O.bright_pairs()):
        assert abs(val(p["kappa"]) - k) < 1e-12
        for key, x in (("u", u), ("v", v)):
            dense = np.zeros(1296)
            for i, a, b in p[key]:
                dense[i] = val((a, b))
            assert np.abs(dense - 4.0 * x).max() < 1e-12


def test_mirror_accepts_and_rejects(cert):
    assert all(LE.check_hb_python(cert).values())
    bad = json.loads(json.dumps(cert))
    i = next(i for i, p in enumerate(bad["pairs"]) if p["kappa"] == [2, 0])
    bad["pairs"][i]["kappa"] = [1, 0]
    r = LE.check_hb_python(bad)
    assert not r["identity"] and not r["kappa"] and r["ortho"] and r["dark"]
    bad = json.loads(json.dumps(cert))
    bad["link_ops"][0]["entries"][0][2] *= -1
    assert not LE.check_hb_python(bad)["identity"]
    bad = json.loads(json.dumps(cert))
    bad["pairs"][0]["u"][0][1] += 1
    r = LE.check_hb_python(bad)
    assert not r["ortho"] and not r["identity"]


def test_zs_conversion():
    assert LE._zs(4 * np.sqrt(2.0)) == [0, 4] and LE._zs(-2.0) == [-2, 0] and LE._zs(1 / np.sqrt(2.0) * 4) == [0, 2]
    with pytest.raises(ValueError):
        LE._zs(0.3)


def test_write_hb_lean_text(cert, tmp_path):
    cp = tmp_path / "c.json"
    cp.write_text(json.dumps(cert))
    f = LE.write_hb_lean(cp, tmp_path / "t.lean")
    text = f.read_text()
    assert "import Su2PlaqCert.Rishon.HB" in text and "native_decide" in text and "sorry" not in text
    assert "def rishonHBCert" in text and "theorem rishon_hb_structure" in text
    f2 = LE.write_hb_lean(cp, tmp_path / "t2.lean", data_path=tmp_path / "HBData.lean")
    assert "def rishonHBCert" not in f2.read_text() and "import Su2PlaqCert.Rishon.HBData" in f2.read_text()
    assert "def rishonHBCert" in (tmp_path / "HBData.lean").read_text()
    with pytest.raises(ValueError):
        cp.write_text(json.dumps({"schema": "other"}))
        LE.write_hb_lean(cp, tmp_path / "x.lean")


def test_repo_generated_files_match_code(cert, tmp_path):
    """The committed HBData.lean / certs file are exactly what the exporter generates now (no hand edits, no drift)."""
    cp = tmp_path / "c.json"
    cp.write_text(json.dumps(cert))
    LE.write_hb_lean(cp, tmp_path / "t.lean", data_path=tmp_path / "HBData.lean")
    from su2plaq.lean import project
    assert (tmp_path / "HBData.lean").read_text() == (project.LEAN_DIR / "Su2PlaqCert/Rishon/HBData.lean").read_text()
    assert (tmp_path / "t.lean").read_text() == (project.LEAN_DIR / "certs/rishon-hb-structure.lean").read_text()


def test_check_hb_statuses(tmp_path):
    ok = tmp_path / "ok.lean"
    ok.write_text("theorem t : 2 + 2 = 4 := by native_decide\n#print axioms t\n")
    r = LE.check_hb(ok, timeout=300)
    assert r["status"] == "certified" and len(set(r["axioms"]) - {"propext", "Classical.choice", "Quot.sound"}) == 1
    no = tmp_path / "no.lean"
    no.write_text("theorem t : 2 + 2 = 5 := by native_decide\n#print axioms t\n")
    assert LE.check_hb(no, timeout=300)["status"] == "rejected"
    broken = tmp_path / "broken.lean"
    broken.write_text("theorem t : := by\n")
    assert LE.check_hb(broken, timeout=300)["status"] == "error"


def test_lean_accepts_repo_file_and_rejects_tampering(cert, tmp_path):
    from su2plaq.lean import project
    assert LE.check_hb(project.LEAN_DIR / "certs/rishon-hb-structure.lean", timeout=300)["status"] == "certified"
    for name, edit in (("kappa", lambda c: c["pairs"][next(i for i, p in enumerate(c["pairs"]) if p["kappa"] == [2, 0])].__setitem__("kappa", [1, 0])),
                       ("link", lambda c: c["link_ops"][0]["entries"][0].__setitem__(2, -c["link_ops"][0]["entries"][0][2])),
                       ("vector", lambda c: c["pairs"][0]["u"][0].__setitem__(1, 5))):
        bad = json.loads(json.dumps(cert))
        edit(bad)
        bp = tmp_path / f"{name}.json"
        bp.write_text(json.dumps(bad))
        r = LE.check_hb(LE.write_hb_lean(bp, tmp_path / f"{name}.lean"), timeout=300)
        assert r["status"] == "rejected", (name, r["status"], r["detail"][-300:])

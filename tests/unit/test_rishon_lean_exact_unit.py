"""M5x (prompts/202): unit tests of the exact-statement exports.  W0: stubs exist and raise; W1: HBLink.lean source checks."""
import importlib
import pathlib

import pytest

LE = importlib.import_module("su2plaq.rishon.lean_export")
ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_m5x_theorem_names_and_paths():
    assert len(LE.RISHON_M5X_THEOREMS) == 11 and len(set(LE.RISHON_M5X_THEOREMS)) == 11
    assert all(n.startswith("Su2Plaq.Rishon.") for n in LE.RISHON_M5X_THEOREMS)
    for p in (LE.HBLINK_LEAN, LE.CORNER_KERNEL_LEAN, LE.UE_SEMANTICS_LEAN, LE.BRIDGE_LEAN):
        assert p.parent == ROOT / "lean" / "Su2Plaq" / "Rishon" and p.suffix == ".lean"
    assert LE.UE_GATE_NAMES == ("x", "cx", "p")


def test_hblink_lean_source_conventions():
    src = LE.HBLINK_LEAN.read_text()
    for bad in ("native_decide", "sorry", "admit", "import Mathlib"):
        assert bad not in src
    imports = [ln.split()[1] for ln in src.splitlines() if ln.startswith("import ")]
    assert sorted(imports) == ["Su2Plaq.Rishon.JW", "Su2PlaqCert.Rishon.HBData"]
    for name in ("hb_link_ops_from_jw", "hb_link_ops_count", "det_u_identity", "u_commute"):
        assert f"theorem {name}" in src and f"Su2Plaq.Rishon.{name}" in LE.RISHON_M5X_THEOREMS
        assert src.split(f"theorem {name}", 1)[1].split(":= by", 1)[1].lstrip().startswith("decide +kernel")


def test_hblink_data_is_the_certificate_field():
    """linkOpsData is the certificate's own list (not retyped): HBData.lean carries 8 link operator literals."""
    data = (ROOT / "lean" / "Su2PlaqCert" / "Rishon" / "HBData.lean").read_text()
    block = data.split("linkOps := [", 1)[1].split("pairs :=", 1)[0]
    assert block.count("[(") == 8

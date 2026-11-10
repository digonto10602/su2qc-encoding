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


# --- W2: CornerKernel.lean -----------------------------------------------------------------------------------------------
def test_corner_kernel_lean_source_conventions():
    src = LE.CORNER_KERNEL_LEAN.read_text()
    for bad in ("native_decide", "sorry", "admit", "import Mathlib"):
        assert bad not in src
    imports = [ln.split()[1] for ln in src.splitlines() if ln.startswith("import ")]
    assert imports == ["Su2Plaq.Rishon.JW"]
    assert "mode true 8" in src and "mode false 8" in src
    stmt = src.split("theorem corner_kernel_dims", 1)[1]
    assert "(List.range 81)" in stmt and "decide +kernel" in stmt.split(":= by", 1)[1]


def test_lean_eval_raises_on_lean_error():
    with pytest.raises(RuntimeError):
        LE.lean_eval("#eval (undefined_symbol_for_test : Nat)", imports=("Su2Plaq.Rishon.JW",))


def test_lean_eval_returns_stdout():
    assert LE.lean_eval("#eval 6 * 7", imports=("Su2Plaq.Rishon.JW",)).strip() == "42"


def test_lean_corner_kernel_dims_against_python_fusion():
    """Spot values and the fusion rule computed here in Python (independent of Lean's cornerCountR)."""
    dims = LE.lean_corner_kernel_dims()
    assert len(dims) == 81 and all(isinstance(d, int) and d >= 0 for d in dims)

    def singlets(spins):
        mult = {0: 1}
        for s in spins:
            new = {}
            for J, m in mult.items():
                for J2 in range(abs(J - s), J + s + 1, 2):
                    new[J2] = new.get(J2, 0) + m
            mult = new
        return mult.get(0, 0)

    for m in range(81):
        ends = [(m // 3 ** e) % 3 for e in range(4)]
        assert dims[m] == singlets(tuple(1 if x == 2 else 0 for x in ends)), (m, ends)


# --- W3: UESemantics.lean, gate export ----------------------------------------------------------------------------------
def _ue(alpha=1.0, outer=False):
    from su2plaq.circuits.rishon import build_UE
    return build_UE(alpha, with_outer=outer, include_outer_electric=outer)


def test_ue_semantics_lean_source_conventions():
    src = LE.UE_SEMANTICS_LEAN.read_text()
    for bad in ("native_decide", "sorry", "admit", "import Mathlib"):
        assert bad not in src
    assert [ln.split()[1] for ln in src.splitlines() if ln.startswith("import ")] == ["Su2Plaq.Rishon.JW"]
    for name in ("card_inner_codes", "ue_gadget_sector", "ue_gates_structure", "ue_outer_gates_structure", "ue_exact_all_codes"):
        assert src.split(f"theorem {name}", 1)[1].split(":= by", 1)[1].lstrip().startswith("decide +kernel")


def test_generated_block_has_no_drift():
    src = LE.UE_SEMANTICS_LEAN.read_text()
    assert f"def ueGates : List Gate := {LE.ue_gate_literal(_ue())}\n" in src
    assert f"def ueOuterGates : List Gate := {LE.ue_gate_literal(_ue(outer=True))}\n" in src
    assert LE.ue_gate_literal(_ue(0.37)) == LE.ue_gate_literal(_ue())


def test_ue_gate_ints_shapes_and_values():
    g = LE.ue_gate_ints(_ue(0.61))
    assert len(g) == 12 and g[:3] == [("cx", 0, 1), ("p", 1, -3), ("cx", 0, 1)]
    assert len(LE.ue_gate_ints(_ue(outer=True))) == 36
    assert LE.ue_gate_literal(_ue()).startswith("[.cx 0 1, .p 1 (-3), .cx 0 1, ")


def test_ue_gate_ints_rejections():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(16)
    qc.metadata = {"alpha": 1.0}
    qc.p(0.3, 0)                                  # 0.3 / 0.25 = 1.2: not an integer
    with pytest.raises(ValueError):
        LE.ue_gate_ints(qc)
    qc = QuantumCircuit(20)
    qc.metadata = {"alpha": 1.0}
    with pytest.raises(ValueError):
        LE.ue_gate_ints(qc)
    qc = QuantumCircuit(16)
    qc.metadata = {"alpha": 1.0}
    qc.cz(0, 1)
    with pytest.raises(ValueError):
        LE.ue_gate_ints(qc)
    qc = QuantumCircuit(16)
    qc.p(0.25, 0)                                 # no alpha in the metadata
    with pytest.raises(ValueError):
        LE.ue_gate_ints(qc)
    qc.metadata = {"alpha": 0.0}
    with pytest.raises(ValueError):
        LE.ue_gate_ints(qc)


def test_write_lean_ue_gates_roundtrip_and_markers(tmp_path):
    copy = tmp_path / "UE.lean"
    copy.write_text(LE.UE_SEMANTICS_LEAN.read_text().replace("(-3), .cx 0 1, .cx 4 5", "(-2), .cx 0 1, .cx 4 5", 1))
    assert copy.read_text() != LE.UE_SEMANTICS_LEAN.read_text()
    LE.write_lean_ue_gates(copy)                  # the generated block is restored
    assert copy.read_text() == LE.UE_SEMANTICS_LEAN.read_text()
    bad = tmp_path / "nomarker.lean"
    bad.write_text("def ueGates : List Gate := []\n")
    with pytest.raises(ValueError):
        LE.write_lean_ue_gates(bad)


def test_lean_ue_gate_images_match_qiskit():
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator
    alpha = 0.37
    for gate in (("x", 1), ("cx", 1, 0), ("p", 0, -3)):
        ref = QuantumCircuit(2)
        if gate[0] == "p":
            ref.p(gate[2] * alpha / 4, gate[1])
        else:
            getattr(ref, gate[0])(*gate[1:])
        assert abs(LE.lean_ue_gate_images(gate, 2, alpha) - Operator(ref).data).max() <= 1e-12

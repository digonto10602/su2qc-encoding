"""Unit tests for the exact-Lean half of spinnet/lean_export.py (prompts/102 steps W0-W1): generated Recoupling block,
lean_eval error handling, Lean-side codes/states/6j.  W2/W3 tests are added with their steps."""
import functools
import pathlib
import shutil

import numpy as np
import pytest

from su2plaq.encodings.spinnet import SpinNet
from su2plaq.spinnet import lean_export as LE
from su2plaq.su2.wigner import six_j


@functools.lru_cache(maxsize=None)
def enc():
    return SpinNet()


def test_w0_interface_names_exist():
    for name in ("RECOUPLING_LEAN", "SEMANTICS_LEAN", "SPECTRUM_LEAN", "BRIDGE_LEAN"):
        p = getattr(LE, name)
        assert isinstance(p, pathlib.Path) and p.parent.name == "SpinNet" and p.suffix == ".lean"
    assert LE.GATE_NAMES == ("x", "cx", "rccx", "h", "rz")
    for fn in ("gate_ints", "gate_literal", "write_lean_exact_tables", "lean_eval", "lean_sixj_table",
               "lean_valid_codes", "lean_states", "lean_gate_images"):
        assert callable(getattr(LE, fn))


def _ub():
    from su2plaq.circuits.spinnet import build_UB
    return build_UB(1.0)


def test_gate_ints_matches_circuit_and_angles():
    qc = _ub()
    gates = LE.gate_ints(qc)
    assert len(gates) == len(qc.data) == 48
    assert [g[2] for g in gates if g[0] == "rz"] == LE.angle_ints(enc())
    for g, ins in zip(gates, qc.data):
        assert g[0] == ins.operation.name
        assert list(g[1:1 + len(ins.qubits)]) == [qc.find_bit(q).index for q in ins.qubits]


def test_gate_ints_rejects_bad_circuits():
    from qiskit import QuantumCircuit
    from su2plaq.circuits.spinnet import build_UB
    with pytest.raises(ValueError):                              # outer register is not modelled
        LE.gate_ints(build_UB(1.0, with_outer=True))
    bad = QuantumCircuit(15, metadata={"beta": 1.0})
    bad.rz(0.123, 0)                                             # 0.123 / 0.5 is not an integer
    with pytest.raises(ValueError):
        LE.gate_ints(bad)
    bad = QuantumCircuit(15, metadata={"beta": 1.0})
    bad.cz(0, 1)                                                 # gate outside GATE_NAMES
    with pytest.raises(ValueError):
        LE.gate_ints(bad)
    nobeta = QuantumCircuit(15)
    nobeta.x(0)
    with pytest.raises(ValueError):
        LE.gate_ints(nobeta)


def test_gate_literal_format_and_beta_independence():
    from su2plaq.circuits.spinnet import build_UB
    lit = LE.gate_literal(_ub())
    assert lit.startswith("[.cx 1 3, .cx 0 1, .cx 0 2, .h 0, ") and lit.endswith(".cx 0 1, .cx 1 3]")
    assert ".rz 0 (-7)" in lit and ".rz 0 6" in lit and lit.count(",") == 47
    assert LE.gate_literal(build_UB(0.61)) == lit


def test_exact_semantics_block_matches_committed_file(tmp_path):
    src = LE.SEMANTICS_LEAN
    assert src.exists(), "Semantics.lean missing"
    text = src.read_text()
    assert f"def ubGates : List Gate := {LE.gate_literal(_ub())}" in text
    copy = tmp_path / "Semantics.lean"
    copy.write_text(text.replace(".rz 0 (-7)", ".rz 0 (-6)"))
    assert LE._write_semantics_gates(copy) == copy
    assert copy.read_text() == text
    assert LE._write_semantics_gates(copy) == copy and copy.read_text() == text
    f = tmp_path / "bad.lean"
    f.write_text("namespace X\nend X\n")
    with pytest.raises(ValueError):
        LE._write_semantics_gates(f)


def test_write_lean_exact_tables_is_idempotent_on_committed_files():
    before = (LE.RECOUPLING_LEAN.read_text(), LE.SEMANTICS_LEAN.read_text())
    paths = LE.write_lean_exact_tables()
    assert paths == (LE.RECOUPLING_LEAN, LE.SEMANTICS_LEAN)
    assert (LE.RECOUPLING_LEAN.read_text(), LE.SEMANTICS_LEAN.read_text()) == before


def test_lean_gate_images_basic_gates():
    beta = 0.61
    x = LE.lean_gate_images(("x", 0), 2, beta)
    assert np.array_equal(x, np.array([[0, 1, 0, 0], [1, 0, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex))
    rz = LE.lean_gate_images(("rz", 1, 3), 2, beta)
    want = np.exp(1j * beta / 4 * 3 * np.array([-1, -1, 1, 1]))          # diag(z^-a, z^a) on qubit 1, a = 3
    assert np.abs(np.diag(rz) - want).max() <= 1e-14 and np.abs(rz - np.diag(np.diag(rz))).max() == 0
    h = LE.lean_gate_images(("h", 0), 1, beta)
    assert np.abs(h - np.array([[1, 1], [1, -1]]) / np.sqrt(2)).max() <= 1e-15
    with pytest.raises(ValueError):
        LE.lean_gate_images(("x", 2), 2, beta)


def test_exact_recoupling_block_matches_encoding_and_committed_file(tmp_path):
    src = LE.RECOUPLING_LEAN
    assert src.exists(), "Recoupling.lean missing"
    text = src.read_text()
    lit = LE.lean_literals(enc())
    assert f"def exportedCodes : List Nat := {lit['codes']}" in text
    assert f"def exportedTwoK : List Int := {lit['coupling']}" in text
    copy = tmp_path / "Recoupling.lean"
    shutil.copy(src, copy)
    copy.write_text(text.replace(lit["coupling"], "[0, 0]"))
    assert copy.read_text() != text
    assert LE._write_recoupling_tables(copy) == copy
    assert copy.read_text() == text                           # block regenerated byte for byte
    assert LE._write_recoupling_tables(copy) == copy and copy.read_text() == text   # idempotent
    assert text.count("-- BEGIN generated exact") == 1 and text.count("-- END generated exact") == 1


def test_exact_recoupling_block_requires_markers(tmp_path):
    f = tmp_path / "bad.lean"
    f.write_text("namespace X\nend X\n")
    with pytest.raises(ValueError):
        LE._write_recoupling_tables(f)
    assert f.read_text() == "namespace X\nend X\n"


def test_lean_eval_raises_on_lean_error():
    with pytest.raises(RuntimeError) as exc:
        LE.lean_eval("#eval (undefinedNameForTest : Nat)")
    assert "undefinedNameForTest" in str(exc.value)


def test_lean_eval_returns_stdout():
    out = LE.lean_eval("#eval IO.println \"hello 42\"", imports=("Su2Plaq.SpinNet.Recoupling",))
    assert "hello 42" in out


def test_lean_valid_codes_are_the_encoding_codes():
    assert LE.lean_valid_codes() == [int(c) for c in enc().inner_codes()]


def test_lean_states_are_the_433_route_b_codes():
    states = LE.lean_states()
    assert len(states) == 433 and len(set(states)) == 433
    want = set()
    for j, J in enc().labels:
        y = sum(int(j[l] == 0.5) << l for l in range(4)) + sum(int(J[c] == 1.0) << (4 + c) for c in range(4))
        o = sum(int(j[4 + k] == 0.5) << k for k in range(8))
        want.add(y + 256 * o)
    assert set(states) == want


def test_lean_sixj_table_known_values_and_wigner():
    t = LE.lean_sixj_table()
    assert len(t) == 729
    # {0 0 0; 0 0 0} = 1 ; {1/2 1/2 0; 1/2 1/2 0} = -1/2
    assert abs(t[(0, 0, 0, 0, 0, 0)] - 1.0) <= 1e-15
    assert abs(t[(1, 1, 0, 1, 1, 0)] + 0.5) <= 1e-15
    worst = max(abs(v - six_j(*(a / 2 for a in k))) for k, v in t.items())
    assert worst <= 1e-12

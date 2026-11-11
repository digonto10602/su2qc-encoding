"""Unit tests for su2plaq.lsh.lean_export (prompts/400 step 7.L2): integer tables, circuit segments, generated block of
lean/Su2Plaq/LSH/Circuit.lean equals the Python objects, source hygiene of the Lean files."""
import functools
import pathlib
import shutil

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


def test_certificate_functions_are_stubs():
    for f, args in ((LE.certify, (None, None, "step", 0.37, 0.61, 1)), (LE.write_pins, ())):
        with pytest.raises(NotImplementedError):
            f(*args)

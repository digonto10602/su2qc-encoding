"""Step 6.1 unit tests: registration, the compress view, rishon_spec, structure facts, spec text, oracle (prompts/203 section 3.1)."""
import functools
import json

import numpy as np
import pytest

import su2plaq.rishon.compress as RC
from su2plaq.compress import oracle as lap_oracle
from su2plaq.compress import spec as lap_spec
from su2plaq.encodings.base import NOMINAL_ANGLES
from su2plaq.rishon import operators as O
from su2plaq.rishon.compress import oracle as ro
from su2plaq.rishon.compress import spec as S


@functools.lru_cache(maxsize=None)
def _spec(kind="step"):
    return S.rishon_spec(kind)


def test_register_is_idempotent_and_runtime_only():
    v1 = lap_spec.get_encoding("rishon")
    S.register(); S.register()
    assert lap_spec.get_encoding("rishon") is v1 is S._VIEW and NOMINAL_ANGLES["rishon"] == (0.37, 0.61) == S.RISHON_NOMINAL
    assert lap_spec.get_encoding("twelve").name == "twelve"          # the laptop entry is untouched
    with pytest.raises(ValueError):
        lap_spec.get_encoding("nonexistent")


def test_spec_matches_laptop_default_and_cap():
    for kind in ("step", "UB", "UE"):
        sp = S.rishon_spec(kind)
        assert sp.sha256() == lap_spec.default_spec("rishon", kind).sha256() and sp.peak_qubit_cap() == 80
    assert S.rishon_spec("step", 2).order == 2 and S.rishon_spec("step", 2).sha256() != _spec().sha256()
    with pytest.raises(ValueError):
        S.rishon_spec("nope")


def test_view_basis_and_vectors():
    v = lap_spec.get_encoding("rishon")
    codes = O.inner_codes()
    assert v.basis.dim == 1296 and v.basis.labels[5] == (int(codes[5]),) and v.basis.index((int(codes[5]),)) == 5
    with pytest.raises(KeyError):
        v.basis.index((1,))
    pv = v.physical_vectors()
    assert len(pv.codes) == 1296 and pv.n_data == 16 and pv.n_outer == 32 and int(pv.codes[9][0]) == int(codes[9])
    assert v.physical_vectors() is pv
    assert len(v.dark_codes()) == 990 and len(v.bright_pairs()) == 81 and v.registers["d"] == list(range(16))
    assert "State indexing" in v.describe() and "1100" in v.describe() and "neither write it nor read it" in v.describe()
    with pytest.raises(ValueError):
        v.import_map("nope")


def test_code_hash_is_stable_and_lists_existing_files():
    h = RC.code_hash()
    assert len(h) == 64 and h == RC.code_hash()
    import pathlib
    src = pathlib.Path(RC._provenance._SRC)
    assert all((src / f).exists() for f in RC.RISHON_EVALUATOR_FILES if f.startswith(("rishon/compress/spec", "rishon/verify", "circuits/rishon")))


def test_structure_facts_values_and_lean_cross_checks():
    f = S.structure_facts()
    by = {x["name"]: x for x in f["facts"]}
    assert by["card_rishon_physical"]["value"] == 38432 and by["card_rishon_closed"]["value"] == 4352
    assert by["card_inner_codes"]["theorem"] == "Su2Plaq.Rishon.card_inner_codes" and by["card_rishon_physical"]["theorem"] == "Su2Plaq.card_rishon_physical"
    hb = by["hb_bright_pairs"]["value"]
    assert hb["kappa_multiset"] == {"1": 32, "2": 48, "4*sqrt2": 1} and hb["vectors"] == 162
    assert by["heights_raising"]["value"]["raises_all_by_one"] and by["heights_raising"]["value"]["W_cubed_zero"]
    ps = by["pair_supports"]["value"]
    assert len(ps["per_pair"]) == 81 and ps["supports_are_affine"] and all(a == 2 ** c and b == 2 ** d for a, b, c, d in ps["per_pair"])
    assert by["amplitude_alphabet"]["value"] == pytest.approx([1.0, 2 ** -0.5, 0.5, 0.25], abs=1e-8)
    cb = by["closed_bright_block"]["value"]
    assert cb["u_is_vac_sum"] and cb["v_is_loop"] and cb["kappa_closed_form"] == "4*sqrt2" and len(cb["loop_codes"]) == 16
    assert S.structure_facts() == f and S.structure_facts() is not S.structure_facts()         # deterministic deep copies
    with pytest.raises(ValueError):
        S._lean_theorem("Su2Plaq/Rishon/Counts.lean", "no_such_theorem")
    with pytest.raises(ValueError):
        S._lean_number("Su2Plaq/Rishon/Counts.lean", "card_rishon_physical", r"(nothing)(\d+)")


def test_gf2_helpers_and_labels():
    assert S._gf2_rank([0b011, 0b110, 0b101]) == 2
    assert S._affine_dim(np.array([5, 4, 7, 6])) == (2, True) and S._affine_dim(np.array([5, 4, 7])) == (2, False)
    assert S._kappa_label(4 * np.sqrt(2)) == "4*sqrt2" and S._kappa_label(2.0) == "2" and S._kappa_label(1.5) == "1.5"
    assert [S._alphabet_label(a) for a in (1.0, 2 ** -0.5, 0.5, 0.25, 2 ** -1.5)] == ["1", "1/sqrt2", "1/2", "1/4", "1/2sqrt2"]
    with pytest.raises(ValueError):
        S._alphabet_k(0.3)


def test_render_and_write(tmp_path):
    sp = _spec()
    t = S.render_spec(sp)
    assert t == S.render_spec(sp) and "433" not in t and "12-qubit" not in t and "1296" in t and "38432" in t
    assert t.count("outer register") == 2 and t.count("neither write it nor read it") == 1           # no repeated sentence
    assert "not a validity verdict" in t and "reports/tests/215" in t
    nb = S.prune_budget(sp)
    assert isinstance(nb, int) and nb == int(np.floor(1e-11 / S.PRUNE_RATE_PER_BRANCHING_GATE)) == 9090
    assert f"allows about {nb} branching gates" in t and "ccx/ccz and all permutation/phase gates count 0" in t and "Qiskit L3" in t
    pr = {f["name"]: f for f in S.structure_facts()["facts"]}["prune_rates"]["value"]
    assert pr["per_branching_gate"] == S.PRUNE_RATE_PER_BRANCHING_GATE and pr["budget_at_cap"] == nb
    assert {"per_branching_gate", "budget_at_cap", "branching", "engine_exact", "provenance"} == set(pr) and "E2" in pr["provenance"]
    assert t.count("Proved structure (Lean)") == 1 and "Proved structure (Lean)" in t and "4\\sqrt2" in t and "outer_read_unsupported" in t
    p = S.write_spec(sp, tmp_path / "x" / "rishon-step.md")
    assert p.read_text() == t
    assert "Target structure" in S.render_spec(_spec("UE")) and "U=U_E(\\alpha)" in S.render_spec(_spec("UE"))
    j = json.loads(S.write_structure_json(tmp_path / "s.json").read_text())
    assert [x["name"] for x in j["facts"]] == [x["name"] for x in S.structure_facts()["facts"]] and len(j["provenance"]["lean_sources"]) >= 7


def test_oracle_functions_and_cli(capsys):
    sp = _spec()
    V = O.inner_target("step", 0.37, 0.61, 1)
    assert np.abs(ro.target(sp) - V).max() <= 1e-12 and np.abs(lap_oracle.target(sp) - V).max() <= 1e-12
    col = ro.column(sp, 7, top=3)
    assert len(col) <= 3 and abs(col[0][1]) == pytest.approx(np.abs(V[:, 7]).max(), abs=1e-12)
    assert ro.column(sp, (int(O.inner_codes()[7]),), top=1) == col[:1]
    assert abs(ro.element(sp, 4, 4) - V[4, 4]) <= 1e-14
    with pytest.raises(IndexError):
        ro.element(sp, 1296, 0)
    assert "State 3:" in ro.codec(sp, 3) and "State 3:" not in ro.codec(sp)
    allp, closed = ro.pairs(sp), ro.pairs(sp, "closed")
    assert len(allp) == 81 and len(closed) == 1 and closed[0]["kappa"] == pytest.approx(4 * np.sqrt(2)) and len(closed[0]["v"]) == 16
    with pytest.raises(ValueError):
        ro.pairs(sp, "some")
    blk = ro.closed_block(sp)
    assert np.abs(blk.conj().T @ blk - np.eye(3)).max() <= 1e-12
    UB = O.inner_target("UB", None, 0.61)           # the closed block of U_B alone is the 3x3 rotation about kappa = 4 sqrt2
    assert ro.main(["--kind", "UE", "--pairs", "--closed"]) == 0
    out = capsys.readouterr().out
    assert out.count("pair ") == 1 and "kappa=5.656854" in out
    assert ro.main(["--kind", "UB", "--beta", "0.2"]) == 0 and "unitary" in capsys.readouterr().out
    assert ro.main(["--codec", "--state", "0", "--block", "--element", "2", "2", "--column", "1", "--top", "2"]) == 0
    assert "State 0" in capsys.readouterr().out and UB.shape == (1296, 1296)


def test_committed_spec_files_equal_the_renderer():
    root = S._default_root()
    for kind in ("step",):
        assert (root / "compress" / "specs" / f"rishon-{kind}.md").read_text() == S.render_spec(_spec(kind))
    assert json.loads((root / "compress" / "specs" / "rishon-structure.json").read_text()) == S.structure_facts()

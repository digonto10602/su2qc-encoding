"""Unit tests for su2plaq.compress.spec and su2plaq.compress.oracle (M2 step 2.1)."""
import json

import numpy as np
import pytest

from su2plaq.compress import oracle, spec as spec_mod
from su2plaq.compress.spec import TaskSpec, default_spec, get_encoding


@pytest.fixture(scope="module")
def sp():
    return default_spec("twelve", "step")


def test_default_spec_fields_and_validation(sp):
    assert (sp.alpha, sp.beta, sp.order, sp.eps) == (0.37, 0.61, 1, 1e-6)
    assert sp.alt_angles == ((0.91, 0.23), (1.70, 1.00)) and sp.tol_err == sp.tol_gauss == 1e-10 and not hasattr(sp, "tol_leak")
    with pytest.raises(ValueError):
        default_spec("twelve", "bogus")
    with pytest.raises(ValueError):
        default_spec("nope")
    with pytest.raises(ValueError):
        TaskSpec("twelve", "step", 0.1, 0.1, order=3)
    assert sp.peak_qubit_cap() == 12 + 16 + 32


def test_sha256_is_stable_and_field_sensitive(sp):
    assert sp.sha256() == default_spec().sha256() and len(sp.sha256()) == 64
    assert sp.with_angles(0.9, 0.2).sha256() != sp.sha256() and sp.with_angles(sp.alpha, sp.beta).sha256() == sp.sha256()
    assert TaskSpec(**{**sp.to_dict(), "tol_gauss": 1e-9}).sha256() != sp.sha256()


def test_render_sections_and_numbers_from_the_spec(sp, monkeypatch, tmp_path):
    monkeypatch.setattr(spec_mod, "STRUCTURE_JSON", tmp_path / "missing.json")
    t = sp.render()
    order = [t.index(h) for h in ("## Task", "## Registers", "## Circuit model", "## Correctness", "## Cost",
                                  "## Proved structure (Lean)", "## Tools")]
    assert order == sorted(order) and "pending" in t
    for needle in ("(0.91, 0.23)", "(1.7, 1)", "ccx (6, 7, 0)", "rccx (3, 4, 0)", "1e-10", "1e-06", "60 qubits", "625", "433"):
        assert needle in t, needle
    t_ub = default_spec("twelve", "UB").render()
    assert "U_B(\\beta)$" in t_ub and "electric layer first" not in t_ub
    assert "U_E(\\alpha/2)" in TaskSpec(**{**sp.to_dict(), "order": 2}).render()
    # structure section lists the machine-proved facts and skips the numerical ones
    s = tmp_path / "structure.json"
    s.write_text(json.dumps({"facts": [{"name": "card_physical", "value": 433, "proved_by": "decide", "theorem": "Th.card"},
                                       {"name": "guess", "value": 7, "proved_by": "numerical"}]}))
    monkeypatch.setattr(spec_mod, "STRUCTURE_JSON", s)
    t2 = sp.render()
    assert "card_physical" in t2 and "Th.card" in t2 and "guess" not in t2 and "pending" not in t2


def test_write_creates_the_instance_file(sp, tmp_path):
    p = sp.write(tmp_path / "s" / "x.md")
    assert p.read_text() == sp.render()


def test_oracle_views_agree_and_labels_work(sp):
    V = oracle.target(sp)
    enc = get_encoding("twelve")
    assert V.shape == (433, 433) and not V.flags.writeable and np.abs(V.conj().T @ V - np.eye(433)).max() < 1e-12
    col = oracle.column(sp, 7, top=1000)
    assert [r for r, _ in col] == [int(r) for r in np.argsort(-np.abs(V[:, 7]), kind="stable") if abs(V[r, 7]) > 1e-14]
    assert abs(sum(abs(v) ** 2 for _, v in col) - 1) < 1e-12
    lab = enc.basis.labels[11]
    assert oracle.column(sp, lab, 3) == oracle.column(sp, 11, 3) and oracle.element(sp, lab, lab) == V[11, 11]
    with pytest.raises(IndexError):
        oracle.element(sp, 433, 0)


def _supported_patterns():
    from su2plaq.exact.physical import s_o_dims

    nz = sorted(o for o, v in s_o_dims(get_encoding("twelve").basis).items() if v > 0)
    return [0, nz[1], nz[len(nz) // 2], nz[-1]]


@pytest.mark.parametrize("pattern", _supported_patterns())
def test_oracle_blocks_are_unitary_and_sized_by_the_outer_spins(sp, pattern):
    enc = get_encoding("twelve")
    b = oracle.block(sp, pattern)
    spins = []
    k = pattern
    for _ in range(8):
        k, s = divmod(k, 5)
        spins.append(0.0 if s == 0 else 0.5)
    n = sum(1 for j, _ in enc.basis.labels if tuple(j[4:]) == tuple(spins))
    assert b.shape == (n, n) and np.abs(b.conj().T @ b - np.eye(n)).max() < 1e-10
    assert oracle.block(sp, 0).shape == (2, 2)
    with pytest.raises(ValueError):
        oracle.block(sp, 5 ** 8)       # not an outer key
    with pytest.raises(ValueError):
        oracle.block(sp, 1)            # a single half-integer outer link: no gauge-invariant state


def test_codec_and_cli(sp, capsys):
    assert "111" in oracle.codec(sp) and "state k" not in oracle.codec(sp)
    assert "label" in oracle.codec(sp, 0)
    assert oracle.main(["--kind", "ue", "--element", "3", "3"]) == 0
    out = capsys.readouterr().out
    v = oracle.element(default_spec("twelve", "UE"), 3, 3)
    assert abs(complex(out.strip().replace(" ", "")) - v) < 1e-12
    assert oracle.main(["--target", "step", "--column", "0", "--top", "2"]) == 0
    assert capsys.readouterr().out.count("row ") == 2
    assert oracle.main(["--block", "0"]) == 0 and "[[" in capsys.readouterr().out
    assert oracle.main([]) == 0 and "unitary" in capsys.readouterr().out

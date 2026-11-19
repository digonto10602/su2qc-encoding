"""Unit tests of `su2plaq.fuzzy.headline_step` (prompts/010 §4.3, step H.3).  Toy headline cache: both units are the circuit-valued
`general` baseline (so no sandboxed program build); the real headline units are checked by the locked M11-H3."""
import json
from types import SimpleNamespace

import pytest

from su2plaq.compress import archive as A
from su2plaq.compress import robust as RB
from su2plaq.fuzzy import compress_hook as H
from su2plaq.fuzzy import headline_step as HS
from su2plaq.encodings import registry

ROWS = {"fuzzy_ub": {"id": "r10-F1-010", "robust_key": (83, 12640, 0, 30000, 10), "t_mean": 632.0, "t_nominal": 638, "cx": 83},
        "fuzzy_link": {"id": "r02-F2-001", "robust_key": (12, 880, 0, 24000, 4), "t_mean": 44.0, "t_nominal": 44, "cx": 12}}


@pytest.fixture(scope="module", autouse=True)
def _installed():
    H.install()


def _toy(monkeypatch, cached=True):
    def headline(enc, kind, root=None, refresh=False, compute=True):
        assert compute is False and kind == H.UNITS[enc]                  # reads the cache only
        if not cached:
            return None
        r = ROWS[enc]
        return {"id": r["id"], "robust_key": r["robust_key"], "t_mean": r["t_mean"], "ranking": [dict(r)]}

    def load(cls, enc, *a, **k):
        e = SimpleNamespace(id=ROWS[enc]["id"], program_path="compress/programs/x/general.circuit", key=(1.0, 2.0, 3.0, 4.0), valid=True)
        return SimpleNamespace(entries=lambda: [SimpleNamespace(id="other", program_path="x/general.circuit", key=(9, 9, 9, 9), valid=True), e])

    monkeypatch.setattr(RB, "headline", headline)
    monkeypatch.setattr(A.Archive, "load", classmethod(load))


def test_module_is_not_hashed():
    for enc in H.ENCODINGS:
        assert "fuzzy/headline_step.py" not in registry.info(enc).evaluator_files


def test_not_cached_raises_file_not_found(monkeypatch, tmp_path):
    _toy(monkeypatch, cached=False)
    with pytest.raises(FileNotFoundError, match="no cached headline"):
        HS.headline_step(root=tmp_path)


@pytest.mark.parametrize("with_outer", [True, False])
def test_headline_step_composes_the_headline_entries(monkeypatch, tmp_path, with_outer):
    _toy(monkeypatch)
    qc, info = HS.headline_step(root=tmp_path, order=1, with_outer=with_outer)
    assert info["units"]["fuzzy_ub"]["entry"] == "r10-F1-010" and info["units"]["fuzzy_link"]["entry"] == "r02-F2-001"
    assert info["units"]["fuzzy_ub"]["robust_key"] == [83, 12640, 0, 30000, 10] and info["units"]["fuzzy_ub"]["t_mean"] == 632.0
    assert info["units"]["fuzzy_link"]["key"] == [1.0, 2.0, 3.0, 4.0]
    # the composition is compress_hook.compose_step of the same unit circuits (here the general ones): same metrics
    ref = H.step_metrics(H.general_link_fn, H.general_ub_fn, with_outer=with_outer)
    assert info["metrics"]["cx"] == ref["cx"] and info["metrics"]["qubits"] == ref["qubits"]
    assert info["metrics"] == H._metrics_dict(qc)
    assert [k for k, *_ in qc.metadata["layers"]].count("outer") == (8 if with_outer else 0)


def test_write_headline_step_schema_and_inner_sums(monkeypatch, tmp_path):
    _toy(monkeypatch)
    calls = []

    def fake_verify(qc, a, b, k, order, n_random, n_phys, seed):
        calls.append((a, b, k, order, n_random, n_phys, seed))
        return {"err": 1e-14, "gauss": 2e-15, "n_inputs": 40, "mode": "layers", "leak": 0.0}

    import su2plaq.fuzzy.verify as V

    monkeypatch.setattr(V, "verify_step_samples", fake_verify)
    out = tmp_path / "out" / "step.json"
    doc = HS.write_headline_step(root=tmp_path, out=out)
    assert json.loads(out.read_text()) == json.loads(json.dumps(doc, default=str))
    assert calls == [(0.37, 0.61, 0.185, 1, 32, 8, 20261104)]                   # the call of the locked M10-G3
    for k in ("rule", "order", "with_outer", "units", "composed", "inner", "general", "verification", "provenance"):
        assert k in doc, k
    assert doc["rule"] == "headline" and doc["order"] == 1 and doc["with_outer"] is True
    assert doc["inner"]["t_mean"] == pytest.approx(632.0 + 4 * 44.0, abs=1e-12) and doc["inner"]["t_nominal"] == 638 + 4 * 44
    qi, _ = HS.headline_step(root=tmp_path, with_outer=False)
    mi = H._metrics_dict(qi)
    assert all(doc["inner"][k] == mi[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits"))
    assert doc["composed"]["cx"] > doc["inner"]["cx"] and set(doc["provenance"]) >= {"git_commit", "git_dirty", "seeds"}
    assert doc["verification"]["seed"] == 20261104 and doc["general"]["cx"] > 0
    # default path
    doc2 = HS.write_headline_step(root=tmp_path)
    assert (tmp_path / "results" / "fuzzy" / "compressed_step_headline.json").exists() and doc2["rule"] == "headline"

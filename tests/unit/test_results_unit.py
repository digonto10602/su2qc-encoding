"""Unit tests for su2plaq.results and metrics.provenance."""
import json

import numpy as np

from su2plaq.evaluate.evaluator import Verdict
from su2plaq.metrics.provenance import provenance
from su2plaq.results.report import render
from su2plaq.results.store import RESULT_KEYS, load_result, save_result, verdict_to_dict


def _verdict():
    return Verdict(ok=True, reason="ok", op_norm_error=np.float64(1e-13), max_leak=0.0, dirty_ancilla=0.0, phase=1j,
                   outer_bits_read=0, n_blocks=1, gauss_residual=2e-16, method="inner_span", engine="sparse", seconds=0.5,
                   failing_inputs=[], n_inputs=433, tolerances={"tol_err": 1e-10, "tol_gauss": 1e-10},
                   block_error=1e-13, leak_amplitude=0.0)


def test_provenance_fields_and_seeds():
    p = provenance({"transpiler": 20261104})
    assert p["seeds"] == {"transpiler": 20261104} and p["cpu_count"] >= 1 and p["timestamp_utc"].endswith("Z")
    assert isinstance(p["git_dirty"], bool) and all(isinstance(v, str) for v in p["versions"].values())
    assert p["versions"]["pygridsynth"] == "1.2.0"


def test_verdict_roundtrip_and_optional_keys(tmp_path):
    ver = verdict_to_dict(_verdict())
    assert ver["block_error"] == 1e-13 and ver["leak_amplitude"] == 0.0
    assert ver["phase"] == [0.0, 1.0] and ver["tolerances"]["tol_gauss"] == 1e-10 and "engine_accuracy" in ver and "certified" in ver
    for v in (ver, _verdict()):  # dict and Verdict objects are both accepted
        p = save_result(tmp_path / "a" / "x.json", encoding="twelve", circuit_id="x", kind="UE", params={"alpha": 0.3},
                        verification=v, metrics={"logical": {"cx": 1}}, seeds={"s": 1})
        d = load_result(p)
        assert list(d) == list(RESULT_KEYS) and d["verification"]["engine"] == "sparse" and d["provenance"]["seeds"] == {"s": 1}
        assert d["files"] == {} and d["extra"] == {}


def _render_two(tmp_path, snapshot=None):
    ver = verdict_to_dict(_verdict())
    mets = {"logical": {"cx": 123, "depth": 7, "n_rot": 2, "t_fixed": 11, "qubits": 5, "ancilla": 1},
            "t_table": [{"eps": 1e-6, "t_fixed": 11, "n_rot": 2, "t_rot_pygridsynth": 126, "t_total": 137, "t_est": 130.7}]}
    # circuit ids that cannot occur in a hexadecimal commit hash or a timestamp (prompts/008 A1)
    kw = {} if snapshot is None else {"provenance_snapshot": snapshot}
    return [save_result(tmp_path / f"{i}.json", encoding="twelve", circuit_id=cid, kind="UB", params={"beta": 0.5},
                        verification=ver, metrics=mets, **kw) for i, cid in enumerate(("zq-first", "zq-second"))]


def test_render_is_deterministic_and_contains_only_json_numbers(tmp_path):
    paths = _render_two(tmp_path)
    t = render(paths)
    assert t == render(paths) and "zq-first" in t and "zq-second" in t and "137" in t and "123" in t and "130.7" in t
    t_noq = render(paths[:1])
    assert "zq-second" not in t_noq
    # a result without t_table has no T-count section
    ver = verdict_to_dict(_verdict())
    p = save_result(tmp_path / "n.json", encoding="twelve", circuit_id="n", kind="UE", params={}, verification=ver, metrics={})
    assert "T-count" not in render([p])


def test_render_negative_check_with_commit_containing_old_ids(tmp_path):
    """Forces the provenance commit to a string that contains the ids the old test used ("c1"); the negative check is on the id."""
    snap = provenance({"s": 1})
    snap["git_commit"] = "c1c1c1c"
    paths = _render_two(tmp_path, snapshot=snap)
    t = render(paths)
    assert "c1c1c1c" in t and "zq-first" in t and "zq-second" in t
    assert "zq-second" not in render(paths[:1]) and t == render(paths)


def test_non_serialisable_numpy_types_are_converted(tmp_path):
    p = save_result(tmp_path / "np.json", encoding="e", circuit_id="c", kind="k", params={"a": np.float64(0.5), "arr": np.arange(3)},
                    verification={"ok": np.bool_(True)}, metrics={"z": 1 + 2j})
    d = json.loads(p.read_text())
    assert d["params"]["arr"] == [0, 1, 2] and d["verification"]["ok"] is True and d["metrics"]["z"] == [1.0, 2.0]


def test_provenance_snapshot_is_shared_and_not_recaptured(tmp_path):
    snap = provenance({"s": 1})
    snap["git_dirty"] = "sentinel"       # a fresh capture could never produce this value
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    paths = [save_result(tmp_path / f"{i}.json", encoding="e", circuit_id=f"c{i}", kind="k", params={}, verification={"ok": True},
                         metrics={}, provenance_snapshot=snap) for i in range(2)]
    docs = [load_result(p) for p in paths]
    assert docs[0]["provenance"] == docs[1]["provenance"] == snap
    snap["git_dirty"] = "changed-after"  # the saved files hold a copy
    assert load_result(paths[0])["provenance"]["git_dirty"] == "sentinel"

"""M0-R1 — results JSON schema, provenance, idempotent report (prompts/002 §2.9, §2.11, METHODS §8). Exact."""
import json
import subprocess

from tests.acceptance._api import api


def test_M0_R1_results_json_and_report(tmp_path, root):
    save_result = api("su2plaq.results.store:save_result")
    load_result = api("su2plaq.results.store:load_result")
    RESULT_KEYS = api("su2plaq.results.store:RESULT_KEYS")
    provenance = api("su2plaq.metrics.provenance:provenance")
    render = api("su2plaq.results.report:render")
    assert tuple(RESULT_KEYS) == ("schema_version", "encoding", "circuit_id", "kind", "params", "provenance", "verification", "metrics", "files", "extra")
    verification = {"ok": True, "reason": "ok", "op_norm_error": 1e-13, "max_leak": 0.0, "dirty_ancilla": 0.0, "phase": [1.0, 0.0],
                    "outer_bits_read": 0, "n_blocks": 1, "gauss_residual": 1e-14, "method": "inner_span", "seconds": 0.5, "n_inputs": 625}
    metrics = {"logical": {"cx": 294, "depth": 500, "n_rot": 6, "t_fixed": 296, "qubits": 34, "ancilla": 22},
               "t_table": [{"eps": 1e-6, "t_fixed": 296, "n_rot": 6, "t_rot_pygridsynth": 372, "t_total": 668, "t_est": 296 + 6 * 59.79, "t_qiskit": 660, "cx_qiskit": 294, "depth_qiskit": 2000}]}
    p = save_result(tmp_path / "UB.json", encoding="twelve", circuit_id="UB", kind="UB", params={"alpha": None, "beta": 0.61, "order": 1},
                    verification=verification, metrics=metrics, files={"qpy": "x.qpy", "sha256": "0" * 64}, extra={"note": "test"})
    d = json.loads(p.read_text())
    assert list(d.keys()) == list(RESULT_KEYS) and d["schema_version"] == 1
    prov = d["provenance"]
    for k in ("git_commit", "git_dirty", "versions", "platform", "cpu_count", "seeds", "timestamp_utc"):
        assert k in prov
    for k in ("python", "numpy", "scipy", "qiskit", "qiskit_aer", "pygridsynth"):
        assert k in prov["versions"]
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    assert prov["git_commit"].startswith(head) or head.startswith(prov["git_commit"])
    assert provenance()["git_commit"] == prov["git_commit"]
    assert load_result(p) == d
    text1 = render([p])
    text2 = render([p])
    assert text1 == text2 and "UB" in text1 and "294" in text1 and "668" in text1
    assert text1.count("|") >= 10  # a markdown table

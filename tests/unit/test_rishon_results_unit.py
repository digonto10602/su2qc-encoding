"""Unit tests of su2plaq.rishon.results and scripts/m5_results.py (step 5.10): helpers on small inputs, and one `--quick` run
of the script (eps = 1e-4 only, no Qiskit Clifford+T, small samples) checked for schema and consistency."""
import importlib.util
import json
import pathlib

import numpy as np
import pytest

from su2plaq.circuits import rishon as C
from su2plaq.encodings.rishon import RishonEncoding
from su2plaq.results.store import RESULT_KEYS
from su2plaq.rishon import observables as O
from su2plaq.rishon import results as R
from su2plaq.rishon.verify import verify

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def enc():
    return RishonEncoding()


def test_verdict_to_dict_is_json_and_complete(enc):
    v = verify(C.build_UE(0.37), enc, "UE", 0.37, None, gauss_sample=4)
    d = R.verdict_to_dict(v)
    json.dumps(d)
    assert d["ok"] and d["method"] == "inner_block" and d["gauss_states"] == 17 + 4 and d["outer_bits_read"] == 0
    assert isinstance(d["phase"], list) and len(d["phase"]) == 2
    assert d["inner_verdict"]["ok"] and d["block_error"] <= d["op_norm_error"]


def test_physics_block_is_computed_and_consistent(enc):
    ph, detail = R.physics_block(enc)
    assert list(ph) == ["dim", "closed", "u2_sector", "inner_span_rank", "bright_pairs"]
    assert ph["inner_span_rank"] == detail["n_inner_codes"] == detail["inner_span_rank_by_corners"]
    assert sum(detail["kappa_multiset"].values()) == ph["bright_pairs"]
    assert detail["counts_by_fusion"]["dim"] == ph["dim"] and detail["counts_by_fusion"]["closed"] == ph["closed"]
    assert detail["n_u1_sectors"] == detail["counts_by_fusion"]["n_u1_sectors"]


def test_touched_qubits_ignores_ancillas():
    qc = C.build_UB(0.61)
    t = R.touched_qubits(qc)
    assert max(t) < 16 and set(t) <= set(range(16))
    assert R.touched_qubits(C.build_UE(0.37)) == [0, 1, 4, 5, 8, 9, 12, 13]
    assert R.touched_qubits(C.build_UE(0.37, with_outer=True, include_outer_electric=True)) == (
        [0, 1, 4, 5, 8, 9, 12, 13] + [16 + 4 * k + j for k in range(8) for j in (0, 1)])


def test_register_rows(enc):
    rows = R.register_rows(enc, {"UE": C.build_UE(0.37), "step": C.build_step(0.37, 0.61)})["rows"]
    assert rows["jw_4_per_link"]["qubits"] == 4 * 12 and rows["codeword_3_per_link"]["qubits"] == 3 * 12
    assert rows["jw_4_per_link"]["touched"] == len(rows["jw_4_per_link"]["touched_qubits"]) <= 16
    assert rows["codeword_3_per_link"]["touched"] is None


def test_outer_electric_check_accepts_right_alpha_and_rejects_wrong(enc):
    qc = C.build_UE(0.37, with_outer=True, include_outer_electric=True)
    ok = R.outer_electric_check(qc, enc, 0.37, n_codes=100)
    assert ok["max_error"] < 1e-12 and ok["n_codes"] == 100 and ok["max_branches"] == 1
    bad = R.outer_electric_check(qc, enc, 0.40, n_codes=100)
    assert bad["max_error"] > 1e-3
    inner_only = R.outer_electric_check(C.build_UE(0.37, with_outer=True), enc, 0.37, n_codes=100)   # misses the outer links
    assert inner_only["max_error"] > 1e-3


def _ue_outer(alpha=0.37):
    return C.build_UE(alpha, with_outer=True, include_outer_electric=True)


def test_outer_electric_certify_accepts_and_is_alpha_sensitive(enc):
    r = R.outer_electric_certify(_ue_outer(0.37), enc, 0.37)
    assert r["certified"] and r["ok"] and r["reason"] == "ok" and r["n_links"] == 12 and r["gates_per_link"] == [3] * 12
    assert len(r["link_errors"]) == 12 and r["error_bound"] == sum(r["link_errors"]) <= 1e-10
    assert abs(abs(r["phase"]) - 1.0) < 1e-12
    wrong = R.outer_electric_certify(_ue_outer(0.37), enc, 0.40)         # right circuit, wrong claimed alpha
    assert not wrong["certified"] and wrong["error_bound"] > 1e-3 and wrong["reason"] == "error"
    json.dumps(R._jsonable(r))                                           # JSON-able


def test_outer_electric_certify_mutants(enc):
    qc = _ue_outer(); qc.p(1e-7, 20)
    r = R.outer_electric_certify(qc, enc, 0.37)
    assert not r["certified"] and 0.9e-7 <= r["error_bound"] <= 1.1e-7 and r["max_link_error"] == r["link_errors"][5]
    qc = _ue_outer(); qc.cx(3, 4)
    r = R.outer_electric_certify(qc, enc, 0.37)
    assert not r["certified"] and r["reason"] == "cross_link_gate"
    qc = _ue_outer(); qc.x(18)
    r = R.outer_electric_certify(qc, enc, 0.37)
    assert not r["certified"] and not r["ok"] and r["reason"] == "error"
    r = R.outer_electric_certify(C.build_UE(0.37, with_outer=True), enc, 0.37)          # outer row missing
    assert not r["certified"] and r["error_bound"] > 1e-10
    r = R.outer_electric_certify(C.build_UE(0.37), enc, 0.37)                           # 16 qubits: not the 48-qubit row
    assert not r["certified"] and r["reason"] == "ancilla_register"


def test_outer_electric_certify_ignores_barrier_and_reports_measure(enc):
    qc = _ue_outer(); qc.barrier()
    assert R.outer_electric_certify(qc, enc, 0.37)["certified"]
    qc = _ue_outer(); qc.measure_all()
    r = R.outer_electric_certify(qc, enc, 0.37)                          # never raises
    assert not r["certified"] and r["reason"] == "error"


def test_outer_electric_certify_agrees_with_sampled_check(enc):
    for alpha in (0.37, 1.70):
        qc = _ue_outer(alpha)
        assert R.outer_electric_certify(qc, enc, alpha)["certified"]
        assert R.outer_electric_check(qc, enc, alpha, n_codes=100)["max_error"] < 1e-12


def test_observable_rows_flatten():
    tab = O.observables_table(angles=((0.37, 0.61),))
    d = R.observable_rows(tab)
    assert len(d["angles"]) == 1
    for th in ("rishon", "ks"):
        assert [r["n"] for r in d[th]] == [1, 2]
        assert set(d[th][0]) == {"alpha", "beta", "n", "E_link", "P", "echo"}
    assert d["closed_forms_max_dev_n1"] < 1e-12
    assert all(np.signbit(r["P"]) == False for r in d["rishon"] + d["ks"] if r["P"] == 0.0)   # no negative zero


@pytest.fixture(scope="module")
def quick_out(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("m5_results", ROOT / "scripts" / "m5_results.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    out = tmp_path_factory.mktemp("rishon_results")
    assert m.main(["--quick", "--out", str(out)]) == 0
    return out


@pytest.mark.parametrize("name", ["UE", "UB", "step", "UE_outer_row"])
def test_quick_result_files(quick_out, name):
    d = json.loads((quick_out / f"{name}.json").read_text())
    assert list(d) == list(RESULT_KEYS) and d["encoding"] == "rishon" and d["circuit_id"] == name
    pv = d["provenance"]
    for k in ("git_commit", "git_dirty", "versions", "seeds", "host", "command", "wall_seconds", "peak_rss_mb", "platform"):
        assert k in pv
    assert pv["quick"] is True
    ex = d["extra"]
    assert ex["register_variants"] == {"jw_4_per_link": 48, "codeword_3_per_link": 36, "touched": 16}
    assert set(ex["physics"]) == {"dim", "closed", "u2_sector", "inner_span_rank", "bright_pairs"}
    m = d["metrics"]
    assert m["logical"]["depth"] > 0 and m["macro"]["depth"] > 0 and "lowered" in m["macro"]["depth_label"]
    assert len(m["t_table"]) == 1 and m["t_table"][0]["eps"] == 1e-4
    assert m["t_table"][0]["t_total"] == m["t_table"][0]["t_fixed"] + m["t_table"][0]["t_rot_pygridsynth"]
    assert (quick_out / f"{name}.qpy").exists() and (quick_out / f"{name}.qasm3").exists()
    v = d["verification"]
    if name == "UE_outer_row":
        assert v["method"] == "outer_electric_check" and v["ok"] and m["logical"]["n_rot"] == 12 and not v["certified"]
    else:
        assert v["ok"] and v["certified"] and v["method"] == "inner_block" and v["outer_bits_read"] == 0
        assert v["gauss_states"] == 17 + 8 and v["inner_verdict"]["ok"]
    s = m["t_table"][0]["synth"]
    if name in ("UE", "UE_outer_row"):
        assert s["verdict"]["ok"] and s["t_matches_table"] and s["error_measured_sum"] <= s["error_bound_sum"] + 1e-15
        assert s["verdict"]["tolerances"]["tol_err"] == s["n_rot"] * 1e-4 + 1e-9
    else:
        assert s == {"skipped": True, "reason": "--quick"}


def test_quick_observables_and_register_rows(quick_out):
    o = json.loads((quick_out / "observables.json").read_text())
    assert len(o["angles"]) == 3 and {r["n"] for r in o["rishon"]} == {1, 2} and len(o["ks"]) == 6
    assert set(map(float, o["closed_spectra"]["g2"])) == {0.5, 1.0, 2.0} and o["provenance"]["git_commit"]
    assert o["closed_forms_max_dev_n1"] < 1e-12
    r = json.loads((quick_out / "register_rows.json").read_text())
    assert r["rows"]["jw_4_per_link"]["qubits"] == 48 and r["rows"]["jw_4_per_link"]["touched"] == 16
    assert r["rows"]["codeword_3_per_link"]["qubits"] == 36

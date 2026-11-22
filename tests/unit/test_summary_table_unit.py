"""scripts/summary_table.py: the Table 2 loop rows (LSH, rishon, fuzzy) are read from the committed result files, not hard-coded."""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def st():
    spec = importlib.util.spec_from_file_location("summary_table", ROOT / "scripts" / "summary_table.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rows(st):
    return {r["loop"]: r for r in st.loop_rows()}


def _j(rel):
    return json.loads((ROOT / rel).read_text())


def test_lsh_row_from_m8_file(st, rows):
    r = rows["4. Loop-string-hadron, step"]
    m8 = _j("results/lsh/m8-compressed.json")
    lg = m8["metrics"]["logical"]
    h = r["headline"]
    assert r["headline_id"] == _j("results/compress/lsh/summary.json")["headline"]["id"] == m8["extra"]["headline"]["id"]
    assert (h["qubits"], h["CX"], h["N_rot"]) == (lg["qubits"], lg["cx"], lg["n_rot"])
    assert h["T(1e-6)"] == st.t_at(m8["metrics"])
    assert h["Lean"] == m8["extra"]["headline"]["lean"]
    stop = _j("results/compress/lsh/stop.json")
    assert r["state"] == f"stopped after round {r['rounds'] - 1} ({st.STOP_REASON_TEXT[stop['reasons'][0]]})"
    assert "M8" not in r["state"] and "not started" not in r["state"]


def test_rishon_row_from_m6_file(st, rows):
    r = rows["3. Rishon, step (no det)"]
    m6 = _j("results/rishon/m6-compressed.json")
    h = r["headline"]
    assert r["headline_id"] == m6["extra"]["headline"]["id"]
    assert h["Lean"] == m6["extra"]["headline"]["lean"] != "not_run"
    assert h["CX"] == m6["metrics"]["logical"]["cx"] and h["T(1e-6)"] == st.t_at(m6["metrics"])
    assert "paused" not in r["state"] and r["state"].startswith("stopped after round")


def test_fuzzy_rows_use_headline_not_archive_best(st, rows):
    r = rows["5. Fuzzy, U_B"]
    s = _j("results/compress/fuzzy_ub/summary.json")
    fz = _j("results/fuzzy/compressed_step_headline.json")
    assert r["headline_id"] == s["headline"]["id"] == fz["units"]["fuzzy_ub"]["entry"]
    assert r["headline"]["CX"] == fz["units"]["fuzzy_ub"]["key"][0]
    assert r["archive_best"] == s["global_best"]
    if s["global_best"] != s["headline"]["id"]:
        assert r["headline_id"] != r["archive_best"]


@pytest.mark.parametrize("enc", ["twelve", "spinnet", "rishon", "lsh", "fuzzy_ub", "fuzzy_link"])
def test_every_loop_row_is_the_summary_headline(rows, enc):
    s = _j(f"results/compress/{enc}/summary.json")
    r = [x for x in rows.values() if x["headline_id"] == s["headline"]["id"]]
    assert len(r) == 1 and r[0]["headline"]["entry / commit"].split(" @ ")[0] == s["headline"]["id"]


def test_build_composed_row_and_lsh_row_in_markdown(st, tmp_path):
    st.build(tmp_path)
    md = (tmp_path / "encodings-gate-counts.md").read_text()
    fz = _j("results/fuzzy/compressed_step_headline.json")
    assert "M8 not started" not in md and "paused" not in md
    assert f"U_B {fz['units']['fuzzy_ub']['entry']}" in md
    data = json.loads((tmp_path / "encodings-gate-counts.json").read_text())
    assert data["fuzzy_composed_step"]["composed"]["cx"] == fz["composed"]["cx"]
    assert any(l["loop"].startswith("4. Loop-string-hadron") for l in data["loops"])


# ---- Lean status of the GENERAL rows: read from the certificate records Report 11 Table 1a cites -----------------------------
GENERAL_LEAN_REPORT11 = {                     # Report 11 Table 1a, Lean column (spin network: "certified (compiled checker)")
    "1. 12-qubit, step": "certified", "2. Spin network, step": "certified", "3. Rishon, step (no det)": "certified",
    "4. Loop-string-hadron, step": "certified", "5. Fuzzy, U_B": "n_a", "5. Fuzzy, link U_E": "n_a",
}


@pytest.mark.parametrize("loop,expect", sorted(GENERAL_LEAN_REPORT11.items()))
def test_general_row_lean_matches_report11_table1a(rows, loop, expect):
    g = rows[loop]["general"]
    assert g["Lean"] == expect and g["Lean source"]


def test_general_lean_read_from_certificate_records(st, rows):
    assert rows["1. 12-qubit, step"]["general"]["Lean"] == _j("results/lean/general_step_certificate.json")["status"]
    assert rows["1. 12-qubit, step"]["general"]["Lean source"] == "certificate: results/lean/general_step_certificate.json"
    assert rows["4. Loop-string-hadron, step"]["general"]["Lean"] == _j("results/lsh/step.json")["extra"]["lean"]["status"]
    assert rows["4. Loop-string-hadron, step"]["general"]["Lean source"] == "certificate: results/lsh/step.json"
    ba = {(r["row"], r["layer"]): r for r in _j("results/rishon/m6-compressed.json")["extra"]["before_after"]}
    assert rows["3. Rishon, step (no det)"]["general"]["Lean"] == ba[("general", "unit")]["lean"]
    # spin network: no separate certificate record -> the archive field, labelled as such
    assert rows["2. Spin network, step"]["general"]["Lean source"].startswith("archive: ")


def test_general_lean_certificate_is_not_hard_coded_and_needs_a_match(st, tmp_path, monkeypatch):
    """The status comes from the record (a 'rejected' record gives 'rejected'); a record about another circuit is ignored."""
    rec = {"status": "rejected", "n_qubits_circuit": 50}
    (tmp_path / "c.json").write_text(json.dumps(rec))
    monkeypatch.setattr(st, "ROOT", tmp_path)
    monkeypatch.setitem(st.GENERAL_LEAN_SOURCES, "twelve", ("c.json", st._read_twelve_cert))
    gen = {"Lean": "not_run", "qubits": "50"}
    assert st.general_lean("twelve", gen) == ("rejected", "certificate: c.json")
    assert st.general_lean("twelve", {"Lean": "not_run", "qubits": "49"}) == ("not_run", "archive: results/compress/twelve/summary.json")
    rec["status"] = None
    (tmp_path / "c.json").write_text(json.dumps(rec))                     # record without a status -> archive fallback
    assert st.general_lean("twelve", gen)[1].startswith("archive: ")
    monkeypatch.setitem(st.GENERAL_LEAN_SOURCES, "twelve", ("missing.json", st._read_twelve_cert))
    assert st.general_lean("twelve", {"Lean": "certified", "qubits": "50"}) == ("certified", "archive: results/compress/twelve/summary.json")


def test_markdown_has_lean_source_column_and_general_rows_certified(st, tmp_path):
    st.build(tmp_path)
    md = (tmp_path / "encodings-gate-counts.md").read_text()
    assert "| Lean | Lean source |" in md
    lines = [l for l in md.splitlines() if "| general |" in l and "certificate:" in l]
    assert len(lines) == 3 and all("| certified |" in l for l in lines)       # twelve, rishon, LSH
    data = json.loads((tmp_path / "encodings-gate-counts.json").read_text())
    assert all(l["general"]["Lean source"] for l in data["loops"]) and all(l["headline"]["Lean source"] for l in data["loops"])

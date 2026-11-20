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

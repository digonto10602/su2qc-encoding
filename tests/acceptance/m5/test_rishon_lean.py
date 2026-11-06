"""M5-L1..L3 — Lean 4 facts of the rishon track (prompts/200 §2.9, steps 5.L1-5.L3; METHODS-rishon R8; prompts/006 trust
levels).  L1/L2 are kernel-checked (standard axioms only, no native_decide, no sorry); L3 is a native certificate
(exactly one native axiom).  Time limits as prompts/006 §7.

PENDING rule: a missing lean/ project, file or `su2plaq.rishon.lean_export` name fails with `PENDING:`."""
import json
import pathlib
import time

import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
COUNT_THEOREMS = {"Su2Plaq.card_rishon_physical": 38432, "Su2Plaq.card_rishon_closed": 4352}
JW_THEOREMS = ("Su2Plaq.Rishon.car_4", "Su2Plaq.Rishon.car_8", "Su2Plaq.Rishon.bilinear_string_free_8",
               "Su2Plaq.Rishon.sector_card", "Su2Plaq.Rishon.u_ladder", "Su2Plaq.Rishon.det_u_sector",
               "Su2Plaq.Rishon.end_bilinear_local")


def _lean_dir(root: pathlib.Path) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing", pytrace=False)
    return d


def _file(d: pathlib.Path, rel: str) -> str:
    f = d / rel
    if not f.exists():
        pytest.fail(f"PENDING: {rel} missing", pytrace=False)
    return f.read_text()


def test_M5_L1_counts_kernel_checked(root):
    """lean/Su2Plaq/Rishon/Counts.lean: rishonTotal = 38432 and rishonClosed = 4352 by `decide` (kernel), standard axioms
    only, statement text pins the values; imported from lean/Su2Plaq.lean; builds within 900 s."""
    d = _lean_dir(root)
    src = _file(d, "Su2Plaq/Rishon/Counts.lean")
    assert "native_decide" not in src and "sorry" not in src
    assert "import Su2Plaq.Structure.Counts" in src
    for name, value in COUNT_THEOREMS.items():
        short = name.split(".")[-1]
        assert f"theorem {short}" in src and f"= {value}" in src.split(f"theorem {short}", 1)[1].split("\n", 1)[0], (name, value)
    assert "Su2Plaq.Rishon.Counts" in (d / "Su2Plaq.lean").read_text()
    LE = api("su2plaq.rishon.lean_export")
    assert set(COUNT_THEOREMS) == set(LE.RISHON_COUNT_THEOREMS)
    P = api("su2plaq.lean.project")
    t0 = time.time()
    r = P.build("Su2Plaq.Rishon.Counts", timeout=900)
    assert r["ok"], r.get("stderr", "")[-2000:]
    assert time.time() - t0 <= 900
    ax = P.print_axioms(list(COUNT_THEOREMS), timeout=900)
    bad = {n: sorted(ax[n] - STANDARD) for n in COUNT_THEOREMS if n not in ax or "<unknown>" in ax[n] or ax[n] - STANDARD}
    assert not bad, bad
    assert P.no_sorry() == []


def test_M5_L2_jw_facts_kernel_checked(root):
    """lean/Su2Plaq/Rishon/JW.lean: the Jordan-Wigner facts used by the encoding (canonical anticommutation on 4 and 8
    modes, string-freeness of the link bilinears on two links, the 6-element two-rishon sector, the A -> Q -> B ladder of
    U, det U = 2|B><A| on the sector, 2-qubit locality of the end bilinears) are theorems with standard axioms only."""
    d = _lean_dir(root)
    src = _file(d, "Su2Plaq/Rishon/JW.lean")
    assert "native_decide" not in src and "sorry" not in src
    for name in JW_THEOREMS:
        assert f"theorem {name.split('.')[-1]}" in src, name
    assert "Su2Plaq.Rishon.JW" in (d / "Su2Plaq.lean").read_text()
    LE = api("su2plaq.rishon.lean_export")
    assert set(JW_THEOREMS) <= set(LE.RISHON_JW_THEOREMS)
    P = api("su2plaq.lean.project")
    r = P.build("Su2Plaq.Rishon.JW", timeout=900)
    assert r["ok"], r.get("stderr", "")[-2000:]
    ax = P.print_axioms(list(JW_THEOREMS), timeout=900)
    bad = {n: sorted(ax[n] - STANDARD) for n in JW_THEOREMS if n not in ax or "<unknown>" in ax[n] or ax[n] - STANDARD}
    assert not bad, bad


@pytest.mark.slow
def test_M5_L3_hb_structure_certificate(root, tmp_path):
    """Exact structure of H_B^in as a native certificate: the exporter writes the 81 bright pairs (4u_p, 4v_p in Z[sqrt2],
    kappa_p) and the checker (lean/Su2PlaqCert/Rishon/HB.lean) recomputes W from the link matrices and verifies
    16 H_B = -sum kappa ((4u)(4v)^T + h.c.), orthonormality, the kappa multiset {1:32, 2:48, 4sqrt2:1} and 990 dark codes;
    the theorem file depends on the standard axioms plus exactly one native axiom; a tampered kappa (2 -> 1) is rejected."""
    d = _lean_dir(root)
    _file(d, "Su2PlaqCert/Rishon/HB.lean")
    LE = api("su2plaq.rishon.lean_export")
    P = api("su2plaq.lean.project")
    t0 = time.time()
    cert = LE.export_hb_certificate(tmp_path / "hb-cert.json")
    c = json.loads(pathlib.Path(cert).read_text())
    assert c["schema"].startswith("su2plaq-rishon-hb") and len(c["pairs"]) == 81 and c["n_codes"] == 1296
    lean_file = LE.write_hb_lean(cert, tmp_path / "rishon-hb-structure.lean")
    text = pathlib.Path(lean_file).read_text()
    assert "native_decide" in text and "sorry" not in text
    r = LE.check_hb(lean_file, timeout=900)
    assert r["status"] == "certified", r
    extra = set(r["axioms"]) - STANDARD
    assert len(extra) == 1 and all(P.is_native_axiom(a) for a in extra), r["axioms"]
    assert time.time() - t0 <= 1800
    i = next(i for i, p in enumerate(c["pairs"]) if p["kappa"] in ("2", [2, 0], "2/1"))
    c["pairs"][i]["kappa"] = "1" if isinstance(c["pairs"][i]["kappa"], str) else [1, 0]
    bad = tmp_path / "hb-bad.json"
    bad.write_text(json.dumps(c))
    bad_lean = LE.write_hb_lean(bad, tmp_path / "rishon-hb-bad.lean")
    r2 = LE.check_hb(bad_lean, timeout=900)
    assert r2["status"] == "rejected", r2

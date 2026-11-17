"""M11-R / M11-T — the two result files the final cross-encoding report is rendered from (prompts/009 §5.4, §7, §8).

R1: results/crosscheck/spectra.json (written by `python scripts/m11_results.py`, i.e. `crosscheck.report.spectra_results`)
    holds the numbers of the spectra cross-check; each is re-checked here against its tolerance and a few are recomputed.
T1: results/crosscheck/gate-table.json (`crosscheck.report.gate_table`) holds one row per encoding in three model blocks
    (A: Kogut-Susskind j_max = 1/2 -- twelve, spinnet, lsh, like for like; B: SU(2) quantum link model + det -- rishon;
    C: fuzzy gauge theory -- fuzzy); general numbers equal the committed general-circuit files, a compressed number is the
    HEADLINE of the archive (smallest robust key, METHODS §12.4), the T-first pick is the smallest robust key with its first two
    components exchanged (sum of T over the 20 pairs first, then CX).
T2: completeness gate of the final report: every row is final and every Kogut-Susskind encoding has a headline cross-verdict.
    It stays red until Report 6 (rishon compression), Report 8 (LSH compression) and the fuzzy headline step exist.

Tolerances are those of test_cross_ks.py / test_cross_models.py (1e-10 exact agreement, 1e-12 algebra, limits as measured);
integers are compared exactly, averaged T counts to 1e-9.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from tests.acceptance._api import api

TOL = 1e-10
ALG = 1e-12
G2_KEYS = ("0.5", "1.0", "2.0")
KS = ("twelve", "spinnet", "lsh")
MODELS = ("rishon_plus", "rishon_minus", "fuzzy_one", "fuzzy_gamma5", "fuzzy_fplus", "fuzzy_fminus")
LEAK_U_SQ = {"rishon_plus": 0.5, "rishon_minus": 0.5, "fuzzy_one": 0.5, "fuzzy_gamma5": 0.5, "fuzzy_fplus": 1.0, "fuzzy_fminus": 1.0}
LEAK_W_SQ = {"rishon_plus": 15.0, "rishon_minus": 15.0, "fuzzy_one": 4.125, "fuzzy_gamma5": 4.125, "fuzzy_fplus": 4.0, "fuzzy_fminus": 4.0}
ROWS = (("twelve", "A", 433), ("spinnet", "A", 433), ("lsh", "A", 433), ("rishon", "B", 38432), ("fuzzy", "C", 101197218))
GENERAL_FILE = {"twelve": "results/twelve/step.json", "spinnet": "results/spinnet/step.json", "lsh": "results/lsh/step.json",
                "rishon": "results/rishon/step3.json", "fuzzy": "results/fuzzy/step.json"}
LOOPS = {"twelve": (("twelve", "step"),), "spinnet": (("spinnet", "step"),), "lsh": (("lsh", "step"),),
         "rishon": (("rishon", "step"),), "fuzzy": (("fuzzy_ub", "UB"), ("fuzzy_link", "UE"))}


def _load(root, name, step):
    p = root / "results" / "crosscheck" / name
    if not p.exists():
        pytest.fail(f"PENDING: results/crosscheck/{name} missing (run scripts/m11_results.py, prompts/009 step {step})", pytrace=False)
    return json.loads(p.read_text())


def _ks_block(g2):
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]])


def check_spectra(d):
    assert d["schema"] == "crosscheck-spectra-1"
    ks = d["ks"]
    for k in G2_KEYS:
        assert 0.0 <= ks["max_pairwise_level_dev"][k] <= TOL, k
        lv = np.asarray(ks["levels"][k], dtype=float)
        assert lv.shape == (433,) and np.all(np.diff(lv) >= -1e-9)
        g2 = float(k)
        for s in (1.0, -1.0):
            assert np.abs(lv - (0.75 * g2 + s * np.sqrt(0.5625 * g2 ** 2 + 4.0 / g2 ** 2))).min() <= TOL, (k, s)
    assert 0.0 <= ks["transported_target_max"] <= TOL
    for e in KS:
        assert {float(x): int(n) for x, n in ks["hb_multiplicities"][e].items()} == {-2.0: 16, -1.0: 96, -0.5: 16, 0.0: 177, 0.5: 16, 1.0: 96, 2.0: 16}
    cv = ks["cross_verdicts"]
    for r in cv:
        for key in ("circuit", "target", "which", "entry", "alpha", "beta", "ok", "total_error", "certified"):
            assert key in r, key
        assert r["circuit"] in KS and r["target"] in KS and r["circuit"] != r["target"] and r["which"] in ("general", "headline")
        assert r["ok"] is True and r["certified"] is True and 0.0 <= r["total_error"] <= TOL, r
        assert (r["entry"] is None) == (r["which"] == "general")
    assert {r["circuit"] for r in cv if r["which"] == "general"} == set(KS)
    assert {r["target"] for r in cv if r["which"] == "general"} == set(KS)
    emb = d["embedding"]
    assert set(emb) == set(MODELS)
    for m in MODELS:
        for k in ("isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette"):
            assert 0.0 <= emb[m][k] <= ALG, (m, k)
        assert abs(emb[m]["leak_U_sq"] - LEAK_U_SQ[m]) <= 1e-9 and abs(emb[m]["leak_plaquette_sq"] - LEAK_W_SQ[m]) <= 1e-6, m
    lim = d["rishon_ks_limit"]
    closed = {(r["g2"], r["L"]): r for r in lim["closed"]}
    full = {(r["g2"], r["L"]): r for r in lim["full"]}
    for g2 in (0.5, 1.0, 2.0):
        ek, vk = np.linalg.eigh(_ks_block(g2))
        pred = -(13.0 / 4.0) / g2 ** 2 * vk[1, :] ** 2
        r = closed[(g2, 256.0)]
        assert np.abs(np.asarray(r["predicted"]) - pred).max() <= 1e-9
        assert (np.abs(np.asarray(r["L_times_dev"]) - pred) / np.abs(pred)).max() <= 0.01, g2
        a, b = full[(g2, 64.0)], full[(g2, 128.0)]
        assert abs(np.log(b["max_dev"] / a["max_dev"]) / np.log(2.0) + 1.0) <= 0.02, g2
        assert abs(128.0 * b["max_dev"] + pred[1]) / abs(pred[1]) <= 0.01, g2
        assert 4 * 128.0 - 12.0 <= b["gap_to_next_band"] <= 4 * 128.0
    fz = d["fuzzy"]
    fb = {tuple(r["signs"]): r for r in fz["flavour_blocks"]}
    assert len(fb) == 16
    for signs, r in fb.items():
        exact = signs in ((1, 1, -1, -1), (-1, -1, 1, 1))
        assert r["dim"] == (2 if exact else (4 if signs in ((1, -1, -1, 1), (-1, 1, 1, -1)) else 3)), signs
        for k in G2_KEYS:
            assert (r["ks_level_distance"][k] <= TOL) if exact else (r["ks_level_distance"][k] >= 0.5), (signs, k)
    iso = fz["isolated"]
    assert max(iso["k1_only"]["ground_splitting"]) <= TOL
    assert abs(iso["k2_only"]["slope_first_pair"] - 7.0) <= 0.02 and abs(iso["r1"]["slope_first_pair"] - 7.0) <= 0.06
    assert iso["k2_only"]["g2"][:2] == [0.15, 0.2] and iso["r1"]["g2"][:2] == [0.15, 0.2]
    assert fz["k2_on_embeddings"]["fuzzy_one"] == [-4.0, 2.0, 2.0, 2.0, 2.0] and fz["k2_on_embeddings"]["fuzzy_gamma5"] == [4.0, -2.0, -2.0, -2.0, -2.0]
    cst = d["closed_sector_table"]
    for k in G2_KEYS:
        g2 = float(k)
        assert np.abs(np.asarray(cst["ks"][k]) - np.linalg.eigvalsh(_ks_block(g2))).max() <= TOL
        ev = np.asarray(cst["rishon"]["lam_d=0"][k], dtype=float)
        assert ev.shape == (17,) and abs(ev[0] - (0.75 * g2 - np.sqrt(0.5625 * g2 ** 2 + 32.0 / g2 ** 2))) <= TOL
        assert len(cst["rishon"]["lam_d=0.2"][k]) == 17 and len(cst["rishon"]["lam_d=0.5"][k]) == 17
        assert len(cst["fuzzy"]["r=0"][k]) == 9 and len(cst["fuzzy"]["r=1"][k]) == 12
    assert len(d["provenance"]["git_commit"]) >= 7 and "command" in d["provenance"]


def test_M11_R1_spectra_results_file(root):
    d = _load(root, "spectra.json", "11.6")
    check_spectra(d)
    # recomputed here from the production functions
    Lm = api("su2plaq.crosscheck.limits")
    K = api("su2plaq.crosscheck.ks")
    rec = next(r for r in d["rishon_ks_limit"]["closed"] if (r["g2"], r["L"]) == (1.0, 256.0))
    ev = np.linalg.eigvalsh(np.asarray(Lm.rishon_closed_block(0.5 - 8 * 256.0 / 3, 1.0, -256.0))) + 8 * 256.0
    assert np.abs(256.0 * (ev[:2] - np.linalg.eigvalsh(_ks_block(1.0))) - np.asarray(rec["L_times_dev"])).max() <= 1e-6
    lv = np.linalg.eigvalsh(np.asarray(K.ks_hamiltonian("twelve", 1.0, include_outer_electric=True)))
    assert np.abs(lv - np.asarray(d["ks"]["levels"]["1.0"])).max() <= TOL
    rep = api("su2plaq.crosscheck.report")
    text = rep.render(root=root)
    for word in ("Kogut-Susskind", "quantum link", "fuzzy", "different model", "T_avg", "spectra.json", "gate-table.json"):
        assert word in text, word


def _general(root, rel):
    d = json.loads((root / rel).read_text())
    m = d["metrics"]
    lg = m.get("logical", m)
    t6 = next(r["t_total"] for r in m["t_table"] if abs(float(r["eps"]) - 1e-6) < 1e-15)
    return {"qubits": lg["qubits"], "cx": lg["cx"], "n_rot": lg["n_rot"], "t_fixed": lg["t_fixed"], "t_1e6": t6}


def _pick(ranking):
    rows = [r for r in ranking if r["robust_key"] is not None]
    head = min(rows, key=lambda r: (tuple(r["robust_key"]), tuple(r["laptop_key"]), r["id"]))
    tkey = lambda r: (r["robust_key"][1], r["robust_key"][0], *r["robust_key"][2:], tuple(r["laptop_key"]), r["id"])     # T first, then CX
    tfirst = min(rows, key=tkey)
    return head, tfirst


def check_gate_table(d, root, headline_of):
    """`headline_of(enc, kind)` -> the cached `robust.headline` dict or None."""
    assert d["schema"] == "crosscheck-gate-table-1" and isinstance(d["unit"], str)
    rows = d["rows"]
    assert [(r["encoding"], r["block"], r["n_physical_states"]) for r in rows] == list(ROWS)
    n_final = 0
    for r in rows:
        enc = r["encoding"]
        assert isinstance(r["model"], str) and r["model"]
        assert r["comparable_with"] == [e for e, b, _ in ROWS if b == r["block"] and e != enc]
        g = _general(root, GENERAL_FILE[enc])
        for k, v in g.items():
            assert r["general"][k] == v, (enc, k)
        assert GENERAL_FILE[enc] in r["general"]["source"]
        assert r["status"] == "final" or r["status"].startswith("pending: "), enc
        heads = {e: headline_of(e, k) for e, k in LOOPS[enc]}
        if r["status"] == "final":
            n_final += 1
            assert all(h is not None for h in heads.values()) and r["headline"] is not None and r["t_first"] is not None, enc
        if r.get("headline") is None or any(h is None for h in heads.values()):
            continue
        if enc != "fuzzy":
            (h,) = heads.values()
            head, tfirst = _pick(h["ranking"])
            assert head["id"] == h["id"]
            assert r["headline"]["entry"] == head["id"] and r["headline"]["cx"] == head["cx"] == head["robust_key"][0]
            assert r["headline"]["qubits"] == head["qubits"] and r["headline"]["t_nominal"] == head["t_nominal"]
            assert abs(r["headline"]["t_mean"] - head["t_mean"]) <= 1e-9 and r["headline"]["angle_linear"] == head["angle_linear"]
            assert r["t_first"]["entry"] == tfirst["id"] and r["t_first"]["cx"] == tfirst["cx"] and abs(r["t_first"]["t_mean"] - tfirst["t_mean"]) <= 1e-9
        else:
            picks = {e: _pick(h["ranking"]) for e, h in heads.items()}
            for e in heads:
                assert r["units"][e]["entry"] == picks[e][0]["id"] == heads[e]["id"]
                assert r["units"][e]["cx"] == picks[e][0]["cx"] and abs(r["units"][e]["t_mean"] - picks[e][0]["t_mean"]) <= 1e-9
            for key, i in (("headline", 0), ("t_first", 1)):                 # inner step = U_B unit + 4 link units
                ub, lk = picks["fuzzy_ub"][i], picks["fuzzy_link"][i]
                assert r[key]["cx"] == ub["cx"] + 4 * lk["cx"], key
                assert abs(r[key]["t_mean"] - (ub["t_mean"] + 4 * lk["t_mean"])) <= 1e-9, key
        if enc == "rishon" and r.get("headline_with_det") is not None:       # det layer in front of the unit: +32 CX (METHODS-rishon R14)
            assert r["headline_with_det"]["cx"] == r["headline"]["cx"] + 32
    assert len(d["provenance"]["git_commit"]) >= 7
    return n_final


def _headline_of(root):
    RB = api("su2plaq.compress.robust")

    def f(enc, kind):
        try:
            return RB.headline(enc, kind, root=root, compute=False)
        except (NotImplementedError, FileNotFoundError):                    # lsh before its loop exists (prompts/401)
            return None

    return f


def test_M11_T1_gate_table_file(root):
    d = _load(root, "gate-table.json", "11.7")
    check_gate_table(d, root, _headline_of(root))


def test_M11_T2_final_report_inputs_complete(root):
    """The gate of the final report: all five rows final (headline of every archive cached and quoted, rishon with its det
    layer, fuzzy with its composed headline step) and a headline cross-verdict for each Kogut-Susskind encoding."""
    t = _load(root, "gate-table.json", "11.8")
    s = _load(root, "spectra.json", "11.8")
    n_final = check_gate_table(t, root, _headline_of(root))
    pending = {r["encoding"]: r["status"] for r in t["rows"] if r["status"] != "final"}
    if pending:
        pytest.fail(f"PENDING: rows not final: {pending}", pytrace=False)
    assert n_final == 5
    rishon = next(r for r in t["rows"] if r["encoding"] == "rishon")
    assert rishon["headline_with_det"] is not None and "three-layer.json" in rishon["headline_with_det"]["source"]
    fuzzy = next(r for r in t["rows"] if r["encoding"] == "fuzzy")
    assert "compressed_step_headline.json" in fuzzy["headline"]["source"]
    check_spectra(s)
    heads = {r["circuit"]: r for r in s["ks"]["cross_verdicts"] if r["which"] == "headline"}
    assert set(heads) == set(KS)
    f = _headline_of(root)
    for e in KS:
        assert heads[e]["entry"] == f(e, "step")["id"], e
    assert s["provenance"].get("git_dirty") is False and t["provenance"].get("git_dirty") is False

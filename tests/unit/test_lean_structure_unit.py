"""Unit tests for the exact structure certificate and its Lean checker (prompts/006 step 2.L6): symmetry candidates, facts,
structure.json, and a battery of single-field tampers that the checker must reject."""
import copy
from fractions import Fraction
import json
import pathlib

import pytest

from su2plaq.lean import certify as C
from su2plaq.lean import structure as S
from su2plaq.lean.certify import LeanCert


@pytest.fixture(scope="module")
def cert(tmp_path_factory):
    p = S.export_structure_certificate(tmp_path_factory.mktemp("sc") / "structure-cert.json")
    return json.loads(pathlib.Path(p).read_text())


def _run(d, tmp_path, name="x.json"):
    p = tmp_path / name
    p.write_text(json.dumps(d))
    r = S.check_structure(p, timeout=600)
    return r


def test_accept_and_shape(cert, tmp_path):
    assert len(cert["states"]) == 433 and len(cert["k_inner"]) == 47 and len(cert["bright_pairs"]) == 8
    assert len(cert["dark_rows"]) == 31 and len(cert["gauge"]) == 433 and len(cert["corner_kernel_dims"]) == 64
    assert {float(l): m for l, m in cert["spectrum"]} == {-2.0: 16, -1.0: 96, -0.5: 16, 0.0: 177, 0.5: 16, 1.0: 96, 2.0: 16}
    assert sorted(Fraction(p["coupling"]) for p in cert["bright_pairs"]) == [Fraction(1, 2)] + [1] * 6 + [2]
    assert cert["inner625"]["component_sizes"] == [[1, 464], [2, 16], [4, 8], [5, 16], [17, 1]]
    assert cert["outer_support"] == {"n_keys": 3153, "max_states": 17}
    r = _run(cert, tmp_path)
    assert r.status == "certified", (r.status, r.reason)


def _tamper(name):
    def f(d):
        if name == "k_inner":
            a, b = d["bright_pairs"][0]["pair"]
            d["k_inner"][a][b] = "1/3"
        elif name == "k_inner_sym":
            a, b = d["bright_pairs"][0]["pair"]
            d["k_inner"][b][a] = "5"
        elif name == "bright_coupling":
            d["bright_pairs"][0]["coupling"] = "7"
        elif name == "dark_row":
            d["dark_rows"][0] = d["bright_pairs"][0]["pair"][0]
        elif name == "gauge":
            k = next(i for i, g in enumerate(d["gauge"]) if i in {p["pair"][0] for p in d["bright_pairs"]} or True)
            # flip the gauge of every second state: some pair becomes inconsistent
            d["gauge"] = [-g if i % 2 else g for i, g in enumerate(d["gauge"])]
        elif name == "spectrum":
            d["spectrum"][3][1] -= 1
            d["spectrum"][4][1] += 1
        elif name == "state_coeff":
            d["states"][100]["terms"][0]["c"][0] = "1/7"
        elif name == "state_swap":
            t = d["states"][100]["terms"]
            t[0]["c"], t[1]["c"] = t[1]["c"], t[0]["c"]
            if t[0]["c"] == t[1]["c"]:
                t[0]["c"] = [("-" + x) if x not in ("0",) else x for x in t[0]["c"]]
        elif name == "generator":
            d["gens"]["L"][0] = [[["0"] * 8 for _ in range(5)] for _ in range(5)]
        elif name == "link_operator":
            d["u_link"][0][1][0][0] = ["1"] + ["0"] * 7
        elif name == "label_j":
            d["labels"][50]["j2"][0] ^= 1
        elif name == "label_J":
            d["labels"][120]["J2"][0] = 2 - d["labels"][120]["J2"][0]
        elif name == "outer_support":
            d["outer_support"]["n_keys"] -= 1
        elif name == "inner625_edges":
            d["inner625"]["n_edges"] += 2
        elif name == "inner625_moduli":
            d["inner625"]["edge_moduli"] = ["1/3"]
        elif name == "inner625_spec":
            d["inner625"]["spectrum"][3][1] -= 1
        elif name == "corner_dim":
            d["corner_kernel_dims"][5]["dim"] += 1
        elif name == "paulo":
            d["u_paulo"][0][0][0][1] = ["2"] + ["0"] * 7
        elif name == "sym_perm":
            s = d["symmetries"][-1]
            s["perm"][0], s["perm"][1] = s["perm"][1], s["perm"][0]
        elif name == "sym_sign":
            s = next(s for s in d["symmetries"] if s["name"] != "identity")
            i = next(i for i in range(433) if d["gauge"][i])
            s["signs"] = [-x if j in (5, 6, 7) else x for j, x in enumerate(s["signs"])]
        elif name == "drop_state":
            d["states"] = d["states"][:-1]
        return d
    return f


TAMPERS = ["k_inner", "k_inner_sym", "bright_coupling", "dark_row", "gauge", "spectrum", "state_coeff", "state_swap", "generator",
           "link_operator", "label_j", "label_J", "outer_support", "inner625_edges", "inner625_moduli", "inner625_spec",
           "corner_dim", "paulo", "sym_perm", "sym_sign", "drop_state"]


@pytest.mark.parametrize("name", TAMPERS)
def test_tampered_structure_certificate_is_rejected(name, cert, tmp_path):
    d = _tamper(name)(copy.deepcopy(cert))
    r = _run(d, tmp_path, f"{name}.json")
    assert r.status == "rejected", (name, r.status, r.reason)


def test_symmetry_candidates_and_facts():
    cands = S.symmetry_candidates()
    assert len(cands) == 16 and len({c["name"] for c in cands}) == 16
    ok = [c for c in cands if c["commutes_HB"] and c["commutes_HE"]]
    assert len(ok) == 16                              # the whole D4 x charge conjugation commutes at the label level
    assert {c["name"] for c in ok} >= {"identity", "C4", "C4^2", "C4^3", "reflect_x", "reflect_y", "cc"}
    ident = next(c for c in ok if c["name"] == "identity")
    assert ident["perm"] == list(range(433)) and set(ident["signs"]) == {1}
    c4 = next(c for c in ok if c["name"] == "C4")
    assert c4["perm"] != list(range(433)) and sorted(c4["perm"]) == list(range(433)) and c4["residual"] <= 1e-10
    # C4 has order four on the labels
    p = c4["perm"]
    q = list(range(433))
    for _ in range(4):
        q = [p[i] for i in q]
    assert q == list(range(433))
    facts = S.structure_facts()
    names = {f["name"] for f in facts["facts"]}
    assert names >= {"card_physical", "card_link_patterns", "card_two_or_more", "card_closed", "far_end_weighted",
                     "card_supported_outer", "max_states_per_outer", "dont_care_codes", "spectrum_multiplicities",
                     "k_inner_bright_pairs", "k_inner_dark_rows", "dark_labels", "inner625_components", "outer_support_table"}
    assert {s["name"] for s in facts["symmetries"]} == {c["name"] for c in ok}
    for f in facts["facts"]:
        assert f["proved_by"] in ("decide", "native", "numerical")
        if f["proved_by"] == "decide":
            assert f["theorem"].startswith("Su2Plaq.") and f["theorem"].split(".")[-1] == f["name"]
    down = S.structure_facts(certified=False)
    assert all(f["proved_by"] != "native" for f in down["facts"])


def test_write_structure_json(tmp_path):
    p = S.write_structure_json(tmp_path / "structure.json")
    doc = json.loads(pathlib.Path(p).read_text())
    assert set(doc) >= {"facts", "symmetries", "provenance"}
    assert doc["provenance"]["structure_certificate"]["status"] == "certified"
    by = {f["name"]: f for f in doc["facts"]}
    assert by["spectrum_multiplicities"]["proved_by"] == "native" and by["card_physical"]["value"] == 433


def test_note_n4_facts_are_native_only_after_a_checker_run(monkeypatch):
    monkeypatch.setattr(S, "_CERT_STATUS", {})
    calls = []

    def fake_check(path, timeout=900.0):
        calls.append(path)
        return LeanCert("rejected", "synthetic", str(path), 0.0, "")

    monkeypatch.setattr(S, "check_structure", fake_check)
    facts = S.structure_facts()                       # default: runs the checker (here: rejects)
    assert calls and all(f["proved_by"] != "native" for f in facts["facts"])
    assert any(f["proved_by"] == "decide" for f in facts["facts"])
    n = len(calls)
    S.structure_facts()                               # cached per checker fingerprint
    assert len(calls) == n
    assert all(f["proved_by"] == "native" for f in S.structure_facts(certified=True)["facts"] if "certificate" in f)

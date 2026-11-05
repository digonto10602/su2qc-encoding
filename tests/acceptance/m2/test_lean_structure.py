"""M2 — Lean 4 and the structure of the physics problem (prompts/006 §1 M5, §3 Counts, §4 structure certificate, §7;
reports/research/004 §2).  Counts are kernel-checked (`decide`, standard axioms); the exact block structure of H_B, K_inner,
the spectrum multiplicities, the 12-qubit inner operator and the symmetries are native-certified exact certificates.

PENDING rule: missing lean/ project or su2plaq.lean package -> `PENDING:` failure, never a collection error."""
import json
import pathlib
import time

import numpy as np
import pytest

from tests.acceptance._api import api

ENC, KIND = "twelve", "step"
STANDARD = {"propext", "Classical.choice", "Quot.sound"}

# LOCKED: kernel-checked counting theorems (prompts/006 §3; values from METHODS §4 and reports/tests/004, 020).
COUNT_THEOREMS = {
    "Su2Plaq.card_physical": 433,
    "Su2Plaq.card_link_patterns": 256,
    "Su2Plaq.card_two_or_more": 95,
    "Su2Plaq.card_closed": 2,
    "Su2Plaq.far_end_weighted": 17362,
    "Su2Plaq.card_supported_outer": 3153,
    "Su2Plaq.max_states_per_outer": 17,
    "Su2Plaq.dont_care_codes": 3471,
}
SPECTRUM = {-2.0: 16, -1.0: 96, -0.5: 16, 0.0: 177, 0.5: 16, 1.0: 96, 2.0: 16}   # reports/tests/005 (M0-X8)


def _lean_dir(root: pathlib.Path) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    return d


def test_lean_counts_kernel_checked(root):
    """The seven counts of the gauge-invariant subspace and the don't-care count are theorems proved by `decide` from the
    corner fusion rule: every name exists, no axiom beyond the standard three (a `decide` proof typically has none), and the
    statement text in Counts.lean pins the locked value."""
    d = _lean_dir(root)
    P = api("su2plaq.lean.project")
    assert set(COUNT_THEOREMS) <= set(P.COUNT_THEOREMS)
    src = (d / "Su2Plaq" / "Structure" / "Counts.lean").read_text()
    assert "native_decide" not in src and "sorry" not in src
    for name, value in COUNT_THEOREMS.items():
        short = name.split(".")[-1]
        assert f"theorem {short}" in src and f"= {value}" in src.split(f"theorem {short}", 1)[1].split("\n", 1)[0], (name, value)
    ax = P.print_axioms(list(COUNT_THEOREMS), timeout=900)
    missing = [n for n in COUNT_THEOREMS if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in COUNT_THEOREMS if ax[n] - STANDARD}
    assert not bad, bad


@pytest.mark.slow
def test_lean_structure_certificate_accept_reject(root, tmp_path):
    """Exact structure certificate: the checker recomputes H_B^phys from the exact physical states and link operators and
    verifies block-diagonality in the outer spins, J conservation, every block = D K_sub D for the 47x47 K_inner and a +-1
    gauge, K_inner = 8 bright 2x2 pairs (couplings 2, 1 x6, 1/2) + 31 dark rows, the spectrum multiplicities, the 625-code
    inner-operator components and the listed symmetries.  A tampered K_inner coupling (2 -> 1) is rejected."""
    _lean_dir(root)
    S = api("su2plaq.lean.structure")
    t0 = time.time()
    path = S.export_structure_certificate(tmp_path / "structure-cert.json")
    d = json.loads(pathlib.Path(path).read_text())
    assert len(d["states"]) == 433 and len(d["k_inner"]) == 47
    assert len(d["bright_pairs"]) == 8 and len(d["dark_rows"]) == 31
    assert {float(l): int(m) for l, m in d["spectrum"]} == SPECTRUM
    assert sum(1 for s in d["symmetries"]) >= 2
    r = S.check_structure(path, timeout=900)
    assert r.status == "certified", (r.status, r.reason)
    assert time.time() - t0 <= 1800
    # tamper: change one bright coupling of K_inner from 2 to 1 (exact rationals as "p/q" strings)
    i, j = [tuple(p["pair"]) for p in d["bright_pairs"] if str(p["coupling"]) in ("2", "2/1", "-2", "-2/1")][0]
    d["k_inner"][i][j] = "1/1" if not str(d["k_inner"][i][j]).startswith("-") else "-1/1"
    bad = tmp_path / "structure-bad.json"
    bad.write_text(json.dumps(d))
    r2 = S.check_structure(bad, timeout=900)
    assert r2.status == "rejected", (r2.status, r2.reason)


def test_structure_json_and_spec_section(root):
    """compress/lean/structure.json lists the proved facts with their trust level, and the task specification renders them
    for the proposers as the section "Proved structure (Lean)"."""
    _lean_dir(root)
    S = api("su2plaq.lean.structure")
    facts = S.structure_facts()
    by_name = {f["name"]: f for f in facts["facts"]}
    for name, value in (("card_physical", 433), ("card_link_patterns", 256), ("card_two_or_more", 95), ("card_closed", 2),
                        ("far_end_weighted", 17362), ("card_supported_outer", 3153), ("max_states_per_outer", 17)):
        assert name in by_name and by_name[name]["value"] == value and by_name[name]["proved_by"] == "decide", name
    assert by_name["spectrum_multiplicities"]["proved_by"] == "native"
    assert {float(l): int(m) for l, m in by_name["spectrum_multiplicities"]["value"]} == SPECTRUM
    assert all(f["proved_by"] in ("decide", "native", "numerical") for f in facts["facts"])
    p = S.write_structure_json(root / "compress" / "lean" / "structure.json")
    assert pathlib.Path(p).exists()
    text = api("su2plaq.compress.spec:default_spec")(ENC, KIND).render()
    assert "Proved structure (Lean)" in text and "433" in text and "3153" in text


def test_symmetry_candidates_verified(root):
    """The 16 geometric x charge-conjugation candidates are searched numerically; the identity and at least one non-trivial
    element commute with H_B and H_E on the 433 states (residual <= 1e-10, float64 on exact-valued matrices); every commuting
    candidate carries a signed label permutation and is listed in the structure facts for the proposers."""
    _lean_dir(root)
    S = api("su2plaq.lean.structure")
    cands = S.symmetry_candidates()
    assert len(cands) == 16
    ok = [c for c in cands if c["commutes_HB"] and c["commutes_HE"]]
    assert any(c["name"] == "identity" for c in ok) and len(ok) >= 2
    for c in ok:
        assert c["residual"] <= 1e-10 and len(c["perm"]) == 433 and len(c["signs"]) == 433
        assert sorted(c["perm"]) == list(range(433)) and set(np.sign(c["signs"]).tolist()) <= {-1.0, 1.0}
    listed = {s["name"] for s in S.structure_facts()["symmetries"]}
    assert {c["name"] for c in ok} <= listed

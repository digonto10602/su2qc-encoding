"""M7-L1, L2, L3 — Lean 4 for the loop-string-hadron encoding (prompts/400 §4; METHODS-lsh L10; trust levels of prompts/006).

L1: kernel-checked counts in lean/Su2Plaq/LSH/Counts.lean (core Lean, `decide` / `decide +kernel`, standard axioms only):
    5 valid site codes, 47 inner codes = 16 bright + 31 dark, 433 states obeying the flux cap and the Abelian Gauss law,
    256 bright states, raw register 82 inner / 5920 states; the loop-number -> flux map is injective; the flux sum is even.
L2: kernel-checked structure of the general circuit in lean/Su2Plaq/LSH/Circuit.lean: the transcoder maps the 47 LSH inner
    codes one-to-one onto the spin-network inner codes and leaves w_c on the third wire; the LSH coupling table equals
    the spin-network one under that map; transcoder + frame turn the plaquette move into X on the walk target; the
    integer Walsh table reproduces 2K on every valid code; flags are uncomputed.  Tables are exported by Python and must
    appear verbatim in the Lean source.
L3: native per-circuit certificate of the general step through `lake exe su2plaq_cert_lsh` (same exact checker as the
    spin network, pinned to the 433 LSH unit codes).
Planner prototypes: scratch/planner/lean/LSHCounts.lean (10.8 s), LSHCircuit.lean (21 s incl. the Mathlib import of
Su2Plaq.SpinNet.Circuit); every theorem depended on [propext] only."""
import pathlib
import time

import numpy as np
import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
COUNT_THEOREMS = {
    "Su2Plaq.LSH.card_site_codes": 5,
    "Su2Plaq.LSH.card_inner_codes": 47,
    "Su2Plaq.LSH.card_bright_codes": 16,
    "Su2Plaq.LSH.card_dark_codes": 31,
    "Su2Plaq.LSH.card_states_lsh": 433,
    "Su2Plaq.LSH.card_bright_states": 256,
    "Su2Plaq.LSH.card_raw_inner": 82,
    "Su2Plaq.LSH.card_raw_states": 5920,
}
RULE_THEOREMS = ("Su2Plaq.LSH.site_valid_list", "Su2Plaq.LSH.flux_injective", "Su2Plaq.LSH.flux_even")
CIRCUIT_THEOREMS = ("Su2Plaq.LSH.transcode_into_spinnet", "Su2Plaq.LSH.transcode_injective", "Su2Plaq.LSH.transcode_w",
                    "Su2Plaq.LSH.coupling_matches_spinnet", "Su2Plaq.LSH.pre_maps_partner_to_x", "Su2Plaq.LSH.walk_table_exact",
                    "Su2Plaq.LSH.ancillas_clean")


def _lean_file(root: pathlib.Path, rel: str) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing", pytrace=False)
    p = d / rel
    if not p.exists():
        pytest.fail(f"PENDING: {p.relative_to(root)} missing (prompts/400 Lean steps)", pytrace=False)
    return p


def _no_native_no_sorry(src: str):
    assert "native_decide" not in src and "sorry" not in src and "admit" not in src


def _axioms_standard(names):
    P = api("su2plaq.lean.project")
    t0 = time.time()
    ax = P.print_axioms(list(names), timeout=900)
    assert time.time() - t0 <= 900
    missing = [n for n in names if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in names if ax[n] - STANDARD}
    assert not bad, bad


def test_M7_L1_lsh_counts_kernel_checked(root):
    """Every count theorem exists in Counts.lean with the locked value in its statement, is proved without native_decide
    or sorry, and depends on the standard axioms only."""
    p = _lean_file(root, "Su2Plaq/LSH/Counts.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert "namespace Su2Plaq.LSH" in src
    for name, value in COUNT_THEOREMS.items():
        short = name.split(".")[-1]
        assert f"theorem {short}" in src, name
        stmt = src.split(f"theorem {short}", 1)[1].split("\n", 1)[0]
        assert f"= {value}" in stmt, (name, value, stmt)
    for name in RULE_THEOREMS:
        assert f"theorem {name.split('.')[-1]}" in src
    stmt = src.split("theorem site_valid_list", 1)[1].split("\n", 1)[0]
    assert "[0, 1, 2, 4, 6]" in stmt
    assert "import Su2Plaq.LSH.Counts" in (root / "lean" / "Su2Plaq.lean").read_text()
    _axioms_standard(list(COUNT_THEOREMS) + list(RULE_THEOREMS))
    assert api("su2plaq.lean.project").no_sorry() == []


def test_M7_L2_general_circuit_structure_kernel_checked(root):
    """Circuit.lean: the seven structure theorems exist with standard axioms only; the integer tables printed by
    su2plaq.lsh.lean_export (47 sorted inner codes, 2K per code, partner per code, rz angles in units of beta/2) appear
    verbatim in the Lean source and agree with the Python objects: 2K in {-4 (x2), -1 (x2), 2 (x12), 0 (x31)}, angles =
    the rotations of build_UB (1e-9)."""
    p = _lean_file(root, "Su2Plaq/LSH/Circuit.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert "import Su2Plaq.SpinNet.Circuit" in src and "namespace Su2Plaq.LSH" in src
    assert "import Su2Plaq.LSH.Circuit" in (root / "lean" / "Su2Plaq.lean").read_text()
    for name in CIRCUIT_THEOREMS:
        assert f"theorem {name.split('.')[-1]}" in src, name
    LE = api("su2plaq.lsh.lean_export")
    enc = api("su2plaq.encodings.lsh:LSH")()
    W = api("su2plaq.lsh.walk")
    codes = enc.inner_codes().tolist()
    coupling = LE.coupling_ints(enc)                       # 2 K[partner, code] per sorted inner code
    partner = LE.partner_ints(enc)                         # partner code (the code itself for dark codes)
    angles = LE.angle_ints(enc)                            # rz angle / (beta/2) per rotation of build_UB, gate order
    assert len(coupling) == 47 and all(isinstance(x, int) for x in coupling) and sorted(set(coupling)) == [-4, -1, 0, 2]
    assert coupling.count(-4) == 2 and coupling.count(-1) == 2 and coupling.count(2) == 12 and coupling.count(0) == 31
    table, ptab = W.coupling_table(enc), W.partner_table(enc)
    assert all(2 * table[c] == x for c, x in zip(codes, coupling))
    assert partner == [ptab.get(c, c) for c in codes]
    lm = api("su2plaq.metrics.logical:logical_metrics")(api("su2plaq.circuits.lsh:build_UB")(0.61))
    assert len(angles) == lm["n_rot"] and all(isinstance(x, int) for x in angles)
    assert np.allclose(sorted(np.array(angles) * 0.61 / 2), sorted(lm["rz_angles"]), atol=1e-9)
    lit = LE.lean_literals(enc)
    for key in ("codes", "coupling", "partner", "angles"):
        assert lit[key] in src, f"Lean table '{key}' differs from the Python export"
    assert lit["codes"] == "[" + ", ".join(str(c) for c in codes) + "]"
    _axioms_standard(CIRCUIT_THEOREMS)


@pytest.mark.slow
def test_M7_L3_native_certificate_general_step(root):
    """Exact Laurent-polynomial certificate (schema su2plaq-cert-1, prompts/006 §4) of build_step(0.37, 0.61, 1,
    with_outer=True): states = the 433 LSH unit codes (n_data = n_outer = 12), target = the exact LSH/route-B blocks over
    K = Q(i, sqrt2, sqrt3), checked by `lake exe su2plaq_cert_lsh check` -> 'certified' (<= 900 s); a circuit with one
    angle changed by a factor 1 + 1e-6 -> 'rejected' or 'n_a'."""
    _lean_file(root, "Su2PlaqCert/LSH/Main.lean")
    _lean_file(root, "Su2PlaqCert/LSH/Pins.lean")
    assert "su2plaq_cert_lsh" in (root / "lean" / "lakefile.toml").read_text()
    LE = api("su2plaq.lsh.lean_export")
    enc = api("su2plaq.encodings.lsh:LSH")()
    build_step = api("su2plaq.circuits.lsh:build_step")
    qc = build_step(0.37, 0.61, 1, with_outer=True)
    t0 = time.time()
    r = LE.certify(qc, enc, "step", 0.37, 0.61, 1)
    assert time.time() - t0 <= 900
    assert r["status"] == "certified", (r["status"], r.get("reason"))
    assert r["cert_path"] and pathlib.Path(r["cert_path"]).exists()
    assert all(api("su2plaq.lean.project").is_native_axiom(a) for a in r.get("axioms", []) if a not in STANDARD)
    bad = build_step(0.37, 0.61 * (1 + 1e-6), 1, with_outer=True)
    r2 = LE.certify(bad, enc, "step", 0.37, 0.61, 1)
    assert r2["status"] in ("rejected", "n_a")

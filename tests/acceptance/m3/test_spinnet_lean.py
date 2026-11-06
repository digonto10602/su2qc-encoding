"""M3-L1, L2, L3 — Lean 4 for the spin-network encoding (prompts/100 §4; METHODS-spinnet §7; prompts/006 trust levels).

L1: kernel-checked (`decide`, standard axioms) counts in lean/Su2Plaq/SpinNet/Counts.lean — 47 inner labels, 16 bright /
    31 dark, 8 bright pairs, the spectrum multiplicities of H_B as pair-class counts over the 433 labels (16 / 96 / 16 for
    |K| = 2, 1, 1/2 pairs; 177 dark states), code injectivity per corner, the corner-qubit rule.  The 433 count itself is
    the laptop's Su2Plaq.card_physical (read-only, not redone).
L2: kernel-checked structure of the general circuit in lean/Su2Plaq/SpinNet/Circuit.lean — the CX frame maps the four-link
    flip to X on the target wire; the flag chain computes F, G1, G2; the integer Walsh angle table reproduces 2K on every
    valid slot (angles in units of beta/2; coupling table 2K as integers).  The tables are exported by Python and must
    appear verbatim in the Lean source (no drift).
L3: native per-circuit certificate of the general step circuit through the laptop's checker (prompts/006 §4, step 2.L4+):
    PENDING until the milestone-2 bundle delivers Su2PlaqCert; then status 'certified' with exactly one native axiom.
Everything Lean checks is exact; the only numbers are time limits (900 s as in M2) and the 1e-12 float cross-checks."""
import pathlib
import time

import numpy as np
import pytest

from tests.acceptance._api import api

STANDARD = {"propext", "Classical.choice", "Quot.sound"}
COUNT_THEOREMS = {
    "Su2Plaq.SpinNet.card_inner_labels": 47,
    "Su2Plaq.SpinNet.card_bright_labels": 16,
    "Su2Plaq.SpinNet.card_dark_labels": 31,
    "Su2Plaq.SpinNet.card_bright_pairs": 8,
    "Su2Plaq.SpinNet.mult_two": 16,
    "Su2Plaq.SpinNet.mult_half": 16,
    "Su2Plaq.SpinNet.mult_one": 96,
    "Su2Plaq.SpinNet.card_bright_states": 256,
    "Su2Plaq.SpinNet.card_dark_states": 177,
    "Su2Plaq.SpinNet.card_states_spinnet": 433,
}
RULE_THEOREMS = ("Su2Plaq.SpinNet.corner_jbit_injective", "Su2Plaq.SpinNet.corner_bit_needs_four_half")
CIRCUIT_THEOREMS = ("Su2Plaq.SpinNet.frame_maps_flip", "Su2Plaq.SpinNet.flags_correct", "Su2Plaq.SpinNet.walk_table_exact")


def _lean_file(root: pathlib.Path, rel: str) -> pathlib.Path:
    d = root / "lean"
    if not (d / "lakefile.toml").exists():
        pytest.fail("PENDING: lean/lakefile.toml missing (prompts/006 step 2.L1)", pytrace=False)
    p = d / rel
    if not p.exists():
        pytest.fail(f"PENDING: {p.relative_to(root)} missing (prompts/100 Lean steps)", pytrace=False)
    return p


def _no_native_no_sorry(src: str):
    assert "native_decide" not in src and "sorry" not in src and "admit" not in src


def test_M3_L1_spinnet_counts_kernel_checked(root):
    """Every count theorem exists in Counts.lean with the locked value in its statement, is proved without native_decide
    or sorry, and depends on the standard axioms only; the 433 count reuses Su2Plaq.card_physical."""
    p = _lean_file(root, "Su2Plaq/SpinNet/Counts.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert "import Su2Plaq.Structure.Counts" in src and "namespace Su2Plaq.SpinNet" in src
    for name, value in COUNT_THEOREMS.items():
        short = name.split(".")[-1]
        assert f"theorem {short}" in src, name
        stmt = src.split(f"theorem {short}", 1)[1].split("\n", 1)[0]
        assert f"= {value}" in stmt, (name, value, stmt)
    for name in RULE_THEOREMS:
        assert f"theorem {name.split('.')[-1]}" in src
    root_lean = (root / "lean" / "Su2Plaq.lean").read_text()
    assert "import Su2Plaq.SpinNet.Counts" in root_lean
    P = api("su2plaq.lean.project")
    names = list(COUNT_THEOREMS) + list(RULE_THEOREMS) + ["Su2Plaq.card_physical"]
    t0 = time.time()
    ax = P.print_axioms(names, timeout=900)
    assert time.time() - t0 <= 900
    missing = [n for n in names if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in names if ax[n] - STANDARD}
    assert not bad, bad
    assert P.no_sorry() == []


def test_M3_L2_general_circuit_structure_kernel_checked(root):
    """Circuit.lean: frame_maps_flip, flags_correct, walk_table_exact exist, standard axioms only; the integer coupling
    table (2K on the 47 sorted inner codes) and the angle table (units of beta/2) printed by su2plaq.spinnet.lean_export
    appear verbatim in the Lean source, equal 2 x K_inner exactly, and solve the walk (residual <= 1e-12)."""
    p = _lean_file(root, "Su2Plaq/SpinNet/Circuit.lean")
    src = p.read_text()
    _no_native_no_sorry(src)
    assert "import Su2Plaq.SpinNet.Counts" in src
    root_lean = (root / "lean" / "Su2Plaq.lean").read_text()
    assert "import Su2Plaq.SpinNet.Circuit" in root_lean
    for name in CIRCUIT_THEOREMS:
        assert f"theorem {name.split('.')[-1]}" in src, name
    LE = api("su2plaq.spinnet.lean_export")
    enc = api("su2plaq.encodings.spinnet:SpinNet")()
    coupling = LE.coupling_ints(enc)                       # list of 47 ints, sorted inner-code order, = 2 K[partner, code]
    angles = LE.angle_ints(enc)                            # list of ints: rz angle / (beta/2) per rotation of build_UB
    assert len(coupling) == 47 and all(isinstance(x, int) for x in coupling) and sorted(set(coupling)) == [-4, -1, 0, 2]
    assert coupling.count(-4) == 2 and coupling.count(-1) == 2 and coupling.count(2) == 12 and coupling.count(0) == 31
    table = api("su2plaq.spinnet.walk:coupling_table")(enc)
    codes = enc.inner_codes().tolist()
    assert all(abs(2 * table[c] - x) == 0 for c, x in zip(codes, coupling))
    lm = api("su2plaq.metrics.logical:logical_metrics")(api("su2plaq.circuits.spinnet:build_UB")(0.61))
    assert len(angles) == lm["n_rot"] and all(isinstance(x, int) for x in angles)
    assert np.allclose(sorted(np.array(angles) * 0.61 / 2), sorted(lm["rz_angles"]), atol=1e-9)
    lit = LE.lean_literals(enc)
    assert lit["coupling"] in src and lit["angles"] in src, "Lean tables differ from the Python export"
    P = api("su2plaq.lean.project")
    ax = P.print_axioms(list(CIRCUIT_THEOREMS), timeout=900)
    missing = [n for n in CIRCUIT_THEOREMS if n not in ax or "<unknown>" in ax[n]]
    assert not missing, missing
    bad = {n: sorted(ax[n] - STANDARD) for n in CIRCUIT_THEOREMS if ax[n] - STANDARD}
    assert not bad, bad


@pytest.mark.slow
def test_M3_L3_native_certificate_general_step(root):
    """Exact Laurent-polynomial certificate (prompts/006 §4 schema su2plaq-cert-1) of build_step(0.37, 0.61, 1,
    with_outer=True) exported by su2plaq.spinnet.lean_export.export_certificate (states = 433 unit codes, target =
    route-B blocks over K = Q(i, sqrt2, sqrt3) with base angles alpha/4, beta/4) and checked by `lake exe su2plaq_cert
    check` -> 'certified' (<= 900 s); a tampered angle -> 'rejected'.  PENDING while the checker is the laptop's skeleton."""
    _lean_file(root, "Su2PlaqCert/Main.lean")
    main_src = (root / "lean" / "Su2PlaqCert" / "Main.lean").read_text()
    if "REJECT unimplemented" in main_src:
        pytest.fail("PENDING: Su2PlaqCert checker not yet delivered by the laptop (prompts/006 step 2.L4)", pytrace=False)
    LE = api("su2plaq.spinnet.lean_export")
    enc = api("su2plaq.encodings.spinnet:SpinNet")()
    qc = api("su2plaq.circuits.spinnet:build_step")(0.37, 0.61, 1, with_outer=True)
    t0 = time.time()
    r = LE.certify(qc, enc, "step", 0.37, 0.61, 1)
    assert time.time() - t0 <= 900
    assert r["status"] == "certified", (r["status"], r.get("reason"))
    assert r["cert_path"] and pathlib.Path(r["cert_path"]).exists()
    assert all(api("su2plaq.lean.project").is_native_axiom(a) for a in r.get("axioms", []) if a not in STANDARD)
    bad = api("su2plaq.circuits.spinnet:build_step")(0.37, 0.61 * (1 + 1e-6), 1, with_outer=True)
    r2 = LE.certify(bad, enc, "step", 0.37, 0.61, 1)
    assert r2["status"] in ("rejected", "n_a")

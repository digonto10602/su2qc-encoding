"""Unit tests for su2plaq.lean.project (step 2.L1): pins, sorry scan, native-axiom recogniser, axiom printing, stubs."""
import os
import pathlib

import pytest

from su2plaq.lean import certify, exact, lemmas, project, rules, structure


def test_pins_and_files():
    assert project.TOOLCHAIN == "leanprover/lean4:v4.35.0" and project.MATHLIB_REV == "v4.35.0"
    assert (project.LEAN_DIR / "lean-toolchain").read_text().strip() == project.TOOLCHAIN
    assert project.STANDARD_AXIOMS == {"propext", "Classical.choice", "Quot.sound"}
    assert len(project.GENERIC_THEOREMS) == 26 and len(set(project.GENERIC_THEOREMS)) == 26
    assert len(project.COUNT_THEOREMS) == 8
    assert all(n.startswith("Su2Plaq.") for n in project.GENERIC_THEOREMS + project.COUNT_THEOREMS)


def test_is_native_axiom():
    f = project.is_native_axiom
    assert f("Su2Plaq.foo._native.native_decide.ax_1") and f("X._native.native_decide.ax_1_2_3")
    assert f("Lean.ofReduceBool")
    assert not any(f(a) for a in project.STANDARD_AXIOMS) and not f("sorryAx")


def test_no_sorry_scanner(tmp_path):
    good = tmp_path / "good.lean"
    good.write_text('-- sorry in a comment\n/- block sorry /- nested sorry -/ still comment sorry -/\n'
                    'def s := "a sorry string"\ntheorem t : 1 = 1 := rfl\ndef sorryFree := 1\n')
    chars = tmp_path / "chars.lean"
    chars.write_text("def a := '\"'\ndef b := '\\''\ndef c (x' : Nat) := x'\ntheorem t : True := by\n  sorry\n")
    assert len(project.no_sorry([chars])) == 1 and ":5:" in project.no_sorry([chars])[0]
    bad = tmp_path / "bad.lean"
    bad.write_text("theorem t : 1 = 2 := by\n  sorry\n/- c -/ theorem u : False := by admit\n")
    assert project.no_sorry([good]) == []
    hits = project.no_sorry([bad])
    assert len(hits) == 2 and ":2:" in hits[0] and ":3:" in hits[1]
    assert project.no_sorry() == []          # the project itself is clean


def test_lake_build_checker_and_exe():
    r = project.build("Su2PlaqCert", timeout=600)
    assert r["ok"], r["stderr"][-1000:]
    r = project.lake(["exe", "su2plaq_cert", "check", "no-such-file.json"], timeout=120)
    assert r.returncode == 1 and r.stdout.strip().startswith("REJECT cannot read")
    r = project.lake(["exe", "su2plaq_cert", "structure", "x.json"], timeout=120)
    assert r.returncode == 1 and r.stdout.strip().startswith("REJECT structure checker not implemented")


def test_print_axioms_real_and_unknown():
    ax = project.print_axioms(["Nat.add_comm", "Classical.em", "Su2Plaq.does_not_exist"], timeout=600)
    assert ax["Nat.add_comm"] == frozenset()
    assert ax["Classical.em"] <= project.STANDARD_AXIOMS and "Classical.choice" in ax["Classical.em"]
    assert ax["Su2Plaq.does_not_exist"] == frozenset({"<unknown>"})
    assert not (project.LEAN_DIR / f"AxiomCheck_{os.getpid()}.lean").exists()   # own temp file only (other workers may run)


def test_skeleton_stubs_raise():
    with pytest.raises(NotImplementedError):
        structure.structure_facts()
    with pytest.raises(NotImplementedError):
        lemmas.check_program_lemmas(pathlib.Path("x.py"))
    assert isinstance(rules.LEAN_RULES, dict)
    assert certify.LeanCert("n_a", "r", None, 0.0, "").axioms == []


L2_THEOREMS = (
    "Su2Plaq.norm_sum_sq_of_pairwise_orth", "Su2Plaq.opNorm_add_three_le_of_orth", "Su2Plaq.rss_le_sum",
    "Su2Plaq.pruning_triangle", "Su2Plaq.opNorm_le_of_blockdiag", "Su2Plaq.verdict_sound",
    "Su2Plaq.gauss_max_ge", "Su2Plaq.span_leak_le_four_gauss", "Su2Plaq.cs_block_bound",
    "Su2Plaq.norm_list_prod_le_one", "Su2Plaq.prod_sub_prod_le", "Su2Plaq.synth_bound",
)


def test_step_2L2_theorems_exist_with_standard_axioms():
    """Evaluator/Gauss/Aer/Synthesis theorems (prompts/006 step 2.L2): kernel-checked, standard axioms only."""
    assert set(L2_THEOREMS) <= set(project.GENERIC_THEOREMS)
    ax = project.print_axioms(list(L2_THEOREMS), timeout=600)
    for n in L2_THEOREMS:
        assert "<unknown>" not in ax[n], n
        assert ax[n] <= project.STANDARD_AXIOMS, (n, sorted(ax[n]))
    assert project.no_sorry() == []
    for f in ("Evaluator", "Gauss", "Aer", "Synthesis"):
        assert "native_decide" not in (project.LEAN_DIR / "Su2Plaq" / f"{f}.lean").read_text()


def test_rccx_phase_rule_in_gates_lean_matches_qiskit():
    """Gates.lean defines RCCX = mono rccxPerm rccxPhase; re-implement that rule here and compare with Qiskit's matrix
    (qubits a, b, h little-endian: index a + 2b + 4h)."""
    import numpy as np
    from qiskit.circuit.library import RCCXGate

    M = np.zeros((8, 8), dtype=complex)
    for a in (0, 1):
        for b in (0, 1):
            for h in (0, 1):
                h2 = (h + a * b) % 2
                if a == 1 and b == 1:
                    ph = 1j if h == 0 else -1j
                elif a == 1 and b == 0 and h == 1:
                    ph = -1
                else:
                    ph = 1
                M[a + 2 * b + 4 * h2, a + 2 * b + 4 * h] = ph
    assert np.abs(M - RCCXGate().to_matrix()).max() < 1e-14
    text = (project.LEAN_DIR / "Su2Plaq" / "Gates.lean").read_text()
    assert "if p.1.1 = 1 ∧ p.1.2.1 = 1 then (if p.2 = 0 then Complex.I else -Complex.I)" in text


L3_THEOREMS = tuple(n for n in project.GENERIC_THEOREMS if n not in L2_THEOREMS)


def test_step_2L3_theorems_exist_with_standard_axioms():
    """Gates / Peephole / Commute theorems and the counts (prompts/006 step 2.L3): kernel-checked, standard axioms only."""
    names = list(L3_THEOREMS) + list(project.COUNT_THEOREMS)
    assert len(L3_THEOREMS) == 14
    ax = project.print_axioms(names, timeout=3600)
    for n in names:
        assert "<unknown>" not in ax[n], n
        assert ax[n] <= project.STANDARD_AXIOMS, (n, sorted(ax[n]))
    assert project.no_sorry() == []
    for f in project.LEAN_DIR.joinpath("Su2Plaq").rglob("*.lean"):
        assert "native_decide" not in f.read_text(), f

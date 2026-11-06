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
    assert r.returncode == 1 and r.stdout.strip().startswith("REJECT cannot read")


def test_print_axioms_real_and_unknown():
    ax = project.print_axioms(["Nat.add_comm", "Classical.em", "Su2Plaq.does_not_exist"], timeout=600)
    assert ax["Nat.add_comm"] == frozenset()
    assert ax["Classical.em"] <= project.STANDARD_AXIOMS and "Classical.choice" in ax["Classical.em"]
    assert ax["Su2Plaq.does_not_exist"] == frozenset({"<unknown>"})
    assert not (project.LEAN_DIR / f"AxiomCheck_{os.getpid()}.lean").exists()   # own temp file only (other workers may run)


def test_lean_cert_defaults():
    assert certify.LeanCert("n_a", "r", None, 0.0, "").axioms == []


def test_polish_rules_table_and_theorems():
    from su2plaq.lean import rules

    assert set(rules.LEAN_RULES) == {"cancel_inverse_pairs", "merge_adjacent_rotations"}
    assert all(v.startswith("Su2Plaq.") and v.split(".")[-1] == k for k, v in rules.LEAN_RULES.items())
    src = (project.LEAN_DIR / "Su2Plaq" / "Rewrites.lean").read_text()
    for needle in ("diagonal (czDiag a b) * diagonal (czDiag b a) = 1", "perm (swapE a b) * perm (swapE b a) = 1",
                   "diagonal (cczDiag a b c) * diagonal (cczDiag c b a) = 1"):
        assert needle in src, needle                 # the symmetric-pair cases the pass cancels
    ax = project.print_axioms(sorted(rules.LEAN_RULES.values()), timeout=600)
    for n, a in ax.items():
        assert a <= project.STANDARD_AXIOMS, (n, sorted(a))


def test_program_lemma_files(tmp_path):
    from su2plaq.lean import lemmas

    prog = tmp_path / "001-x.py"
    prog.write_text("# program\n")
    assert lemmas.lemma_file_for(prog) is None and lemmas.check_program_lemmas(prog)["status"] == "none"
    lem = tmp_path / "001-x.lean"

    def run(text):
        lem.write_text(text)
        return lemmas.check_program_lemmas(prog, timeout=120)

    ok = run("import Su2Plaq\n\ntheorem fact_a : (2 : Nat) + 2 = 4 := by decide\n\ntheorem fact_b (a b : Nat) : a + b = b + a := Nat.add_comm a b\n")
    assert ok["status"] == "proved" and ok["axioms_ok"] and ok["theorems"] == ["fact_a", "fact_b"], ok
    assert run("import Su2Plaq\ntheorem t : (2 : Nat) + 2 = 5 := by sorry\n")["status"] == "failed"
    assert run("import Su2Plaq\ntheorem t : (2 : Nat) + 2 = 4 := by native_decide\n")["status"] == "failed"
    assert run("import Su2Plaq\ntheorem t : (2 : Nat) + 2 = 5 := by decide\n")["status"] == "failed"       # does not elaborate
    r = run("import Std\ntheorem t : (2 : Nat) + 2 = 4 := by decide\n")
    assert r["status"] == "failed" and "import" in r["message"]
    # classical axioms are standard; a hand-declared axiom is not accepted
    assert run("import Su2Plaq\ntheorem t (p : Prop) : p ∨ ¬p := Classical.em p\n")["status"] == "proved"
    assert run("import Su2Plaq\naxiom bad : (2 : Nat) = 3\ntheorem t : (2 : Nat) = 3 := bad\n")["status"] == "failed"
    assert not list((project.LEAN_DIR).glob("Lemma_*.lean"))


def test_lemma_files_with_side_effects_or_no_theorem(tmp_path):
    from su2plaq.lean import lemmas

    prog = tmp_path / "002-y.py"
    prog.write_text("# program\n")
    lem = tmp_path / "002-y.lean"
    victim = tmp_path / "pwned.txt"

    def run(text):
        lem.write_text(text)
        return lemmas.check_program_lemmas(prog, timeout=120)

    base = "import Su2Plaq\ntheorem t : (2 : Nat) + 2 = 4 := by decide\n"
    for bad in (f'#eval IO.FS.writeFile "{victim}" "x"', "#exit", "run_cmd pure ()", "run_tac pure ()", "initialize foo : IO.Ref Nat <- IO.mkRef 0",
                "elab \"evil\" : command => pure ()", "macro \"m\" : term => `(1)", "unsafe def u : Nat := 1", "axiom ax : False"):
        r = run(base + bad + "\n")
        assert r["status"] == "failed" and "not accepted" in r["message"], (bad, r)
        assert not victim.exists()
    # words inside comments and identifiers are fine
    assert run("import Su2Plaq\n-- #eval IO.println in a comment\ntheorem eval_io_ok : (1 : Nat) = 1 := rfl\n")["status"] == "proved"
    # a file without theorem / lemma is not 'proved'
    r = run("import Su2Plaq\n\ndef foo : Nat := 3\n")
    assert r["status"] == "none" and "no theorem" in r["message"]
    assert run("import Su2Plaq\n")["status"] == "none"

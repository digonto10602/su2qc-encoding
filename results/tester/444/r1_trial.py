"""Tester 444: run the locked test M8-R1 body against the TRIAL results file (scratch/m8trial444) in a scratch root made of symlinks (real tree untouched).
Variant A: trial file as written (provenance.git_dirty True -> expected failure at that assertion).  Variant B: same file with git_dirty forced False in the scratch copy
only, to see which assertion fails next (expected: only the missing theorem file / its path).  Variant C: B plus the theorem_file field set in the scratch copy
(stands in for step 8.9), to check that all remaining assertions (markdown included) hold."""
import sys, os, json, pathlib, shutil, traceback
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); SC = pathlib.Path(sys.argv[1]); TRIAL = ROOT / "scratch/m8trial444"
root = SC / "root"; shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
for p in ROOT.iterdir():
    if p.name in ("results",): continue
    (root / p.name).symlink_to(p)
(root / "results").mkdir()
for p in (ROOT / "results").iterdir():
    if p.name != "lsh": (root / "results" / p.name).symlink_to(p)
(root / "results/lsh").mkdir()
for p in (ROOT / "results/lsh").iterdir(): (root / "results/lsh" / p.name).symlink_to(p)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests/acceptance/m8")); sys.path.insert(0, str(ROOT / "src"))
import pytest
import test_lsh_m8_gate as T
out = {}
def attempt(label):
    try:
        T.test_M8_R1_results_and_before_after(root); out[label] = "PASSED"
    except BaseException as e:   # pytest.fail raises Failed (BaseException subclass)
        tb = traceback.extract_tb(e.__traceback__)[-1]
        out[label] = f"{type(e).__name__}: {str(e)[:160]} @ line {tb.lineno}: {tb.line}"
for var in ("A", "B", "C"):
    for n in ("m8-compressed.json", "m8-before-after.md", "m8-headline-step.qasm3", "m8-headline-step.qpy"):
        (root / "results/lsh" / n).unlink(missing_ok=True)
    for n in os.listdir(TRIAL):
        shutil.copy(TRIAL / n, root / "results/lsh" / n)
    if var in ("B", "C"):
        d = json.load(open(root / "results/lsh/m8-compressed.json")); d["provenance"]["git_dirty"] = False
        if var == "C": d["extra"]["lean"]["theorem_file"] = "lean/certs/lsh-best-step.lean"   # scratch copy only: stands in for step 8.9
        json.dump(d, open(root / "results/lsh/m8-compressed.json", "w"))
    attempt(var)
    print(var, out[var], flush=True)
json.dump(out, open(ROOT / "results/tester/444/r1_trial.json", "w"), indent=1)

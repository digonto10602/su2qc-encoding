import sys, json, pathlib, tempfile, shutil
sys.path.insert(0, "src")
from su2plaq.encodings.lsh import LSH
from su2plaq.lsh import lean_export as LE
from su2plaq.circuits.lsh import build_step
tmp = pathlib.Path(tempfile.mkdtemp(prefix="t408b-", dir="scratch/tester")); enc = LSH(); qc = build_step(0.37, 0.61, 1, with_outer=True)
LE._git_dirty = lambda: True
r = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp)
LE._git_dirty = lambda: False       # "clean worktree" regeneration over an existing dirty-written certificate
r = LE.certify(qc, enc, "step", 0.37, 0.61, 1, out_dir=tmp)
res = {"git_dirty_after_clean_regeneration_over_existing": json.loads(open(r["cert_path"]).read())["provenance"]["git_dirty"]}
shutil.rmtree(tmp)
json.dump(res, open("results/lsh_tester/tester-408-dirty-trap.json", "w")); print(res)

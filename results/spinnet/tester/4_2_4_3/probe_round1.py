import sys, shutil, json, pathlib
from su2plaq.spinnet import loop as L
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
shutil.copytree(src, dst)
base = (dst / "compress/programs/spinnet/seed/001-spinnet_v2_pairs9.py").read_text()
good = base.replace("FAMILY = 'seed'", "FAMILY = 'F1'").replace("PARENT = None", "PARENT = 'r00-seed-001'")
assert good != base
fam = dst / "compress/programs/spinnet/F1"; fam.mkdir(parents=True)
(fam / "001-same.py").write_text(good.replace("SUMMARY: the vendored", "SUMMARY: (copy) the vendored"))
bad = good.replace("    return b", "    b.x(0)\n    return b").replace("SUMMARY: the vendored", "SUMMARY: (bad: extra x) the vendored")
(fam / "002-bad.py").write_text(bad)
info = L.run_round(1, evaluate=True, dry_run=True, root=dst, lean=False)
d = json.loads((dst / "results/compress/spinnet/round-001.json").read_text())
print(json.dumps({"info": info, "spinnet": d["spinnet"], "cands": [(c["label"], c["valid"], c["reason"], c["key"], c["parent"], c["parent_known"], c["family"]) for c in d["candidates"]], "invalid": d["invalid"]}, indent=1, default=str)[:3000])
att = [json.loads(x) for x in (dst / "compress/attempts/spinnet.jsonl").read_text().splitlines()]
print([(a["id"], a["round"], a["valid"], a["reason"]) for a in att if a["round"] == 1])
print((L.make_brief(2, "F1", root=dst)).read_text()[:2500])

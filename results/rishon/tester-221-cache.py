"""Tester 221: cache behaviour of robust.headline (tmp root, copy of archive + robust.json; the real files are not touched).
 (a) unchanged cache -> no rebuild (time << 1 s), ranking identical to a fresh recompute (refresh=True) for all 16 entries;
 (b) cache record with a wrong program_sha256 for r04-F1-004 (and a falsified T) -> entry recomputed, T restored;
 (c) cache record with the right sha but a falsified t_sum (tamper) -> trusted (documents what the cache does NOT verify);
 (d) wrong evaluator_sha256 or angle_set sha -> everything recomputed (counted by timing / by value restore)."""
import json, os, shutil, tempfile, time, pathlib, sys, subprocess
import su2plaq.rishon.compress
from su2plaq.rishon.compress import robust
from su2plaq.compress.spec import ROOT
tmp = pathlib.Path(tempfile.mkdtemp(prefix="t221cache", dir=sys.argv[1]))
shutil.copytree(ROOT / "compress/archive/rishon", tmp / "compress/archive/rishon")
(tmp / "results/compress/rishon").mkdir(parents=True)
orig = json.load(open(ROOT / "results/compress/rishon/robust.json"))
cf = tmp / "results/compress/rishon/robust.json"
def put(d): cf.write_text(json.dumps(d))
def run(**kw):
    t = time.time(); h = robust.headline("step", root=tmp, **kw); return h, time.time() - t
out = {}
put(orig); h, dt = run(); base = [(r["id"], r["robust_key"]) for r in h["ranking"]]
out["a_unchanged"] = dict(seconds=dt, headline=h["id"], key=h["robust_key"], same_as_cache=all(tuple(orig["entries"][i]["robust_key"]) == tuple(k) for i, k in base if k))
print("a", out["a_unchanged"])
# (b)
d = json.loads(json.dumps(orig)); e = d["entries"]["r04-F1-004"]; e["program_sha256"] = "0" * 64; e["t_sum"] = 1; e["robust_key"][1] = 1; e["t_eps"][0] = 1
put(d); h, dt = run(); r0 = next(r for r in h["ranking"] if r["id"] == "r04-F1-004")
out["b_wrong_program_sha"] = dict(seconds=dt, restored_key=r0["robust_key"], correct=tuple(r0["robust_key"]) == (228, 16876, 0, 28328, 53))
print("b", out["b_wrong_program_sha"])
# (c)
d = json.loads(json.dumps(orig)); d["entries"]["r04-F1-004"]["robust_key"][1] = 1
put(d); h, dt = run(); r0 = next(r for r in h["ranking"] if r["id"] == "r04-F1-004")
out["c_tampered_value_same_sha"] = dict(seconds=dt, key_used=r0["robust_key"], trusted=r0["robust_key"][1] == 1)
print("c", out["c_tampered_value_same_sha"])
# (d) evaluator hash mismatch -> full recompute
d = json.loads(json.dumps(orig)); d["evaluator_sha256"] = "f" * 64
for v in d["entries"].values(): v["robust_key"][1] = 1
put(d); h, dt = run()
rec = json.loads(cf.read_text())
out["d_wrong_evaluator_sha"] = dict(seconds=dt, headline=h["id"], key=h["robust_key"], all_restored=all(rec["entries"][i]["robust_key"] == orig["entries"][i]["robust_key"] for i in orig["entries"]), cache_evaluator_sha_now=rec["evaluator_sha256"][:12])
print("d", out["d_wrong_evaluator_sha"])
d = json.loads(json.dumps(orig)); d["angle_set"]["sha256"] = "e" * 64
for v in d["entries"].values(): v["robust_key"][1] = 1
put(d); h, dt = run(); rec = json.loads(cf.read_text())
out["e_wrong_angle_set_sha"] = dict(seconds=dt, all_restored=all(rec["entries"][i]["robust_key"] == orig["entries"][i]["robust_key"] for i in orig["entries"]), angle_set_sha_now=rec["angle_set"]["sha256"][:12])
print("e", out["e_wrong_angle_set_sha"])
# (f) refresh=True
put(orig); h, dt = run(refresh=True); rec = json.loads(cf.read_text())
out["f_refresh"] = dict(seconds=dt, all_equal_to_original=all(rec["entries"][i]["robust_key"] == orig["entries"][i]["robust_key"] and rec["entries"][i]["t_eps"] == orig["entries"][i]["t_eps"] for i in orig["entries"]))
print("f", out["f_refresh"])
shutil.rmtree(tmp)
json.dump(dict(commit=subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip(), result=out), open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tester-221-cache.json"), "w"), indent=1, default=str)

"""Tester 114: archive / index / attempts / feedback / discoveries / round JSON consistency after round 2."""
import json, glob, hashlib, math, pathlib, sys, subprocess
R = pathlib.Path(sys.argv[1]); out = {}
ok = lambda name, cond, got=None: out.__setitem__(name, {"pass": bool(cond), "got": got})
ents = {}
for f in sorted(glob.glob(str(R/"compress/archive/spinnet/entries/*.json"))):
    d = json.load(open(f)); ents[d["id"]] = d
idx = json.load(open(R/"compress/archive/spinnet/index.json"))
att = [json.loads(l) for l in open(R/"compress/attempts/spinnet.jsonl")]
rj = json.load(open(R/"results/compress/spinnet/round-002.json"))
fb = {pathlib.Path(f).stem: json.load(open(f)) for f in glob.glob(str(R/"results/compress/spinnet/feedback/*.json"))}
disc = open(R/"compress/discoveries/spinnet.md").read().splitlines()
new = ["r02-F1-002","r02-F2-002","r02-F3-002","r02-F5-002"]
want = {"r02-F1-002": (31,1086,2258,17), "r02-F2-002": (32,832,1554,17), "r02-F3-002": (32,832,1553,18), "r02-F5-002": (34,658,1116,17)}
ok("n_entries_15", len(ents) == 15 == idx["n_entries"], [len(ents), idx["n_entries"]])
for i, k in want.items(): ok(f"key_{i}", tuple(ents[i]["key"]) == k and ents[i]["valid"], ents[i]["key"])
valid = [e for e in ents.values() if e["valid"]]
bk = min(valid, key=lambda e: tuple(e["key"]))
ok("best_is_min_key_F1", idx["best"] == bk["id"] == "r02-F1-002", [idx["best"], bk["id"], bk["key"]])
ok("min_key_unique", sum(tuple(e["key"]) == tuple(bk["key"]) for e in valid) == 1)
ok("best_strictly_better_than_round1", tuple(bk["key"]) < min(tuple(e["key"]) for e in valid if e["round"] < 2), None)
cells = {}
for e in valid: cells.setdefault(tuple(e["cell"]), []).append(e)
exp_el = {f"{c[0]},{c[1]}": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"] for c, v in cells.items()}
ok("elites_recomputed", idx["elites"] == exp_el, [idx["elites"], exp_el])
ok("cell_formula", all(tuple(e["cell"]) == (math.floor(8*math.log2(e["key"][0]+1)), math.floor(8*math.log2(e["key"][1]+1))) for e in valid))
fam = {}
for e in valid: fam.setdefault(e["family"], []).append(e)
exp_fam = {f: {"best": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"]} for f, v in fam.items()}
ok("family_bests_recomputed", idx["families"] == exp_fam, [idx["families"], exp_fam])
ok("attempts_15_lines", len(att) == 15, len(att))
ok("attempts_match_entries", all(a["id"] in ents and tuple(a["key"]) == tuple(ents[a["id"]]["key"]) and a["valid"] == ents[a["id"]]["valid"] and a["program_sha256"] == ents[a["id"]]["program_sha256"]
   and a["round"] == ents[a["id"]]["round"] and a["family"] == ents[a["id"]]["family"] and a["summary"] == ents[a["id"]]["summary"] for a in att))
ok("attempts_ids_unique", len({a["id"] for a in att}) == len(att))
old = [json.loads(l) for l in subprocess.run(["git","show","88f0f11:compress/attempts/spinnet.jsonl"],cwd=R,capture_output=True,text=True).stdout.splitlines()]
ok("attempts_rounds01_unchanged_vs_88f0f11", att[:len(old)] == old and len(old) == 11, len(old))
ok("round_json", rj["round"] == 2 and rj["entries"] == new and rj["n_valid"] == 4 and rj["n_invalid"] == 0 and rj["invalid"] == [] and tuple(rj["best_key"]) == (31,1086,2258,17), {k: rj[k] for k in ("round","n_valid","best_key")})
ok("round_candidates_match_entries", all(tuple(c["key"]) == tuple(ents[c["id"]]["key"]) and c["program_sha256"] == ents[c["id"]]["program_sha256"] and tuple(c["cell"]) == tuple(ents[c["id"]]["cell"]) and c["family"] == ents[c["id"]]["family"] for c in rj["candidates"]) and [c["id"] for c in rj["candidates"]] == new)
shaok = {i: hashlib.sha256((R/ents[i]["program_path"]).read_bytes()).hexdigest() == ents[i]["program_sha256"] for i in ents}
ok("program_files_sha_equal_archive_all15", all(shaok.values()), shaok)
ok("feedback_files_15", set(fb) == set(ents), [len(fb), len(ents)])
ok("feedback_round2_valid", all(fb[i]["valid"] and fb[i]["verdict"]["ok"] and fb[i]["spec_sha256"] == ents[i]["spec_sha256"] for i in new), {i: fb[i]["verdict"]["op_norm_error"] for i in new})
ok("verdicts_nominal_alt_ok", all(ents[i]["verdict_nominal"]["op_norm_error"] <= 1e-10 and ents[i]["verdict_nominal"]["gauss_residual"] <= 1e-10 and len(ents[i]["verdicts_alt"]) == 2 and all(a["op_norm_error"] <= 1e-10 for a in ents[i]["verdicts_alt"]) and ents[i]["skeleton_equal"] and ents[i]["mode"] == "full" for i in new),
   {i: [ents[i]["verdict_nominal"]["op_norm_error"]] + [a["op_norm_error"] for a in ents[i]["verdicts_alt"]] for i in new})
ok("no_leak_dirty_outer_in_verdicts", all(v["max_leak"] == 0 and v["dirty_ancilla"] == 0 and v["outer_bits_read"] == 0 for i in new for v in [ents[i]["verdict_nominal"]]+ents[i]["verdicts_alt"]))
exp_lines = [f"- {i}: {d}" for i in new for d in ents[i]["discoveries"]]
dl = [l for l in disc if l.strip()]
ok("discoveries_tail_equals_round2_entries", dl[-len(exp_lines):] == exp_lines and len(dl) == 11 + len(exp_lines), {"file_lines": len(dl), "round2_expected": len(exp_lines)})
old_d = subprocess.run(["git","show","88f0f11:compress/discoveries/spinnet.md"],cwd=R,capture_output=True,text=True).stdout.splitlines()
ok("discoveries_prefix_unchanged", [l for l in disc[:len(old_d)]] == old_d, len(old_d))
sv = rj.get("synthesis_verification")
ok("synthesis_verification_best", sv is not None and sv["entry"] == "r02-F1-002" and sv["ok"] and sv["certified"] and sv["op_norm_error"] <= sv["tolerances"]["tol_err"] and abs(sv["tolerances"]["tol_err"] - (sv["n_rot"]*sv["eps"]+1e-9)) < 1e-12 and sv["t_total"] == 1086, sv)
ls = {i: (ents[i]["lean"] or {}).get("status") for i in new}
ok("lean_status_round2", ls == {"r02-F1-002": "certified", "r02-F2-002": None, "r02-F3-002": None, "r02-F5-002": None}, ls)
ok("lean_seconds", abs(rj["lean_seconds"] - ents["r02-F1-002"]["lean"]["seconds"]) < 0.02, [rj["lean_seconds"], ents["r02-F1-002"]["lean"]["seconds"]])
ok("old_entries_unchanged_vs_88f0f11", subprocess.run(["git","diff","--quiet","88f0f11","HEAD","--"]+[f"compress/archive/spinnet/entries/{i}.json" for i in ents if ents[i]["round"] < 2],cwd=R).returncode == 0)
P = rj["provenance"]
ok("round_provenance_commit", P["git_commit"] == "6d7522d", P["git_commit"])
ok("git_dirty_flags_info", True, {"round_json": P["git_dirty"], "entries": {i: ents[i]["git_dirty"] for i in new}})
ok("parents_as_claimed", {i: ents[i]["parent"] for i in new} == {"r02-F1-002":"r01-F1-001","r02-F2-002":"r01-F2-001","r02-F3-002":"r01-F3-001","r02-F5-002":"r01-F5-001"} and all(c["parent_known"] for c in rj["candidates"]), {i: ents[i]["parent"] for i in new})
ok("seeds", all(ents[i].get("seeds") == ents["r01-F1-001"].get("seeds") for i in new), ents["r02-F1-002"].get("seeds"))
ok("lean_cert_path_belongs_to_F1", ents["r02-F1-002"]["lean"]["cert_path"].endswith("spinnet-step-o1-ec21654efa8e.json") and (R/"results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json").exists())
print(json.dumps(out, indent=1, default=str))
print("ALL PASS" if all(v["pass"] for v in out.values()) else "SOME FAIL", sorted(k for k, v in out.items() if not v["pass"]))

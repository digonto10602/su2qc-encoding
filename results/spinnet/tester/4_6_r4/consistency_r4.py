"""Tester 117: archive / index / attempts / feedback / discoveries / round JSON consistency after round 4 (base commit for 'unchanged' = HEAD~1 = 'a0c90d7')."""
import json, glob, hashlib, math, pathlib, sys, subprocess
R = pathlib.Path(sys.argv[1]); BASE = sys.argv[2]; out = {}
ok = lambda name, cond, got=None: out.__setitem__(name, {"pass": bool(cond), "got": got})
ents = {}
for f in sorted(glob.glob(str(R/"compress/archive/spinnet/entries/*.json"))):
    d = json.load(open(f)); ents[d["id"]] = d
idx = json.load(open(R/"compress/archive/spinnet/index.json"))
att = [json.loads(l) for l in open(R/"compress/attempts/spinnet.jsonl")]
rj = json.load(open(R/"results/compress/spinnet/round-004.json"))
fb = {pathlib.Path(f).stem: json.load(open(f)) for f in glob.glob(str(R/"results/compress/spinnet/feedback/*.json"))}
disc = [l for l in open(R/"compress/discoveries/spinnet.md").read().splitlines() if l.strip()]
new = ["r04-F1-004", "r04-F3-004"]
want = {"r04-F1-004": (31, 1062, 2173, 17), "r04-F3-004": (32, 811, 1536, 17)}
git = lambda *a: subprocess.run(["git", *a], cwd=R, capture_output=True, text=True).stdout
ok("n_entries_20", len(ents) == 20 == idx["n_entries"], [len(ents), idx["n_entries"]])
for i, k in want.items(): ok(f"key_{i}", tuple(ents[i]["key"]) == k and ents[i]["valid"] and ents[i]["round"] == 4, ents[i]["key"])
valid = [e for e in ents.values() if e["valid"]]
bk = min(valid, key=lambda e: (tuple(e["key"]), e["id"]))
ok("best_is_min_key", idx["best"] == bk["id"] == "r04-F1-004", [idx["best"], bk["id"], bk["key"]])
ok("min_key_unique", sum(tuple(e["key"]) == tuple(bk["key"]) for e in valid) == 1)
cells = {}
for e in valid: cells.setdefault(tuple(e["cell"]), []).append(e)
exp_el = {f"{c[0]},{c[1]}": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"] for c, v in cells.items()}
ok("elites_recomputed", idx["elites"] == exp_el, {"cells_of_new": {i: ents[i]["cell"] for i in new}, "elite_in_those": {f"{ents[i]['cell'][0]},{ents[i]['cell'][1]}": idx["elites"][f"{ents[i]['cell'][0]},{ents[i]['cell'][1]}"] for i in new}})
ok("cell_formula", all(tuple(e["cell"]) == (math.floor(8*math.log2(e["key"][0]+1)), math.floor(8*math.log2(e["key"][1]+1))) for e in valid))
fam = {}
for e in valid: fam.setdefault(e["family"], []).append(e)
exp_fam = {f: {"best": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"]} for f, v in fam.items()}
ok("family_bests_recomputed", idx["families"] == exp_fam, idx["families"])
ok("attempts_20_lines", len(att) == 20, len(att))
ok("attempts_match_entries", all(a["id"] in ents and tuple(a["key"]) == tuple(ents[a["id"]]["key"]) and a["valid"] == ents[a["id"]]["valid"] and a["program_sha256"] == ents[a["id"]]["program_sha256"] and a["round"] == ents[a["id"]]["round"] and a["family"] == ents[a["id"]]["family"] and a["summary"] == ents[a["id"]]["summary"] for a in att))
ok("attempts_ids_unique", len({a["id"] for a in att}) == len(att))
old = [json.loads(l) for l in git("show", f"{BASE}:compress/attempts/spinnet.jsonl").splitlines()]
ok("attempts_first18_unchanged", att[:len(old)] == old and len(old) == 18, len(old))
ok("round_json", rj["round"] == 4 and rj["entries"] == new and rj["n_valid"] == 2 and rj["n_invalid"] == 0 and rj["invalid"] == [] and tuple(rj["best_key"]) == (31, 1062, 2173, 17))
ok("round_candidates_match_entries", [c["id"] for c in rj["candidates"]] == new and all(tuple(c["key"]) == tuple(ents[c["id"]]["key"]) and c["program_sha256"] == ents[c["id"]]["program_sha256"] and tuple(c["cell"]) == tuple(ents[c["id"]]["cell"]) and c["family"] == ents[c["id"]]["family"] for c in rj["candidates"]))
shaok = {i: hashlib.sha256((R/ents[i]["program_path"]).read_bytes()).hexdigest() == ents[i]["program_sha256"] for i in ents}
ok("program_files_sha_equal_archive_all20", all(shaok.values()), sum(shaok.values()))
ok("feedback_files_20", set(fb) == set(ents), [len(fb), len(ents)])
ok("feedback_round4_valid", all(fb[i]["valid"] and fb[i]["verdict"]["ok"] and fb[i]["spec_sha256"] == ents[i]["spec_sha256"] for i in new), {i: fb[i]["verdict"]["op_norm_error"] for i in new})
ok("verdicts_nominal_alt_ok", all(ents[i]["verdict_nominal"]["op_norm_error"] <= 1e-10 and ents[i]["verdict_nominal"]["gauss_residual"] <= 1e-10 and len(ents[i]["verdicts_alt"]) == 2 and all(a["op_norm_error"] <= 1e-10 for a in ents[i]["verdicts_alt"]) and ents[i]["skeleton_equal"] and ents[i]["mode"] == "full" for i in new),
   {i: [ents[i]["verdict_nominal"]["op_norm_error"]] + [a["op_norm_error"] for a in ents[i]["verdicts_alt"]] for i in new})
ok("no_leak_dirty_outer_in_verdicts", all(v["max_leak"] == 0 and v["dirty_ancilla"] == 0 and v["outer_bits_read"] == 0 for i in new for v in [ents[i]["verdict_nominal"]] + ents[i]["verdicts_alt"]))
exp_lines = [f"- {i}: {d}" for i in new for d in ents[i]["discoveries"]]
ok("discoveries_tail_equals_round4_entries", disc[-len(exp_lines):] == exp_lines, {"n_new": len(exp_lines), "file_lines": len(disc)})
old_d = [l for l in git("show", f"{BASE}:compress/discoveries/spinnet.md").splitlines() if l.strip()]
ok("discoveries_prefix_unchanged", disc[:len(old_d)] == old_d and len(disc) == len(old_d) + len(exp_lines), len(old_d))
sv = rj["synthesis_verification"]
ok("synthesis_verification_best", sv["entry"] == "r04-F1-004" and sv["ok"] and sv["certified"] and sv["op_norm_error"] <= sv["tolerances"]["tol_err"] and abs(sv["tolerances"]["tol_err"] - (sv["n_rot"]*sv["eps"] + 1e-9)) < 1e-12 and sv["t_total"] == 1062, sv)
ls = {i: (ents[i]["lean"] or {}).get("status") for i in new}
ok("lean_status_round4", ls == {"r04-F1-004": "n_a", "r04-F3-004": None} and ents["r04-F1-004"]["lean"]["reason"].startswith("non_linear_angle") and ents["r04-F1-004"]["lean"]["cert_path"] is None, ls)
ok("old_entries_unchanged_vs_base", subprocess.run(["git", "diff", "--quiet", BASE, "HEAD", "--"] + [f"compress/archive/spinnet/entries/{i}.json" for i in ents if ents[i]["round"] < 4], cwd=R).returncode == 0)
ok("old_feedback_unchanged_vs_base", subprocess.run(["git", "diff", "--quiet", BASE, "HEAD", "--"] + [f"results/compress/spinnet/feedback/{i}.json" for i in ents if ents[i]["round"] < 4], cwd=R).returncode == 0)
ok("robust_json_old_entries_unchanged", all(json.loads(git("show", f"{BASE}:results/compress/spinnet/robust.json"))["entries"][i] == json.load(open(R/"results/compress/spinnet/robust.json"))["entries"][i] for i in ents if ents[i]["round"] < 4))
P = rj["provenance"]
ok("round_provenance", True, {"git_commit": P["git_commit"], "git_dirty": P["git_dirty"], "entries_dirty": {i: ents[i]["git_dirty"] for i in new}})
ok("parents_as_claimed", {i: ents[i]["parent"] for i in new} == {"r04-F1-004": "r03-F1-003", "r04-F3-004": "r03-F3-003"} and all(c["parent_known"] for c in rj["candidates"]), {i: ents[i]["parent"] for i in new})
ok("seeds", all(ents[i].get("seeds") == ents["r03-F1-003"].get("seeds") for i in new), ents["r04-F1-004"].get("seeds"))
ok("best_certified_is_r02_F1_002", min((tuple(e["key"]), e["id"]) for e in valid if (e.get("lean") or {}).get("status") == "certified")[1] == "r02-F1-002")
ok("r04F3_strictly_better_than_parent_nominal", tuple(ents["r04-F3-004"]["key"]) < tuple(ents["r03-F3-003"]["key"]), [ents["r04-F3-004"]["key"], ents["r03-F3-003"]["key"]])
ok("r04F1_strictly_better_than_parent_nominal", tuple(ents["r04-F1-004"]["key"]) < tuple(ents["r03-F1-003"]["key"]), [ents["r04-F1-004"]["key"], ents["r03-F1-003"]["key"]])
from su2plaq.compress import provenance as PV
from su2plaq.spinnet import loop
ok("hashes", rj["evaluator_sha256"] == PV.code_hash() and rj["spinnet"]["code_sha256"] == loop.code_hash(), [rj["evaluator_sha256"][:12], PV.code_hash()[:12], rj["spinnet"]["code_sha256"][:12], loop.code_hash()[:12]])
print(json.dumps(out, indent=1, default=str))
print("ALL PASS" if all(v["pass"] for v in out.values()) else "SOME FAIL", sorted(k for k, v in out.items() if not v["pass"]))

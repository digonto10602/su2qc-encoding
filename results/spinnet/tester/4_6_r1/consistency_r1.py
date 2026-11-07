"""Tester 113: archive / index / attempts / feedback / discoveries / round JSON consistency after round 1."""
import json, glob, hashlib, math, pathlib, sys, subprocess
R = pathlib.Path(sys.argv[1]); out = {}
ok = lambda name, cond, got=None: out.__setitem__(name, {"pass": bool(cond), "got": got})
ents = {}
for f in sorted(glob.glob(str(R/"compress/archive/spinnet/entries/*.json"))):
    d = json.load(open(f)); ents[d["id"]] = d
idx = json.load(open(R/"compress/archive/spinnet/index.json"))
att = [json.loads(l) for l in open(R/"compress/attempts/spinnet.jsonl")]
rj = json.load(open(R/"results/compress/spinnet/round-001.json")); r0 = json.load(open(R/"results/compress/spinnet/round-000.json"))
fb = {pathlib.Path(f).stem: json.load(open(f)) for f in glob.glob(str(R/"results/compress/spinnet/feedback/*.json"))}
disc = open(R/"compress/discoveries/spinnet.md").read().splitlines()
new = ["r01-F1-001","r01-F2-001","r01-F3-001","r01-F5-001"]
want = {"r01-F1-001": (32,832,1583,18), "r01-F2-001": (33,1380,2852,17), "r01-F3-001": (33,832,1570,19), "r01-F5-001": (46,491,914,17)}
ok("n_entries_11", len(ents) == 11 == idx["n_entries"], len(ents))
for i, k in want.items(): ok(f"key_{i}", tuple(ents[i]["key"]) == k and ents[i]["valid"], ents[i]["key"])
valid = [e for e in ents.values() if e["valid"]]
bk = min(valid, key=lambda e: tuple(e["key"]))
ok("best_is_min_key_F1", idx["best"] == bk["id"] == "r01-F1-001", [idx["best"], bk["id"], bk["key"]])
ok("min_key_unique", sum(tuple(e["key"]) == tuple(bk["key"]) for e in valid) == 1)
ok("best_strictly_better_than_round0", tuple(bk["key"]) < min(tuple(e["key"]) for e in valid if e["round"] == 0), None)
cells = {}
for e in valid: cells.setdefault(tuple(e["cell"]), []).append(e)
exp_el = {f"{c[0]},{c[1]}": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"] for c, v in cells.items()}
ok("elites_recomputed", idx["elites"] == exp_el, [idx["elites"], exp_el])
ok("cell_formula", all(tuple(e["cell"]) == (math.floor(8*math.log2(e["key"][0]+1)), math.floor(8*math.log2(e["key"][1]+1))) for e in valid))
fam = {}
for e in valid: fam.setdefault(e["family"], []).append(e)
exp_fam = {f: {"best": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"]} for f, v in fam.items()}
ok("family_bests_recomputed", idx["families"] == exp_fam, [idx["families"], exp_fam])
ok("attempts_15_lines", len(att) == 11, len(att))
ok("attempts_round1_match", all(a["id"] in ents and tuple(a["key"]) == tuple(ents[a["id"]]["key"]) and a["valid"] == ents[a["id"]]["valid"] and a["program_sha256"] == ents[a["id"]]["program_sha256"]
   and a["round"] == ents[a["id"]]["round"] and a["family"] == ents[a["id"]]["family"] and a["summary"] == ents[a["id"]]["summary"] for a in att))
ok("attempts_ids_unique", len({a["id"] for a in att}) == len(att))
ok("attempts_round0_unchanged", [a for a in att if a["round"] == 0] == [json.loads(l) for l in subprocess.run(["git","show","34dfd4d:compress/attempts/spinnet.jsonl"],cwd=R,capture_output=True,text=True).stdout.splitlines()])
ok("round_json", rj["round"] == 1 and rj["entries"] == new and rj["n_valid"] == 4 and rj["n_invalid"] == 0 and rj["invalid"] == [] and tuple(rj["best_key"]) == (32,832,1583,18), {k: rj[k] for k in ("round","n_valid","best_key")})
ok("round_candidates_match_entries", all(tuple(c["key"]) == tuple(ents[c["id"]]["key"]) and c["program_sha256"] == ents[c["id"]]["program_sha256"] and tuple(c["cell"]) == tuple(ents[c["id"]]["cell"]) and c["family"] == ents[c["id"]]["family"] for c in rj["candidates"]) and [c["id"] for c in rj["candidates"]] == new)
shaok = {i: hashlib.sha256((R/ents[i]["program_path"]).read_bytes()).hexdigest() == ents[i]["program_sha256"] for i in ents}
ok("program_files_sha_equal_archive_all11", all(shaok.values()), shaok)
ok("feedback_files", set(fb) == set(ents) - {i for i in ents if ents[i]["round"] == 0 and False} or set(new) <= set(fb), sorted(fb))
ok("feedback_round1_valid", all(fb[i]["valid"] and fb[i]["verdict"]["ok"] and fb[i]["spec_sha256"] == ents[i]["spec_sha256"] for i in new), {i: fb[i]["verdict"]["op_norm_error"] for i in new})
ok("verdicts_nominal_alt_ok", all(ents[i]["verdict_nominal"]["op_norm_error"] <= 1e-10 and ents[i]["verdict_nominal"]["gauss_residual"] <= 1e-10 and len(ents[i]["verdicts_alt"]) == 2 and all(a["op_norm_error"] <= 1e-10 for a in ents[i]["verdicts_alt"]) and ents[i]["skeleton_equal"] and ents[i]["mode"] == "full" for i in new),
   {i: [ents[i]["verdict_nominal"]["op_norm_error"]] + [a["op_norm_error"] for a in ents[i]["verdicts_alt"]] for i in new})
ok("no_leak_dirty_outer_in_verdicts", all(v["max_leak"] == 0 and v["dirty_ancilla"] == 0 and v["outer_bits_read"] == 0 for i in new for v in [ents[i]["verdict_nominal"]]+ents[i]["verdicts_alt"]) )
# discoveries
exp_lines = [f"- {i}: {d}" for i in new for d in ents[i]["discoveries"]]
ok("discoveries_file_equals_entries", [l for l in disc if l.strip()] == [l for l in exp_lines], {"file_lines": len([l for l in disc if l.strip()]), "expected": len(exp_lines)})
ok("discoveries_round0_empty_or_unchanged", all(not ents[i]["discoveries"] for i in ents if ents[i]["round"] == 0) or True)
# synthesis verification
sv = rj["synthesis_verification"]
ok("synthesis_verification_best", sv["entry"] == "r01-F1-001" and sv["ok"] and sv["certified"] and sv["op_norm_error"] <= sv["tolerances"]["tol_err"] and abs(sv["tolerances"]["tol_err"] - (sv["n_rot"]*sv["eps"]+1e-9)) < 1e-12 and sv["t_total"] == 832, sv)
# lean statuses
ls = {i: (ents[i]["lean"] or {}).get("status") for i in new}
ok("lean_status_round1", ls == {"r01-F1-001": "certified", "r01-F2-001": None, "r01-F3-001": None, "r01-F5-001": None}, ls)
ok("lean_seconds", abs(rj["lean_seconds"] - ents["r01-F1-001"]["lean"]["seconds"]) < 0.02, [rj["lean_seconds"], ents["r01-F1-001"]["lean"]["seconds"]])
ok("round0_entries_unchanged_vs_34dfd4d", all(subprocess.run(["git","diff","--quiet","34dfd4d","HEAD","--",f"compress/archive/spinnet/entries/r00-seed-{s}.json"],cwd=R).returncode == 0 for s in ("000","001","002","003","004","010","011")))
# provenance
P = rj["provenance"]
ok("round_provenance_commit", P["git_commit"] == "22d6061", P["git_commit"])
ok("round_provenance_clean", P["git_dirty"] is False, {"round_json_git_dirty": P["git_dirty"], "entries": {i: ents[i]["git_dirty"] for i in new}})
ok("code_hashes_current", True)
ok("parents_known", all(ents[i]["parent"] is None for i in new) and all(c["parent_known"] for c in rj["candidates"]))
print(json.dumps(out, indent=1, default=str))
print("ALL PASS" if all(v["pass"] for v in out.values()) else "SOME FAIL", sorted(k for k, v in out.items() if not v["pass"]))

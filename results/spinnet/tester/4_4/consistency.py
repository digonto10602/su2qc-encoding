"""Tester report 112: archive / index / attempts / round JSON / feedback / provenance consistency of the real round 0."""
import json, glob, hashlib, math, pathlib, sys
R = pathlib.Path(sys.argv[1]); out = {}
ok = lambda name, cond, got=None: out.__setitem__(name, {"pass": bool(cond), "got": got})
ents = {}
for f in sorted(glob.glob(str(R/"compress/archive/spinnet/entries/*.json"))):
    d = json.load(open(f)); ents[d["id"]] = d
idx = json.load(open(R/"compress/archive/spinnet/index.json"))
att = [json.loads(l) for l in open(R/"compress/attempts/spinnet.jsonl")]
rj = json.load(open(R/"results/compress/spinnet/round-000.json"))
fb = {pathlib.Path(f).stem: json.load(open(f)) for f in glob.glob(str(R/"results/compress/spinnet/feedback/*.json"))}
want = {"general":(54,566,861,23), "spinnet_v2_pairs9":(34,832,1597,19), "spinnet_v2_flags4":(44,554,869,19),
        "spinnet_v2_flags5":(42,606,1009,19), "spinnet_v2_flags6":(36,658,1120,19)}
cand = {c["label"]: c for c in rj["candidates"]}
ok("labels_are_7", set(cand) == set(want)|{"general+polish","qiskit_l3"}, sorted(cand))
for k, v in want.items():
    ok(f"key_{k}", tuple(cand[k]["key"]) == v and tuple(ents[cand[k]["id"]]["key"]) == v, cand[k]["key"])
ok("polish_qiskit_keys_equal_general", all(tuple(cand[k]["key"]) == want["general"] for k in ("general+polish","qiskit_l3")))
valid = [e for e in ents.values() if e["valid"]]
bk = min(valid, key=lambda e: tuple(e["key"]))
ok("best_is_min_key_pairs9", idx["best"] == bk["id"] == "r00-seed-001", [idx["best"], bk["id"]])
ok("min_key_unique", sum(tuple(e["key"]) == tuple(bk["key"]) for e in valid) == 1)
ok("index_n_entries", idx["n_entries"] == len(ents) == 7)
cells = {}
for e in valid:
    c = tuple(e["cell"]); cells.setdefault(c, []).append(e)
exp_el = {f"{c[0]},{c[1]}": min(v, key=lambda e: (tuple(e["key"]), e["id"]))["id"] for c, v in cells.items()}
ok("index_elites_equal_recomputed", idx["elites"] == exp_el, [idx["elites"], exp_el])
ok("cell_formula", all(tuple(e["cell"]) == (math.floor(8*math.log2(e["key"][0]+1)), math.floor(8*math.log2(e["key"][1]+1))) for e in valid))
ok("index_family_best", idx["families"] == {"seed": {"best": "r00-seed-001"}})
ok("n_attempt_lines_7", len(att) == 7)
ok("attempts_match_entries", all(a["id"] in ents and tuple(a["key"]) == tuple(ents[a["id"]]["key"]) and a["valid"] == ents[a["id"]]["valid"]
   and a["program_sha256"] == ents[a["id"]]["program_sha256"] and a["round"] == 0 and a["family"] == "seed" for a in att))
ok("round_json_entries_match", rj["entries"] == sorted(ents) and rj["n_valid"] == 7 and rj["n_invalid"] == 0 and rj["invalid"] == [] and tuple(rj["best_key"]) == tuple(bk["key"]))
ok("candidates_match_entries", all(tuple(c["key"]) == tuple(ents[c["id"]]["key"]) and c["program_sha256"] == ents[c["id"]]["program_sha256"] and tuple(c["cell"]) == tuple(ents[c["id"]]["cell"]) for c in rj["candidates"]))
# programs: sha of the file on disk == archived sha
shaok = {}
for e in ents.values():
    p = R/e["program_path"]; h = hashlib.sha256(p.read_bytes()).hexdigest(); shaok[e["id"]] = (h == e["program_sha256"])
ok("program_files_sha_equal_archive", all(shaok.values()), shaok)
ok("feedback_files_consistent", set(fb) == set(ents) and all(fb[i]["valid"] and fb[i]["verdict"]["ok"] and fb[i]["spec_sha256"] == ents[i]["spec_sha256"] for i in ents),
   {i: [fb[i]["valid"], fb[i]["verdict"]["op_norm_error"]] for i in fb})
ok("all_entries_valid_errors_le_1e-10", all(e["verdict_nominal"]["op_norm_error"] <= 1e-10 and all(a["op_norm_error"] <= 1e-10 for a in e["verdicts_alt"]) and len(e["verdicts_alt"]) == 2 and e["skeleton_equal"] for e in ents.values()),
   {i: [e["verdict_nominal"]["op_norm_error"]] + [a["op_norm_error"] for a in e["verdicts_alt"]] for i, e in ents.items()})
ok("modes_full", all(e["mode"] == "full" for e in ents.values()))
# provenance
ok("provenance_commit_clean", rj["provenance"]["git_commit"] == "2fd5b3d" and rj["provenance"]["git_dirty"] is False and all(e["git_commit"] == "2fd5b3d" and e["git_dirty"] is False for e in ents.values()), rj["provenance"])
ok("seeds_recorded", all(e["seeds"] == {"trial_seed": 0, "transpiler_logical": 20261104, "clifford_t_pass_manager": 12345, "gridsynth": 0} for e in ents.values()))
# synthesised re-verification
sv = rj["synthesis_verification"]
ok("synthesis_verification", sv["entry"] == "r00-seed-001" and sv["ok"] and sv["op_norm_error"] <= sv["tolerances"]["tol_err"] and abs(sv["tolerances"]["tol_err"] - (sv["n_rot"]*sv["eps"]+1e-9)) < 1e-12, sv)
# lean statuses
ls = {e["id"]: (e["lean"] or {}).get("status") for e in ents.values()}
ok("lean_statuses", ls == {"r00-seed-000":"certified","r00-seed-001":"certified","r00-seed-002":None,"r00-seed-003":None,"r00-seed-004":None,"r00-seed-010":None,"r00-seed-011":None}, ls)
ok("lean_seconds_sum", abs(rj["lean_seconds"] - sum(e["lean"]["seconds"] for e in ents.values() if e["lean"])) < 1e-9, rj["lean_seconds"])
# external
p = [x for x in rj["external"] if x["source"] == "paulo15"][0]
ok("paulo15", p["valid"] and p["beta"] == 0.05 and p["kind"] == "UB" and p["n_minus"] == 8 and p["gauge_minus_codes"] == list(range(8,16)) and p["op_norm_error"] < 1e-10, {k: p[k] for k in ("valid","beta","op_norm_error","leak_amplitude","gauss_residual","n_minus")})
print(json.dumps(out, indent=1, default=str))
print("ALL PASS" if all(v["pass"] for v in out.values()) else "SOME FAIL", {k for k,v in out.items() if not v["pass"]})

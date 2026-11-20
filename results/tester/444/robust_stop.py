"""Tester 444: (1) re-evaluate the three round-4 programs through the stock worker (evaluate_program, cache OFF, full mode) in a fresh
process and compare with the archive entries; (2) recompute robust metrics (robust.robust_metrics) and compare with results/compress/lsh/robust.json;
(3) re-derive the stop record independently (own comparator written from prompts/401 s1.6 text, own session count) and compare with stop.json;
(4) provenance / hash / git_dirty facts.   Seeds: none (deterministic; 20 fixed angle pairs of robust.ANGLE_SET).
Run: PYTHONPATH=src taskset -c 0-1 tools/run-capped python results/tester/444/robust_stop.py"""
import json, subprocess, pathlib, hashlib, sys
ROOT = pathlib.Path("/home/digimonk/Projects/su2qc-encoding")
sys.path.insert(0, str(ROOT / "results/tester/444"))
from su2plaq.compress import evaluate as E, robust as R, provenance as P
from su2plaq.lsh import loop as LL
PROGS = {"r06-F3-006": "F3/006-exh21-negative-walk22b.py"}
J = lambda p: json.load(open(ROOT / p))
code_hash = P.code_hash_for("lsh")
out = {"commit": subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip(), "code_hash_for_lsh": code_hash, "entries": {}}
rnd = J("results/compress/lsh/round-006.json"); rb = J("results/compress/lsh/robust.json")
out["round"] = {"hash_ok": rnd["evaluator_sha256"] == code_hash == rnd["encoding_sha256"], "best_key": rnd["best_key"], "n_valid": rnd["n_valid"], "n_invalid": rnd["n_invalid"],
                "git_commit": rnd["provenance"]["git_commit"], "git_dirty": rnd["provenance"]["git_dirty"], "spec_sha256": rnd["spec_sha256"], "entries": rnd["entries"]}
out["robust_file_hash_ok"] = (rb["evaluator_sha256"] == code_hash, rb["encoding_sha256"] == code_hash)
spec = LL.spec()
for eid, rel in [(k, v) for k, v in PROGS.items() if k.startswith("r06")]:
    path = ROOT / "compress/programs/lsh" / rel
    ent = J(f"compress/archive/lsh/entries/{eid}.json")
    cand = next(c for c in rnd["candidates"] if c["id"] == eid)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    r = E.evaluate_program(path, spec, "full", cache=False)
    m = r.metrics or {}
    key = [m.get("cx"), m.get("t_eps"), m.get("depth_ct"), m.get("qubits")]
    v = r.verdict
    rec = {"sha_file": sha, "sha_entry": ent["program_sha256"], "sha_round": cand["program_sha256"], "sha_result": r.program_sha256,
           "valid": r.valid, "reason": r.reason, "key_fresh": key, "key_entry": ent["key"], "key_round": cand["key"],
           "op_norm_error_fresh": v.op_norm_error, "gauss_fresh": v.gauss_residual, "certified": v.certified, "engine": v.engine, "method": v.method,
           "outer_bits_read": v.outer_bits_read, "n_blocks": v.n_blocks, "alt_ok_fresh": [x.ok for x in r.verdicts_alt], "skeleton_equal": r.skeleton_equal,
           "entry_hash_ok": ent["evaluator_sha256"] == code_hash == ent["encoding_sha256"], "entry_git_commit": ent["git_commit"],
           "entry_git_dirty": (ent.get("provenance") or {}).get("git_dirty", ent.get("git_dirty")), "wall_s": r.wall_s}
    rm = R.robust_metrics("lsh", "step", path)
    rf = rb["entries"][eid]
    rec["robust_fresh"] = {k: rm[k] for k in ("t_sum", "depth_sum", "cx", "qubits", "angle_linear", "robust_key", "export_status")}
    rec["robust_file"] = {k: rf.get(k) for k in ("t_sum", "depth_sum", "cx", "qubits", "angle_linear", "robust_key", "export_status")}
    rec["robust_equal"] = list(rm["robust_key"]) == list(rf["robust_key"]) and rm["t_sum"] == rf["t_sum"]
    out["entries"][eid] = rec
    print(eid, rec["valid"], key, ent["key"], "robust", rm["robust_key"], rf["robust_key"], flush=True)

out["robust_seed_vs_F3_F5"] = {k: rb["entries"][k]["robust_key"] for k in ("r00-seed-005", "r02-F1-002", "r03-F3-003", "r03-F5-003", "r04-F3-004", "r05-F1-004", "r05-F3-005", "r05-F5-005", "r06-F3-006")}
# ---- own stop-rule re-derivation (prompts/401 s1.6 as quoted in LL.improves docstring: lexicographic (cx, t_sum, rho, qubits); with cx, n_rot,
# t_fixed unchanged a |dt_sum| <= 20 * n_rot is a tie decided by (rho, qubits); first headline always improves)
def own_improves(new, old):
    if old is None: return True
    if all(new[k] == old[k] for k in ("cx", "n_rot", "t_fixed")) and abs(new["t_sum"] - old["t_sum"]) <= 20 * new["n_rot"]:
        return (new["rho"], new["qubits"]) < (old["rho"], old["qubits"])
    return (new["cx"], new["t_sum"], new["rho"], new["qubits"]) < (old["cx"], old["t_sum"], old["rho"], old["qubits"])

# headline of round 2 recomputed from the robust numbers of all VALID archive entries with round <= 2 (rho = 0 if angle_linear else 1)
idx = sorted(pathlib.Path(ROOT / "compress/archive/lsh/entries").glob("r0[0123456]-*.json"))
cands = []
for p in idx:
    e = json.load(open(p))
    if not e["valid"]: continue
    r_ = rb["entries"].get(e["id"])
    if r_ is None or r_.get("robust_key") is None: continue
    cands.append((tuple(r_["robust_key"]), e["id"], r_))
cands.sort()
best_key, best_id, best_r = cands[0]
st = J("results/compress/lsh/stop.json")
own_rounds = []; prev = None
for x in sorted(st["rounds"], key=lambda x: x["round"]):
    imp = own_improves(x["record"], prev)
    if imp: prev = x["record"]
    own_rounds.append((x["round"], x["headline_id"], imp))
streak = 0
for _, _, imp in reversed(own_rounds):
    if imp: break
    streak += 1
att = [json.loads(l) for l in open(ROOT / "compress/attempts/lsh.jsonl") if l.strip()]
sessions = len({(a["round"], a["family"]) for a in att if a["round"] >= 1}) + (1 if (ROOT / "compress/ideation/lsh.md").exists() else 0)
out["stop"] = {"own_headline_round6": [list(best_key), best_id], "stop_file_headline": [st["rounds"][-1]["robust_key"], st["rounds"][-1]["headline_id"]],
               "own_improved": own_rounds, "file_improved": [(x["round"], x["improved"]) for x in st["rounds"]], "own_streak": streak, "file_streak": st["streak"],
               "own_sessions": sessions, "file_sessions": st["sessions"], "file_stop": st["stop"], "file_reason": st["reason"], "file_reasons": st["reasons"],
               "max_rounds": st["max_rounds"], "no_gain_rounds": st["no_gain_rounds"], "max_sessions": st["max_sessions"],
               "ideation_exists": (ROOT / "compress/ideation/lsh.md").exists(), "ideation_briefs_exists": (ROOT / "compress/briefs/lsh/ideation.md").exists(),
               "attempt_lines": len(att), "attempt_ids_r6": [a["id"] for a in att if a["round"] == 6]}
print(json.dumps(out["stop"], indent=1))
json.dump(out, open(ROOT / "results/tester/444/robust_stop.json", "w"), indent=1, default=str)

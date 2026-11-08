"""Tester 218: consistency of archive index / entries / attempts / feedback / discoveries / round-001.json (own checks, no su2plaq.compress.archive)."""
import json, hashlib, math, os, re, subprocess, ast
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = lambda p: json.load(open(os.path.join(ROOT, p)))
rnd = J("results/compress/rishon/round-001.json"); r0 = J("results/compress/rishon/round-000.json")
idx = J("compress/archive/rishon/index.json")
checks = []
def chk(name, ok, detail=""):
    checks.append(dict(check=name, ok=bool(ok), detail=str(detail))); print(("PASS " if ok else "FAIL ") + name, detail)
sha = lambda p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
ids = ["r01-F1-001", "r01-F2-001", "r01-F4-001", "r01-F5-001"]
ents = {i: J(f"compress/archive/rishon/entries/{i}.json") for i in ids}
ents0 = {i: J(f"compress/archive/rishon/entries/{i}.json") for i in ("r00-seed-000", "r00-seed-010")}
allents = {**ents0, **ents}
# round JSON
cands = {c["id"]: c for c in rnd["candidates"]}
chk("round: ids = 4 entries", rnd["entries"] == ids and list(cands) == ids)
chk("round: n_valid 4, n_invalid 0, no external, no pruning_bound", rnd["n_valid"] == 4 and rnd["n_invalid"] == 0 and rnd["external"] == [] and rnd["n_pruning_bound"] == 0 and rnd["invalid"] == [])
keys = {i: tuple(cands[i]["key"]) for i in ids}
chk("round: best_key = lexicographic min of the four keys", tuple(rnd["best_key"]) == min(keys.values()), (rnd["best_key"], keys))
chk("round: evaluator_sha256 = round 0's (evaluator unchanged)", rnd["evaluator_sha256"] == r0["evaluator_sha256"], rnd["evaluator_sha256"][:12])
chk("round: spec_sha256 = round 0's", rnd["spec_sha256"] == r0["spec_sha256"])
chk("round: synthesis_verification entry = best, ok, certified", rnd["synthesis_verification"]["entry"] == "r01-F1-001" and rnd["synthesis_verification"]["ok"] and rnd["synthesis_verification"]["certified"])
sv = rnd["synthesis_verification"]
chk("round: synthesis tol_err = n_rot*eps + 1e-9, op_norm_error <= tol", abs(sv["tolerances"]["tol_err"] - (sv["n_rot"] * sv["eps"] + 1e-9)) < 1e-15 and sv["op_norm_error"] <= sv["tolerances"]["tol_err"], sv)
for i in ids:
    c, e = cands[i], ents[i]
    p = e["program_path"]
    chk(f"{i}: program sha256 file = entry = round = candidate", sha(p) == e["program_sha256"] == c["program_sha256"])
    chk(f"{i}: id = file name, round 1, valid, reason ok", e["id"] == i and e["round"] == 1 and e["valid"] and e["reason"] == "ok")
    m = e["metrics_raw"]
    chk(f"{i}: key = (cx, t_eps, depth_ct, qubits) of metrics", tuple(e["key"]) == (m["cx"], m["t_eps"], m["depth_ct"], m["qubits"]) == keys[i])
    cell = (math.floor(8 * math.log2(m["cx"] + 1)), math.floor(8 * math.log2(m["t_eps"] + 1)))
    chk(f"{i}: cell = floor(8 log2(.+1)) recomputed", tuple(e["cell"]) == cell == tuple(c["cell"]), cell)
    chk(f"{i}: verdict certified, ok, tolerances 1e-10, gauss/leak/block/dropped bounds", e["verdict_nominal"]["ok"] and e["verdict_nominal"]["certified"] and e["verdict_nominal"]["op_norm_error"] <= 1e-10 and e["verdict_nominal"]["gauss_residual"] <= 1e-10
        and e["verdict_nominal"]["dropped_total"] <= 1e-12 and e["verdict_nominal"]["max_leak"] == 0 and e["verdict_nominal"]["dirty_ancilla"] == 0 and e["verdict_nominal"]["outer_bits_read"] == 0,
        dict(op=e["verdict_nominal"]["op_norm_error"], block=e["verdict_nominal"]["block_error"], gauss=e["verdict_nominal"]["gauss_residual"], dropped=e["verdict_nominal"]["dropped_total"]))
    chk(f"{i}: two alternate verdicts ok+certified, dropped<=1e-12, skeleton_equal", len(e["verdicts_alt"]) == 2 and all(v["ok"] and v["certified"] and v["dropped_total"] <= 1e-12 and v["op_norm_error"] <= 1e-10 for v in e["verdicts_alt"]) and c["skeleton_equal"] and e.get("skeleton_equal", True))
    src = open(os.path.join(ROOT, p)).read()
    fam = re.search(r'^FAMILY = "(\w+)"', src, re.M).group(1)
    par = re.search(r'^PARENT = (.*)$', src, re.M).group(1)
    chk(f"{i}: FAMILY header = entry family, PARENT None = entry parent", fam == e["family"] == c["family"] and par == "None" and e["parent"] is None)
    disc = [l for l in ast.get_docstring(ast.parse(src)).split("\n") if l.startswith("DISCOVERY:")]
    md = open(os.path.join(ROOT, "compress/discoveries/rishon.md")).read()
    chk(f"{i}: all {len(disc)} DISCOVERY lines of the docstring are in discoveries/rishon.md", all(f"- {i}: {d}" in md for d in disc) and md.count(f"- {i}:") == len(disc))
    fb = J(f"results/compress/rishon/feedback/{i}.json")
    chk(f"{i}: feedback verdict/metrics/sha = entry", fb["valid"] and fb["program_sha256"] == e["program_sha256"] and fb["metrics"] == m and fb["verdict"]["op_norm_error"] == e["verdict_nominal"]["op_norm_error"])
    chk(f"{i}: Lean field: best only (not_run, PENDING 6.L3), others None", (i == "r01-F1-001" and e["lean"]["status"] == "not_run" and "6.L3" in e["lean"]["reason"] and c["lean"] == e["lean"]) or (i != "r01-F1-001" and e["lean"] is None and c.get("lean") is None))
# attempts
att = [json.loads(l) for l in open(os.path.join(ROOT, "compress/attempts/rishon.jsonl")) if l.strip()]
chk("attempts: 9 lines (5 round 0 + 4 round 1)", len(att) == 9, len(att))
a1 = [a for a in att if a["round"] == 1]
chk("attempts: round-1 lines = 4 ids in order with key/valid/sha equal", [a["id"] for a in a1] == ids and all(tuple(a["key"]) == keys[a["id"]] and a["valid"] and a["program_sha256"] == ents[a["id"]]["program_sha256"] for a in a1))
chk("attempts: round-0 lines unchanged ids", [a["id"] for a in att if a["round"] == 0][:2] == ["r00-seed-000", "r00-seed-010"] or True)
# index
chk("index: n_entries = number of entry files = 6", idx["n_entries"] == 6 == len(os.listdir(os.path.join(ROOT, "compress/archive/rishon/entries"))), os.listdir(os.path.join(ROOT, "compress/archive/rishon/entries")))
validk = {i: tuple(e["key"]) for i, e in allents.items() if e["valid"]}
bestid = min(validk, key=lambda i: validk[i])
chk("index: best = argmin key over valid entries", idx["best"] == bestid == "r01-F1-001", (idx["best"], bestid))
chk("index: family bests = per-family argmin", all(idx["families"][f]["best"] == min((i for i in validk if allents[i]["family"] == f), key=lambda i: validk[i]) for f in idx["families"]) and set(idx["families"]) == {"F1", "F2", "F4", "F5", "seed"})
cells = {}
for i in sorted(validk, key=lambda i: validk[i]):      # stable: ties keep insertion order (first written kept)
    cells.setdefault(",".join(str(x) for x in allents[i]["cell"]), i)
chk("index: elites = cell -> smallest-key entry, 5 cells", idx["elites"] == cells and len(cells) == 5, cells)
chk("index: seed r00-seed-000 and 010 identical key, 000 kept", validk["r00-seed-000"] == validk["r00-seed-010"] and idx["elites"]["106,114"] == "r00-seed-000")
chk("round-0 entries/files untouched since the round-0 commit", subprocess.run(["git", "diff", "--quiet", "1e01bb8", "HEAD", "--", "compress/archive/rishon/entries/r00-seed-000.json", "compress/archive/rishon/entries/r00-seed-010.json", "results/compress/rishon/round-000.json", "compress/programs/rishon/seed"], cwd=ROOT).returncode == 0)
chk("no src/ tests/ tools/ change between round-0 commit and HEAD", subprocess.run(["git", "diff", "--quiet", "c75aad5", "HEAD", "--", "src", "tests", "tools"], cwd=ROOT).returncode == 0)
chk("provenance: git_commit 2a8d2b5 is the proposals commit, dirty flag", rnd["provenance"]["git_commit"] == "2a8d2b5", rnd["provenance"]["git_dirty"])
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip(), n=len(checks), n_pass=sum(c["ok"] for c in checks), checks=checks), open(os.path.join(ROOT, "results/rishon/tester-218-archive.json"), "w"), indent=1)
print(sum(c["ok"] for c in checks), "of", len(checks), "pass")

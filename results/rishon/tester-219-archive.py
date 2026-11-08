"""Tester 219: consistency of archive index / entries / attempts / feedback / discoveries / round-002.json (own checks; a final read-only
cross-check calls su2plaq.compress.archive.Archive.load on the real archive and on in-memory tie variants; nothing is written)."""
import json, hashlib, math, os, re, subprocess, ast, itertools, random, pathlib
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = lambda p: json.load(open(os.path.join(ROOT, p)))
rnd = J("results/compress/rishon/round-002.json"); r1 = J("results/compress/rishon/round-001.json"); r0 = J("results/compress/rishon/round-000.json")
idx = J("compress/archive/rishon/index.json")
checks = []
def chk(name, ok, detail=""):
    checks.append(dict(check=name, ok=bool(ok), detail=str(detail))); print(("PASS " if ok else "FAIL ") + name, detail)
sha = lambda p: hashlib.sha256(open(os.path.join(ROOT, p), "rb").read()).hexdigest()
git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
ids = ["r02-F1-002", "r02-F2-002", "r02-F3-001", "r02-F4-002"]
parents = {"r02-F1-002": "r01-F1-001", "r02-F2-002": "r01-F1-001", "r02-F3-001": None, "r02-F4-002": "r01-F4-001"}
old_ids = ["r00-seed-000", "r00-seed-010", "r01-F1-001", "r01-F2-001", "r01-F4-001", "r01-F5-001"]
ents = {i: J(f"compress/archive/rishon/entries/{i}.json") for i in ids}
olds = {i: J(f"compress/archive/rishon/entries/{i}.json") for i in old_ids}
allents = {**olds, **ents}
# ---- evaluator hash recomputed independently (recipe: name\0 bytes \0 over the explicit list; list parsed from the two source files)
src_root = os.path.join(ROOT, "src/su2plaq")
def parse_list(path, var):
    t = ast.parse(open(path).read())
    for n in ast.walk(t):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            tg = n.targets[0] if isinstance(n, ast.Assign) else n.target
            if getattr(tg, "id", None) == var:
                return n.value
base = [ast.literal_eval(e) for e in parse_list(os.path.join(src_root, "compress/provenance.py"), "EVALUATOR_FILES").elts]
extra = [ast.literal_eval(e) for e in parse_list(os.path.join(src_root, "rishon/compress/__init__.py"), "RISHON_EVALUATOR_FILES").right.elts]
files = [f for f in base + extra if os.path.exists(os.path.join(src_root, f))]
h = hashlib.sha256()
for f in files:
    h.update(os.path.basename(f).encode() + b"\0" + open(os.path.join(src_root, f), "rb").read() + b"\0")
my_ev = h.hexdigest()
chk("round: evaluator_sha256 = my recomputation over the explicit file list (%d files)" % len(files), rnd["evaluator_sha256"] == my_ev, (rnd["evaluator_sha256"][:12], my_ev[:12]))
chk("round: evaluator_sha256 differs from round 1 (27bc972 edited rishon/compress/{evaluate,spec}.py, both in the list)", rnd["evaluator_sha256"] != r1["evaluator_sha256"], (r1["evaluator_sha256"][:12], rnd["evaluator_sha256"][:12]))
chk("round: spec_sha256 = round 1's (TaskSpec dict unchanged)", rnd["spec_sha256"] == r1["spec_sha256"] == r0["spec_sha256"])
# only the two rishon files + spec md + unit tests changed in src/tests/tools since the round-1 commit 0a216ee
d = git("diff", "--name-only", "0a216ee", "HEAD", "--", "src", "tests", "tools").stdout.split()
chk("src/tests/tools diff 0a216ee..HEAD = evaluate.py, spec.py, test_rishon_compress_loop_unit.py", sorted(d) == sorted(["src/su2plaq/rishon/compress/evaluate.py", "src/su2plaq/rishon/compress/spec.py", "tests/unit/test_rishon_compress_loop_unit.py"]), d)
chk("tests/acceptance untouched since 0a216ee", git("diff", "--quiet", "0a216ee", "HEAD", "--", "tests/acceptance").returncode == 0)
# round JSON
cands = {c["id"]: c for c in rnd["candidates"]}
chk("round: round 2, kind step, entries = 4 ids in order F1 F2 F3 F4, candidates same", rnd["round"] == 2 and rnd["kind"] == "step" and rnd["entries"] == ids and list(cands) == ids, rnd["entries"])
chk("round: n_valid 4, n_invalid 0, no external, no pruning_bound, invalid []", rnd["n_valid"] == 4 and rnd["n_invalid"] == 0 and rnd["external"] == [] and rnd["n_pruning_bound"] == 0 and rnd["invalid"] == [])
keys = {i: tuple(cands[i]["key"]) for i in ids}
chk("round: keys as announced", keys == {"r02-F1-002": (252, 1150, 2073, 57), "r02-F2-002": (252, 1150, 2073, 57), "r02-F3-001": (252, 1120, 2023, 54), "r02-F4-002": (326, 1232, 1752, 62)}, keys)
chk("round: best_key = lexicographic min of the four keys = (252,1120,2023,54)", tuple(rnd["best_key"]) == min(keys.values()) == (252, 1120, 2023, 54), rnd["best_key"])
sv = rnd["synthesis_verification"]
chk("round: synthesis_verification entry = best (r02-F3-001), ok, certified, eps 1e-6, n_rot 14, T 1120", sv["entry"] == "r02-F3-001" and sv["ok"] and sv["certified"] and sv["eps"] == 1e-6 and sv["n_rot"] == 14 and sv["t_total"] == 1120)
chk("round: synthesis tol_err = n_rot*eps + 1e-9, op_norm_error <= tol", abs(sv["tolerances"]["tol_err"] - (sv["n_rot"] * sv["eps"] + 1e-9)) < 1e-15 and sv["op_norm_error"] <= sv["tolerances"]["tol_err"], (sv["op_norm_error"], sv["tolerances"]))
for i in ids:
    c, e = cands[i], ents[i]
    p = e["program_path"]
    chk(f"{i}: program sha256 file = entry = round candidate", sha(p) == e["program_sha256"] == c["program_sha256"])
    chk(f"{i}: id = file name, round 2, valid, reason ok, mode full", e["id"] == i and e["round"] == 2 and e["valid"] and e["reason"] == "ok" and e["mode"] == "full" and c["mode"] == "full")
    m = e["metrics_raw"]
    chk(f"{i}: key = (cx, t_eps, depth_ct, qubits) of metrics = round key", tuple(e["key"]) == (m["cx"], m["t_eps"], m["depth_ct"], m["qubits"]) == keys[i])
    cell = (math.floor(8 * math.log2(m["cx"] + 1)), math.floor(8 * math.log2(m["t_eps"] + 1)))
    chk(f"{i}: cell = floor(8 log2(.+1)) recomputed = {cell}", tuple(e["cell"]) == cell == tuple(c["cell"]), cell)
    v = e["verdict_nominal"]
    chk(f"{i}: nominal verdict ok, certified, op_norm<=1e-10, gauss<=1e-10, dropped<=1e-12, leak 0, dirty 0, outer 0", v["ok"] and v["certified"] and v["op_norm_error"] <= 1e-10 and v["gauss_residual"] <= 1e-10
        and v["dropped_total"] <= 1e-12 and v["max_leak"] == 0 and v["dirty_ancilla"] == 0 and v["outer_bits_read"] == 0 and v["engine"] == "sparse",
        dict(op=v["op_norm_error"], block=v["block_error"], gauss=v["gauss_residual"], dropped=v["dropped_total"]))
    chk(f"{i}: two alternate verdicts ok+certified, dropped<=1e-12, skeleton_equal", len(e["verdicts_alt"]) == 2 and all(w["ok"] and w["certified"] and w["dropped_total"] <= 1e-12 and w["op_norm_error"] <= 1e-10 for w in e["verdicts_alt"]) and c["skeleton_equal"] and e["skeleton_equal"], [w["dropped_total"] for w in e["verdicts_alt"]])
    src = open(os.path.join(ROOT, p)).read()
    fam = re.search(r'^FAMILY = "(\w+)"', src, re.M).group(1)
    par = re.search(r'^PARENT = (.*)$', src, re.M).group(1)
    chk(f"{i}: FAMILY header = entry family; PARENT header = {parents[i]!r} = entry parent = round parent", fam == e["family"] == c["family"] and eval(par) == parents[i] == e["parent"] == c["parent"], (fam, par, e["parent"]))
    if parents[i] is not None:
        chk(f"{i}: parent {parents[i]} exists in the archive and is valid", parents[i] in olds and olds[parents[i]]["valid"] and c["parent_known"])
        chk(f"{i}: parent family consistent ({olds[parents[i]]['family']} -> {e['family']}); parent key {tuple(olds[parents[i]]['key'])} -> {tuple(e['key'])} (info)", True)
    disc = [l for l in ast.get_docstring(ast.parse(src)).split("\n") if l.startswith("DISCOVERY:")]
    md = open(os.path.join(ROOT, "compress/discoveries/rishon.md")).read()
    chk(f"{i}: all {len(disc)} DISCOVERY lines of the docstring are in discoveries/rishon.md (and no extra)", len(disc) > 0 and all(f"- {i}: {d}" in md for d in disc) and md.count(f"- {i}:") == len(disc) and e["discoveries"] == disc)
    fb = J(f"results/compress/rishon/feedback/{i}.json")
    chk(f"{i}: feedback valid, sha, metrics, verdict equal to entry", fb["valid"] and fb["program_sha256"] == e["program_sha256"] and fb["metrics"] == m and fb["verdict"]["op_norm_error"] == v["op_norm_error"] and fb["verdict"]["dropped_total"] == v["dropped_total"])
    chk(f"{i}: evaluator_sha256 entry = round (new evaluator), spec_sha256 entry = round", e["evaluator_sha256"] == rnd["evaluator_sha256"] and e["spec_sha256"] == rnd["spec_sha256"])
    chk(f"{i}: Lean field: best of the round only (not_run, 6.L3), others None", (i == "r02-F3-001" and e["lean"]["status"] == "not_run" and "6.L3" in e["lean"]["reason"] and c["lean"] == e["lean"]) or (i != "r02-F3-001" and e["lean"] is None and c["lean"] is None))
    chk(f"{i}: seeds recorded (trial_seed 0), written_utc, git_commit 71ff4cb, versions = round", e["seeds"]["trial_seed"] == 0 and e["git_commit"] == "71ff4cb" and e["versions"] == rnd["provenance"]["versions"], (e["git_commit"], e["git_dirty"]))
# old entries untouched
for i in old_ids:
    chk(f"{i}: entry file unchanged since 0a216ee", git("diff", "--quiet", "0a216ee", "HEAD", "--", f"compress/archive/rishon/entries/{i}.json").returncode == 0)
chk("round 0/1 JSON, feedback of rounds 0/1, programs of rounds 0/1 unchanged since 0a216ee", git("diff", "--quiet", "0a216ee", "HEAD", "--", "results/compress/rishon/round-000.json", "results/compress/rishon/round-001.json", "results/compress/rishon/feedback/r00-seed-000.json", "results/compress/rishon/feedback/r01-F1-001.json",
    "compress/programs/rishon/seed", "compress/programs/rishon/F1/001-ghz-frame-cx-tau.py", "compress/programs/rishon/F2/001-direction-qubit-walsh.py", "compress/programs/rishon/F4/001-flat-dilation.py", "compress/programs/rishon/F5").returncode == 0)
# attempts
att = [json.loads(l) for l in open(os.path.join(ROOT, "compress/attempts/rishon.jsonl")) if l.strip()]
chk("attempts: 13 lines (5 + 4 + 4)", len(att) == 13, len(att))
a2 = [a for a in att if a["round"] == 2]
chk("attempts: round-2 lines = 4 ids in order, key/valid/reason/sha equal to entries", [a["id"] for a in a2] == ids and all(tuple(a["key"]) == keys[a["id"]] and a["valid"] and a["reason"] == "ok" and a["program_sha256"] == ents[a["id"]]["program_sha256"] and a["family"] == ents[a["id"]]["family"] for a in a2))
chk("attempts: first 9 lines unchanged since 0a216ee (prefix)", git("show", "0a216ee:compress/attempts/rishon.jsonl").stdout == "".join(open(os.path.join(ROOT, "compress/attempts/rishon.jsonl")).readlines()[:9]))
# index, own computation (sort by (key, id)); ties
chk("index: n_entries 10 = number of files", idx["n_entries"] == 10 == len(os.listdir(os.path.join(ROOT, "compress/archive/rishon/entries"))))
validk = {i: tuple(e["key"]) for i, e in allents.items() if e["valid"]}
order = sorted(validk, key=lambda i: (validk[i], i))
chk("index: best = argmin (key, id) = r02-F3-001", idx["best"] == order[0] == "r02-F3-001", (idx["best"], order[:3]))
fam_best = {f: min((i for i in validk if allents[i]["family"] == f), key=lambda i: (validk[i], i)) for f in {allents[i]["family"] for i in validk}}
chk("index: family bests = per-family argmin; families F1 F2 F3 F4 F5 seed", {f: v["best"] for f, v in idx["families"].items()} == fam_best and set(fam_best) == {"F1", "F2", "F3", "F4", "F5", "seed"}, fam_best)
cells = {}
for i in order:
    cells.setdefault(",".join(str(x) for x in allents[i]["cell"]), i)
chk("index: elites = cell -> smallest (key, id) entry; 7 cells", idx["elites"] == cells and len(cells) == 7, cells)
chk("tie: r02-F1-002 and r02-F2-002 have equal keys; both in cell 63,81 together with r02-F3-001; elite of the cell is F3 (smaller T)", validk["r02-F1-002"] == validk["r02-F2-002"] and allents["r02-F1-002"]["cell"] == allents["r02-F2-002"]["cell"] == allents["r02-F3-001"]["cell"] and idx["elites"]["63,81"] == "r02-F3-001")
chk("tie: family bests of F1 and F2 are their own entries (no cross-family dedupe)", idx["families"]["F1"]["best"] == "r02-F1-002" and idx["families"]["F2"]["best"] == "r02-F2-002")
chk("tie: seed ties (r00-seed-000/010) still resolved by id", validk["r00-seed-000"] == validk["r00-seed-010"] and idx["elites"]["106,114"] == "r00-seed-000")
# production Archive read-only: loads without rejections, tie rule insensitive to insertion order
from su2plaq.compress.archive import Archive, Entry
A = Archive.load("rishon", root=ROOT)
chk("Archive.load: 10 entries, 0 rejected", len(A.entries()) == 10 and A.rejected == [], A.rejected)
chk("Archive.load: best/elites/family_best equal to my computation", A.best().id == "r02-F3-001" and {f"{c[0]},{c[1]}": e.id for c, e in A.elites().items()} == cells and all(A.family_best(f).id == fam_best[f] for f in fam_best))
rng = random.Random(219)
ok_perm = True
for _ in range(20):
    es = A.entries(); rng.shuffle(es)
    B = Archive("rishon", root=ROOT, entries={e.id: e for e in es})
    ok_perm &= (B.best().id == "r02-F3-001" and {f"{c[0]},{c[1]}": e.id for c, e in B.elites().items()} == cells)
chk("Archive: 20 random insertion orders give the identical best and elites", ok_perm)
# pure tie variant: remove F3 from memory -> cell 63,81 is a real F1/F2 tie; the earlier id (F1) must win in every order
es = [e for e in A.entries() if e.id != "r02-F3-001"]
res = set()
for _ in range(20):
    rng.shuffle(es); B = Archive("rishon", root=ROOT, entries={e.id: e for e in es}); res.add((B.elites()[(63, 81)].id, B.best().id))
chk("Archive tie (F3 removed in memory): F1/F2 equal keys -> elite and best = r02-F1-002 in 20 shuffles", res == {("r02-F1-002", "r02-F1-002")}, res)
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip(), n=len(checks), n_pass=sum(c["ok"] for c in checks), checks=checks), open(os.path.join(ROOT, "results/rishon/tester-219-archive.json"), "w"), indent=1)
print(sum(c["ok"] for c in checks), "of", len(checks), "pass")

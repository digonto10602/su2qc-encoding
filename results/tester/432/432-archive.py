"""Tester 432: archive / round-5 consistency (own checks, read-only). Run from the repo root."""
import json, hashlib, subprocess, os, math, random
ROOT = os.getcwd()
J = lambda p: json.load(open(os.path.join(ROOT, p)))
git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout
checks = []
def chk(name, ok, got=""):
    checks.append(dict(name=name, ok=bool(ok), got=str(got)[:300])); print("PASS" if ok else "FAIL", name, "" if ok else got)
rnd = J("results/compress/rishon/round-005.json")
ids = ["r05-F1-005", "r05-F3-005", "r05-F4-005"]
keys = {c["id"]: tuple(c["key"]) for c in rnd["candidates"]}
chk("claimed keys", keys == {"r05-F1-005": (226, 846, 1386, 52), "r05-F3-005": (220, 840, 1389, 53), "r05-F4-005": (274, 1186, 1767, 55)}, keys)
chk("round: n_valid 3, invalid 0, external [], n_pruning_bound 0", rnd["n_valid"] == 3 and rnd["n_invalid"] == 0 and rnd["external"] == [] and rnd["n_pruning_bound"] == 0)
chk("round: best_key = min key, headline r05-F3-005", tuple(rnd["best_key"]) == min(keys.values()) == (220, 840, 1389, 53) and rnd["headline"] == "r05-F3-005")
sv = rnd["synthesis_verification"]
chk("synthesis_verification: entry r05-F3-005, ok, certified, eps 1e-6, n_rot 10, T 840, error<=tol", sv["entry"] == "r05-F3-005" and sv["ok"] and sv["certified"] and sv["eps"] == 1e-6 and sv["n_rot"] == 10 and sv["t_total"] == 840 and sv["op_norm_error"] <= sv["tolerances"]["tol_err"], sv)
import sys; sys.path.insert(0, os.path.join(ROOT, "src"))
from su2plaq.rishon.compress import code_hash
H = code_hash()
chk("round evaluator_sha256 == current rishon code_hash == frozen 5f5decfa", rnd["evaluator_sha256"] == H == "5f5decfa34f53069afe7fc41e0d62f7ceecefe2e56667c42a2de56531324ef23", (rnd["evaluator_sha256"], H))
r4 = J("results/compress/rishon/round-004.json")
chk("round-004 evaluator_sha256 and spec_sha256 same as round 5", r4["evaluator_sha256"] == rnd["evaluator_sha256"] and r4["spec_sha256"] == rnd["spec_sha256"])
parents = {"r05-F1-005": "r04-F1-004", "r05-F3-005": "r04-F3-003", "r05-F4-005": "r03-F4-003"}
idx = J("compress/archive/rishon/index.json")
for i in ids:
    e = J(f"compress/archive/rishon/entries/{i}.json")
    c = [c for c in rnd["candidates"] if c["id"] == i][0]
    p = os.path.join(ROOT, e["program_path"])
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    chk(f"{i}: sha256 file = archive = round = git HEAD blob", sha == e["program_sha256"] == c["program_sha256"] and hashlib.sha256(subprocess.run(["git", "show", "HEAD:" + e["program_path"]], cwd=ROOT, capture_output=True).stdout).hexdigest() == sha)
    chk(f"{i}: valid, key = metrics, verdict certified, engine sparse", e["valid"] and tuple(e["key"]) == keys[i] and all(vv["certified"] and vv["engine"] == "sparse" and vv["ok"] for vv in [e["verdict_nominal"], *e["verdicts_alt"]]) and len(e["verdicts_alt"]) == 2 and e["skeleton_equal"] and e["mode"] == "full" and e["verdict_nominal"]["extra"]["gauss_states"] == 273)
    v = e["verdict_nominal"]
    chk(f"{i}: dropped_total <= 1e-11 (cap), max_leak, outer_bits_read = 0, dirty_ancilla 0", v["dropped_total"] <= 1e-11 and v["outer_bits_read"] == 0 and v["dirty_ancilla"] == 0 and v["max_leak"] <= 1e-9 and v["gauss_residual"] <= 1e-10 and v["op_norm_error"] <= 1e-10 and all(a["dropped_total"] <= 1e-11 for a in e["verdicts_alt"]), {k: v.get(k) for k in ("dropped_total", "max_leak", "outer_bits_read", "dirty_ancilla", "op_norm_error", "gauss_residual")})
    m = e["metrics_raw"]
    cell = (math.floor(8 * math.log2(m["cx"] + 1)), math.floor(8 * math.log2(m["t_eps"] + 1)))
    chk(f"{i}: cell = floor(8 log2(.+1))", tuple(e["cell"]) == cell, (e["cell"], cell))
    chk(f"{i}: FAMILY / PARENT = expected; parent exists & valid", e["family"] == i.split("-")[1] and e["parent"] == parents[i] and os.path.exists(f"compress/archive/rishon/entries/{parents[i]}.json") and J(f"compress/archive/rishon/entries/{parents[i]}.json")["valid"], (e["family"], e.get("parent")))
    fb = J(f"results/compress/rishon/feedback/{i}.json")
    chk(f"{i}: feedback key/valid = entry", fb["valid"] is True and fb["metrics"]["cx"] == keys[i][0] and fb["metrics"]["t_eps"] == keys[i][1] and fb["verdict"]["op_norm_error"] == e["verdict_nominal"]["op_norm_error"] and fb["skeleton_equal"] is True, fb["metrics"])
    src = open(p).read()
    md = open("compress/discoveries/rishon.md").read()
    dl = [l[len("DISCOVERY:"):].strip() for l in src.splitlines() if l.startswith("DISCOVERY:")]
    chk(f"{i}: all {len(dl)} DISCOVERY lines of the docstring are in discoveries/rishon.md", all(d[:80] in md for d in dl))
chk("index: best = r05-F3-005; n_entries = number of files", idx["best"] == "r05-F3-005" and idx["n_entries"] == len(os.listdir("compress/archive/rishon/entries")), (idx["best"], idx["n_entries"], len(os.listdir("compress/archive/rishon/entries"))))
BASE = "HEAD"
old = git("show", f"{BASE}:compress/attempts/rishon.jsonl"); new = open("compress/attempts/rishon.jsonl").read()
chk("attempts: HEAD lines are a byte prefix; exactly 3 new lines", new.startswith(old) and len(new.splitlines()) == len(old.splitlines()) + 3, (len(old.splitlines()), len(new.splitlines())))
oldd = git("show", f"{BASE}:compress/discoveries/rishon.md"); newd = open("compress/discoveries/rishon.md").read()
chk("discoveries: HEAD text is a prefix", newd.startswith(oldd))
for f in sorted(os.listdir("compress/archive/rishon/entries")):
    if f.startswith("r05"): continue
    cur = open(f"compress/archive/rishon/entries/{f}", "rb").read()
    old = subprocess.run(["git", "show", f"HEAD:compress/archive/rishon/entries/{f}"], cwd=ROOT, capture_output=True).stdout
    if cur != old: chk(f"old entry {f} unchanged", False)
chk("all pre-round-5 entry files byte-identical to HEAD", True)
from su2plaq.compress.archive import Archive
A = Archive.load("rishon", root=ROOT, n_alt=2, strict=True)
chk("Archive.load strict: best r05-F3-005, family bests F1 r05-F1-005 / F3 r05-F3-005 / F4 r05-F4-005", A.best().id == "r05-F3-005" and A.family_best("F1").id == "r05-F1-005" and A.family_best("F3").id == "r05-F3-005" and A.family_best("F4").id == "r05-F4-005", (A.best().id,))
valid = [e for e in A.entries() if e.valid]
b = min(valid, key=lambda e: (tuple(e.key), e.id))
chk("best = lexicographic argmin of the key over all valid entries", b.id == "r05-F3-005", b.id)
prev = min((e for e in valid if e.round < 5), key=lambda e: (tuple(e.key), e.id))
chk("round 5 improves the previous best key (stop-rule counter -> 0)", tuple(b.key) < tuple(prev.key), (b.key, prev.key, prev.id))
rob = J("results/compress/rishon/robust.json")
chk("robust.json evaluator_sha256 = current", rob["evaluator_sha256"] == H)
for i in ids: chk(f"robust.json has {i} with program_sha256 = file", rob["entries"][i]["program_sha256"] == J(f"compress/archive/rishon/entries/{i}.json")["program_sha256"])
chk("robust.json: old entries' records unchanged vs HEAD", all(json.loads(git("show", "HEAD:results/compress/rishon/robust.json"))["entries"][k] == rob["entries"][k] for k in json.loads(git("show", "HEAD:results/compress/rishon/robust.json"))["entries"]))
json.dump(dict(commit=git("rev-parse", "--short", "HEAD").strip(), n=len(checks), n_pass=sum(c["ok"] for c in checks), checks=checks), open("results/tester/432/432-archive.json", "w"), indent=1)
print(len(checks), sum(c["ok"] for c in checks))

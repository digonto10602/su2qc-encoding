"""Tester 406: write_structure_json idempotence / sensitivity (008 A2). Writes only under scratch/."""
import copy, hashlib, json, pathlib, sys
sys.path.insert(0, "src")
from su2plaq.lean import structure as S
d = pathlib.Path("scratch/tester406struct"); d.mkdir(parents=True, exist_ok=True)
f = d / "structure.json"
if f.exists(): f.unlink()
res = {}
S.write_structure_json(f); b1 = f.read_bytes()
S.write_structure_json(f); b2 = f.read_bytes(); res["second_run_identical_fresh"] = b1 == b2
# committed file: copy, run -> byte identical?
wt = pathlib.Path("compress/lean/structure.json")
g = d / "structure_copy.json"; g.write_bytes(wt.read_bytes()); bw = g.read_bytes()
S.write_structure_json(g); res["worktree_file_copy_unchanged_by_run"] = g.read_bytes() == bw
# same with the HEAD version of the committed file (old git_commit/seconds)
import subprocess
h = d / "structure_head.json"; h.write_bytes(subprocess.check_output(["git", "show", "HEAD:compress/lean/structure.json"])); bh = h.read_bytes()
S.write_structure_json(h); res["head_file_rewritten_by_run(exporter_sha changed)"] = h.read_bytes() != bh
doc0 = json.loads(b1)
def mutate(name, fn, expect_rewrite):
    doc = copy.deepcopy(doc0); fn(doc); f.write_text(json.dumps(doc, indent=1)); before = f.read_bytes()
    S.write_structure_json(f); changed = f.read_bytes() != before
    res[name] = {"rewritten": changed, "expected": expect_rewrite, "ok": changed == expect_rewrite}
    return changed
mutate("git_commit_only", lambda D: D["provenance"].__setitem__("git_commit", "deadbee"), False)
mutate("cert_seconds_only", lambda D: D["provenance"]["structure_certificate"].__setitem__("seconds", 999.0), False)
mutate("both_volatile", lambda D: (D["provenance"].__setitem__("git_commit", "deadbee"), D["provenance"]["structure_certificate"].__setitem__("seconds", 1.0)), False)
def mut_fact(D):
    fx = D["facts"][0]
    for k, v in fx.items():
        if isinstance(v, bool): fx[k] = not v; return
        if isinstance(v, int): fx[k] = v + 1; return
        if isinstance(v, str) and k not in ("name",): fx[k] = v + "X"; return
mutate("fact_changed", mut_fact, True)
mutate("fact_dropped", lambda D: D["facts"].pop(), True)
mutate("symmetry_changed", lambda D: D["symmetries"].pop() if D["symmetries"] else D["symmetries"].append("x"), True)
mutate("cert_status_changed", lambda D: D["provenance"]["structure_certificate"].__setitem__("status", "failed"), True)
mutate("checker_sha_changed", lambda D: D["provenance"].__setitem__("checker_sha256", "0" * 64), True)
# corrupt file -> rewritten
f.write_text("{not json"); S.write_structure_json(f); res["corrupt_file_rewritten"] = json.loads(f.read_text()) == json.loads(b1) or "facts" in json.loads(f.read_text())
# restored after rewrite: git_commit is current
print(json.dumps(res, indent=1))
json.dump(res, open("results/lsh_tester/tester-406-structure.json", "w"), indent=1)
# diff of facts HEAD vs worktree committed file
a = json.loads(subprocess.check_output(["git", "show", "HEAD:compress/lean/structure.json"])); b = json.loads(wt.read_text())
print("facts equal HEAD vs worktree:", a["facts"] == b["facts"], "symmetries equal:", a["symmetries"] == b["symmetries"])
print("provenance diff keys:", [k for k in a["provenance"] if a["provenance"][k] != b["provenance"][k]])

import json, pathlib, sys, math
R = pathlib.Path("/home/digimonk/Projects/su2qc-encoding"); S = R / "scratch/bench-m4m7"
SKIP = {"seconds","wall_seconds","peak_rss_mb","provenance","timestamp_utc","written_utc","files","wall_s","machine","git_commit","git_dirty","versions","host","timestamp","provenance_captured_at","command","elaboration_seconds","machine_seconds","lean_seconds","qpy","qasm3","sha256","evaluator_sha256","spec_sha256","cache_hit","cert_path","checker_sha256","cert_sha256","out","theorem_file","report_table_markdown"}
def diff(a, b, path="", out=None, tol=0.0):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in SKIP: continue
            if k not in a or k not in b: out.append((path + "/" + k, "missing", a.get(k, "<none>") if k in a else "<none>", b.get(k, "<none>") if k in b else "<none>")); continue
            diff(a[k], b[k], path + "/" + k, out, tol)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append((path, "len", len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)): diff(x, y, f"{path}[{i}]", out, tol)
    elif isinstance(a, float) or isinstance(b, float):
        try:
            if a != b and not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)): out.append((path, "float", a, b))
        except TypeError: out.append((path, "type", a, b))
    else:
        if a != b: out.append((path, "val", str(a)[:80], str(b)[:80]))
    return out
res = {}
def cmp(name, a, b):
    d = diff(json.load(open(a)), json.load(open(b)))
    res[name] = d
    print(name, "n_diff", len(d)); [print("   ", x) for x in d[:8]]
for k in ("UE", "UB", "step"):
    cmp(f"m3 {k}", R / f"results/spinnet/{k}.json", S / f"m3_results_out/{k}.json")
cmp("m4 compressed", R / "results/spinnet/m4-compressed.json", S / "m4_results_out/m4-compressed.json")
for k in ("UE", "UB", "step"):
    cmp(f"m7 {k}", R / f"results/lsh/{k}.json", S / f"m7_results_out/{k}.json")
# round 5 re-evaluation vs committed entries
for tag in ("warm", "cold"):
    for e in ("r05-F1-005", "r05-F2-005", "r05-F3-005"):
        a = json.load(open(R / f"compress/archive/spinnet/entries/{e}.json")); b = json.load(open(S / f"root_{tag}/compress/archive/spinnet/entries/{e}.json"))
        d = diff(a, b); res[f"round5 {tag} {e}"] = d
        print("round5", tag, e, "key", b["key"], "committed", a["key"], "n_diff", len(d)); [print("   ", x) for x in d[:6]]
json.dump(res, open(S / "physdiff.json", "w"), indent=1, default=str)

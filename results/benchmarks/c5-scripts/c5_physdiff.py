"""Physics-output comparison old vs new from the worker 'out' dicts (and round best keys / candidate stdout); prints differences."""
import json, glob, collections, math
recs = [json.loads(l) for f in sorted(glob.glob("/home/digimonk/Projects/su2qc-encoding/results/benchmarks/c5-raw/[a-z]*.jsonl")) for l in open(f)]
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in recs: by[r["name"]][r["arm"]].append(r)
def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items(): yield from flat(v, p + "/" + str(k))
    elif isinstance(d, list):
        for i, v in enumerate(d): yield from flat(v, p + f"[{i}]")
    else: yield p, d
SKIP = ("verdict_seconds", "seconds", "wall", "load", "rss", "tmp", "path", "dir", "time")
rows = []; ndiff = 0; ncmp = 0; maxabs = 0.0
for name, arms in sorted(by.items()):
    if "old" not in arms or "new" not in arms: continue
    o = [r for r in arms["old"] if "result" in r]; n = [r for r in arms["new"] if "result" in r]
    if not o or not n:
        # cand/round: compare tails
        so = {r.get("stdout_tail", "")[-400:] for r in arms["old"]}; sn = {r.get("stdout_tail", "")[-400:] for r in arms["new"]}
        ko = {str(r["round_json"]["best_key"]) + "|" + str(r["round_json"]["n_valid"]) for r in arms["old"] if r.get("round_json")}
        kn = {str(r["round_json"]["best_key"]) + "|" + str(r["round_json"]["n_valid"]) for r in arms["new"] if r.get("round_json")}
        if ko or kn: rows.append((name, "round best_key|n_valid", ko, kn, ko == kn))
        continue
    fo = dict(flat(o[0]["result"]["out"])); fn = dict(flat(n[0]["result"]["out"]))
    for k in sorted(set(fo) | set(fn)):
        if any(s in k for s in SKIP): continue
        a, b = fo.get(k, "<missing>"), fn.get(k, "<missing>"); ncmp += 1
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            d = abs(a - b)
            if not (a == b or (isinstance(a, float) and math.isnan(a) and math.isnan(b))):
                maxabs = max(maxabs, d) if d == d else maxabs
                if d > 1e-13 + 1e-9 * abs(a): ndiff += 1; rows.append((name, k, a, b, False))
        elif a != b: ndiff += 1; rows.append((name, k, a, b, False))
print("fields compared", ncmp, "differing beyond rounding (1e-13 + 1e-9 rel)", ndiff, "max abs diff of numeric fields", maxabs)
for r in rows: print(r)

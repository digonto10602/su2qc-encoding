"""Aggregate results/benchmarks/c5-raw/*.jsonl -> medians [min,max] per (job, arm), old/new ratio, flags > 10 %.
usage: c5_analyze.py > summary.json (also prints a text table)"""
import json, glob, statistics as st, sys, collections
recs = [json.loads(l) for f in sorted(glob.glob("/home/digimonk/Projects/su2qc-encoding/results/benchmarks/c5-raw/[a-z]*.jsonl")) if "smoke" not in f for l in open(f)]
by = collections.defaultdict(lambda: collections.defaultdict(list))
for r in recs: by[r["name"]][r["arm"]].append(r)
def med(x): return st.median(x)
def rng(x): return [min(x), max(x)]
out = {}
for name, arms in by.items():
    o = {"n": {a: len(v) for a, v in arms.items()}, "rc": {a: [r["rc"] for r in v] for a, v in arms.items()},
         "load_before": {a: [round(r["load_before"], 2) for r in v] for a, v in arms.items()},
         "load_after": {a: [round(r["load_after"], 2) for r in v] for a, v in arms.items()}, "rows": {}}
    ok = {a: [r for r in v if r["rc"] == 0] for a, v in arms.items()}
    kind = recs[[r["name"] for r in recs].index(name)]["kind"]
    if kind == "worker":
        keys = None
        for a in ok:
            for r in ok[a]:
                if "result" in r: keys = list(r["result"]["times"]); break
        for k in keys or []:
            row = {}
            for a in ("old", "new"):
                firsts = [r["result"]["times"][k][0] for r in ok.get(a, []) if "result" in r and k in r["result"]["times"]]
                laters = [x for r in ok.get(a, []) if "result" in r and k in r["result"]["times"] for x in r["result"]["times"][k][1:]]
                row[a] = {"first": [med(firsts), *rng(firsts)] if firsts else None, "later": [med(laters), *rng(laters)] if laters else None}
            out_row = {"old": row["old"], "new": row["new"]}
            for w in ("first", "later"):
                if row["old"][w] and row["new"][w]: out_row["ratio_" + w] = row["new"][w][0] / row["old"][w][0]
            o["rows"][k] = out_row
        o["rss_mb"] = {a: [r["result"]["rss_mb"] for r in ok.get(a, []) if "result" in r] for a in ("old", "new")}
        o["process_wall_s"] = {a: [r["wall_s"] for r in ok.get(a, [])] for a in ("old", "new")}
    else:
        o["wall_s"] = {a: [med([r["wall_s"] for r in ok[a]]), *rng([r["wall_s"] for r in ok[a]])] for a in ("old", "new") if ok.get(a)}
        if "old" in o["wall_s"] and "new" in o["wall_s"]: o["ratio_wall"] = o["wall_s"]["new"][0] / o["wall_s"]["old"][0]
        if kind == "round":
            o["round_wall_json"] = {a: [med([r["round_json"]["wall_s"] for r in ok[a] if r.get("round_json")]), *rng([r["round_json"]["wall_s"] for r in ok[a] if r.get("round_json")])] for a in ("old", "new") if ok.get(a)}
            o["round_best_key"] = {a: sorted({str(r["round_json"]["best_key"]) for r in ok[a] if r.get("round_json")}) for a in ok}
    out[name] = o
json.dump(out, open("/home/digimonk/Projects/su2qc-encoding/results/benchmarks/c5-raw/summary.json", "w"), indent=1)
def f(x): return "-" if x is None else f"{x[0]:.4g} [{x[1]:.4g},{x[2]:.4g}]"
for name, o in sorted(out.items()):
    print("##", name, o["n"], "rc", o["rc"])
    for k, r in o["rows"].items():
        if k.startswith("import"): continue
        print(f"  {k:36s} old {f(r['old']['first']):28s}/{f(r['old']['later']):28s} new {f(r['new']['first']):28s}/{f(r['new']['later']):28s} ratio {r.get('ratio_first',float('nan')):.3f}/{r.get('ratio_later',float('nan')):.3f}")
    if "wall_s" in o: print("  wall", {a: f(v) for a, v in o["wall_s"].items()}, "ratio", round(o.get("ratio_wall", float("nan")), 3), o.get("round_wall_json", ""))

"""Summaries of raw_<phase>.json (driver output) -> medians and ranges; comparison with results/benchmarks/spinnet-m3.json (report 100).
usage: python analyze_m4.py <scratch_dir>"""
import json, sys, statistics, pathlib
S = pathlib.Path(sys.argv[1])
def ms(xs): return (statistics.median(xs), min(xs), max(xs))
def fmt(t, p=4): return f"{t[0]:.{p}g} [{t[1]:.{p}g}, {t[2]:.{p}g}]"
def task_stats(runs, key, first):
    """first=True: first call of each process; else all later calls pooled"""
    xs = []
    for r in runs:
        v = r["times"].get(key, [])
        if not v: continue
        xs += [v[0]] if first else v[1:]
    return ms(xs) if xs else None
out = {}
base = json.load(open(pathlib.Path(__file__).resolve().parents[1] / "spinnet-m3.json"))["raw"]
for ph in ("tasksA", "tasksB"):
    f = S / f"raw_{ph}.json"
    if not f.exists(): continue
    raw = json.load(open(f))
    for task, runs in raw["tasks"].items():
        keys = [k for k in runs[0]["times"] if k not in ("import_evaluator", "import_spinnet", "import_lsh")]
        o = {"n_proc": len(runs), "rss_mb": ms([r["rss_mb"] for r in runs]), "load_before": [r["load_before"] for r in runs], "keys": {}}
        for k in keys:
            n = len(runs[0]["times"][k])
            o["keys"][k] = {"first": task_stats(runs, k, True), "later": task_stats(runs, k, False) if n > 1 else None}
        o["out"] = runs[-1]["out"]
        if task in base["tasks"]:
            bk = {}
            for k in base["tasks"][task][0]["times"]:
                bn = len(base["tasks"][task][0]["times"][k])
                bf = ms([r["times"][k][0] for r in base["tasks"][task]])
                bl = ms([x for r in base["tasks"][task] for x in r["times"][k][1:]]) if bn > 1 else None
                bk[k] = {"first": bf, "later": bl}
            o["baseline_100"] = bk
        out.setdefault(ph, {})[task] = o
for ph in ("round", "scripts", "suites_m4", "suites_m7", "suites_unit"):
    f = S / f"raw_{ph}.json"
    if not f.exists(): continue
    raw = json.load(open(f))
    for name, c in raw["cmds"].items():
        w = [r["wall"] for r in c["runs"]]
        out.setdefault(ph, {})[name] = {"cmd": c["cmd"], "walls": w, "wall": ms(w), "rss_mb": ms([r["maxrss_kb"] / 1024 for r in c["runs"]]),
                                        "rc": [r["rc"] for r in c["runs"]], "load_before": [r["load_before"] for r in c["runs"]],
                                        "tail": [r["tail"][-200:] for r in c["runs"]]}
json.dump(out, open(S / "summary.json", "w"), indent=1, default=str)
for ph, d in out.items():
    print("##", ph)
    for name, o in d.items():
        if "keys" in o:
            print(f"{name}: rss {o['rss_mb'][0]:.0f} MB; " + "; ".join(f"{k}: first {fmt(v['first'])}" + (f" later {fmt(v['later'])}" if v['later'] else "") for k, v in o["keys"].items() if k not in ("SpinNet()_in_task","LSH()_in_task")))
            if "baseline_100" in o:
                print("   base100: " + "; ".join(f"{k}: first {fmt(v['first'])}" + (f" later {fmt(v['later'])}" if v['later'] else "") for k, v in o["baseline_100"].items() if k not in ("import_evaluator","import_spinnet")))
        else:
            print(f"{name}: wall {fmt(o['wall'],5)} s rss {o['rss_mb'][0]:.0f} MB rc {o['rc']} loads {[l[0] for l in o['load_before']]}")

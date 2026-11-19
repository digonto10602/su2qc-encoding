import json, sys, statistics as st, collections, pathlib
f = pathlib.Path(sys.argv[1]); recs = [json.loads(l) for l in f.read_text().splitlines()]
by = collections.defaultdict(list)
for r in recs: by[r["name"]].append(r)
out = {}
for n, rs in by.items():
    meas = [r for r in rs if r["rep"] != 0]; warm = [r for r in rs if r["rep"] == 0]
    w = [r["wall_s"] for r in meas]; c = [r["user_s"] + r["sys_s"] for r in meas]
    out[n] = {"n": len(meas), "wall_median": st.median(w), "wall_min": min(w), "wall_max": max(w), "wall_all": w,
              "cpu_median": st.median(c), "cpu_all": c, "warmup_wall": [r["wall_s"] for r in warm], "rss_mb_max": max(r["maxrss_mb"] for r in rs),
              "load_before": [r["load_before"][0] for r in meas], "load_max": max(max(r["load_before"][0], r["load_after"][0]) for r in meas),
              "rc": sorted({r["rc"] for r in rs}),
              "pinned_cpu_busy_min": min(min(r["cpu_busy_frac"].values()) for r in meas),
              "sibling_busy_max": max([max(r["sibling_cpu_busy_frac"].values(), default=0) for r in meas], default=0),
              "spread_pct": 100 * (max(w) - min(w)) / st.median(w)}
for n, o in out.items():
    print(f"{n:28s} n={o['n']} wall med {o['wall_median']:.2f} [{o['wall_min']:.2f},{o['wall_max']:.2f}] spread {o['spread_pct']:.0f}% cpu med {o['cpu_median']:.1f} rss {o['rss_mb_max']:.0f} MB loadmax {o['load_max']:.1f} sibmax {o['sibling_busy_max']:.2f} rc {o['rc']}")
json.dump(out, open(sys.argv[2], "w"), indent=1)

"""Summarise raw_m7tasks.json: per task and tree (HEAD vs milestone-7 source), first-call and later-call medians [min,max], ratio HEAD/M7src."""
import json, sys, statistics as st
d = json.load(open(sys.argv[1]))
def ms(x): return f"{st.median(x):.4f} [{min(x):.4f},{max(x):.4f}]"
rows = {}
for name, v in d["runs"].items():
    task, tag = name.split("@"); runs = v["runs"]
    if task == "lsh_enc_build":
        keys = ["LSH()", "target_UB", "target_step", "build_UE", "build_UB", "build_step1", "build_step2"]
        for k in keys:
            first = [r["times"][k][0] for r in runs]; later = [t for r in runs for t in r["times"][k][1:]]
            rows[(task + ":" + k, tag)] = (first, later, runs)
        continue
    for k in runs[0]["times"]:
        if k in ("import_evaluator", "import_lsh", "LSH()_in_task"): continue
        first = [r["times"][k][0] for r in runs]; later = [t for r in runs for t in r["times"][k][1:]]
        rows[(task + ":" + k, tag)] = (first, later, runs)
out = []
for (key, tag), (f, l, runs) in rows.items():
    if tag != "head": continue
    ref = rows.get((key, "m7src"))
    rec = {"quantity": key, "head_first": f, "head_later": l, "m7_first": ref[0] if ref else None, "m7_later": ref[1] if ref else None,
           "load_before_head": [r["load_before"][0] for r in runs]}
    out.append(rec)
    line = f"{key:42s} HEAD first {ms(f)} later {ms(l) if l else '-'}"
    if ref:
        rf = st.median(f) / st.median(ref[0]); rl = (st.median(l) / st.median(ref[1])) if l and ref[1] else float('nan')
        line += f" | M7src first {st.median(ref[0]):.4f} later {st.median(ref[1]) if ref[1] else float('nan'):.4f} | ratio first {rf:.3f} later {rl:.3f}"
    print(line)
json.dump(out, open(sys.argv[2], "w"), indent=1)

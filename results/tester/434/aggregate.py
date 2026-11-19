import json, glob, collections, subprocess
out = {"commit": subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip(), "seed": 434, "bases": {}}
tot = collections.Counter()
for nm in ["UE", "UD", "UB", "F3", "step"]:
    rows = []
    for f in sorted(glob.glob(f"results/tester/434/mut_{nm}_*.json")): rows += json.load(open(f))
    if not rows: continue
    c = collections.Counter()
    for r in rows:
        c[(r["expect"], r["verdict"])] += 1
    unexpected = [r for r in rows if not r["as_expected"]]
    out["bases"][nm] = {"mutants": len(rows), "expected_reject_got_reject": c[("reject", "reject")], "expected_reject_got_accept": c[("reject", "accept")],
                        "expected_accept_got_accept": c[("accept", "accept")], "expected_accept_got_reject": c[("accept", "reject")],
                        "errors_or_timeouts": sum(1 for r in rows if r["verdict"] == "ERROR"), "unexpected": unexpected,
                        "max_seconds": max(r["seconds"] for r in rows), "labels_accepted": sorted(r["label"] for r in rows if r["verdict"] == "accept")}
    tot.update(c)
    print(nm, len(rows), dict(c), "unexpected:", len(unexpected))
out["total"] = {f"exp_{a}_got_{b}": v for (a, b), v in tot.items()}
json.dump(out, open("results/tester/434-mutation.json", "w"), indent=1)
print(out["total"])

import json, subprocess, sys, time
res = {}
for nm, p in [("UB", "scratch/t434/UB/UB-o1-d2869a2974b9.json"), ("step", "scratch/t434/step/step-o1-280998490c3e.json"), ("UE", "scratch/t434/UE/UE-o1-fcc27782db55.json"), ("F3", "scratch/t434/F3/step-o1-24d16bdd9c45.json")]:
    c = json.load(open(p))
    g = next(g for g in c["gates"] if "m" in g)
    s = next(i for i in range(3) if g["m"][i])
    g["m"][s] *= 10 ** 30
    open("scratch/t434/huge.json", "w").write(json.dumps(c, separators=(",", ":")))
    t0 = time.time()
    r = subprocess.run(["lean/.lake/build/bin/su2plaq_rishon_cert", "check", "scratch/t434/huge.json"], capture_output=True, text=True, timeout=900)
    res[nm] = {"slot": s, "line": r.stdout.strip()[:100], "seconds": time.time() - t0}; print(nm, res[nm], flush=True)
json.dump(res, open("results/tester/434-huge-exp.json", "w"), indent=1)

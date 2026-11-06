import json, glob, re, subprocess
res = {}
for f in sorted(glob.glob("own_0*.out")):
    for line in open(f):
        m = re.match(r"^(\S+) (\S+) (\S+) (\{.*\})$", line.strip())
        if m:
            d = eval(m.group(4)); res[f"{m.group(1)}@{m.group(2)},{m.group(3)}"] = {k: d[k] for k in ("err", "ancilla_or_leak_weight_max_sum", "outer_changed_sum", "n_qubits", "wall")}
mem = {}
for f in sorted(glob.glob("*.err")):
    t = open(f).read()
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", t); w = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)", t)
    if m: mem[f] = {"max_rss_GB": int(m.group(1)) / 1e6, "wall": w.group(1)}
paulo = None
try: paulo = json.loads(open("own_paulo2.out").read())
except Exception as e: paulo = str(e)
commit = subprocess.run("git rev-parse --short HEAD", shell=True, capture_output=True, text=True).stdout.strip()
json.dump({"commit": commit, "mode": "step", "report": "reports/tests/112-m4-round-000.md", "angle_pairs": [[0.37, 0.61], [0.91, 0.23], [1.70, 1.0]],
           "target": "scipy expm of exact.spinnet route-B H_B (6j) x diag e^{-i alpha H_E}", "seeds": {"paulo_random_gauge": 20261104},
           "aer_433_states": res, "paulo15": paulo, "memory": mem}, open("../4_4.json", "w"), indent=1)
print(len(res), "cases; max err", max(v["err"] for v in res.values()) if res else None)

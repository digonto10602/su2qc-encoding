import json, copy, glob, subprocess, os
EXE = "/home/digimonk/Projects/su2qc-encoding/lean/.lake/build/bin/su2plaq_cert"
base = json.load(open(glob.glob("certs/UB-*.json")[0])); G = base["gates"]
os.makedirs("mutub2", exist_ok=True)
rows = []
for i in (347, 349, 371, 373, 386, 388):
    m = G[i]["m"]
    for new in ([m[0], 2*m[1]], [m[0], m[1]//2], [m[0], m[1]+2], [m[0], m[1]-2]):
        d = copy.deepcopy(base); d["gates"][i]["m"] = new
        p = f"mutub2/{i}_{new[1]}.json"; json.dump(d, open(p, "w"))
        r = subprocess.run([EXE, "check", p], capture_output=True, text=True).stdout.strip()
        rows.append((i, m, new, r[:60]))
        print(f"gate {i} {m} -> {new}: {r[:70]}", flush=True)
print("all rejected:", all(r[3].startswith("REJECT") for r in rows), len(rows))

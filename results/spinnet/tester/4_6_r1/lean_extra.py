import json, copy, subprocess, collections, pathlib, sys
root = pathlib.Path(sys.argv[1]); T = root/"results/spinnet/tester/4_6_r1/certs"
exe = root/"lean/.lake/build/bin/su2plaq_cert_spinnet"
old = json.load(open(root/"results/spinnet/certs/spinnet-step-o1-47a41f2305b0.json"))
print(collections.Counter(x["g"] for x in old["gates"]))
def chk(p): 
    r = subprocess.run([str(exe),"check",str(p)],capture_output=True,text=True); return (r.stdout.strip().splitlines() or [r.stderr[-200:]])[0]
d = copy.deepcopy(old); g = d["gates"]; g[95], g[97] = g[97], g[95]
p = T/"F1-mut-swap_noncommuting.json"; p.write_text(json.dumps(d, separators=(",",":"))); print("swap non-commuting cx(0,3)<->cx(3,1):", chk(p))
d = copy.deepcopy(old); d["gates"][97]["q"] = [3, 0]; p = T/"F1-mut-retarget_last_cx.json"; p.write_text(json.dumps(d, separators=(",",":"))); print("retarget last cx:", chk(p))
d = copy.deepcopy(old); d["program_sha256"] = "0"*64; p = T/"F1-mut-sha.json"; p.write_text(json.dumps(d, separators=(",",":"))); print("program_sha256 changed (identifier only):", chk(p))

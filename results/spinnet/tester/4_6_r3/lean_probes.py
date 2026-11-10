import json, copy, subprocess, collections, pathlib, sys
root = pathlib.Path(sys.argv[1]); T = root/"results/spinnet/tester/4_6_r3/certs"
exe = root/"lean/.lake/build/bin/su2plaq_cert_spinnet"
old = json.load(open(root/"results/spinnet/certs/spinnet-step-o1-ec21654efa8e.json"))
print(collections.Counter(x["g"] for x in old["gates"]))
def chk(p):
    r = subprocess.run([str(exe),"check",str(p)],capture_output=True,text=True); return (r.stdout.strip().splitlines() or [r.stderr[-200:]])[0]
def w(name, d):
    p = T/f"F1-mut-{name}.json"; p.write_text(json.dumps(d, separators=(",",":"))); return p
g0 = old["gates"]
cxi = [i for i,x in enumerate(g0) if x["g"]=="cx"]
# pairs of cx that are consecutive in the cx list, share a qubit as (control of one, target of the other) and have no other gate on those qubits in between
def touches(x, qs): return bool(set(x["q"]) & qs)
res = []
for a, b in zip(cxi, cxi[1:]):
    qa, qb = g0[a]["q"], g0[b]["q"]
    if (qa[0]==qb[1] or qa[1]==qb[0]) and not any(touches(g0[m], set(qa)|set(qb)) for m in range(a+1, b)):
        d = copy.deepcopy(old); g = d["gates"]; g[a], g[b] = g[b], g[a]
        res.append((a, b, qa, qb, chk(w(f"swap_noncommuting_{a}_{b}", d))))
for r in res: print("swap non-commuting adjacent cx (gate idx %d,%d) %s <-> %s:" % r[:4], r[4])
print("n non-commuting adjacent pairs probed:", len(res), "all rejected:", all(r[4].startswith("REJECT") for r in res))
last_cx = max(i for i,x in enumerate(g0) if x["g"]=="cx")
d = copy.deepcopy(old); d["gates"][last_cx]["q"] = d["gates"][last_cx]["q"][::-1]; print("reverse last cx:", chk(w("reverse_last_cx", d)))
# retarget last cx to a different data qubit
d = copy.deepcopy(old); q = d["gates"][last_cx]["q"]; d["gates"][last_cx]["q"] = [q[0], (q[1]+1) % 8 if (q[1]+1)%8 != q[0] else (q[1]+2)%8]; print("retarget last cx:", chk(w("retarget_last_cx", d)))
d = copy.deepcopy(old); d["program_sha256"] = "0"*64; print("program_sha256 changed (identifier only):", chk(w("sha", d)))
# p-gate (electric) exponent shift and s->sdg
d = copy.deepcopy(old); pg = next(x for x in d["gates"] if x["g"]=="p"); pg["m"][0] += 1; print("first p exponent alpha +1:", chk(w("p_plus1", d)))
d = copy.deepcopy(old); sg = next(x for x in d["gates"] if x["g"]=="s"); sg["g"]="sdg"; print("s -> sdg:", chk(w("s_to_sdg", d)))
d = copy.deepcopy(old); del d["gates"][-1]; print("drop last gate (", old["gates"][-1]["g"], "):", chk(w("drop_last", d)))
d = copy.deepcopy(old); d["gates"].insert(0, {"g":"x","q":[8]}); print("x on outer qubit 8 at start:", chk(w("x_outer", d)))
d = copy.deepcopy(old); d["gates"].insert(0, {"g":"x","q":[16]}); print("x on ancilla 16 at start (dirty):", chk(w("x_anc", d)))

# broader non-commuting swap: consecutive cx (in the cx list) sharing a qubit as control/target, in-between gates ignored (a plain mutation)
res = []
for a, b in zip(cxi, cxi[1:]):
    qa, qb = g0[a]["q"], g0[b]["q"]
    if qa[0]==qb[1] or qa[1]==qb[0]:
        d = copy.deepcopy(old); g = d["gates"]; g[a], g[b] = g[b], g[a]
        res.append((a, b, qa, qb, chk(w(f"swapany_{a}_{b}", d))))
print("swap of consecutive cx sharing control/target (in-between gates ignored): %d probes, %d rejected" % (len(res), sum(r[4].startswith("REJECT") for r in res)))
for r in res[:4]: print("   ", r)

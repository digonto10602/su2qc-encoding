"""Tester 434 item 4: r06-F3-006 rotation angles are linear in (alpha, beta, sqrt2 beta) with denominators <= 64 and the certificate's
gate exponents reproduce the circuit's float angles (at the nominal pair and at 8 random pairs, built from the program source)."""
import json, pathlib, itertools, math, numpy as np, pickle
from fractions import Fraction
from su2plaq.rishon.compress import spec as SP, evaluate as EV
from su2plaq.rishon import lean_cert as LC
spec = SP.rishon_spec("step")
e = json.load(open("compress/archive/rishon/entries/r06-F3-006.json"))
src = pathlib.Path(e["program_path"]).read_bytes()
cert = json.load(open("scratch/t434/F3/step-o1-24d16bdd9c45.json"))
SQ2 = math.sqrt(2)
rng = np.random.default_rng(434)
pairs = [(spec.alpha, spec.beta)] + [(float(a), float(b)) for a, b in rng.uniform(0.1, 2.0, size=(8, 2))]
specs = [spec.with_angles(a, b) for a, b in pairs]
circs, _ = EV._build_in_subprocess(src, specs, EV.BUILD_TIMEOUT_S)
ROT = ("rz", "p", "crz", "crx", "cp")
def rots(c): return [(i.operation.name, float(i.operation.params[0])) for i in c.data if i.operation.name in ROT]
r0 = rots(circs[0]); print("rotation gates in circuit:", [(n, round(t, 6)) for n, t in r0])
cg = [g for g in cert["gates"] if "m" in g]
print("cert gates with m:", len(cg), "circuit rotation gates:", len(r0))
base = cert["base"]
out = {"n_rot": len(r0), "rows": []}
# 1. independent brute-force linear recogniser: smallest d <= 64 with integer (a, b, c): theta d = a alpha + b beta + c sqrt2 beta, |a|,|b|,|c| <= 64 d
def brute(theta, al, be):
    r = np.arange(-130, 131); A, C = np.meshgrid(r, r, indexing="ij")
    for d in range(1, 65):
        B = np.rint((theta * d - A * al - C * SQ2 * be) / be)
        ok = (np.abs(A * al + B * be + C * SQ2 * be - theta * d) < 1e-11 * d) & (np.abs(B) <= 130)
        if ok.any():
            cost = np.where(ok, np.abs(A) + np.abs(B) + np.abs(C), 10**9); i, j = np.unravel_index(np.argmin(cost), cost.shape)
            return (int(A[i, j]), int(B[i, j]), int(C[i, j]), d)
    return None
# 2. certificate exponent -> float angle at pair
def cert_angle(g, a, b):
    m = g["m"]; return m[0] * a / base["d_alpha"] + m[1] * b / base["d_beta"] + m[2] * SQ2 * b / base["d_gamma"]
# gate order: the exporter lowers the circuit in program order; rotation gates of the circuit map 1:1 to cert gates with m (p/rz only here)
names = [n for n, _ in r0]
assert [g["g"] for g in cg] == names, ([g["g"] for g in cg], names)
maxdev = 0.0; maxden = 0
for k, (n, th) in enumerate(r0):
    # for rz the cert exponent is the full angle exponent (rz(theta) half angle = theta/2)
    row = {"gate": n, "theta_nominal": th, "cert_m": cg[k]["m"], "brute": brute(th, spec.alpha, spec.beta)}
    if row["brute"]: maxden = max(maxden, row["brute"][3])
    devs = []
    for (a, b), c in zip(pairs, circs):
        devs.append(abs(rots(c)[k][1] - cert_angle(cg[k], a, b)))
    row["max_dev_over_9_pairs"] = max(devs); maxdev = max(maxdev, max(devs)); out["rows"].append(row)
    print(row)
out["max_dev_all"] = maxdev; out["max_denominator"] = maxden; out["pairs"] = pairs
print("max |circuit angle - cert exponent angle| over", len(pairs), "pairs:", maxdev, " max denominator", maxden)
json.dump(out, open("results/tester/434-angles-F3.json", "w"), indent=1)

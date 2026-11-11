import sys, json, hashlib, numpy as np
rng = np.random.default_rng(20261107)
a = rng.uniform(0.05, 2.0, 20)
b = rng.uniform(0.05, 1.2, 20)
pairs = tuple((float(x), float(y)) for x, y in zip(a, b))
sha = hashlib.sha256(repr(pairs).encode()).hexdigest()
from su2plaq.spinnet import loop
print("own sha", sha)
print("loop sha", loop.angle_set_sha256())
print("equal pairs", pairs == loop.ANGLE_SET, "ranges ok", a.min()>=0.05, a.max()<2.0, b.min()>=0.05, b.max()<1.2)
r = json.load(open("results/compress/spinnet/robust.json"))
print("cache sha", r["angle_set"]["sha256"], r["angle_set"]["pairs"] == [list(p) for p in pairs], r["angle_set"]["seed"], r["angle_set"]["n"])
json.dump({"sha": sha, "pairs": pairs}, open("results/spinnet/tester/4_6_r5/probe_a.json","w"))

"""rz angles of build_UB / build_step: HEAD walk.py (argv[1] = src dir; argv[2] = out json); prints JSON."""
import sys, json
sys.path.insert(0, sys.argv[1])
import su2plaq, numpy as np
assert su2plaq.__file__.startswith(sys.argv[1]), su2plaq.__file__
from su2plaq.circuits.spinnet import build_UB, build_step
res = {}
for b in (0.05, 0.23, 0.61, 1.0, 2.0):
    res[f"UB{b}"] = [float(i.operation.params[0]) for i in build_UB(b).data if i.operation.name == "rz"]
res["step"] = [float(i.operation.params[0]) for i in build_step(0.37, 0.61, 1, with_outer=True).data if i.operation.name == "rz"]
json.dump(res, open(sys.argv[2], "w"))

import json, collections, time
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.evaluate import sparse_sim as SS
spec = rishon_spec("step")
res = {}
def stats(name, qc):
    ops, ph = SS._translate(qc)
    c = collections.Counter(o[0] for o in ops)
    br = sum(c[k] for k in SS._BRANCH)
    res[name] = {"macro_ops": dict(qc.count_ops()), "sim_ops": dict(c), "n_branching_sim_gates": br, "n_sim_gates": len(ops)}
    print(name, res[name]["macro_ops"] if len(str(res[name]['macro_ops']))<300 else '...', "branching:", br, "H:", c["h"], "ccx(native):", c["ccx"], "total", len(ops), flush=True)
t=time.time()
stats("general(ccx)", BL.general_circuit(spec,"ccx"))
stats("general-rccx", BL.general_circuit(spec,"rccx"))
stats("general-mcx", BL.general_circuit(spec,"mcx"))
pol,log = BL.polish(BL.general_circuit(spec),spec); print(log)
stats("general+polish", pol)
l3 = BL.qiskit_l3(spec, seed=12345); print("l3 built", time.time()-t, flush=True)
stats("qiskit_l3", l3)
json.dump(res, open("/tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/t216/counts.json","w"), indent=1)

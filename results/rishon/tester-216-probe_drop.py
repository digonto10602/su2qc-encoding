import json, time, numpy as np
import su2plaq.rishon.compress  # noqa
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress.spec import rishon_spec
from su2plaq.rishon.compress.evaluate import trial_states
from su2plaq.compress.spec import get_encoding
from su2plaq.evaluate import sparse_sim as SS
spec = rishon_spec("step")
codes = np.array(get_encoding("rishon").inner_codes(), dtype=np.int64)
idx = trial_states(spec)
inp = codes[idx]
print("trial inputs", len(inp), "of", len(codes))
circs = {"general(ccx)": BL.general_circuit(spec,"ccx"), "general-rccx": BL.general_circuit(spec,"rccx"),
         "general-mcx": BL.general_circuit(spec,"mcx"), "qiskit_l3": BL.qiskit_l3(spec, seed=12345)}
out = {}
for k, qc in circs.items():
    t=time.time()
    b = SS.run_batch(qc, inp)
    d = b.dropped_l2
    ops,_ = SS._translate(qc)
    nh = sum(1 for o in ops if o[0] in SS._BRANCH)
    rms = float(np.sqrt(np.mean(d**2)))
    out[k] = {"n_cols":len(inp),"dropped_total_64":b.dropped_total,"d_c_mean":float(d.mean()),"d_c_max":float(d.max()),"d_c_rms":rms,
              "extrap_1296_total":rms*np.sqrt(1296),"n_branching_gates":nh,"per_branching_gate_per_col_rms":rms/nh,"wall_s":time.time()-t}
    print(k, json.dumps(out[k]), flush=True)
json.dump(out, open(__import__("os").environ.get("OUT","/tmp/drop.json"),"w"), indent=1)

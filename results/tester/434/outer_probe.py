import json, pathlib
from su2plaq.rishon import lean_cert as LC
from su2plaq.rishon.compress import baselines as BL, spec as SP
spec = SP.rishon_spec("UE"); base = BL.general_circuit(spec)
print("qubits", base.num_qubits)
D = pathlib.Path("scratch/t434/outer"); res = {}
def probe(name, f):
    qc = base.copy(); f(qc)
    c = LC.certify_circuit(qc, spec, out_dir=D)
    res[name] = (c.status, c.reason[:80]); print(name, res[name], flush=True)
probe("control: unchanged", lambda q: None)
probe("data->outer write cx(0,20)", lambda q: q.cx(0, 20))
probe("outer-controlled cx(20,1)", lambda q: q.cx(20, 1))
probe("rz on outer 40", lambda q: q.rz(0.2775, 40))
probe("h on outer 17", lambda q: q.h(17))
probe("x on outer 47 then x (identity pair)", lambda q: (q.x(47), q.x(47)))
probe("x on unused qubit above outer (if any)", lambda q: q.x(q.num_qubits - 1))
json.dump(res, open("results/tester/434-outer-probe.json", "w"), indent=1)

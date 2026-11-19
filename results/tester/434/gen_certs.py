"""Tester 434: generate fresh certificates (own out dir) for the circuits to be mutated; record status, time, Lean peak RSS."""
import json, pathlib, resource, time, sys
from su2plaq.rishon import lean_cert as LC
from su2plaq.rishon.compress import baselines as BL, spec as SP, round as RD
from su2plaq.circuits import rishon as CR
from su2plaq.compress import spec as CS
OUT = pathlib.Path("scratch/t434"); OUT.mkdir(exist_ok=True)
spec = SP.rishon_spec("step"); specUB = SP.rishon_spec("UB"); specUE = SP.rishon_spec("UE")
res = {}
def run(name, f):
    t0 = time.time(); c = f()
    res[name] = {"status": c.status, "reason": c.reason, "cert": c.cert_path, "seconds": time.time() - t0,
                 "maxrss_children_MB": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024}
    print(name, res[name], flush=True)
which = sys.argv[1:]
if "UE" in which: run("UE", lambda: LC.certify_circuit(BL.general_circuit(specUE), specUE, out_dir=OUT / "UE"))
if "UB" in which: run("UB", lambda: LC.certify_circuit(BL.general_circuit(specUB), specUB, out_dir=OUT / "UB"))
if "UD" in which: run("UD", lambda: LC.certify_det_layer(CR.build_UD(0.29), 0.29, out_dir=OUT / "UD"))
if "step" in which: run("step", lambda: LC.certify_circuit(BL.general_circuit(spec), spec, out_dir=OUT / "step"))
if "F3" in which:
    e = json.load(open("compress/archive/rishon/entries/r06-F3-006.json"))
    circ, err = RD._circuit_of(spec, e["program_path"], "x", None, pathlib.Path("."))
    assert circ is None or True
    print("circuit", circ.num_qubits, len(circ.data), err)
    fit = LC.confirm_angle_fit(e["program_path"], spec, root=pathlib.Path("."))
    print("confirmed", fit["confirmed"], fit["reason"])
    run("F3", lambda: LC.certify_circuit(circ, spec, out_dir=OUT / "F3", angle_fit=fit))
    import pickle; pickle.dump(circ, open(OUT / "F3_circuit.pkl", "wb"))
json.dump(res, open(f"results/tester/434/gen_{'_'.join(which)}.json", "w"), indent=1)

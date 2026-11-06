import json, pathlib, sys, time, os, glob
sys.path.insert(0, "/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
SP = pathlib.Path("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/adv")
from su2plaq.compress import evaluate as E
from su2plaq.compress.spec import default_spec, TaskSpec
for f in glob.glob(str(SP/"MARKER_*")): os.remove(f)
parent_events = []
def hook(ev, args):
    if ev == "import" and args and ("adv" in str(args[0]) or "programs" in str(args[0]) or str(args[0]).startswith("su2plaq_program")):
        parent_events.append(("import", str(args[0])))
    if ev == "open" and args and "MARKER_" in str(args[0]):
        parent_events.append(("open", str(args[0])))
    if ev == "exec" :
        pass
sys.addaudithook(hook)
UE = default_spec("twelve", "UE")
names = sys.argv[1:] or sorted(p.stem for p in (SP/"programs").glob("*.py"))
out = {}
E.BUILD_TIMEOUT_S = 8.0
for nm in names:
    p = SP/"programs"/f"{nm}.py"
    row = {}
    for mode in ("trial", "full"):
        t0 = time.time()
        try:
            r = E.evaluate_program(p, UE, mode)
            v = r.verdict
            row[mode] = dict(valid=r.valid, reason=r.reason, msg=(r.message or "")[:140].replace("\n"," | "), t=round(time.time()-t0,1),
                             err=None if v is None else float(v.op_norm_error), leak=None if v is None else float(v.leak_amplitude), gauss=None if v is None else float(v.gauss_residual),
                             qubits=None if r.metrics is None else r.metrics["qubits"], skel=r.skeleton_equal)
        except Exception as e:
            row[mode] = dict(exception=f"{type(e).__name__}: {e}"[:200])
        if mode == "trial" and not row[mode].get("valid", True) is True and nm not in ("cheat_subset_states",) and row[mode].get("reason") in ("contract","build_error","build_timeout"):
            row["full"] = "same as trial"; break
    out[nm] = row
    print(nm, json.dumps(row), flush=True)
print("PARENT EVENTS", parent_events)
print("MARKERS", [os.path.basename(x) for x in glob.glob(str(SP/"MARKER_*"))])
json.dump(out, open(SP/"results_cases.json","w"), indent=1)

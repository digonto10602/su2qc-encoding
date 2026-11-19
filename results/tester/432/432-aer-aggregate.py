import numpy as np, glob, json, os, subprocess
here = os.path.dirname(os.path.abspath(__file__))
rows = {}
for f in sorted(glob.glob(os.path.join(here, "432-aer-r05-*.npz"))):
    d = np.load(f); n = os.path.basename(f)[8:-4]
    cid, tag = n.rsplit("-", 1) if not n.endswith("nominal") else (n[:-8], "nominal")
    rows.setdefault(cid, {})[tag] = dict(n_codes=int(len(d["cols"])), qubits_min=int(d["nq"].min()), qubits_max=int(d["nq"].max()), max_col_maxabs_err=float(d["colerr_max"].max()), max_col_L2_err=float(d["colerr_l2"].max()),
        max_weight_outside=float(np.abs(d["w_out"]).max()), phase_deviation=float(abs(abs(d["phase"]) - 1)), phase_angle=float(np.angle(d["phase"])), alpha=float(d["alpha"]), beta=float(d["beta"]), cpu_seconds=float(d["seconds"].sum()))
    print(cid, tag, rows[cid][tag])
json.dump(dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip(), rows=rows), open(os.path.join(here, "432-aer-summary.json"), "w"), indent=1)

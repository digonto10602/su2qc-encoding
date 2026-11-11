"""Tester 403: saved results/lsh/{UB,step,step_order2}.qpy exact on 433 states vs independent 6j targets (reuses simulate() of tester-403-wrap-exact.py)."""
import json
src = open("results/lsh_tester/tester-403-wrap-exact.py").read().split("out = {")[0]
exec(src)
from qiskit import qpy
from su2plaq.exact.spinnet import h_electric_6j
hE = np.diag(h_electric_6j(labs, inner_only=True)); a, b = 0.37, 0.61
UE = lambda al: np.diag(np.exp(-1j * al * hE))
rows = []
for nm, T in (("UB", U6(b)), ("step", U6(b) @ UE(a)), ("step_order2", UE(a/2) @ U6(b) @ UE(a/2))):
    qc = qpy.load(open(f"results/lsh/{nm}.qpy", "rb"))[0]
    M, al, il, sl = simulate(qc)
    e2, emax, ph, unit = compare(M, T)
    r = dict(file=nm, op_norm_err=e2, max_entry_err=emax, global_phase=ph, unitarity_dev=unit, anc_leak_prob_max=float(al.max()), invalid_data_leak_max=float(il.max()), span_leak_max=float(sl.max()),
             ctrl_wrong_order=compare(M, U6(b) if nm != "UB" else np.eye(433))[0])
    print(r, flush=True); rows.append(r)
json.dump(rows, open("results/lsh_tester/tester-403-step-exact.json", "w"), indent=1)

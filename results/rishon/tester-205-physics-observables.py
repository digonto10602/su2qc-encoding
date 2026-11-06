"""Tester 205: physics block, observables.json and register_rows.json vs independent computation.
Reuses the independent construction (own 16-mode JW, own 1296 codes, expm_multiply) from tester-203-observables-independent.py (lines up to the
comparison loop), compares to results/rishon/observables.json (the FILE, not production), closed forms and closed-spectrum formulas."""
import json, subprocess, sys, collections, math, pathlib
src = pathlib.Path("results/rishon/tester-203-observables-independent.py").read_text().split('rec["angles"] = {}')[0]
exec(compile(src, "t203head", "exec"))
D = json.load(open("results/rishon/observables.json"))
res = {"commit": rec["commit"], "own_W_leak": rec["W_leak_outside_codes"], "n_inner_codes_own": int(len(codes))}
worst = 0.0; rows = []
for th, mine_f in (("rishon", mine_rishon), ("ks", mine_ks)):
    for r in D[th]:
        m = mine_f(r["alpha"], r["beta"])[r["n"]]
        dev = max(abs(r[k]-m[k]) for k in ("E_link","P","echo")); worst = max(worst, dev)
        rows.append(dict(theory=th, alpha=r["alpha"], beta=r["beta"], n=r["n"], file={k:r[k] for k in ("E_link","P","echo")}, own=m, dev=dev))
res["rows"] = rows; res["worst_file_vs_own"] = worst
# closed forms n=1
cfdev = 0.0
for r in D["rishon"]+D["ks"]:
    if r["n"]!=1: continue
    b=r["beta"]
    if r in D["ks"]: tk=2*b; cf=(0.75*np.sin(tk)**2, 0.0, np.cos(tk)**2)
    else: tr=4*np.sqrt(2)*b; cf=(0.375*np.sin(tr)**2, 0.0, 0.25*(1+np.cos(tr))**2)
    cfdev=max(cfdev, abs(r["E_link"]-cf[0]), abs(r["P"]-cf[1]), abs(r["echo"]-cf[2]))
res["n1_file_vs_closed_form_max_dev"]=float(cfdev)
res["n1_P_signs"]=[str(r["P"]) for r in D["rishon"]+D["ks"] if r["n"]==1]
# spectra from the file
sd=0.0; mult={}
for i,g2 in enumerate(D["closed_spectra"]["g2"]):
    s=np.sqrt(9/16*g2**2+32/g2**2); fr=np.sort([0.0,0.75*g2+s,0.75*g2-s]); e=np.array(D["closed_spectra"]["rishon"][i]["eigenvalues"])
    sd=max(sd, np.abs(np.sort(e)-fr).max())
    sk=np.sqrt(9/16*g2**2+4/g2**2); fk=np.sort([0.75*g2+sk,0.75*g2-sk]); ek=np.array(D["closed_spectra"]["ks"][i]["eigenvalues"])
    sd=max(sd, np.abs(np.sort(ek)-fk).max())
    mult[str(g2)]=(D["closed_spectra"]["rishon"][i]["multiplicities"], D["closed_spectra"]["ks"][i]["multiplicities"])
res["spectra_file_vs_formula_max_dev"]=float(sd); res["multiplicities"]=mult
res["negative_zero_in_file"]= open("results/rishon/observables.json").read().count("-0.0")
# physics block: own numbers
bright=0
# own bright pairs: eigendecompose HB restricted: count nonzero-eigenvalue spectral multiplicities
ev=np.linalg.eigvalsh(HB); vals=collections.Counter(np.round(ev,6))
res["own_HB_spectrum"]={str(k):int(v) for k,v in sorted(vals.items())}
res["own_HB_nonzero"]=int(sum(v for k,v in vals.items() if abs(k)>1e-6))
# bright pairs: HB = -sum kappa(u v^T+h.c.): nonzero eig pairs (+-k) => pairs count = nonzero/2
res["own_bright_pairs"]=res["own_HB_nonzero"]//2
P=json.load(open("results/rishon/UB.json"))["extra"]
res["file_physics"]=P["physics"]; res["file_kappa"]=P["physics_detail"]["kappa_multiset"]
kap=P["physics_detail"]["kappa_multiset"]; res["kappa_sum"]=sum(kap.values()); res["kappa_vs_my_spectrum"]={"eig": {k:v for k,v in res["own_HB_spectrum"].items() if abs(float(k))>1e-6}}
# physics identical across files; counts arithmetic
allsame=True
for k in ["UE","UE_outer_row","UB","step","step_order2"]:
    d=json.load(open(f"results/rishon/{k}.json")); allsame &= (d["extra"]["physics"]==P["physics"] and d["extra"]["physics_detail"]==P["physics_detail"])
res["physics_same_in_all_files"]=allsame
det=P["physics_detail"]; res["inner_codes_arith"]=(det["n_inner_codes"]==P["physics"]["inner_span_rank"]==1296, det["n_dark_codes"], 1296-det["n_dark_codes"], "bright-component codes; 162 paired + 144 zero modes =", 162+144)
res["register_ok"]=None
Rr=json.load(open("results/rishon/register_rows.json"))["rows"]
res["register_rows"]={k:v["qubits"] for k,v in Rr.items()}; res["touched"]=Rr["jw_4_per_link"]["touched"]
json.dump(res, open("results/rishon/tester-205-physics-observables.json","w"), indent=1, default=float)
print(json.dumps({k:v for k,v in res.items() if k!="rows"}, indent=1, default=float))

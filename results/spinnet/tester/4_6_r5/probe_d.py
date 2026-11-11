import json
r = json.load(open("results/compress/spinnet/robust.json"))
print({k:(v if k!="entries" and k!="angle_set" else "...") for k,v in r.items()})
ents = r["entries"]
print(len(ents), list(next(iter(ents.values())).keys()))
rows=[]
for i,e in ents.items():
    # recompute key from raw lists
    ts=sum(e["t_eps"]); ds=sum(e["depth_ct"])
    rho = 0 if not e["export_status"].startswith("non_linear_angle") else 1
    key=(e["cx"], ts, rho, ds, e["qubits"]) if e["skeleton_equal"] else None
    assert (key is None and e["robust_key"] is None) or tuple(e["robust_key"])==key, i
    assert len(e["t_eps"])==20 and len(e["depth_ct"])==20
    rows.append((key, tuple(e["laptop_key"]), i, e))
rows=[x for x in rows if x[0] is not None]
rows.sort(key=lambda x:(x[0],x[1],x[2]))
for k,l,i,e in rows: print(i, k, l, round(e["t_sum"]/20,2), e["export_status"][:40])
json.dump([[list(k),list(l),i] for k,l,i,e in rows], open("results/spinnet/tester/4_6_r5/probe_d_rank.json","w"))

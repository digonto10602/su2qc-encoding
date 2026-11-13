import subprocess, json, sys, statistics
R="/home/digimonk/Projects/su2qc-encoding"; W=R+"/results/benchmarks/spinnet-m4-scripts/bench_worker_m4.py"
pairs=[("eval_UB_auto","lsh_eval_UB"),("eval_step1","lsh_eval_step1"),("eval_UE","lsh_eval_UE"),("synth_step1","lsh_synth_step1"),("enc_build","lsh_enc_build")]
res={}
for rep in range(6):
    for pr in pairs:
        for t in pr:
            p=subprocess.run(["taskset","-c","14",sys.executable,W,t,"/tmp"],capture_output=True,text=True,cwd=R)
            r=json.loads([l for l in p.stdout.splitlines() if l.startswith("RESULT ")][0][7:]); res.setdefault(t,[]).append(r)
out={}
for t,rs in res.items():
    d={}
    for k in rs[0]["times"]:
        if k.startswith("import") or k.endswith("_in_task"): continue
        f=[r["times"][k][0] for r in rs]; la=[x for r in rs for x in r["times"][k][1:]]
        d[k]={"first":[statistics.median(f),min(f),max(f)],"later":[statistics.median(la),min(la),max(la)] if la else None}
    out[t]=d
json.dump({"raw_times":{t:[r["times"] for r in rs] for t,rs in res.items()},"summary":out},open(R+"/scratch/bench-m4m7/sn_vs_lsh.json","w"))
for t,d in out.items():
    print(t,{k:(round(v["first"][0],4), round(v["later"][0],4) if v["later"] else None) for k,v in d.items()})

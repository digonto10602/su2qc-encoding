import subprocess, json, sys, os, statistics, time
ROOT="/home/digimonk/Projects/su2qc-encoding"
trees={"old_9c0aee6":ROOT+"/scratch/old-9c0aee6","new_HEAD":ROOT}
tasks=["eval_UB_auto","eval_UE","eval_twelve_UB","synth_UB","enc_build","ops"]
res={t:{k:[] for k in trees} for t in tasks}; loads=[]
for rep in range(4):
    for t in tasks:
        for k,root in trees.items():
            order=(k,)
            p=subprocess.run(["taskset","-c","14",sys.executable,root+"/results/benchmarks/spinnet-m4-scripts/bench_worker_m4.py",t,"/tmp"],capture_output=True,text=True,cwd=root)
            l=[x for x in p.stdout.splitlines() if x.startswith("RESULT ")]
            if not l: print(k,t,p.stderr[-500:]); sys.exit(1)
            r=json.loads(l[0][7:]); r["load"]=open("/proc/loadavg").read().split()[0]; res[t][k].append(r)
    print("rep",rep,"done",flush=True)
json.dump(res,open(ROOT+"/scratch/bench-m4m7/ab.json","w"))
def md(xs): return statistics.median(xs)
for t in tasks:
    print("##",t)
    for key in res[t]["old_9c0aee6"][0]["times"]:
        if key.startswith("import"): continue
        row=[]
        for k in trees:
            f=[r["times"][key][0] for r in res[t][k]]; la=[x for r in res[t][k] for x in r["times"][key][1:]]
            row.append((k, md(f), md(la) if la else None))
        o,n=row
        print(f"{key}: old first {o[1]:.4f} later {o[2] if o[2] is None else round(o[2],4)} | new first {n[1]:.4f} later {n[2] if n[2] is None else round(n[2],4)} | ratio first {n[1]/o[1]:.3f}" + (f" later {n[2]/o[2]:.3f}" if o[2] else ""))

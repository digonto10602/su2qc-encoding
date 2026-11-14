import json, statistics as st, collections, sys
R="results/benchmarks/rishon-m5d-raw/ctl/"
def load(f):
    d=collections.defaultdict(list)
    try:
        for l in open(R+f):
            r=json.loads(l); d[r["task"]].append(r)
    except FileNotFoundError: pass
    return d
res={}
for suffix in ("", "_twelve"):
    o,n=load("old%s.jsonl"%suffix),load("new%s.jsonl"%suffix)
    for t in o:
        if t not in n: continue
        names=set(k for r in o[t] for k in r["times"])
        for k in sorted(names):
            if k in ("import",) or k.startswith("import "): continue
            for pos,label in ((0,"first"),(-1,"later")):
                def vals(d):
                    return [r["times"][k][pos] for r in d[t] if k in r["times"] and (pos==0 or len(r["times"][k])>1)]
                a,b=vals(o),vals(n)
                if not a or not b or st.median(a)<1e-3: continue
                res[(t,k,label)]=(st.median(a),min(a),max(a),st.median(b),min(b),max(b),len(a),len(n[t]))
for (t,k,l),v in res.items():
    print("%-16s %-44s %-5s old %.4g [%.4g,%.4g]  new %.4g [%.4g,%.4g]  new/old %.3f  (n=%d)"%(t,k,l,*v[:6],v[3]/v[0],v[6]))
json.dump({"%s|%s|%s"%k:dict(old_median=v[0],old_min=v[1],old_max=v[2],new_median=v[3],new_min=v[4],new_max=v[5],ratio=v[3]/v[0],n=v[6]) for k,v in res.items()}, open("results/benchmarks/rishon-m5d-raw/ctl/ctl_summary.json","w"), indent=1)

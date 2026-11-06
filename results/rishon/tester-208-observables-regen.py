"""Tester 205: regenerate the observables block with the CURRENT working tree and diff against results/rishon/observables.json (ignoring provenance)."""
import json, sys, math
sys.path.insert(0,"scripts"); 
from su2plaq.rishon import observables as O, results as R
ANGLES=((0.37,0.61),(0.91,0.23),(1.70,1.00))
new=R._jsonable(R.observable_rows(O.observables_table(ANGLES))); old=json.load(open("results/rishon/observables.json")); old.pop("provenance")
diffs=[]
def walk(a,b,p=""):
    if isinstance(a,dict):
        assert set(a)==set(b),(p,set(a)^set(b))
        for k in a: walk(a[k],b[k],p+"/"+str(k))
    elif isinstance(a,list):
        assert len(a)==len(b),p
        for i,(x,y) in enumerate(zip(a,b)): walk(x,y,p+f"[{i}]")
    elif isinstance(a,float):
        if repr(a)!=repr(b): diffs.append((p,repr(a),repr(b)))
    elif a!=b: diffs.append((p,a,b))
walk(new,old)
res={"n_diffs":len(diffs),"diffs":diffs[:20],"max_abs_numeric_diff":max([abs(float(x)-float(y)) for _,x,y in diffs] or [0.0])}
print(res); json.dump(res,open("results/rishon/tester-208-observables-regen.json","w"),indent=1)

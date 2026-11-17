import sys, hashlib, json, subprocess, numpy as np
# independent set
rng=np.random.default_rng(20261107)
a=rng.uniform(0.05,2.0,20); b=rng.uniform(0.05,1.2,20)
mine=tuple((float(x),float(y)) for x,y in zip(a,b))
def child(tree):
    code=("import sys;sys.path.insert(0,%r);"
          "from su2plaq.spinnet import loop as L;from su2plaq.rishon.compress import robust as R;"
          "import json;print(json.dumps({'S':[list(p) for p in L.ANGLE_SET],'R':[list(p) for p in R.ANGLE_SET],'Ssha':L.angle_set_sha256(),'Rsha':R.angle_set_sha256(),"
          "'G':[list(p) for p in __import__('su2plaq.compress.robust',fromlist=['x']).ANGLE_SET] if %r else None}))")%(tree+"/src", tree=="NEW")
    return code
res={}
for name,tree in (("old","/home/digimonk/Projects/su2qc-encoding/scratch/t419/old"),("new","/home/digimonk/Projects/su2qc-encoding")):
    code=("import sys;sys.path.insert(0,%r);import json;"
          "from su2plaq.spinnet import loop as L;from su2plaq.rishon.compress import robust as R;"
          "out={'S':[list(p) for p in L.ANGLE_SET],'R':[list(p) for p in R.ANGLE_SET],'Ssha':L.angle_set_sha256(),'Rsha':R.angle_set_sha256()}\n"
          "if %r:\n from su2plaq.compress import robust as G;out['G']=[list(p) for p in G.ANGLE_SET];out['Gsha']=G.angle_set_sha256()\n"
          "print(json.dumps(out))")%(tree+"/src", name=="new")
    r=subprocess.run([sys.executable,"-I","-c",code],capture_output=True,text=True,cwd="/tmp")
    if r.returncode: print(r.stderr[-2000:]); raise SystemExit
    res[name]=json.loads(r.stdout)
mine_l=[list(p) for p in mine]
sha=hashlib.sha256(repr(mine).encode()).hexdigest()
print("mine sha",sha)
for k in ("old","new"):
    for t in ("S","R","G"):
        if t in res[k]: print(k,t,"== mine (exact floats):",res[k][t]==mine_l)
print("shas",res["old"]["Ssha"],res["old"]["Rsha"],res["new"]["Ssha"],res["new"]["Rsha"],res["new"]["Gsha"])
print("all equal to mine sha:", all(v==sha for v in (res["old"]["Ssha"],res["old"]["Rsha"],res["new"]["Ssha"],res["new"]["Rsha"],res["new"]["Gsha"])))

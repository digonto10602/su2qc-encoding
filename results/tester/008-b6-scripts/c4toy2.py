import sys, hashlib, json, pathlib, tempfile
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
from types import SimpleNamespace
from su2plaq.compress import robust as RB, archive as A, report as RP, brief as BR
import su2plaq.compress.spec as S
tmp=pathlib.Path(tempfile.mkdtemp(dir="/home/digimonk/Projects/su2qc-encoding/scratch/t419"))
enc="twelve"; kind="step"
# three valid entries + one invalid with the best everything + one without program file
# (id, archive key, robust key, valid)
rows=[("rA",(40,1000,2000,10),(40,20000,1,40000,10),True),   # archive best?  not: lowest CX is invalid entry rI
      ("rB",(41,900,1800,10),(41,18000,0,36000,10),True),
      ("rC",(41,950,1900,10),(41,18000,0,35000,10),True),   # ties rB on CX,T,rho -> depth decides
      ("rD",(40,1100,2100,10),(40,19000,0,39000,10),True),
      ("rI",(30,500,1000,10),(30,100,0,100,10),False)]
ents=[];tab={}
for i,(eid,key,rk,val) in enumerate(rows):
    f=tmp/"compress"/"programs"/enc/"F1"/f"{i:03d}.py"; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(f"#{eid}\n")
    sha=hashlib.sha256(f.read_bytes()).hexdigest()
    ents.append(SimpleNamespace(id=eid,program_path=str(f.relative_to(tmp)),program_sha256=sha,valid=val,key=key,family="F1",round=i,lean=None))
    tab[f.name]={"program_sha256":sha,"angle_set_sha256":RB.angle_set_sha256(),"skeleton_equal":True,"t_eps":[rk[1]//20]*20,"depth_ct":[rk[3]//20]*20,
      "t_sum":rk[1],"depth_sum":rk[3],"t_mean":rk[1]/20,"cx":key[0],"qubits":key[3],"angle_linear":rk[2]==0,"export_status":"ok","robust_key":rk}
valid=[e for e in ents if e.valid]
best=min(valid,key=lambda e:tuple(e.key))
A.Archive.load=classmethod(lambda cls,*a,**k: SimpleNamespace(entries=lambda: list(ents),best=lambda: best))
RB.robust_metrics=lambda e,k,p,root=None: dict(tab[pathlib.Path(p).name])
h=RB.headline(enc,kind,root=tmp)
print("ranking",[r["id"] for r in h["ranking"]],"headline",h["id"],"archive_best",h["archive_best"])
assert [r["id"] for r in h["ranking"]]==["rD","rA","rC","rB"], "CX 40: T 19000 < 20000"
assert h["id"]=="rD" and h["archive_best"]=="rA" and "rI" not in [r["id"] for r in h["ranking"]]
rows_=RB.report_rows(enc,kind,root=tmp,h=h)
for r in rows_: print(r)
print("OK toy ranking")

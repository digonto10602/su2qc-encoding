import sys,time,pathlib,json
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.compress import report as RP
root=pathlib.Path("/home/digimonk/Projects/su2qc-encoding/scratch/t419/rootrep")
enc,kind=sys.argv[1:3]
rf=root/"results/compress"/enc/"robust.json"
print("robust.json exists before:",rf.exists(), "mtime", rf.stat().st_mtime if rf.exists() else None)
t=time.time()
txt=RP.report_table(enc,kind,root=root)
print(f"report_table seconds {time.time()-t:.1f}")
print("robust.json mtime after", rf.stat().st_mtime if rf.exists() else None)
i=txt.find("### Headline"); print(txt[i:i+1500] if i>=0 else "NO HEADLINE TABLE")

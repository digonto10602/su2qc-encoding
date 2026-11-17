import sys,pathlib
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
from su2plaq.compress import brief as BR, robust as RB
from su2plaq.encodings import registry
root=pathlib.Path("/home/digimonk/Projects/su2qc-encoding/scratch/t419/rootrep")
first=RB.HEADLINE_RULE_SECTION.strip().splitlines()[0]
for enc,kind in [("twelve","step"),("spinnet","step"),("rishon","step"),("fuzzy_ub","UB"),("fuzzy_link","UE"),("lsh","step")]:
    try:
        p=BR.make_brief(enc,kind,9,"F1",root=root)
        t=p.read_text()
        n=t.count(first)
        sect=RB.HEADLINE_RULE_SECTION.strip() in t
        print(enc,kind,"brief",p.name,"headline heading count",n,"full paragraph present",sect,"len",len(t))
        # spinnet/rishon own sections?
        print("   other headline headings:",[l for l in t.splitlines() if l.startswith("## Headline")])
    except Exception as e:
        print(enc,kind,"ERR",type(e).__name__,str(e)[:200])

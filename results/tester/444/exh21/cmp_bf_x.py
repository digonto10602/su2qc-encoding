import subprocess, re, sys
def bf(q, LT):
    inp=f"{len(q)-1} "+" ".join(map(str,q))+"\n"
    r=subprocess.run(["./bf",str(LT),"lab_own.txt","-v"],input=inp,capture_output=True,text=True).stdout
    d={}
    for l in r.splitlines():
        m=re.match(r"FEAS walk#\d+ e0=\d used=(\d+) n:\d+ U=([0-9a-f]+)",l)
        if m: u=m.group(2).zfill(16); d[u]=min(d.get(u,99),int(m.group(1)))
    return d, r.splitlines()[-1]
def xx(q, LT):
    r=subprocess.run(["./x3",str(LT),"0","1",",".join(map(str,q))],capture_output=True,text=True,env={"PATH":"/usr/bin"}).stdout
    d={}
    for l in r.splitlines():
        m=re.match(r"FOUND m=\d+ k=\d+ used=(\d+) U=([0-9a-f]+)",l)
        if m: u=m.group(2).zfill(16); d[u]=min(d.get(u,99),int(m.group(1)))
    return d
walks={"W1":[0,16,20,21,5,13,29,25,27,19,3,7,23,22,30,14,15,11,9,8,0],
       "W6":[0,4,20,21,5,13,29,25,9,11,27,11,15,14,30,31,23,19,3,7,3,1,0],
       "W5":[0,16,20,21,5,13,29,25,27,19,3,7,23,31,30,14,15,31,27,11,9,8,0]}
for n,q in walks.items():
    for LT in range(len(q)-1, len(q)-1+(5 if len(q)-1==20 else 4)):
        b,_=bf(q,LT); x=xx(q,LT)
        print(n,"m",len(q)-1,"LT",LT,"bf feasible sets",len(b),"x feasible sets",len(x),"identical (U -> min cost)",b==x, flush=True)

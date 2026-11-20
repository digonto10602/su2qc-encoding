import numpy as np, itertools as it
from scipy.optimize import milp, LinearConstraint, Bounds
L=[l.split() for l in open('lab.txt').read().split('\n')[1:] if l.strip()]
lab=[int(a) for a,b in L]; g=np.array([float(b) for a,b in L])
chi=lambda x: np.array([(-1.0)**bin(l&x).count('1') for l in lab])
def pt(v,e): return (v&15)|(e<<4)|(((v>>4)&1)<<5)
def lifts(q):
    m=len(q)-1; ia=[i for i in range(m) if q[i]^q[i+1]==16]
    for e0 in (0,1):
        for ch in it.product((0,1),repeat=len(ia)):
            e=e0; pts=[pt(q[0],e)]; gens=[]; j=0
            for i in range(m):
                d=q[i]^q[i+1]
                if d==16:
                    if ch[j]: e^=1; gens.append('oB0')
                    else: gens.append('oA0')
                    j+=1
                else: gens.append({1:'p',2:'y1',4:'y2',8:'y3'}[d])
                pts.append(pt(q[i+1],e))
            yield e0,gens,pts
def feas(U):
    X=np.stack([chi(x) for x in sorted(U)],1); a=np.linalg.lstsq(X,g,rcond=None)[0]; return np.abs(X@a-g).max()<1e-9
def minsup(U,tl=60):
    U=sorted(U); n=len(U); X=np.stack([chi(x) for x in U],1); M=8
    c=np.concatenate([np.zeros(2*n),np.ones(n)]); I=np.eye(n); Z=np.zeros((n,n))
    cons=[LinearConstraint(np.hstack([X,-X,np.zeros((len(lab),n))]),g,g),
          LinearConstraint(np.vstack([np.hstack([I,Z,-M*I]),np.hstack([Z,I,-M*I])]),-np.inf,0)]
    r=milp(c,constraints=cons,integrality=np.concatenate([np.zeros(2*n),np.ones(n)]),bounds=Bounds(0,np.concatenate([np.full(2*n,M),np.ones(n)])),options={'time_limit':tl})
    a=r.x[:n]-r.x[n:2*n]; return {U[i]:a[i] for i in range(n) if abs(a[i])>1e-7}, r
import sys
q=[int(t) for t in sys.argv[1].split(',')]
for e0,gens,pts in lifts(q):
    U=set(pts)
    if feas(U):
        sol,r=minsup(U)
        print('start e',e0,'end pt',pts[-1],'|U|',len(U),'minsup',len(sol),'status',r.status, 'gens',' '.join(gens))
        print('  coefs',{k:round(v,4) for k,v in sol.items()})

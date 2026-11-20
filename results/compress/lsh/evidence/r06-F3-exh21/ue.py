import itertools as it, numpy as np
codes=[(0,0,0),(0,0,1),(0,1,0),(1,0,0),(1,1,0)]  # (vp,nv,pn)
S=[]
for cs in it.product(codes,repeat=4):
    ok=all((cs[c][2]^cs[c][1])==(cs[(c+1)%4][2]^cs[(c+1)%4][0]) for c in range(4))
    if ok: S.append(cs)
print(len(S))
# data bits order: d[3c]=pn, d[3c+1]=nv, d[3c+2]=vp
X=np.array([[ (cs[c][2],cs[c][1],cs[c][0])[k] for c in range(4) for k in range(3)] for cs in S])
f=np.array([sum(cs[c][2]+cs[c][1] for c in range(4)) for cs in S],float)
masks=range(1,4096)
chars={}
for m in masks:
    v=tuple((-1)**((X@np.array([(m>>i)&1 for i in range(12)]))%2))
    chars.setdefault(v,m)
V=np.array(list(chars.keys()),float); M=list(chars.values()); print('distinct chars',len(V))
one=np.ones(len(S))
# pairs: f in span{1,a,b}?
best=None
A=V
import sys
n=len(V)
for i in range(n):
    for j in range(i+1,n):
        B=np.stack([one,A[i],A[j]],1); c=np.linalg.lstsq(B,f,rcond=None)[0]
        if np.abs(B@c-f).max()<1e-9: print('pair',M[i],M[j],c); best=1
print('pairs done',best)

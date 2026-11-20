import itertools as it, numpy as np
codes=[(0,0,0),(0,0,1),(0,1,0),(1,0,0),(1,1,0)]  # (vp,nv,pn)
S=[cs for cs in it.product(codes,repeat=4) if all((cs[c][2]^cs[c][1])==(cs[(c+1)%4][2]^cs[(c+1)%4][0]) for c in range(4))]
print(len(S))
X=np.array([[ (cs[c][2],cs[c][1],cs[c][0])[k] for c in range(4) for k in range(3)] for cs in S])
f=np.array([sum(cs[c][2]+cs[c][1] for c in range(4)) for cs in S],float)
P=np.array([[(m>>i)&1 for i in range(12)] for m in range(4096)])
CH=(-1.0)**((X@P.T)%2)   # 47 x 4096
_,idx=np.unique(CH.T,axis=0,return_index=True); idx=sorted(idx); V=CH[:,idx]; print('distinct',V.shape[1])
# remove constant
nc=[k for k in range(V.shape[1]) if not np.all(V[:,k]==1)]; V=V[:,nc]; M=[idx[k] for k in nc]
# center: work in complement of constant
Vc=V-V.mean(0); fc=f-f.mean()
n=Vc.shape[1]
# triples: f_c in span of 3 centered chars. For each pair (i,j): residual of fc after projecting on span(i,j); then need some k with Vc_k residual parallel
G=Vc.T@Vc
found=0
for i in range(n):
  for j in range(i+1,n):
    B=Vc[:,[i,j]]
    Q,_=np.linalg.qr(B)
    r=fc-Q@(Q.T@fc)
    if np.linalg.norm(r)<1e-9: print('PAIR',M[i],M[j]); found+=1; continue
    R=Vc-Q@(Q.T@Vc)      # 47 x n
    nr=np.linalg.norm(R,axis=0); ok=nr>1e-9
    cosv=np.abs(r@R)/(np.linalg.norm(r)*np.where(ok,nr,1))
    hit=np.nonzero(ok & (cosv>1-1e-12))[0]
    for k in hit:
      if k>j: print('TRIPLE',M[i],M[j],M[k]); found+=1
  if found>20: break
print('found',found)

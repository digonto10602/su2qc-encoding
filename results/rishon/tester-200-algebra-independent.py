# Independent check: own construction using Pauli-string JW from scratch (qubit k <- tensor via explicit index ops), compare to production.
import sys, json, itertools
sys.path.insert(0, "/home/digonto/Projects/su2qc-rishon/src")
import numpy as np
from su2plaq.rishon import algebra as A

# --- independent JW via bit manipulation (no kron): c_k |n> = (-1)^{popcount(n & (2^k-1))} |n ^ 2^k> if bit k set
def c_bits(k, n):
    D = 1 << n
    M = np.zeros((D, D), complex)
    for s in range(D):
        if (s >> k) & 1:
            sign = (-1) ** bin(s & ((1 << k) - 1)).count("1")
            M[s ^ (1 << k), s] = sign
    return M
sig = [np.array([[0,1],[1,0]],complex), np.array([[0,-1j],[1j,0]]), np.diag([1,-1]).astype(complex)]
T = [s/2 for s in sig]
res = {}
c = [c_bits(k,4) for k in range(4)]; cd=[m.conj().T for m in c]
I=np.eye(16)
res["car_max"] = max(
  max(np.abs(c[k]@cd[l]+cd[l]@c[k]-(I if k==l else 0)).max() for k in range(4) for l in range(4)),
  max(np.abs(c[k]@c[l]+c[l]@c[k]).max() for k in range(4) for l in range(4)))
U = [[c[i]@cd[2+j] for j in range(2)] for i in range(2)]
L = [sum(T[a][i,j]*cd[i]@c[j] for i in range(2) for j in range(2)) for a in range(3)]
R = [sum(T[a][i,j]*cd[2+i]@c[2+j] for i in range(2) for j in range(2)) for a in range(3)]
N = sum(cd[k]@c[k] for k in range(4)); Tb = sum(cd[k]@c[k] for k in (2,3)) - sum(cd[k]@c[k] for k in (0,1))
com=lambda a,b:a@b-b@a
m1=m2=m3=m4=m5=0
for a in range(3):
    for i in range(2):
        for j in range(2):
            m1=max(m1,np.abs(com(L[a],U[i][j]) + sum(T[a][i,k]*U[k][j] for k in range(2))).max())
            m2=max(m2,np.abs(com(R[a],U[i][j]) - sum(U[i][k]*T[a][k,j] for k in range(2))).max())
for i,j,k,l in itertools.product(range(2),repeat=4): m3=max(m3,np.abs(com(U[i][j],U[k][l])).max())
for i,j in itertools.product(range(2),repeat=2):
    m4=max(m4,np.abs(com(N,U[i][j])).max(), np.abs(com(Tb,U[i][j])-2*U[i][j]).max())
eps={(0,1,2):1,(1,2,0):1,(2,0,1):1,(0,2,1):-1,(2,1,0):-1,(1,0,2):-1}
for a,b in itertools.product(range(3),repeat=2):
    for X in (L,R):
        m5=max(m5,np.abs(com(X[a],X[b])-sum(1j*eps.get((a,b,cc),0)*X[cc] for cc in range(3))).max())
    m5=max(m5,np.abs(com(L[a],R[b])).max())
res.update(BCW_L_U=m1,BCW_R_U=m2,UU=m3,N_Tb=m4,su2su2=m5)
# sector & casimir
nd=np.rint(np.diag(N).real).astype(int); sec=np.flatnonzero(nd==2)
res["sector_dim"]=len(sec); res["sector"]=sec.tolist()
cas=np.diag(sum(l@l for l in L)).real[sec]; res["casimir"]=cas.tolist()
# sector invariance and decomposition: diagonalise Casimir on the sector, multiplicities
Cs = sum(l@l for l in L)[np.ix_(sec,sec)]
ev=np.round(np.linalg.eigvalsh(Cs),12); res["casimir_eig_sector"]=ev.tolist()
# j=1/2 quartet: dimension = 2j+1 left x 2 right= 4;  singlets 2
res["n_singlets"]=int((np.abs(ev)<1e-10).sum()); res["n_quartet"]=int((np.abs(ev-0.75)<1e-10).sum())
# production vs mine
lk=A.RishonLink()
dev=0
for k in range(4): dev=max(dev,np.abs(lk.c[k]-c[k]).max(),np.abs(lk.cdag[k]-cd[k]).max())
for a in range(3): dev=max(dev,np.abs(lk.L[a]-L[a]).max(),np.abs(lk.R[a]-R[a]).max())
for i in range(2):
    for j in range(2): dev=max(dev,np.abs(lk.U(i,j)-U[i][j]).max())
res["prod_vs_indep_max"]=dev
# string-freeness: link bilinears on n links with global JW vs 4-qubit local op kron'd
import scipy.sparse as sp
def c_sp(k,n):
    D=1<<n; s=np.arange(D); has=((s>>k)&1)==1; src=s[has]
    sign=1-2*(np.array([bin(int(x)&((1<<k)-1)).count("1") for x in src])%2)
    return sp.csr_matrix((sign.astype(complex),(src^(1<<k),src)),shape=(D,D))
def embed(M16, link, nl):
    out=sp.identity(1,format="csr",dtype=complex)
    for l in range(nl):
        out=sp.kron(sp.csr_matrix(M16) if l==link else sp.identity(16,dtype=complex,format="csr"),out,format="csr")
    return out
sf={}
for nl in (2,3):
    n=4*nl; ct=[c_sp(k,n) for k in range(n)]
    worst=0
    for link in range(nl):
        b=4*link
        for k in range(4):
            for l in range(4):
                for gl,lo in ((ct[b+k]@ct[b+l].conj().T, c[k]@cd[l]),(ct[b+k].conj().T@ct[b+l], cd[k]@c[l])):
                    worst=max(worst,abs(gl-embed(lo,link,nl)).max())
                if link==0 and nl==2:
                    worst=max(worst,np.abs(A.global_bilinear(k,l,n)-embed(c[k]@cd[l],0,nl).toarray()).max())
    sf[f"{n}_modes"]=worst
res["string_free_max"]=sf
# note global_bilinear(k,l,n) acts on modes k,l=0..3 -> only link 0
res["string_free_max"]=sf
# end generators
for end in "LR":
    G=[A.RishonLink().end_generator(a,end) for a in range(3)]
    c2=[c_bits(k,2) for k in range(2)]
    ref=[sum(T[a][i,j]*c2[i].conj().T@c2[j] for i in range(2) for j in range(2)) for a in range(3)]
    res[f"end_gen_{end}"]=max(np.abs(G[a]-ref[a]).max() for a in range(3))
    # compare with 16x16 L (on link qubits 0,1) / R (qubits 2,3)
    Lm = L if end=="L" else R
    q0 = 0 if end=="L" else 2
    emb=[]
    for a in range(3):
        ops=[np.eye(2)]*4; 
        # kron 4x4 on qubits q0,q0+1
        m=np.eye(1)
        mats=[]
        if end=="L": full=np.kron(np.eye(4),G[a])
        else: full=np.kron(G[a],np.eye(4))
        emb.append(full)
    res[f"end_gen_embed_{end}"]=max(np.abs(emb[a]-Lm[a]).max() for a in range(3))
# det U
D=U[0][0]@U[1][1]-U[0][1]@U[1][0]
res["detU_vs_2cLcRcLcR"]=np.abs(D-2*c[0]@cd[2]@c[1]@cd[3]).max()
Ds=D[np.ix_(sec,sec)]; ex=np.zeros((6,6)); ex[5,0]=2
res["detU_sector"]=np.abs(Ds-ex).max()
print(json.dumps(res,indent=1,default=float))
json.dump(res,open("/tmp/claude-1000/-home-digonto-Projects-su2qc-desktop-package/fbcc8d73-b256-4509-96f5-20b02443a448/scratchpad/indep.json","w"),default=float)

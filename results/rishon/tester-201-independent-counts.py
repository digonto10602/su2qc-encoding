"""Tester 201: independent counts of the rishon physical space (no su2plaq imports).
Route H: Haar integral over SU(2)^4 x U(1)^4 of the product of link characters (exact uniform-grid quadrature).
Route K: brute-force 8-qubit corner (own JW) Gauss kernels, summed over end-occupation assignments.
Geometry is derived from the link coordinates of docs/METHODS.md Sec. 1."""
import itertools, json, subprocess, sys
import numpy as np

LINKS = [("b",(0,0),(1,0),1),("r",(1,0),(1,1),1),("t",(0,1),(1,1),1),("l",(0,0),(0,1),1),
         ("o0",(-1,0),(0,0),0),("o1",(0,-1),(0,0),0),("o2",(1,0),(2,0),0),("o3",(1,-1),(1,0),0),
         ("o4",(1,1),(2,1),0),("o5",(1,1),(1,2),0),("o6",(-1,1),(0,1),0),("o7",(0,1),(0,2),0)]
SITES = [(0,0),(1,0),(1,1),(0,1)]
cidx = {s:i for i,s in enumerate(SITES)}
# per link: (corner at start or None, corner at end or None)
LK = [(cidx.get(s), cidx.get(e), inner) for _,s,e,inner in LINKS]
inner = [i for i,l in enumerate(LK) if l[2]]
outer = [i for i,l in enumerate(LK) if not l[2]]
for i in inner: assert LK[i][0] is not None and LK[i][1] is not None
for i in outer: assert (LK[i][0] is None) != (LK[i][1] is None)
# corner -> ends (link, side) side 'L' = start, 'R' = end ; order: inner links first then outer (any order is fine for counts)
CORN = [[] for _ in range(4)]
for i,(cs,ce,inn) in enumerate(LK):
    if cs is not None: CORN[cs].append((i,'L'))
    if ce is not None: CORN[ce].append((i,'R'))
assert all(len(c)==4 for c in CORN)

# ---------------- Route H
def route_H(N=16, Nz=9):
    th = 2*np.pi*np.arange(N)/N
    w1 = 2*np.sin(th)**2/N                      # Haar weight on class functions, normalised to 1
    assert abs(w1.sum()-1)<1e-12
    chi = 2*np.cos(th)
    idx = np.array(list(itertools.product(range(N),repeat=4)))   # [N^4,4]
    W = np.prod(w1[idx],axis=1)
    X = chi[idx]                                  # [N^4,4]
    phi = 2*np.pi*np.arange(Nz)/Nz
    z = np.exp(1j*phi)                            # [Nz]
    # F[s,p0,p1,p2,p3]
    def zc(c,p):  # shape broadcast over 4 z axes
        sh=[1,1,1,1,1]; sh[1+c]=Nz
        return (z**p).reshape(sh)
    def chic(c):
        return X[:,c].reshape(-1,1,1,1,1)
    tot = None; closed=None
    Fall = np.ones((len(W),Nz,Nz,Nz,Nz),dtype=complex)
    Fclosed = np.ones_like(Fall)
    for i,(cs,ce,inn) in enumerate(LK):
        if inn:
            f = zc(cs,2) + zc(ce,2) + zc(cs,1)*zc(ce,1)*chic(cs)*chic(ce)
            Fall = Fall*f; Fclosed = Fclosed*f
        else:
            c = cs if cs is not None else ce
            Fall = Fall*(1+zc(c,2)+zc(c,1)*chic(c))
            Fclosed = Fclosed*(1+zc(c,2)+0*chic(c))   # near end empty or full (singlets)
    wsh = W.reshape(-1,1,1,1,1)
    P = (wsh*Fall).sum(axis=0)                      # polynomial values on z-grid
    Pc = (wsh*Fclosed).sum(axis=0)
    coef = np.fft.fftn(P)/Nz**4                     # coefficient of z^k : sum_p P(z_p) z_p^{-k}/Nz^4 = fftn
    coefc = np.fft.fftn(Pc)/Nz**4
    assert np.abs(coef.imag).max()<1e-6 and np.abs(coef.real-np.rint(coef.real)).max()<1e-6, np.abs(coef.real-np.rint(coef.real)).max()
    C = np.rint(coef.real).astype(np.int64)
    Cc = np.rint(coefc.real).astype(np.int64)
    return dict(dim=int(C.sum()), closed=int(Cc.sum()), n_u1_sectors=int((C>0).sum()), u2_sector=int(C[4,4,4,4]),
                max_int_dev=float(np.abs(coef.real-np.rint(coef.real)).max()), neg=int((C<0).sum()))

# ---------------- Route K : own JW, 8-qubit corner
I2=np.eye(2,dtype=complex); Zm=np.diag([1,-1]).astype(complex); SM=np.array([[0,1],[0,0]],complex)
SIG=[np.array([[0,1],[1,0]],complex),np.array([[0,-1j],[1j,0]]),np.array([[1,0],[0,-1]],complex)]
def kron_le(ops):
    out=np.eye(1,dtype=complex)
    for o in ops: out=np.kron(o,out)           # ops[0] = qubit 0 = least significant
    return out
def jw(k,n): return kron_le([Zm]*k+[SM]+[I2]*(n-k-1))
def end_gens(nq=8):
    c=[jw(k,nq) for k in range(nq)]; cd=[m.conj().T for m in c]
    G=[[sum(0.5*SIG[a][i,j]*(cd[2*e+i]@c[2*e+j]) for i in range(2) for j in range(2)) for e in range(4)] for a in range(3)]
    n=[sum(cd[2*e+i]@c[2*e+i] for i in range(2)) for e in range(4)]
    return G,n
def route_K():
    G,n = end_gens(8)
    # locality check: end e generator equals the same 4x4 on qubits (2e,2e+1)
    M4 = [G[a][0][np.ix_(range(4),range(4))] for a in range(3)]
    for a in range(3):
        for e in range(4):
            ops=[I2]*8
            Mfull = np.kron(np.kron(np.eye(4**(3-e)), M4[a]), np.eye(4**e))
            assert np.abs(Mfull-G[a][e]).max()<1e-13, (a,e)
    Gt=[sum(G[a][e] for e in range(4)) for a in range(3)]
    C=sum(g@g for g in Gt)
    occ=np.stack([np.rint(np.diag(n[e]).real).astype(int) for e in range(4)],axis=1)   # [256,4]
    kdim={}
    for nt in itertools.product(range(3),repeat=4):
        sel=np.flatnonzero(np.all(occ==np.array(nt),axis=1))
        sub=C[np.ix_(sel,sel)]
        assert np.abs(sub-sub.conj().T).max()<1e-12
        # C must preserve occupancy sectors
        w=np.linalg.eigvalsh(sub)
        kdim[nt]=int(np.sum(w<1e-9))
        # gap check: smallest nonzero eigenvalue
        nz=w[w>=1e-9]
        assert len(nz)==0 or nz.min()>0.2
    leak=0.0
    for nt in itertools.product(range(3),repeat=4):
        sel=np.flatnonzero(np.all(occ==np.array(nt),axis=1)); rest=np.flatnonzero(~np.all(occ==np.array(nt),axis=1))
        leak=max(leak,np.abs(C[np.ix_(sel,rest)]).max())
    # global sum: occupation of each link's near end/L end n in {0,1,2}; inner: L=n, R=2-n; outer: near=n
    tot=closed=u2=pats=0; sect=set()
    for ns in itertools.product(range(3),repeat=12):
        wgt=1; Q=[]
        for c in range(4):
            nt=[]
            for (l,side) in CORN[c]:
                inn=LK[l][2]
                if inn: nt.append(ns[l] if side=='L' else 2-ns[l])
                else: nt.append(ns[l])
            nt=tuple(nt)
            # kernel table is indexed by end order e=0..3 in the order of CORN[c]; occupancy of end e is given: the 8-qubit
            # corner ends are all equivalent (same 4x4 form), so the order is irrelevant for the dimension: use a canonical sort
            wgt*=kdim[tuple(sorted(nt))] if False else kdim[nt]
            Q.append(sum(nt))
            if wgt==0: break
        if wgt==0: continue
        pats+=1; tot+=wgt; sect.add(tuple(Q))
        if all(ns[l]!=1 for l in outer): closed+=wgt
        if all(q==4 for q in Q): u2+=wgt
    return dict(dim=tot,closed=closed,n_u1_sectors=len(sect),u2_sector=u2,type_patterns=pats,casimir_occupancy_leak=float(leak),
                kernel_dim_nonzero=sum(1 for v in kdim.values() if v>0))
if __name__=="__main__":
    out={"commit":subprocess.check_output(["git","rev-parse","--short","HEAD"],text=True).strip(),
         "route_H":route_H(), "route_K":route_K()}
    print(json.dumps(out,indent=1))
    json.dump(out,open("results/rishon/tester-201-independent-counts.json","w"),indent=1)

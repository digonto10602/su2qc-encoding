import sys, json, math
sys.path.insert(0,'/home/digimonk/Projects/su2qc-encoding/src')
import numpy as np, mpmath
from su2plaq.metrics.cliffordt import pygridsynth_word, pygridsynth_tcount
from pygridsynth.gridsynth import gridsynth_gates
H=np.array([[1,1],[1,-1]])/np.sqrt(2); S=np.diag([1,1j]); T=np.diag([1,np.exp(1j*np.pi/4)]); X=np.array([[0,1],[1,0]]); W=np.exp(1j*np.pi/4)*np.eye(2)
M=dict(H=H,S=S,T=T,X=X,W=W)
def mat(w):
    U=np.eye(2,dtype=complex)
    for c in w: U=U@M[c]
    return U
def dist(A,B):
    # min over phase of spectral norm: exact via 2x2: scan + refine
    ov=np.trace(B.conj().T@A); ph=ov/abs(ov)
    best=np.linalg.norm(A-ph*B,2)
    # brute-force check on phase grid to confirm optimum
    phs=np.exp(1j*np.linspace(-np.pi,np.pi,20001))
    # use closed form vals: A-phB is normal-ish? just evaluate grid around ph
    a0=np.angle(ph); g=a0+np.linspace(-1e-3,1e-3,2001)
    vals=[np.linalg.norm(A-np.exp(1j*x)*B,2) for x in g[::20]]
    return best, min(vals)
rng=np.random.default_rng(20261104)
thetas=[float(x) for x in rng.uniform(-math.pi,math.pi,24)]
epss=[1e-4,1e-6,1e-8,1e-10]
res={}
bad=0
for eps in epss:
    Ts=[];offs=[];errs=[];fails=0;same=0
    for th in thetas:
        w=pygridsynth_word(th,eps)
        w2=str(gridsynth_gates(theta=mpmath.mpf(repr(th)),epsilon=mpmath.mpf(repr(eps))))
        same+= (w==w2)
        A=mat(w); B=np.diag([np.exp(-0.5j*th),np.exp(0.5j*th)])
        d,dmin=dist(A,B)
        unit=np.linalg.norm(A.conj().T@A-np.eye(2))
        Tn=w.count("T"); Ts.append(Tn); offs.append(Tn-3*math.log2(1/eps)); errs.append(d)
        if d>eps or dmin<d-1e-13*0 and False: fails+=1
        if d>eps: fails+=1
        # word must be in Clifford+T alphabet
        assert set(w)<=set("HSTXW")
    res[eps]={"T_mean":float(np.mean(Ts)),"T_min":min(Ts),"T_max":max(Ts),"3log2":3*math.log2(1/eps),
      "off_mean":float(np.mean(offs)),"off_min":float(min(offs)),"off_max":float(max(offs)),
      "err_max":float(max(errs)),"err_over_eps_max":float(max(errs)/eps),"fails":fails,"word_same_as_direct":same,
      "digonto_formula_T_minus_?":None,"digonto_3ln_eps":3*math.log(eps), "Ts":Ts}
    bad+=fails
    print(f"eps={eps:g}: T mean {np.mean(Ts):.2f} min {min(Ts)} max {max(Ts)} | 3log2(1/eps)={3*math.log2(1/eps):.2f} | offset mean {np.mean(offs):.2f} [{min(offs):.2f},{max(offs):.2f}] | max err {max(errs):.2e} (<=eps? {max(errs)<=eps}) | 3ln(eps)={3*math.log(eps):.2f} | words equal direct call {same}/24")
print("word error failures:",bad)
json.dump({"thetas":thetas,"res":{str(k):v for k,v in res.items()},"seed":20261104},open("t2.json","w"))

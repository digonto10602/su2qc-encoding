import sys, json, itertools, math
import numpy as np
from functools import lru_cache
from sympy import Rational as R
from sympy.physics.wigner import clebsch_gordan, wigner_6j
sys.path.insert(0,"/home/digimonk/Projects/su2qc-encoding/src")
def rat(x): return R(int(round(2*x)),2)
@lru_cache(maxsize=None)
def cg(j1,j2,j3,m1,m2,m3): return float(clebsch_gordan(rat(j1),rat(j2),rat(j3),rat(m1),rat(m2),rat(m3)))
def ms(j): return [j-k for k in range(int(round(2*j))+1)]
def tri(a,b,c):
    a2,b2,c2=(int(round(2*x)) for x in (a,b,c)); return abs(a2-b2)<=c2<=a2+b2 and (a2+b2+c2)%2==0
def E(j,jp):
    """E^a: V_j -> V_j', <j' m+a|E^a|j m> = <j m 1/2 a|j' m+a>. returns dict a-> matrix (dim jp x dim j)"""
    out={}
    for a in (.5,-.5):
        M=np.zeros((len(ms(jp)),len(ms(j))))
        for im,m in enumerate(ms(j)):
            mp=m+a
            if abs(mp)<=jp+1e-9:
                M[ms(jp).index(mp) if mp in ms(jp) else [abs(x-mp)<1e-9 for x in ms(jp)].index(True), im]=cg(j,.5,jp,m,a,mp)
        out[a]=M
    return out
def corner_op(jl,jb,jlp,jbp):
    El,Eb=E(jl,jlp),E(jb,jbp)
    return sum((-1)**int(round(.5-a))*np.kron(El[a],Eb[-a]) for a in (.5,-.5))   # l (x) b -> l' (x) b'
def spin_ops(j):
    m=ms(j); d=len(m); Jz=np.diag(m); Jp=np.zeros((d,d))
    for i,mm in enumerate(m):
        if i>0: Jp[i-1,i]=math.sqrt(j*(j+1)-mm*(mm+1))
    return Jz,Jp
def two(j1,j2):
    z1,p1=spin_ops(j1);z2,p2=spin_ops(j2);I1=np.eye(len(z1));I2=np.eye(len(z2))
    return np.kron(z1,I2)+np.kron(I1,z2), np.kron(p1,I2)+np.kron(I1,p2)
# scalar check
for (jl,jb,jlp,jbp) in [(0,0,.5,.5),(.5,.5,0,0),(.5,0,0,.5),(.5,.5,1,0),(.5,.5,1,1)]:
    C=corner_op(jl,jb,jlp,jbp); zi,pi_=two(jl,jb); zo,po=two(jlp,jbp)
    print("scalar check",(jl,jb,jlp,jbp),np.abs(C@zi-zo@C).max(),np.abs(C@pi_-po@C).max(), "max|C|",np.abs(C).max())
def tensor_pair(j1,j2,j3,j4,pairing,J):
    """4-leg singlet T[m1,m2,m3,m4] for legs (1,2,3,4)=(l,b,o1,o2). pairing 1: (12)J (34)J ; pairing 2: (13)J (24)J"""
    sh=[len(ms(j)) for j in (j1,j2,j3,j4)]; T=np.zeros(sh)
    for M in ms(J):
        for i,(a,b,c,d) in enumerate(itertools.product(*[ms(j) for j in (j1,j2,j3,j4)])): pass
    for ia,a in enumerate(ms(j1)):
     for ib,b in enumerate(ms(j2)):
      for ic,c in enumerate(ms(j3)):
       for id_,d in enumerate(ms(j4)):
        s=0.0
        for M in ms(J):
            if pairing==1:
                s+=cg(j1,j2,J,a,b,M)*cg(j3,j4,J,c,d,-M)*(-1)**int(round(J-M))
            else:
                s+=cg(j1,j3,J,a,c,M)*cg(j2,j4,J,b,d,-M)*(-1)**int(round(J-M))
        T[ia,ib,ic,id_]=s/math.sqrt(2*J+1)
    return T
def admissible_J(j1,j2,j3,j4,pairing):
    if pairing==1: return [J/2 for J in range(0,5) if tri(j1,j2,J/2) and tri(j3,j4,J/2)]
    return [J/2 for J in range(0,5) if tri(j1,j3,J/2) and tri(j2,j4,J/2)]
def amp(jl,jb,jlp,jbp,o1,o2,pairing):
    C=corner_op(jl,jb,jlp,jbp)
    dl,db,d1,d2=[len(ms(j)) for j in (jl,jb,o1,o2)]
    res={}
    for J in admissible_J(jl,jb,o1,o2,pairing):
        T=tensor_pair(jl,jb,o1,o2,pairing,J); assert abs(np.linalg.norm(T)-1)<1e-12,(np.linalg.norm(T))
        v=T.reshape(dl*db,d1*d2)
        w=C@v  # (dlp*dbp) x (d1 d2)
        W=w.reshape(len(ms(jlp)),len(ms(jbp)),d1,d2)
        for Jp in admissible_J(jlp,jbp,o1,o2,pairing):
            Tp=tensor_pair(jlp,jbp,o1,o2,pairing,Jp)
            res[(J,Jp)]=float(np.sum(Tp*W))
        # leakage out of singlet space of final = norm check
        tot=sum(res[(J,Jp)]**2 for Jp in admissible_J(jlp,jbp,o1,o2,pairing) if (J,Jp) in res)
        res[("norm2",J)]=(float(np.sum(W*W)),tot)
    return res
out={"pairing1":[],"pairing2":[]}
# formula-side numbers: |amp| vs sqrt(2jl'+1)sqrt(2jb'+1)*|6j|
def six(a,b,c,d,e,f): return float(wigner_6j(rat(a),rat(b),rat(c),rat(d),rat(e),rat(f)))
print("=== pairing 1 (l b | o1 o2): J-diagonal, o-independent? and equals sqrt((2jl'+1)(2jb'+1)) |6j| ===")
rows=[]
for (jl,jb,jlp,jbp) in [(0,0,.5,.5),(.5,.5,0,0),(.5,0,0,.5),(0,.5,.5,0),(.5,.5,.5,.5-1) ,(.5,.5,1,0),(.5,.5,1,1),(.5,.5,0,1)]:
    if min(jlp,jbp)<0: continue
    for o1,o2 in itertools.product((0,.5,1),repeat=2):
        if not (admissible_J(jl,jb,o1,o2,1) and admissible_J(jlp,jbp,o1,o2,1)): continue
        r=amp(jl,jb,jlp,jbp,o1,o2,1)
        for (J,Jp),v in r.items():
            if J=="norm2": continue
            if abs(v)>1e-12 or J==Jp:
                # formula: pair (p,n)=(l,b): amp ~ <jl'||E||jl><jb'||E||jb> {J jb' jl'; 1/2 jl jb}
                f=six(J,jbp,jlp,.5,jl,jb)*math.sqrt((2*jlp+1)*(2*jbp+1))
                rows.append(((jl,jb,jlp,jbp),(o1,o2),J,Jp,v,f))
byk={}
for (inn,o,J,Jp,v,f) in rows: byk.setdefault((inn,J,Jp),[]).append((o,v,f))
maxdev=0;maxdiff=0;Joff=0
for k,lst in byk.items():
    vals=[v for _,v,_ in lst]; fs=[f for _,_,f in lst]
    spread=max(vals)-min(vals); maxdev=max(maxdev,spread)
    mag=max(abs(abs(v)-abs(f)) for _,v,f in lst); maxdiff=max(maxdiff,mag)
    if k[1]!=k[2] and any(abs(v)>1e-12 for v in vals): Joff=max(Joff,max(abs(v) for v in vals))
    print(k,[(o,round(v,6)) for o,v,_ in lst][:6],"| formula |.|",round(abs(fs[0]),6))
print("pairing1: max spread over outer spins =",maxdev,"  max||amp|-|formula||=",maxdiff,"  J-off-diagonal max =",Joff)
out["pairing1"]={"max_spread_over_outer":maxdev,"max_abs_diff_vs_formula":maxdiff,"J_offdiag":Joff,"n_entries":len(rows)}
print("=== pairing 2 (l o1 | b o2) ===")
rows2=[]
for (jl,jb,jlp,jbp) in [(0,0,.5,.5),(.5,.5,0,0),(.5,0,0,.5),(0,.5,.5,0),(.5,.5,1,0),(.5,.5,1,1),(.5,.5,0,1)]:
    for o1,o2 in itertools.product((0,.5,1),repeat=2):
        if not (admissible_J(jl,jb,o1,o2,2) and admissible_J(jlp,jbp,o1,o2,2)): continue
        r=amp(jl,jb,jlp,jbp,o1,o2,2)
        for (K,Kp),v in r.items():
            if K=="norm2": continue
            rows2.append(((jl,jb,jlp,jbp),(o1,o2),K,Kp,v))
by2={}
for (inn,o,K,Kp,v) in rows2: by2.setdefault((inn,K,Kp),[]).append((o,v))
n_dep=0; examples=[]
for k,lst in by2.items():
    if len(lst)>1:
        vals=[abs(v) for _,v in lst]
        if max(vals)-min(vals)>1e-9: n_dep+=1; examples.append((k,lst))
print("pairing2: label triples (inner transition,K,K') realised with >=2 outer pairs:",sum(1 for l in by2.values() if len(l)>1),"; with o-dependent |amp|:",n_dep)
for k,lst in examples[:6]: print("  ",k,[(o,round(v,6)) for o,v in lst])
out["pairing2"]={"triples_multi_outer":sum(1 for l in by2.values() if len(l)>1),"n_o_dependent":n_dep,"examples":[(str(k),[(str(o),v) for o,v in l]) for k,l in examples[:8]]}
# restrict to jmax=1/2 outer/inner-physical examples
print("--- same, with outer spins restricted to {0,1/2} and inner in {0,1/2} (truncated physical labels) ---")
by2t={}
for (inn,o,K,Kp,v) in rows2:
    if max(o)<=.5 and max(inn)<=.5: by2t.setdefault((inn,K,Kp),[]).append((o,v))
for k,lst in by2t.items():
    print("  ",k,[(o,round(v,6)) for o,v in lst])
json.dump(out,open("/tmp/claude-1000/-home-digimonk-Projects-su2qc-encoding/6f24cad7-b2eb-5b02-89d1-34310bbf63e6/scratchpad/out2.json","w"),indent=1,default=str)

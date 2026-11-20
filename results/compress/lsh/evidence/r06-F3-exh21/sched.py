# usage: sched.py <q5walk> ; picks the feasible lift with min support, orients it to start at e (16) and end at 0,
# prints START_C and WALK (rotation at first visit of each support point)
import sys
from fractions import Fraction
sys.argv=[sys.argv[0],sys.argv[1]]
exec(open('mk.py').read().split('import sys')[0])
q=[int(t) for t in sys.argv[1].split(',')]
best=None
for e0,gens,pts in lifts(q):
    if feas(set(pts)):
        sol,r=minsup(set(pts))
        if best is None or len(sol)<len(best[2]): best=(gens,pts,sol)
gens,pts,sol=best
G={'p':1,'y1':2,'y2':4,'y3':8,'oA0':32,'oB0':48}
if pts[0]!=16: gens=gens[::-1]; pts=pts[::-1]
assert pts[0]==16 and pts[-1]==0, (pts[0],pts[-1])
done=set(); out=[]
def co(x): return Fraction(round(sol[x]*8),8)
st=co(16) if 16 in sol else Fraction(0); done.add(16)
x=16
for g in gens:
    x^=G[g]; c=Fraction(0)
    if x in sol and x not in done: c=co(x); done.add(x)
    out.append((g,c))
assert done>=set(sol)
print('nsupport',len(sol)); print('START_C =',repr(st)); print('WALK =',out)

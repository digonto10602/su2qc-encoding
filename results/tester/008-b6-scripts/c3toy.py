import sys, math; sys.path.insert(0,"src")
from qiskit import QuantumCircuit
from su2plaq.compress import robust as RB
pairs=[*RB.ANGLE_SET,(0.37,0.61)]
def mk(fn):
    out=[]
    for a,b in pairs:
        q=QuantumCircuit(2); fn(q,a,b); out.append(q)
    return out
cases={
 "linear (a, -b/2, 3a-b)": lambda q,a,b:(q.rz(a,0),q.rz(-b/2,1),q.cx(0,1),q.rz(3*a-b,1)),
 "zero angle only": lambda q,a,b:(q.rz(0.0,0),q.h(1)),
 "shift pi/2": lambda q,a,b:q.rz(a+math.pi/2,0),
 "shift pi/4": lambda q,a,b:q.p(b+math.pi/4,0),
 "shift 1e-8 (tiny)": lambda q,a,b:q.rz(a+1e-8,0),
 "shift 1e-10 (below tol)": lambda q,a,b:q.rz(a+1e-10,0),
 "pure const pi/2": lambda q,a,b:q.rz(math.pi/2,0),
 "a*b": lambda q,a,b:q.rz(a*b,0),
 "linear but wrong at nominal": lambda q,a,b:q.rz(a+(0.1 if (a,b)==pairs[-1] else 0),0),
}
for k,f in cases.items():
    print(f"{k:32s}", RB.generic_angle_linear(mk(f),pairs))

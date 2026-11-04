"""Lookahead DAG scheduling: among ready branching gates pick the one whose closing partner (next H on the
same qubit) has the smallest number of *not yet executed branching gates* in its dependency cone."""
import sys, time, math, numpy as np
from qiskit import qasm3
QASM = "/home/digimonk/Projects/su2qc-paulo-code/SU2_plaquette_12qubit_encoding/SU2_plaquette_jmax_half_CT.qasm"
qc = qasm3.load(QASM); n = qc.num_qubits
qi = {q: i for i, q in enumerate(qc.qubits)}
gates = [(inst.operation.name, tuple(qi[q] for q in inst.qubits)) for inst in qc.data]
BRANCH = {"h"}

def schedule(gates, n):
    G = len(gates); succ = [[] for _ in range(G)]; pred = [[] for _ in range(G)]; last = [None]*n
    for g, (name, qs) in enumerate(gates):
        for q in qs:
            if last[q] is not None: succ[last[q]].append(g); pred[g].append(last[q])
            last[q] = g
    # next branching gate on the same qubit after g (for branching g)
    nxt = [None]*G; lastb = [None]*n
    for g in reversed(range(G)):
        name, qs = gates[g]
        if name in BRANCH:
            nxt[g] = lastb[qs[0]]; lastb[qs[0]] = g
    done = [False]*G; indeg = [len(pred[g]) for g in range(G)]
    ready = set(g for g in range(G) if indeg[g] == 0); order = []
    def cone_cost(target):
        # number of unexecuted branching gates in the dependency cone of `target` (excluding target)
        seen = set(); stack = [target]; cost = 0
        while stack:
            g = stack.pop()
            for p in pred[g]:
                if not done[p] and p not in seen:
                    seen.add(p); stack.append(p)
                    if gates[p][0] in BRANCH: cost += 1
        return cost
    while ready:
        nb = [g for g in ready if gates[g][0] not in BRANCH]
        if nb:
            g = min(nb)
        else:
            best = None
            for g in ready:
                c = cone_cost(nxt[g]) if nxt[g] is not None else 10**6
                if best is None or c < best[0]: best = (c, g)
            g = best[1]
        ready.discard(g); done[g] = True; order.append(g)
        for s in succ[g]:
            indeg[s] -= 1
            if indeg[s] == 0: ready.add(s)
    assert len(order) == G
    return [gates[g] for g in order]

t0 = time.time(); sched = schedule(gates, n); print(f"scheduling {time.time()-t0:.1f}s")
openq = set(); peak = 0
for name, qs in sched:
    if name == "h":
        q = qs[0]; openq.symmetric_difference_update({q})
    peak = max(peak, len(openq))
print("scheduled order: peak open H qubits =", peak)
PH = {"s": 1j, "sdg": -1j, "t": np.exp(1j*math.pi/4), "tdg": np.exp(-1j*math.pi/4)}
R2 = 1/math.sqrt(2)
def run(gs, inputs):
    keys = np.array(inputs, np.int64); cols = np.arange(len(inputs), dtype=np.int64); amps = np.ones(len(inputs), complex); pk = 0
    for name, qs in gs:
        if name == "cx":
            mc, mt = 1<<qs[0], 1<<qs[1]; keys = np.where(keys & mc != 0, keys ^ mt, keys)
        elif name in PH:
            m = 1<<qs[0]; amps = np.where(keys & m != 0, amps*PH[name], amps)
        elif name == "x": keys ^= (1<<qs[0])
        elif name == "h":
            m = 1<<qs[0]; b = (keys & m) != 0
            keys = np.concatenate([keys & ~m, keys | m]); cols = np.concatenate([cols, cols]); amps = np.concatenate([amps*R2, np.where(b, -amps*R2, amps*R2)])
            comb = keys*1024 + cols; u, inv = np.unique(comb, return_inverse=True); a = np.zeros(len(u), complex); np.add.at(a, inv, amps)
            keep = np.abs(a) > 1e-14; u, a = u[keep], a[keep]; keys, cols, amps = u//1024, u%1024, a
        pk = max(pk, len(keys))
    return keys, cols, amps, pk
t0 = time.time(); k, c, a, pk = run(sched, [0]); print(f"single input: peak {pk}, {time.time()-t0:.1f}s")
def code_of(p):
    if p == 0: return 0
    m, mp = {1: (1, 1), 2: (1, 0), 3: (0, 1), 4: (0, 0)}[p]
    return mp | (m << 1) | (1 << 2)
link_codes = [code_of(p) for p in range(5)]
codes = np.array([sum(link_codes[(idx // 5 ** l) % 5] << (3 * l) for l in range(4)) for idx in range(625)], dtype=np.int64)
t0 = time.time(); keys, cols, amps, pk = run(sched, codes); print(f"625 inputs: peak {pk}, {time.time()-t0:.1f}s, final {len(keys)}")
np.savez("/home/digimonk/Projects/su2qc-encoding/scratch/planner/paulo_out.npz", keys=keys, cols=cols, amps=amps, codes=codes)

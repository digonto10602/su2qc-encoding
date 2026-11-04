"""Physical-subspace dimensions for C1..C4 on the 2x2 torus via vertex intertwiner counting,
spin-network spectrum at jmax=1 (reference B), and Trotter error numbers at jmax=1/2."""
import itertools, time, sys
import numpy as np, scipy.sparse as sp, scipy.linalg as la
sys.path.insert(0, "/home/digimonk/Projects/su2qc-encoding/scratch/planner")
from proto_m1 import *

lat = Torus2x2()

def vertex_dim(legs_j):
    """dimension of the SU(2) singlet space of a product of spins"""
    # count via character: iterate coupling
    mult = {0.0: 1}
    for j in legs_j:
        new = {}
        for J, c in mult.items():
            for K in np.arange(abs(J - j), J + j + 1e-9, 1.0):
                new[float(K)] = new.get(float(K), 0) + c
        mult = new
    return mult.get(0.0, 0)

def count(jmax, sources=(), fermions=False):
    """sources: list of site tuples carrying a static spin-1/2; fermions: 2-colour staggered per site"""
    nl = len(lat.links)
    total = 0
    matter_opts = [(0.0, 1)]  # (spin, multiplicity of states with that spin)
    if fermions:
        matter_opts = [(0.0, 1), (0.5, 1), (0.0, 1)]  # n=0, n=1 (doublet), n=2 (singlet)
    for jconf in itertools.product(jvals(jmax), repeat=nl):
        base_legs = {s: [] for s in lat.sites}
        for i, l in enumerate(lat.links):
            st, en = lat.link_ends(l)
            base_legs[st].append(jconf[i]); base_legs[en].append(jconf[i])
        for s in sources:
            base_legs[s].append(0.5)
        if not fermions:
            d = 1
            for s in lat.sites:
                d *= vertex_dim(base_legs[s])
            total += d
        else:
            for mconf in itertools.product(matter_opts, repeat=len(lat.sites)):
                d = 1
                for s, (jm, _) in zip(lat.sites, mconf):
                    d *= vertex_dim(base_legs[s] + ([jm] if jm > 0 else []))
                total += d
    return total

if __name__ == "__main__":
    for jmax in (0.5, 1.0):
        print(f"jmax={jmax}: C1={count(jmax)}  C3adj={count(jmax, [(0,0),(1,0)])}  C3diag={count(jmax, [(0,0),(1,1)])}  "
              f"C3single={count(jmax, [(0,0)])}  C2={count(jmax, fermions=True)}  C4adj={count(jmax, [(0,0),(1,0)], True)}  C4diag={count(jmax, [(0,0),(1,1)], True)}")
    # B at jmax=1
    t0 = time.time(); B1 = build_B(lat, 1.0); print("B jmax=1 built in", time.time() - t0)
    e1 = spectrum(B1["H"]); print("B jmax=1 lowest 8:", e1[:8])
    np.save("/home/digimonk/Projects/su2qc-encoding/scratch/planner/eB_j1.npy", e1)
    # Trotter errors at jmax=1/2 (63-dim)
    B = build_B(lat, 0.5)
    H = B["H"].toarray(); HE = B["HE"].toarray(); P = [p.toarray() for p in B["plaq"]]
    for g2 in (1.0, 2.0):
        H = g2 / 2 * HE - 1 / (2 * g2) * sum(p + p.conj().T for p in P)
        Hh = (H + H.conj().T) / 2
        for dt in (0.2, 0.1, 0.05, 0.025):
            Uex = la.expm(-1j * Hh * dt)
            UE = la.expm(-1j * (g2 / 2) * HE * dt / 2)
            UP = [la.expm(1j / (2 * g2) * (p + p.conj().T) * dt) for p in P]
            U1 = la.expm(-1j * (g2 / 2) * HE * dt)
            for p in P: U1 = U1 @ la.expm(1j / (2 * g2) * (p + p.conj().T) * dt)
            U2 = UE
            for p in UP: U2 = U2 @ p
            # symmetric: E/2 P1 P2 P3 P4 P4 P3 P2 P1 E/2 with half angles
            UPh = [la.expm(1j / (2 * g2) * (p + p.conj().T) * dt / 2) for p in P]
            U2s = UE
            for p in UPh: U2s = U2s @ p
            for p in reversed(UPh): U2s = U2s @ p
            U2s = U2s @ UE
            err1 = la.norm(U1 - Uex, 2); err2 = la.norm(U2s - Uex, 2)
            print(f"g2={g2} dt={dt}: ||U1-Uex||={err1:.3e}  ||U2sym-Uex||={err2:.3e}  N(T=1)={1/dt:.0f} -> total err1={err1/dt:.3e} err2={err2/dt:.3e}")

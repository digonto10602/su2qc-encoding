"""Auditor 200: U(1) sector of the reference closed states; det-term effect on the closed sector (gamma != 0 probe)."""
import numpy as np
from scipy.linalg import expm
from su2plaq.rishon import physical as P, operators as O
b = P.rishon_basis()
ci = P.closed_indices(b)
print("closed refs (vac_A, vac_B, loop) labels:", [b.labels[k][0] for k in ci[:3]])
print("U(1) charges Q_c of vac_A, vac_B, loop:", [b.u1_charges(k) for k in ci[:3]])
qs = [b.u1_charges(k) for k in ci]
print("U(1) charges of the 17 closed refs:", sorted(set(qs)))
# gamma probe: H = HE + HB + gamma * D (inner det term), echo of vac_A after one 1st-order step with an extra det layer
HE = np.diag(O.h_electric_inner()); HB = O.h_magnetic_inner().real; D = O.det_term_inner().real
codes = O.inner_codes(); va, vb, _ = O.closed_codes(); i0 = int(np.searchsorted(codes, va))
alpha, beta = 0.37, 0.61
for gamma in (0.0, 0.1, 0.3):
    U = expm(-1j * gamma * D) @ expm(-1j * beta * HB) @ expm(-1j * alpha * HE)
    psi = U[:, i0]
    print(f"gamma*dt={gamma}: E_link={0.25*np.real(psi.conj()@HE@psi):.6f} echo={abs(psi[i0])**2:.6f} ||[D,HB]||={np.linalg.norm(D@HB-HB@D,2):.3f}")
ev = np.linalg.eigvalsh(0.5*HE*1.0 + HB/1.0 + 0.2*D)
print("g2=1, gamma=0.2: number of eigenvalues within 1e-9 of 0:", int(np.sum(abs(ev) < 1e-9)), "(gamma=0:", int(np.sum(abs(np.linalg.eigvalsh(0.5*HE+HB)) < 1e-9)), ")")

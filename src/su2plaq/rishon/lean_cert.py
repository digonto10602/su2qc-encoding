"""Three-angle Laurent certificates for rishon circuits (prompts/203 section 3.2).  STUBS (steps 6.L2-6.L4); `SCHEMA` and `recognise_angle` (step 6.4b, pure Python) are real."""
from __future__ import annotations

import math

import numpy as np

from su2plaq.rishon.compress._pending import pending

SCHEMA = "su2plaq-rishon-cert3-1"
_SQRT2 = math.sqrt(2.0)


class Laurent3:
    """dict[(m_alpha, m_beta, m_gamma)] -> su2plaq.lean.exact.KNum; arithmetic; evaluate(theta_alpha, theta_beta, theta_gamma); to_json()."""

    def __init__(self, *args, **kwargs):
        raise pending("lean_cert.Laurent3", "6.L2")


def recognise_angle(theta: float, alpha: float, beta: float, max_den: int = 64, tol: float = 1e-12):
    """(m_alpha, m_beta, m_gamma, d) with theta = (m_alpha alpha + m_beta beta + m_gamma sqrt2 beta)/d (the three-variable rule of
    prompts/203 section 2), d the smallest positive integer <= max_den that admits integer m (so gcd(m, d) = 1), |m| <= 64 d
    (|m| <= 128 when all of alpha, beta and sqrt2 beta are used); None if there is none.  Pure Python (no Lean).

    Search order: smallest d first; for each d the supports (a) alpha alone, (b) beta and sqrt2 beta (1 and sqrt2 are
    independent over Q, so the pair is unique), (c) alpha together with a nonzero sqrt2 beta part.  Inside a support the
    smallest sum |m| wins.  A combination of alpha and beta WITHOUT sqrt2 beta is deliberately not recognised: alpha and beta
    are both rational at the nominal pair (0.37, 0.61), so such a combination fits every decimal angle (0.123 =
    (5 alpha + beta)/20) and carries no information.  Angle 0 is (0, 0, 0, 1).  `tol` bounds |fit - theta| in radians."""
    theta, alpha, beta = float(theta), float(alpha), float(beta)
    if alpha <= 0.0 or beta <= 0.0 or max_den < 1:
        raise ValueError("recognise_angle needs alpha > 0, beta > 0 and max_den >= 1")
    gam = _SQRT2 * beta
    if abs(theta) <= tol:
        return (0, 0, 0, 1)
    for d in range(1, int(max_den) + 1):
        target, eps, bound = theta * d, tol * d, 64 * d
        m = int(np.rint(target / alpha))              # (a) alpha alone
        if m != 0 and abs(m) <= bound and abs(m * alpha - target) <= eps:
            return (m, 0, 0, d)
        mg = np.arange(-bound, bound + 1, dtype=np.int64)    # (b) beta and sqrt2 beta
        mb = np.rint((target - mg * gam) / beta)
        ok = (np.abs(mb * beta + mg * gam - target) <= eps) & (np.abs(mb) <= bound)
        if ok.any():
            cost = np.where(ok, np.abs(mb) + np.abs(mg), np.inf)
            i = int(np.argmin(cost))
            return (0, int(mb[i]), int(mg[i]), d)
        b3 = min(bound, 128)                          # (c) alpha with a nonzero sqrt2 beta part
        ma = np.arange(-b3, b3 + 1, dtype=np.int64)
        mgc = np.arange(-b3, b3 + 1, dtype=np.int64)
        MA, MG = np.meshgrid(ma, mgc, indexing="ij")
        MB = np.rint((target - MA * alpha - MG * gam) / beta)
        ok = (np.abs(MB * beta + MA * alpha + MG * gam - target) <= eps) & (np.abs(MB) <= b3) & (MA != 0) & (MG != 0)
        if ok.any():
            cost = np.where(ok, np.abs(MA) + np.abs(MB) + np.abs(MG), np.inf)
            i, j = np.unravel_index(int(np.argmin(cost)), cost.shape)
            return (int(MA[i, j]), int(MB[i, j]), int(MG[i, j]), d)
    return None


def export_raw_circuit(qc, out_path, *, alpha: float, beta: float):
    raise pending("lean_cert.export_raw_circuit", "6.L2")


def certify_circuit_kind(qc, kind: str, alpha: float, beta: float, order: int, out_dir=None, timeout: float = 900.0):
    raise pending("lean_cert.certify_circuit_kind", "6.L3")


def check_theorem_file(path, timeout: float = 1800.0) -> dict:
    raise pending("lean_cert.check_theorem_file", "6.L3")


def export_inner_certificate(qc, kind: str, alpha: float, beta: float, order: int, out_path, *, alt_angles=None):
    raise pending("lean_cert.export_inner_certificate", "6.L2")


def check_inner_certificate(path, timeout: float = 900.0):
    raise pending("lean_cert.check_inner_certificate", "6.L2")


def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0):
    raise pending("lean_cert.certify_circuit", "6.L3")


def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list:
    raise pending("lean_cert.checker_eval", "6.L2")


def write_theorem_file(cert_path, theorem_name: str, out_path):
    raise pending("lean_cert.write_theorem_file", "6.L3")

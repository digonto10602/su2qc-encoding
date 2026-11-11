"""Shared observables rishon vs Kogut-Susskind (prompts/200 §2.7; METHODS-rishon R5). `ks_closed_block` (5.3), the rest (5.5)."""
from __future__ import annotations

import numpy as np

import functools

from su2plaq.rishon import operators as _ops


def ks_closed_block(g2: float) -> np.ndarray:
    """KS closed-sector block in (vacuum, loop) at coupling g2 (METHODS §4): [[0, -2/g2], [-2/g2, 3 g2/2]].
    Independent of exact.operators (values quoted from the methods text)."""
    g2 = float(g2)
    return np.array([[0.0, -2.0 / g2], [-2.0 / g2, 1.5 * g2]], dtype=np.complex128)


def _group(ev: np.ndarray, tol: float = 1e-9) -> tuple[list[float], list[int]]:
    """Sorted eigenvalues -> (distinct values, multiplicities); neighbours within `tol` are one level (mean value)."""
    ev = np.sort(np.asarray(ev, dtype=float))
    vals: list[list[float]] = []
    for x in ev:
        if vals and abs(x - vals[-1][-1]) <= tol:
            vals[-1].append(float(x))
        else:
            vals.append([float(x)])
    return [float(np.mean(v)) for v in vals], [len(v) for v in vals]


def closed_spectra(g2_list=(0.5, 1.0, 2.0), lam_d: float = 0.0) -> dict:
    """Closed-sector spectra of H(g2).  Rishon: per outer singlet choice the 17 closed states (16 vacuum codes + loop) are diagonalised
    as the full block `operators.closed_block_full` (its 3x3 bright part is `operators.closed_block`; the 14 remaining levels
    are whatever the model gives, not typed in).  KS: the 2x2 block `ks_closed_block`.
    `lam_d` = lambda_D (METHODS-rishon R13): the rishon block gains lam_d H_D^in (KS has no det term); 0.0 is unchanged.
    -> {"rishon": {g2: {"eigenvalues", "multiplicities"}}, "ks": {...}}."""
    if lam_d != 0.0:
        raise NotImplementedError("PENDING: closed_spectra(lam_d != 0) (prompts/204 step D4)")
    out: dict = {"rishon": {}, "ks": {}}
    for g2 in g2_list:
        g2 = float(g2)
        ev = np.linalg.eigvalsh(_ops.closed_block_full(g2))
        vals, mult = _group(ev)
        out["rishon"][g2] = {"eigenvalues": vals, "multiplicities": mult}
        vals, mult = _group(np.linalg.eigvalsh(ks_closed_block(g2)))
        out["ks"][g2] = {"eigenvalues": vals, "multiplicities": mult}
    return out


@functools.lru_cache(maxsize=1)
def _ks_basis():
    from su2plaq.exact.physical import physical_basis

    return physical_basis(convention="cg")


@functools.lru_cache(maxsize=1)
def _ks_ops():
    """(basis, H_E inner diagonal, H_B on the physical basis, index of the KS vacuum) of the laptop's KS theory."""
    from su2plaq.exact.operators import h_electric_inner, h_magnetic_phys

    b = _ks_basis()
    HB, _ = h_magnetic_phys(b)
    vac = b.index(((0.0,) * 12, (0.0,) * 4))
    return b, h_electric_inner(b), HB, vac


def _evolve(U: np.ndarray, psi0: np.ndarray, n_steps: int) -> list[np.ndarray]:
    out, psi = [], psi0
    for _ in range(n_steps):
        psi = U @ psi
        out.append(psi)
    return out


def observables(alpha: float, beta: float, n_steps: int = 2, order: int = 1, eta: float | None = None) -> dict:
    """E_link(n) = <H_E^inner>/4, P(n) = -<H_B>/2, echo(n) = |<Omega|U_1^n|Omega>|^2 from the vacuum, n = 1..n_steps
    (METHODS-rishon R5).  Rishon: vac_A and the 1296-dim inner target; KS: the closed vacuum and the laptop's
    433-dim physical target.  -> {"rishon": {n: {...}}, "ks": {n: {...}}} (n integer keys).
    `eta` (prompts/204): the "rishon" rows use the three-layer step; "ks" rows unchanged.  Not built yet (step D4)."""
    if eta is not None:
        raise NotImplementedError("PENDING: observables(eta=...) (prompts/204 step D4)")
    out: dict = {"rishon": {}, "ks": {}}
    va, _, _ = _ops.closed_codes()
    codes = _ops.inner_codes()
    i0 = int(np.searchsorted(codes, va))
    psi0 = np.zeros(len(codes), dtype=np.complex128)
    psi0[i0] = 1.0
    HE = _ops.h_electric_inner()
    HB = _ops.h_magnetic_inner().real
    U = _ops.inner_target("step", alpha, beta, order)
    for n, psi in enumerate(_evolve(U, psi0, n_steps), start=1):
        p = np.abs(psi) ** 2
        out["rishon"][n] = {"E_link": float(0.25 * (p @ HE)), "P": float(-0.5 * np.real(np.conj(psi) @ (HB @ psi))),
                            "echo": float(abs(psi[i0]) ** 2)}
    from su2plaq.exact.operators import target

    b, HEk, HBk, k0 = _ks_ops()
    Uk = target(b, "step", alpha, beta, order)
    psi0 = np.zeros(b.dim, dtype=np.complex128)
    psi0[k0] = 1.0
    for n, psi in enumerate(_evolve(Uk, psi0, n_steps), start=1):
        p = np.abs(psi) ** 2
        out["ks"][n] = {"E_link": float(0.25 * (p @ HEk)), "P": float(-0.5 * np.real(np.conj(psi) @ (HBk @ psi))),
                        "echo": float(abs(psi[k0]) ** 2)}
    return out


def closed_forms(alpha, beta) -> dict:
    """n = 1 closed forms (R5): theta_KS = 2 beta, theta_R = 4 sqrt2 beta; E_link = 3/4 sin^2 theta_KS vs 3/8 sin^2 theta_R,
    echo = cos^2 theta_KS vs (1 + cos theta_R)^2 / 4; P(1) = 0 in both.  Independent of alpha (U_E|Omega> is a phase)."""
    tk, tr = 2.0 * beta, 4.0 * np.sqrt(2.0) * beta
    return {"ks": {"E_link": float(0.75 * np.sin(tk) ** 2), "P": 0.0, "echo": float(np.cos(tk) ** 2)},
            "rishon": {"E_link": float(0.375 * np.sin(tr) ** 2), "P": 0.0, "echo": float(0.25 * (1.0 + np.cos(tr)) ** 2)}}


def observables_table(angles=((0.37, 0.61), (0.91, 0.23), (1.70, 1.00))) -> dict:
    """The Report-5 table, JSON-able (string keys for n): {"angles", "rishon", "ks", "closed_forms", "closed_spectra",
    "definitions"}; "rishon"/"ks" are lists over the angle pairs of {"1": {...}, "2": {...}}."""
    tab: dict = {"angles": [list(map(float, a)) for a in angles], "rishon": [], "ks": [], "closed_forms": []}
    for a, b in angles:
        ob = observables(a, b, n_steps=2)
        for th in ("rishon", "ks"):
            tab[th].append({str(n): v for n, v in ob[th].items()})
        tab["closed_forms"].append(closed_forms(a, b))
    sp = closed_spectra()
    tab["closed_spectra"] = {"g2": [float(g) for g in sp["rishon"]],
                             "rishon": [sp["rishon"][g] for g in sp["rishon"]], "ks": [sp["ks"][g] for g in sp["ks"]]}
    tab["definitions"] = {
        "state": "n first-order steps U_1 = U_B(beta) U_E(alpha) from the vacuum (rishon vac_A, KS closed vacuum)",
        "E_link": "(1/4) <H_E^inner>", "P": "<Re Tr U_P> = -(1/2) <H_B>", "echo": "|<Omega|U_1^n|Omega>|^2",
        "theta_KS": "2 beta", "theta_R": "4 sqrt(2) beta"}
    return tab


def det_observables_table(triples=((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07)), lam_d_list=(0.0, 0.2, 0.5)) -> dict:
    """The JSON of results/rishon/observables_det.json (prompts/204 section 7, DT7).  STUB (prompts/204 step D4)."""
    raise NotImplementedError("PENDING: observables.det_observables_table (prompts/204 step D4)")

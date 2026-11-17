"""The KS j <= 1/2 link as a compression of the rishon and fuzzy links (prompts/009 §3.2, §5.2; docs/METHODS.md §13.2).

Our derivation (not from the literature).  For a normalised invariant state s of the model link and a unit phase c define the
isometry V (16 x 5, columns in the order of `LinkSpace(0.5).states`) by
    V|0> = s,    V sqrt2 U^KS_ab |0> = sqrt2 U_ab s / c.
Then V^dag V = 1, V^dag U_ab V = c U^KS_ab, V^dag L_a V = L^KS_a, V^dag R_a V = R^KS_a, V^dag H_E V = j(j+1), [VV^dag, L_a] =
[VV^dag, R_a] = 0, and (V^{(x)4})^dag W V^{(x)4} = W^KS.  The leak (1 - VV^dag) U V is NOT zero: that is the different physics.
Plaquette quantities are formed from 5 x 5 factors (never a 65536 x 625 array).
"""
from __future__ import annotations

import itertools

import numpy as np

LINK_MODELS = ("rishon_plus", "rishon_minus", "fuzzy_one", "fuzzy_gamma5", "fuzzy_fplus", "fuzzy_fminus")


def _check_model(model):
    if model not in LINK_MODELS:
        raise ValueError(f"unknown link model {model!r}; expected one of {LINK_MODELS}")


def _model_link_ops(model) -> dict:
    """Link operators (16 x 16) of the model taken from its own module: U[a][b], L[a], R[a], HE (the link electric energy)."""
    _check_model(model)
    if model.startswith("rishon"):
        from su2plaq.rishon.algebra import RishonLink

        rl = RishonLink()
        return {"U": [[rl.U(i, j) for j in range(2)] for i in range(2)], "L": list(rl.L), "R": list(rl.R),
                "HE": 0.5 * (rl.casimir_L + rl.casimir_R)}
    from su2plaq.fuzzy import link as fz

    return {"U": [[fz.U_op(a, b) for b in range(2)] for a in range(2)], "L": [fz.calT_L(A) for A in range(3)],
            "R": [fz.calT_R(A) for A in range(3)], "HE": 0.5 * fz.K1()}


def _singlet(model) -> np.ndarray:
    """The invariant state s (16-vector) of §3.2."""
    s = np.zeros(16, dtype=np.complex128)
    if model.startswith("rishon"):
        from su2plaq.rishon.algebra import CODE_A, CODE_B

        s[CODE_A] = 1.0 / np.sqrt(2.0)
        s[CODE_B] = (1.0 if model == "rishon_plus" else -1.0) / np.sqrt(2.0)
        return s
    G5 = np.diag([1.0, 1.0, -1.0, -1.0])
    M = {"fuzzy_one": 0.5 * np.eye(4), "fuzzy_gamma5": 0.5 * G5, "fuzzy_fplus": (np.eye(4) + G5) / (2.0 * np.sqrt(2.0)),
         "fuzzy_fminus": (np.eye(4) - G5) / (2.0 * np.sqrt(2.0))}[model]
    return M.reshape(16).astype(np.complex128)


def link_isometry(model) -> tuple[np.ndarray, complex]:
    """(V (16, 5), c) of §3.2; c = 1j for rishon_minus, 1 otherwise."""
    from su2plaq.su2.algebra import LinkSpace

    _check_model(model)
    ks = LinkSpace(0.5)
    UK = ks.U()
    ops = _model_link_ops(model)
    s = _singlet(model)
    e0 = np.zeros(5, dtype=np.complex128)
    e0[ks.index[(0.0, 0.0, 0.0)]] = 1.0
    c = 1j if model == "rishon_minus" else 1.0
    cols_model, cols_ks = [s], [e0]
    for a, b in itertools.product(range(2), repeat=2):
        cols_model.append(np.sqrt(2.0) * ops["U"][a][b] @ s / c)
        cols_ks.append(np.sqrt(2.0) * UK[a][b] @ e0)
    V = np.array(cols_model).T @ np.linalg.inv(np.array(cols_ks).T)
    return V.astype(np.complex128), complex(c)


def _kron4(ms):
    return np.kron(ms[3], np.kron(ms[2], np.kron(ms[1], ms[0])))          # links (b, r, t, l), b least significant


def compressed_plaquette(U, V) -> tuple[np.ndarray, np.ndarray]:
    """((V^{(x)4})^dag W V^{(x)4}, (W V^{(x)4})^dag (W V^{(x)4})), both 625 x 625, W = sum_{abce} U_b[a,b] U_r[b,c] U_t[e,c]^dag U_l[a,e]^dag
    (the contraction of exact.operators._build_W); only 5 x 5 factors are formed."""
    Vd = V.conj().T
    idx = list(itertools.product(range(2), repeat=4))

    def factors(a, b, c, e):
        return [U[a][b], U[b][c], U[e][c].conj().T, U[a][e].conj().T]          # links b, r, t, l

    Wc = np.zeros((625, 625), dtype=np.complex128)
    for t in idx:
        Wc += _kron4([Vd @ X @ V for X in factors(*t)])
    G = np.zeros((625, 625), dtype=np.complex128)
    for t in idx:
        Ft = factors(*t)
        for u in idx:
            G += _kron4([Vd @ Y.conj().T @ X @ V for X, Y in zip(factors(*u), Ft)])
    return Wc, G


def link_compression(model) -> dict:
    """{"phase": c, "isometry", "U", "L", "R", "HE", "P_commutes_generators", "plaquette": max-entry residuals, "leak_U": max_ab ||(1-P) U_ab V||_2,
    "leak_plaquette": ||(1-P4) W V4||_2}."""
    from su2plaq.exact.operators import plaquette_W
    from su2plaq.su2.algebra import LinkSpace

    ks = LinkSpace(0.5)
    UK = ks.U()
    LK, RK = ks.generators()
    CK = ks.casimir()
    ops = _model_link_ops(model)
    V, c = link_isometry(model)
    Vd = V.conj().T
    P = V @ Vd
    one = np.eye(16)
    res = {"phase": c,
           "isometry": float(np.abs(Vd @ V - np.eye(5)).max()),
           "U": max(float(np.abs(Vd @ ops["U"][a][b] @ V - c * UK[a][b]).max()) for a in range(2) for b in range(2)),
           "L": max(float(np.abs(Vd @ ops["L"][a] @ V - LK[a]).max()) for a in range(3)),
           "R": max(float(np.abs(Vd @ ops["R"][a] @ V - RK[a]).max()) for a in range(3)),
           "HE": float(np.abs(Vd @ ops["HE"] @ V - CK).max()),
           "P_commutes_generators": max(float(np.abs(P @ X - X @ P).max()) for X in [*ops["L"], *ops["R"]]),
           "leak_U": max(float(np.linalg.norm((one - P) @ ops["U"][a][b] @ V, 2)) for a in range(2) for b in range(2))}
    Wc, G = compressed_plaquette(ops["U"], V)
    res["plaquette"] = float(np.abs(Wc - plaquette_W(convention="cg")).max())
    res["leak_plaquette"] = float(np.sqrt(max(np.linalg.eigvalsh(G - Wc.conj().T @ Wc).max(), 0.0)))
    return res

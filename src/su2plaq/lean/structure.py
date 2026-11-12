"""Structure of the physics problem, proved / certified in Lean (prompts/006 §1 M5, §4, §5; docs/METHODS.md §11.3).

Python conjectures and computes, exactly; the Lean checker (`su2plaq_cert structure`) verifies.  The exact structure
certificate (`compress/lean/structure-cert.json`) carries the 433 exact states (CG convention, electric keys), the exact link
operators and generators, and the claimed decomposition; the checker recomputes

* orthonormality of the states, the covariance relations of U_ij with the generators (so the data is an SU(2) link space),
  the Gauss law at the four corners, the spins j_l and the inner-pair spins J_c of every state;
* H_B^phys = -(Psi^dag (W (x) 1) Psi + h.c.) from the exact states and U_ij, and that it equals D K_inner D (K_inner the
  47 x 47 exact inner matrix, D a +-1 gauge) inside every outer-spin block and 0 between blocks; J_c is conserved;
* K_inner = 8 bright 2x2 pairs + 31 dark rows;
* the spectrum multiplicities of H_B (exact ranks of H_B - lambda per block), the number of supported outer m-patterns and the
  maximum number of states sharing one;
* the components, edge moduli and spectrum of -(W + W^dag) on the 625 Paulo inner codes;
* the per-corner kernel dimensions of the Casimir and that they add up to the 433 states;
* every listed symmetry (signed label permutation commuting with H_B and with the inner electric energy).

Facts proved by `decide` are the kernel-checked counts of `Su2Plaq/Structure/Counts.lean`.  Nothing here is part of the
validity of a circuit.
"""
from __future__ import annotations

import collections
import functools
import itertools
import json
import pathlib
import subprocess
import time
from fractions import Fraction

import numpy as np

from su2plaq.lean import certify as C
from su2plaq.lean import exact as E
from su2plaq.lean import project as P
from su2plaq.lean.certify import LeanCert

ROOT = pathlib.Path(__file__).resolve().parents[3]
STRUCTURE_JSON = ROOT / "compress" / "lean" / "structure.json"
STRUCTURE_CERT = ROOT / "compress" / "lean" / "structure-cert.json"
SCHEMA = "su2plaq-structure-1"
LAMBDAS = (-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0)
_KZ = E.KNum(0)


def _z(x) -> E.KNum:
    return E.KNum.of(x)


# ---------------------------------------------------------------------------------------------------------------------
# exact spin / generator data
def _half_spin_exact():
    h = Fraction(1, 2)
    return [[[_z(0), _z(h)], [_z(h), _z(0)]],
            [[_z(0), E.KNum(0, -h)], [E.KNum(0, h), _z(0)]],
            [[_z(h), _z(0)], [_z(0), _z(-h)]]]


@functools.lru_cache(maxsize=1)
def exact_link_gens():
    """(L_a, R_a), a = x, y, z, as 5x5 KNum matrices on LinkSpace(0.5): L_a = -J_a^T on mL, R_a = J_a on mR (exact);
    cross-checked against `LinkSpace.generators()`."""
    from su2plaq.su2.algebra import LinkSpace, m_values

    ls = LinkSpace(0.5)
    J = {0.0: [[[_z(0)]] for _ in range(3)], 0.5: _half_spin_exact()}
    L = [[[_z(0) for _ in range(ls.dim)] for _ in range(ls.dim)] for _ in range(3)]
    R = [[[_z(0) for _ in range(ls.dim)] for _ in range(ls.dim)] for _ in range(3)]
    for j in ls.spins:
        mv = m_values(j)
        for a in range(3):
            Ja = J[j][a]
            n = len(mv)
            La = [[-Ja[c][r] for c in range(n)] for r in range(n)]          # -J^T
            for p, mL in enumerate(mv):
                for q, mLp in enumerate(mv):
                    for mR in mv:
                        i, k = ls.index[(j, mLp, mR)], ls.index[(j, mL, mR)]
                        L[a][i][k] = L[a][i][k] + La[q][p]
            for p, mR in enumerate(mv):
                for q, mRp in enumerate(mv):
                    for mL in mv:
                        i, k = ls.index[(j, mL, mRp)], ls.index[(j, mL, mR)]
                        R[a][i][k] = R[a][i][k] + Ja[q][p]
    Lf, Rf = ls.generators()
    for a in range(3):
        for i in range(ls.dim):
            for k in range(ls.dim):
                if (abs(L[a][i][k].to_complex() - Lf[a][i, k]) > E.CROSS_TOL
                        or abs(R[a][i][k].to_complex() - Rf[a][i, k]) > E.CROSS_TOL):
                    raise E.ExactError("exact link generators deviate from float")
    return L, R


def _paulo_adapter():
    from su2plaq.su2.algebra import paulo_adapter

    return paulo_adapter()


def _mat_json(M) -> list:
    return [[x.to_json() for x in row] for row in M]


# ---------------------------------------------------------------------------------------------------------------------
# data of the physical basis
@functools.lru_cache(maxsize=1)
def _data() -> dict:
    basis = E._exact_basis_cached("cg")
    H = E.exact_HB()
    labs = [b["label"] for b in basis]
    n = len(basis)
    inner = sorted({(l[0][:4], l[1]) for l in labs})
    idx = {x: i for i, x in enumerate(inner)}
    iota = [idx[(l[0][:4], l[1])] for l in labs]
    outer = [l[0][4:] for l in labs]
    # K_inner = |H| on edge instances; the gauge makes every edge positive
    K = {}
    gauge = [1] * n
    seen = [False] * n
    for (k, l), v in sorted(H.items()):
        if k == l:
            raise E.ExactError("H_B has a nonzero diagonal entry")
        if outer[k] != outer[l]:
            raise E.ExactError("H_B connects two outer-spin blocks")
        a, b = iota[k], iota[l]
        mod = v if _positive(v) else -v
        if (a, b) in K and K[(a, b)] != mod:
            raise E.ExactError("H_B is not a function of the inner labels inside an outer block")
        K[(a, b)] = mod
    for (k, l), v in sorted(H.items()):
        if k < l:
            if seen[l]:
                raise E.ExactError("H_B graph is not a matching: gauge propagation needs a tree")
            gauge[l] = gauge[k] * (1 if _positive(v) else -1)
            seen[l] = True
    k_inner = [[K.get((a, b), _KZ) for b in range(len(inner))] for a in range(len(inner))]
    for a in range(len(inner)):
        for b in range(len(inner)):
            if k_inner[a][b] != k_inner[b][a]:
                raise E.ExactError("K_inner is not symmetric")
    bright = [(a, b, k_inner[a][b]) for a in range(len(inner)) for b in range(a + 1, len(inner)) if not k_inner[a][b].is_zero()]
    rows_used = {x for a, b, _ in bright for x in (a, b)}
    dark = [a for a in range(len(inner)) if not any(not x.is_zero() for x in k_inner[a])]
    if len(rows_used) != 2 * len(bright) or set(dark) & rows_used or len(dark) + len(rows_used) != len(inner):
        raise E.ExactError("K_inner is not a matching plus dark rows")
    # spectrum multiplicities by exact traces of the spectral projectors
    spec = {lam: Fraction(0) for lam in E.SPECTRUM}
    for ks, proj in E._beta_blocks():
        for lam, Pm in proj.items():
            tr = E.KNum(0)
            for i in range(len(ks)):
                tr = tr + Pm[i][i]
            if not (tr.is_real() and not (tr.c or tr.e or tr.g)):
                raise E.ExactError("trace of a spectral projector is not rational")
            spec[lam] += tr.a
    spectrum = []
    for lam in E.SPECTRUM:
        m = spec[lam]
        if m.denominator != 1:
            raise E.ExactError("non-integer multiplicity")
        spectrum.append([float(lam), int(m)])
    return {"basis": basis, "H": H, "labels": labs, "inner": inner, "iota": iota, "outer": outer, "k_inner": k_inner,
            "gauge": gauge, "bright": bright, "dark": dark, "spectrum": spectrum}


def _positive(v: E.KNum) -> bool:
    """Sign of a real element of Q(sqrt2, sqrt3), decided by its float value (the components are small rationals)."""
    x = v.to_complex().real
    if abs(x) < 1e-9:
        raise E.ExactError("zero or tiny matrix element where a nonzero one was expected")
    return x > 0


# ---------------------------------------------------------------------------------------------------------------------
# the 625-code inner operator (Paulo basis)
def _modulus(v: E.KNum) -> str:
    """|v| as a rational string; raises unless v is +-(rational) (true for the edges of the inner operator)."""
    if v.b or v.c or v.d or v.e or v.f or v.g or v.h:
        raise E.ExactError("an edge of the inner operator is not rational")
    return E._fmt(abs(v.a))


@functools.lru_cache(maxsize=1)
def _inner625() -> dict:
    W = E.exact_plaquette_W_paulo()
    M: dict = {}
    for col, d in W.items():
        for row, v in d.items():
            for (i, j), val in (((row, col), -v), ((col, row), -v.conj())):
                M[(i, j)] = M[(i, j)] + val if (i, j) in M else val
    M = {t: v for t, v in M.items() if not v.is_zero()}
    for (i, j), v in M.items():
        if M.get((j, i)) != v.conj():
            raise E.ExactError("inner operator is not Hermitian")
    edges = sorted(t for t in M if t[0] < t[1])
    diag = [t for t in M if t[0] == t[1]]
    parent = list(range(625))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in edges:
        parent[find(i)] = find(j)
    comps = collections.defaultdict(list)
    for i in range(625):
        comps[find(i)].append(i)
    sizes = collections.Counter(len(c) for c in comps.values())
    mods = sorted({_modulus(M[t]) for t in edges})
    dense = np.zeros((625, 625), dtype=complex)
    for (i, j), v in M.items():
        dense[i, j] = v.to_complex()
    ev = np.linalg.eigvalsh(dense)
    spectrum = []
    for lam in LAMBDAS:
        spectrum.append([lam, int(np.sum(np.abs(ev - lam) < 1e-9))])
    if sum(m for _, m in spectrum) != 625:
        raise E.ExactError("inner operator has an eigenvalue outside {0, +-1/2, +-1, +-2}")
    return {"n_edges": len(edges), "n_diag": len(diag), "edge_moduli": mods,
            "component_sizes": sorted([s, c] for s, c in sizes.items()), "spectrum": spectrum}


# ---------------------------------------------------------------------------------------------------------------------
# corner kernel dimensions (float singlets give the claimed dimension; Lean recomputes them exactly)
def _corner_kernel_dims() -> list:
    from su2plaq.exact.physical import corner_singlets
    from su2plaq.geometry import plaquette_diagram

    d = plaquette_diagram()
    out = []
    for c in d.corners:
        roles = tuple(r for _, r in c.ends)
        for j2 in itertools.product((0, 1), repeat=4):
            vecs, _ = corner_singlets(tuple(x / 2 for x in j2), roles)
            out.append({"corner": c.index, "j2": list(j2), "dim": int(vecs.shape[1])})
    return out


def _outer_support() -> dict:
    basis = E._exact_basis_cached("cg")
    sup = collections.defaultdict(set)
    for k, b in enumerate(basis):
        for key in b["keys"]:
            sup[int(key) // 625].add(k)
    return {"n_keys": len(sup), "max_states": max(len(v) for v in sup.values())}


# ---------------------------------------------------------------------------------------------------------------------
# symmetries
_D4 = (("identity", lambda x, y: (x, y)), ("C4", lambda x, y: (1 - y, x)), ("C4^2", lambda x, y: (1 - x, 1 - y)),
       ("C4^3", lambda x, y: (y, 1 - x)), ("reflect_x", lambda x, y: (1 - x, y)), ("reflect_y", lambda x, y: (x, 1 - y)),
       ("reflect_diag", lambda x, y: (y, x)), ("reflect_antidiag", lambda x, y: (1 - y, 1 - x)))


def _site_maps():
    """For every D4 element: (link permutation, corner permutation) of the plaquette diagram (outer legs map to outer legs)."""
    from su2plaq.geometry import plaquette_diagram

    d = plaquette_diagram()
    by_ends = {frozenset((l.start, l.end)): l.index for l in d.links}
    corner_of_site = {c.site: c.index for c in d.corners}
    res = []
    for name, g in _D4:
        pl = [by_ends[frozenset((g(*l.start), g(*l.end)))] for l in d.links]
        pc = [corner_of_site[g(*c.site)] for c in d.corners]
        res.append((name, pl, pc))
    return res


def symmetry_candidates(basis=None) -> list[dict]:
    """The 16 candidates (D4 of the square, with its outer legs, x charge conjugation).  A geometric element permutes the link
    spins and the corner spins J_c of the state labels; charge conjugation m -> -m leaves the labels unchanged.  The signs of
    the signed label permutation are fixed by gauge alignment (solved exactly from H_B).  `commutes_HB` / `commutes_HE` say
    whether the signed permutation commutes with H_B and with the inner electric energy (exactly); `perm`/`signs` are
    filled for the commuting ones.  `residual` is the float64 maximum deviation of the commutators of the exact-valued
    matrices (0 up to rounding when both commute)."""
    dat = _data()
    labs, H = dat["labels"], dat["H"]
    n = len(labs)
    index = {l: k for k, l in enumerate(labs)}
    Hf = np.zeros((n, n))
    for (i, j), v in H.items():
        Hf[i, j] = v.to_complex().real
    e_in = np.array([sum(j * (j + 1) for j in l[0][:4]) for l in labs])
    out = []
    for gi, (gname, pl, pc) in enumerate(_site_maps()):
        for cc in (False, True):
            name = gname + ("*cc" if cc else "") if not (gname == "identity" and cc) else "cc"
            if gname == "identity" and not cc:
                name = "identity"
            cand = {"name": name, "geometry": gname, "charge_conjugation": cc, "commutes_HB": False, "commutes_HE": False,
                    "residual": float("inf"), "perm": [], "signs": []}
            perm = []
            for l in labs:
                j2 = [None] * 12
                J2 = [None] * 4
                for i in range(12):
                    j2[pl[i]] = l[0][i]
                for c in range(4):
                    J2[pc[c]] = l[1][c]
                perm.append(index.get((tuple(j2), tuple(J2))))
            if None in perm or sorted(perm) != list(range(n)):
                out.append(cand)
                continue
            # gauge alignment: s_k s_l = H[pk, pl] / H[k, l] on every edge
            signs = [0] * n
            ok = len(H) == sum(1 for (k, l) in H if (perm[k], perm[l]) in H)
            for (k, l), v in sorted(H.items()):
                w = H.get((perm[k], perm[l]))
                if w is None:
                    ok = False
                    break
                if w == v:
                    r = 1
                elif w == -v:
                    r = -1
                else:
                    ok = False
                    break
                if k < l:
                    if signs[k] == 0:
                        signs[k] = 1
                    if signs[l] != 0 and signs[l] != signs[k] * r:
                        ok = False
                        break
                    signs[l] = signs[k] * r
                elif k == l and r != 1:
                    ok = False
                    break
            if not ok:
                out.append(cand)
                continue
            signs = [s if s else 1 for s in signs]
            S = np.array(signs, dtype=float)
            pa = np.array(perm)
            res_hb = float(np.abs(Hf[np.ix_(pa, pa)] - np.outer(S, S) * Hf).max())
            res_he = float(np.abs(e_in[pa] - e_in).max())
            cand.update(commutes_HB=res_hb <= 1e-10, commutes_HE=res_he <= 1e-10, residual=max(res_hb, res_he))
            if cand["commutes_HB"] and cand["commutes_HE"]:
                cand["perm"] = perm
                cand["signs"] = signs
            cand["note"] = ("label-level action; charge conjugation fixes all labels, so its signed permutation coincides with the "
                            "geometric one after gauge alignment" if cc else "label-level action, gauge-aligned signs")
            out.append(cand)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the certificate
def export_structure_certificate(out_path) -> pathlib.Path:
    """Write the exact structure certificate (JSON, schema su2plaq-structure-1) read by `su2plaq_cert structure`."""
    from su2plaq.geometry import plaquette_diagram

    dat = _data()
    basis = dat["basis"]
    L, R = exact_link_gens()
    U = E.exact_link_U()
    d = plaquette_diagram()
    sym = [c for c in symmetry_candidates() if c["perm"]]
    cert = {
        "schema": SCHEMA,
        "corners": [[[link, 0 if role == "out" else 1] for link, role in c.ends] for c in d.corners],
        "spin_half": [_mat_json(m) for m in _half_spin_exact()],
        "gens": {"L": [_mat_json(m) for m in L], "R": [_mat_json(m) for m in R]},
        "u_link": [[_mat_json(U[a][b]) for b in range(2)] for a in range(2)],
        "u_paulo": [[_mat_json(E.exact_paulo_U()[a][b]) for b in range(2)] for a in range(2)],
        "states": [{"k": k, "terms": [{"code": int(key), "c": a.to_json()} for key, a in zip(b["keys"], b["amps"])]}
                   for k, b in enumerate(basis)],
        "labels": [{"j2": [int(round(2 * x)) for x in l[0]], "J2": [int(round(2 * x)) for x in l[1]]} for l in dat["labels"]],
        "inner_labels": [{"j2": [int(round(2 * x)) for x in j], "J2": [int(round(2 * x)) for x in J]} for j, J in dat["inner"]],
        "k_inner": [[x.to_json()[0] if x.is_zero() or x.to_json()[1:] == ["0"] * 7 else None for x in row]
                    for row in dat["k_inner"]],
        "v_paulo": [[int(x) for x in row] for row in _paulo_adapter()],
        "gauge": dat["gauge"],
        "bright_pairs": [{"pair": [a, b], "coupling": c.to_json()[0]} for a, b, c in dat["bright"]],
        "dark_rows": dat["dark"],
        "spectrum": dat["spectrum"],
        "outer_support": _outer_support(),
        "inner625": _inner625(),
        "corner_kernel_dims": _corner_kernel_dims(),
        "symmetries": [{"name": c["name"], "perm": c["perm"], "signs": c["signs"]} for c in sym],
        "provenance": {"git_commit": C._git_commit(), "exporter_sha256": C._exporter_sha()},
    }
    for row in cert["k_inner"]:
        if any(x is None for x in row):
            raise E.ExactError("K_inner has a non-rational entry")
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert, separators=(",", ":")))
    return out_path


def check_structure(path, timeout: float = 900.0) -> LeanCert:
    """`su2plaq_cert structure <path>`: ACCEPT -> certified, REJECT <reason> -> rejected, anything else -> failed."""
    t0 = time.time()
    try:
        sha = C.checker_sha256()
        r = C._run_checker(["structure", str(path)], timeout)
    except subprocess.TimeoutExpired:
        return LeanCert("failed", f"timeout after {timeout}s", str(path), time.time() - t0, "")
    except (RuntimeError, OSError) as exc:
        return LeanCert("failed", str(exc), str(path), time.time() - t0, "")
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    dt = time.time() - t0
    if line == "ACCEPT":
        return LeanCert("certified", "", str(path), dt, sha)
    if line.startswith("REJECT"):
        return LeanCert("rejected", line[len("REJECT"):].strip(), str(path), dt, sha)
    return LeanCert("failed", f"checker output {line!r} stderr {r.stderr.strip()[-300:]!r}", str(path), dt, sha)


# ---------------------------------------------------------------------------------------------------------------------
_COUNT_FACTS = (("card_physical", 433, "the Gauss-law subspace has 433 states"),
                ("card_link_patterns", 256, "link-spin patterns with at least one state"),
                ("card_two_or_more", 95, "link-spin patterns carrying at least two states"),
                ("card_closed", 2, "states with all outer spins 0"),
                ("far_end_weighted", 17362, "sum over states of prod over outer links (2j+1)"),
                ("card_supported_outer", 3153, "outer m-patterns carrying at least one state (NOT dim S_o)"),
                ("max_states_per_outer", 17, "maximum number of states with weight on one outer m-pattern (NOT dim S_o)"),
                ("dont_care_codes", 3471, "4^6 - 5^4 inner codes of the 12 qubits are not physical-link patterns"))


_CERT_STATUS: dict = {}


def _structure_certified() -> bool:
    """Export the structure certificate and run the compiled checker (cached per checker / exporter fingerprint)."""
    key = (C.checker_sha256(), C._exporter_sha())
    if key not in _CERT_STATUS:
        _CERT_STATUS[key] = check_structure(export_structure_certificate(STRUCTURE_CERT)).status == "certified"
    return _CERT_STATUS[key]


def structure_facts(certified: bool | None = None) -> dict:
    """{"facts": [{name, value, proved_by, theorem | certificate, note}], "symmetries": [...], "provenance": {...}}.
    proved_by is "decide" (kernel-checked count), "native" (the exact structure certificate was accepted by the compiled Lean
    checker; trust: compiler) or "numerical".  `certified=None` (default) exports and checks the structure certificate first
    (cached) -- a fact is never labelled native without a checker run; pass the outcome of an earlier run to avoid re-checking
    (`False` downgrades the native facts to numerical)."""
    dat = _data()
    if certified is None:                         # never label a fact native without running the checker
        certified = _structure_certified()
    native = "native" if certified else "numerical"
    cert_ref = "compress/lean/structure-cert.json (su2plaq_cert structure)"
    facts = []
    for name, value, note in _COUNT_FACTS:
        facts.append({"name": name, "value": value, "proved_by": "decide", "theorem": f"Su2Plaq.{name}", "note": note})
    inner = dat["inner"]
    sp = dat["spectrum"]
    facts.append({"name": "spectrum_multiplicities", "value": sp, "proved_by": native, "certificate": cert_ref,
                  "note": "[[lambda, multiplicity]] of H_B^phys on the 433 states, lambda in {0, +-1/2, +-1, +-2}"})
    facts.append({"name": "k_inner_bright_pairs", "value": [[a, b, float(c.to_complex().real)] for a, b, c in dat["bright"]],
                  "proved_by": native, "certificate": cert_ref,
                  "note": "H_B^phys = D K D inside every outer-spin block; K_inner (47 inner labels) pairs 16 'bright' labels "
                          "in 8 2x2 blocks [index, index, coupling]; indices into the sorted inner labels ((2j_b,2j_r,2j_t,2j_l),(2J_0..2J_3))"})
    facts.append({"name": "k_inner_dark_rows", "value": len(dat["dark"]), "proved_by": native, "certificate": cert_ref,
                  "note": "inner labels on which H_B^phys acts as zero (a corner with J=1 is annihilated)"})
    facts.append({"name": "dark_labels", "value": [[[int(round(2 * x)) for x in inner[a][0]], [int(round(2 * x)) for x in inner[a][1]]]
                                                    for a in dat["dark"]], "proved_by": native, "certificate": cert_ref,
                  "note": "the dark inner labels ((2j_b,2j_r,2j_t,2j_l),(2J_0..2J_3)): H_B^phys annihilates every state carrying one"})
    i6 = _inner625()
    facts.append({"name": "inner625_components",
                  "value": {"n_edges": i6["n_edges"], "edge_moduli": i6["edge_moduli"], "component_sizes": i6["component_sizes"],
                            "spectrum": i6["spectrum"]},
                  "proved_by": native, "certificate": cert_ref,
                  "note": "-(W + W^dag) on the 625 inner codes (Paulo basis): connected components [size, count], edge moduli, spectrum"})
    osup = _outer_support()
    facts.append({"name": "outer_support_table", "value": osup, "proved_by": native, "certificate": cert_ref,
                  "note": "recomputed from the exact states: number of outer m-patterns with support and the largest number of "
                          "states sharing one"})
    sym = [c for c in symmetry_candidates() if c["perm"]]
    return {"facts": facts,
            "symmetries": [{"name": c["name"], "perm": c["perm"], "signs": c["signs"]} for c in sym],
            "provenance": {"git_commit": C._git_commit(), "exporter_sha256": C._exporter_sha(),
                           "checker_sha256": C.checker_sha256() if (C.P.LEAN_DIR / ".lake").exists() else None,
                           "note": "decide = kernel-checked (standard axioms); native = compiled-checker trust; the numerical "
                                   "evaluator remains ground truth"}}


def _stable_part(doc: dict) -> dict:
    """The content of a structure.json that decides whether the file must be rewritten: facts, symmetries, provenance without
    the volatile `git_commit` and the checker `seconds` (prompts/008 step A2)."""
    prov = dict(doc.get("provenance", {}))
    prov.pop("git_commit", None)
    cert = dict(prov.get("structure_certificate", {}))
    cert.pop("seconds", None)
    prov["structure_certificate"] = cert
    return {"facts": doc.get("facts"), "symmetries": doc.get("symmetries"), "provenance": prov}


def write_structure_json(path=None) -> pathlib.Path:
    """compress/lean/structure.json: {"facts": [...], "symmetries": [...], "provenance": {...}}.  The exact structure certificate
    is exported and checked first; if it is not accepted the native facts are recorded as `numerical`.  An existing file whose
    content is unchanged (see `_stable_part`) is not rewritten, so `git status` stays empty."""
    path = pathlib.Path(path) if path is not None else STRUCTURE_JSON
    cert_path = export_structure_certificate(STRUCTURE_CERT)
    res = check_structure(cert_path)
    doc = structure_facts(certified=(res.status == "certified"))
    doc["provenance"]["structure_certificate"] = {"status": res.status, "reason": res.reason, "seconds": res.seconds}
    new = json.loads(json.dumps(doc, default=str))
    if path.exists():
        try:
            old = json.loads(path.read_text())
        except ValueError:
            old = None
        if old is not None and _stable_part(old) == _stable_part(new):
            return path                           # unchanged content: keep the file (and its git_commit / seconds) as first written
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(new, indent=1))
    return path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--export", action="store_true", help="write compress/lean/structure.json")
    ap.add_argument("--certificate", action="store_true", help="also (re)write compress/lean/structure-cert.json")
    args = ap.parse_args()
    if args.certificate:
        print(export_structure_certificate(STRUCTURE_CERT))
    if args.export:
        print(write_structure_json())

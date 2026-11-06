"""M9 step 9.7: write results/fuzzy/{UE,UK,UB,step,outer_row,shared_observables,splitting}.json (prompts/300 §2, §3 step 9.7).
Deterministic; every number is computed here.

    PYTHONPATH=src python scripts/m9_results.py [--out results/fuzzy] [--jobs 8]

For U_E, U_K, U_B and the step (order 1; order 2 in extra) at (alpha, beta) = (0.37, 0.61), r = 1 (kappa2 = 0.185): the exact-angle
circuit is verified (links and the plaquette row block as complete unitaries, the step by layer blocks + a sampled composition,
METHODS-fuzzy F6), its logical metrics and the T(eps) table at eps in {1e-4, 1e-6, 1e-8, 1e-10} are computed, and every synthesised
circuit is re-verified with synth_tolerances.  Extras: alternate angles (0.91, 0.23), (1.70, 1.00) and r = 0, the outer-link row
(8 outer U_E + 8 outer U_K blocks), the commuting-cluster product and Trotter order splitting errors, the shared observable table,
and a static summary of the fuzzy Lean files.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import pathlib
import re
import time

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from su2plaq.circuits import fuzzy as C  # noqa: E402
from su2plaq.evaluate.evaluator import synth_tolerances  # noqa: E402
from su2plaq.fuzzy import gauss as gz  # noqa: E402
from su2plaq.fuzzy import link as lk  # noqa: E402
from su2plaq.fuzzy import observables as ob  # noqa: E402
from su2plaq.fuzzy import plaquette as pq  # noqa: E402
from su2plaq.fuzzy import targets as tg  # noqa: E402
from su2plaq.fuzzy import verify as vf  # noqa: E402
from su2plaq.metrics.cliffordt import synthesize, t_table  # noqa: E402
from su2plaq.metrics.logical import logical_metrics  # noqa: E402
from su2plaq.metrics.provenance import provenance  # noqa: E402
from su2plaq.results.store import save_result, verdict_to_dict  # noqa: E402

ALPHA, BETA, R = 0.37, 0.61, 1.0
ALTS = ((0.91, 0.23), (1.70, 1.00))                      # alternate (alpha, beta), as in the locked M9 tests
EPS = (1e-4, 1e-6, 1e-8, 1e-10)
CLUSTER_BETAS = (0.61, 0.23, 1.0)
TOL_EXACT = 1e-10
N_RANDOM, N_PHYS, SAMPLE_SEED = 32, 8, 20261104
SEEDS = {"transpiler_logical": 20261104, "clifford_t_pass_manager": 12345, "step_samples": SAMPLE_SEED}
ROOT = pathlib.Path(__file__).resolve().parents[1]
SCOPE = {"UE": "full_unitary_link", "UK": "full_unitary_link", "UB": "full_unitary_row_block",
         "step": "blocks_certified_composition_sampled"}


# ---------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------
def _rel(p: pathlib.Path) -> str:
    p = p.resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _save_circuit(qc, out: pathlib.Path, name: str) -> dict:
    from qiskit import qasm3, qpy

    qpath = out / f"{name}.qpy"
    with open(qpath, "wb") as fh:
        qpy.dump(qc, fh)
    files = {"qpy": _rel(qpath), "sha256": hashlib.sha256(qpath.read_bytes()).hexdigest()}
    try:
        apath = out / f"{name}.qasm3"
        apath.write_text(qasm3.dumps(qc))
        files["qasm3"] = _rel(apath)
    except Exception as exc:  # export limitation of Qiskit, recorded not hidden
        files["qasm3"] = None
        files["qasm3_error"] = f"{type(exc).__name__}: {exc}"
    return files


def _phase_dist(U: np.ndarray, V: np.ndarray) -> float:
    """min over global phases of ||U - e^{i phi} V||_2."""
    tr = np.vdot(V, U)
    ph = tr / abs(tr) if abs(tr) > 1e-300 else 1.0
    return float(np.linalg.norm(U - ph * V, 2))


def _kinetic_layer_check(qc, V16: np.ndarray) -> dict:
    """The 16-qubit kinetic layer `build_UE/build_UK` (register 'd') must be the four 16x16 link blocks, no gate crossing two
    links; returns the worst block distance to V16 (global phase optimised per block)."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator

    blocks = [QuantumCircuit(4) for _ in range(4)]
    for inst in qc.data:
        qs = [qc.find_bit(q).index for q in inst.qubits]
        link = qs[0] // 4
        if link > 3 or any(q // 4 != link for q in qs):
            raise ValueError(f"gate {inst.operation.name} on {qs} is not inside one inner link")
        blocks[link].append(inst.operation, [q % 4 for q in qs])
    errs = [_phase_dist(Operator(b).data, np.asarray(V16, dtype=np.complex128)) for b in blocks]
    return {"n_blocks": 4, "block_errors": errs, "max_block_error": max(errs)}


def _step_verdict(res: dict, tol: float, seconds: float, method: str) -> dict:
    """Verification block of a step circuit from verify_step_samples: op_norm_error = err (= block error + ancilla leak amplitude)."""
    err, leak, g = float(res["err"]), float(res["leak"]), float(res["gauss"])
    ok = bool(err <= tol and g <= tol)
    return {"ok": ok, "reason": "ok" if ok else "tolerance", "op_norm_error": err, "max_leak": leak ** 2, "dirty_ancilla": leak ** 2,
            "phase": None, "outer_bits_read": 0, "n_blocks": None, "gauss_residual": g, "method": method, "engine": res["mode"],
            "engine_accuracy": None, "certified": False, "tolerances": {"tol_err": tol, "tol_gauss": tol},
            "dropped_total": 0.0, "block_error": max(err - leak, 0.0), "leak_amplitude": leak, "seconds": seconds,
            "n_inputs": int(res["n_inputs"]), "failing_inputs": [], "extra": {"scope": SCOPE["step"], "mode": res["mode"]}}


def synthesize_layered(qc, eps: float):
    """`synthesize` applied layer by layer (the instruction ranges of ``qc.metadata['layers']``) and re-assembled in circuit order,
    with the layer ranges of the result in ``metadata['layers']``.  The gate content equals ``synthesize(qc, eps)`` (the same word
    for every rotation angle; the global phase is the sum of the layers'); the layer metadata lets the step verification use the
    certified per-layer operators instead of a dense 23-qubit statevector run over ~1e4-1e5 gates."""
    from qiskit import QuantumCircuit

    layers = (qc.metadata or {}).get("layers")
    if not layers:
        raise ValueError("circuit has no layer metadata")
    if layers[0][1] != 0 or layers[-1][2] != len(qc.data) or any(layers[i][2] != layers[i + 1][1] for i in range(len(layers) - 1)):
        raise ValueError("layers do not tile the circuit")
    out = QuantumCircuit(*qc.qregs, global_phase=qc.global_phase)
    new_layers, tot = [], {"n_rot": 0, "t_rot": 0, "error_bound_sum": 0.0, "error_measured_sum": 0.0}
    for kind, a, b in layers:
        sub = QuantumCircuit(*qc.qregs)
        for inst in qc.data[a:b]:
            sub.append(inst.operation, [sub.qubits[qc.find_bit(q).index] for q in inst.qubits])
        ss, info = synthesize(sub, eps)
        i0 = len(out.data)
        out.compose(ss, inplace=True)
        new_layers.append((kind, i0, len(out.data)))
        for k in tot:
            tot[k] += info[k]
    out.metadata = {**qc.metadata, "layers": new_layers}
    return out, tot


def _logical(qc) -> dict:
    lm = logical_metrics(qc)
    return {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}


def _build(kind, alpha, beta, kappa2, order):
    if kind == "UE":
        return C.build_UE(alpha)
    if kind == "UK":
        return C.build_UK(kappa2)
    if kind == "UB":
        return C.build_UB(beta)
    return C.build_step(alpha, beta, kappa2=kappa2, order=order)


def _verify_any(kind, qc, alpha, beta, kappa2, order, tol, link_qc=None, n_random=N_RANDOM, n_phys=N_PHYS):
    """Verification block of circuit `qc` (a build_* circuit, exact or Clifford+T synthesised) -> dict.  Kinetic layers: the
    one-link circuit `link_qc` (default: the exact link circuit) as a complete 16x16 unitary + the check that the layer is four
    such blocks; plaquette: the complete 256x256 row block; step: layer blocks + sampled composition (F6)."""
    t0 = time.time()
    if kind in ("UE", "UK"):
        V = tg.UE_link(alpha) if kind == "UE" else tg.UK_link(kappa2)
        layer = _kinetic_layer_check(qc, V)
        if link_qc is None:
            link_qc = C.link_UE(alpha) if kind == "UE" else C.link_UK(kappa2)
        d = verdict_to_dict(vf.verify_link(link_qc, V, tol_err=tol))
        d["extra"] = {"scope": SCOPE[kind], "layer_blocks_max_error": layer["max_block_error"], "layer_n_blocks": 4}
        if layer["max_block_error"] > tol:
            d["ok"], d["reason"] = False, "layer_blocks"
        return d
    if kind == "UB":
        d = verdict_to_dict(vf.verify_plaquette(qc, tg.UB_row(beta), tol_err=tol))
        d["extra"]["scope"] = SCOPE["UB"]
        return d
    res = vf.verify_step_samples(qc, alpha, beta, kappa2, order, n_random=n_random, n_phys=n_phys, seed=SAMPLE_SEED)
    return _step_verdict(res, tol, time.time() - t0, SCOPE["step"])


def _verdict_light(d: dict) -> dict:
    """The fields of a verification block that are kept inside the T-table rows."""
    keep = ("ok", "reason", "op_norm_error", "block_error", "leak_amplitude", "max_leak", "dirty_ancilla", "gauss_residual",
            "method", "engine", "certified", "tolerances", "n_inputs", "seconds", "extra")
    return {k: d[k] for k in keep if k in d}


# ---------------------------------------------------------------------------------------------------------------------
# pooled tasks (top level so that they pickle)
# ---------------------------------------------------------------------------------------------------------------------
def _task_row(spec):
    """One T-table row (pygridsynth + Qiskit) with the re-verification of the circuit synthesised at that eps."""
    kind, alpha, beta, kappa2, order, eps = spec
    qc = _build(kind, alpha, beta, kappa2, order)
    row = t_table(qc, (eps,))[0]
    t0 = time.time()
    synth, info = synthesize_layered(qc, eps) if kind == "step" else synthesize(qc, eps)
    tol = synth_tolerances(info["n_rot"], eps)["tol_err"]
    link_synth = None
    if kind in ("UE", "UK"):
        link_synth, _ = synthesize(C.link_UE(alpha) if kind == "UE" else C.link_UK(kappa2), eps)
    v = _verify_any(kind, synth, alpha, beta, kappa2, order, tol, link_qc=link_synth, n_random=16, n_phys=4)
    row["synth"] = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
                    "error_measured_sum": info["error_measured_sum"], "verdict": _verdict_light(v), "seconds": time.time() - t0}
    return spec, row


def _task_exact(spec):
    kind, alpha, beta, kappa2, order = spec
    qc = _build(kind, alpha, beta, kappa2, order)
    t0 = time.time()
    v = _verify_any(kind, qc, alpha, beta, kappa2, order, TOL_EXACT)
    return spec, {"verification": v, "logical": _logical(qc), "seconds": time.time() - t0}


def _task_alternate(spec):
    """Exact-angle verification of all four kinds (step in both orders) at one parameter point."""
    alpha, beta, r = spec
    k2 = tg.kappa2_of(alpha, r)
    out = {"params": {"alpha": alpha, "beta": beta, "kappa2": k2, "r": r}}
    for name, kind, order in (("UE", "UE", 1), ("UK", "UK", 1), ("UB", "UB", 1), ("step_order1", "step", 1), ("step_order2", "step", 2)):
        if r == 0.0 and kind in ("UE", "UB"):
            continue                                       # unchanged by r
        _, res = _task_exact((kind, alpha, beta, k2, order))
        out[name] = {"verification": _verdict_light(res["verification"]), "logical": res["logical"], "seconds": res["seconds"]}
    return spec, out


# ---------------------------------------------------------------------------------------------------------------------
# outer row, splitting, Lean
# ---------------------------------------------------------------------------------------------------------------------
def _link_metrics(link_qc, V, eps_list=EPS) -> dict:
    lm = logical_metrics(link_qc)
    out = {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits")}
    out["ancilla"] = link_qc.num_qubits - 4
    rows = t_table(link_qc, eps_list)
    for row in rows:
        synth, info = synthesize(link_qc, row["eps"])
        tol = synth_tolerances(info["n_rot"], row["eps"])["tol_err"]
        row["synth"] = {"n_rot": info["n_rot"], "t_rot": info["t_rot"], "error_bound_sum": info["error_bound_sum"],
                        "verdict": _verdict_light(verdict_to_dict(vf.verify_link(synth, V, tol_err=tol)))}
    out["t_table"] = rows
    out["verification"] = _verdict_light(verdict_to_dict(vf.verify_link(link_qc, V, tol_err=TOL_EXACT)))
    return out


def outer_row_block(alpha=ALPHA, beta=BETA, kappa2=None) -> dict:
    """Content of outer_row.json without provenance: per-link U_E and U_K metrics and the totals over the 8 outer links."""
    kappa2 = tg.kappa2_of(alpha, R) if kappa2 is None else kappa2
    per = {"UE": _link_metrics(C.link_UE(alpha), tg.UE_link(alpha)), "UK": _link_metrics(C.link_UK(kappa2), tg.UK_link(kappa2))}
    n = 8
    totals = {"cx": n * (per["UE"]["cx"] + per["UK"]["cx"]), "n_rot": n * (per["UE"]["n_rot"] + per["UK"]["n_rot"]),
              "t_fixed": n * (per["UE"]["t_fixed"] + per["UK"]["t_fixed"]), "t_table": []}
    for ue, uk in zip(per["UE"]["t_table"], per["UK"]["t_table"]):
        assert ue["eps"] == uk["eps"]
        totals["t_table"].append({"eps": ue["eps"], "t_rot_pygridsynth": n * (ue["t_rot_pygridsynth"] + uk["t_rot_pygridsynth"]),
                                  "t_total": n * (ue["t_total"] + uk["t_total"]),
                                  "t_qiskit": n * (ue["t_qiskit"] + uk["t_qiskit"]),
                                  "cx_qiskit": n * (ue["cx_qiskit"] + uk["cx_qiskit"])})
    # cross-check against the whole step circuit with the outer register: the increment is exactly the totals
    inner = logical_metrics(C.build_step(alpha, beta, kappa2=kappa2, order=1))
    full = logical_metrics(C.build_step(alpha, beta, kappa2=kappa2, order=1, with_outer=True))
    comm = vf._outer_block_commutator(C.build_step(alpha, beta, kappa2=kappa2, order=1, with_outer=True))
    check = {"cx_increment": full["cx"] - inner["cx"], "n_rot_increment": full["n_rot"] - inner["n_rot"],
             "t_fixed_increment": full["t_fixed"] - inner["t_fixed"], "max_commutator_with_gauss_generators": comm,
             "matches_totals": bool(full["cx"] - inner["cx"] == totals["cx"] and full["n_rot"] - inner["n_rot"] == totals["n_rot"]
                                    and full["t_fixed"] - inner["t_fixed"] == totals["t_fixed"])}
    return {"n_outer_links": n, "params": {"alpha": alpha, "beta": None, "kappa2": kappa2, "r": R}, "per_link": per, "totals": totals,
            "consistency_with_build_step_with_outer": check,
            "note": "each outer link carries one full-angle link_UE(alpha) and one link_UK(kappa2) block (Digonto's decision 7: a "
                    "separate row); the blocks commute with every Gauss generator and with the inner part, so they are verified per "
                    "link as complete 16x16 unitaries."}


def isolated_plaquette_basis():
    """Orthonormal basis (50, 65536) of the Gauss kernel of the four inner links alone (outer links removed: every corner is
    2-valent), index sum_l nib_l 16^l.  Exact reduction: corners 0 and 2 involve the disjoint link pairs (0,3) and (1,2); their
    pair kernels N_a, N_b (256 x d) span a space of dimension d_a d_b in which corners 1 and 3 are small matrices built from the
    pair-level matrices N^dag T N (cross terms factorise, same-link terms use N^dag T T N)."""
    def T_of(A, role):
        return lk.calT_L(A) if role == "out" else lk.calT_R(A)

    def inner_ends(c):
        return [(l, r) for l, r in gz.CORNER_ENDS[c] if l < 4]

    pairs = {}
    for c in (0, 2):
        (la, ra), (lb, rb) = inner_ends(c)
        H = np.zeros((256, 256), dtype=np.complex128)
        for A in range(3):
            G = np.kron(T_of(A, ra), np.eye(16)) + np.kron(np.eye(16), T_of(A, rb))
            H += G.conj().T @ G
        w, V = np.linalg.eigh(H)
        pairs[c] = ((la, lb), V[:, w < 1e-9])
    (la, lb), Na = pairs[0]
    (lc, ld), Nb = pairs[2]
    da, db = Na.shape[1], Nb.shape[1]
    where = {}                                              # link -> (pair index, position in pair)
    for pi, (l1, l2) in enumerate(((la, lb), (lc, ld))):
        where[l1], where[l2] = (pi, 0), (pi, 1)
    Ns = (Na, Nb)

    def one(l, X):
        """N^dag (X on link l) N on the pair containing l (d x d)."""
        pi, pos = where[l]
        M = np.kron(X, np.eye(16)) if pos == 0 else np.kron(np.eye(16), X)
        return pi, Ns[pi].conj().T @ M @ Ns[pi]

    def embed(pi, M):
        return np.kron(M, np.eye(db)) if pi == 0 else np.kron(np.eye(da), M)

    Hred = np.zeros((da * db, da * db), dtype=np.complex128)
    for c in (1, 3):
        ends = inner_ends(c)
        for A in range(3):
            for i, (l1, r1) in enumerate(ends):
                for j, (l2, r2) in enumerate(ends):
                    T1, T2 = T_of(A, r1), T_of(A, r2)
                    if l1 == l2:
                        pi, M = one(l1, T1 @ T2)
                        Hred += embed(pi, M)
                    else:
                        p1, M1 = one(l1, T1)
                        p2, M2 = one(l2, T2)
                        assert p1 != p2
                        Hred += np.kron(M1, M2) if p1 == 0 else np.kron(M2, M1)
    w, V = np.linalg.eigh(0.5 * (Hred + Hred.conj().T))
    Z = V[:, w < 1e-9]
    letters = {0: "p", 1: "q", 2: "r", 3: "s"}              # tensor axes (link3, link2, link1, link0) = (s, r, q, p)
    # basis vector n = sum_{ab} Z[(a,b), n] N_a[(x,y), a] N_b[(z,w), b]
    Zt = Z.T.reshape(-1, da, db)
    Xa = Na.reshape(16, 16, da)
    Xb = Nb.reshape(16, 16, db)
    vecs = np.einsum(f"{letters[la]}{letters[lb]}a,{letters[lc]}{letters[ld]}b,nab->nsrqp", Xa, Xb, Zt).reshape(Z.shape[1], 65536)
    return vecs, w


def gauss_residual_dense(vecs: np.ndarray) -> float:
    """max_{c,A} ||G^A_c v|| over the rows of `vecs` (65536-vectors of the four inner links; outer ends dropped)."""
    worst = 0.0
    for c in range(4):
        for A in range(3):
            acc = np.zeros_like(vecs)
            for l, role in gz.CORNER_ENDS[c]:
                if l >= 4:
                    continue
                T = lk.calT_L(A) if role == "out" else lk.calT_R(A)
                t = vecs.reshape(-1, 16, 16, 16, 16)
                ax = 1 + (3 - l)
                acc += np.moveaxis(np.tensordot(T, t, axes=([1], [ax])), 0, ax).reshape(vecs.shape)
            worst = max(worst, float(np.linalg.norm(acc, axis=1).max()))
    return worst


def splitting_block(alpha=ALPHA, beta=BETA, r=R) -> dict:
    from scipy.linalg import expm

    W = pq.plaquette_row()
    rows = []
    for b in CLUSTER_BETAS:
        Ue, Uc = expm(2j * b * W), pq.cluster_product(b)
        rows.append({"beta": b, "error": float(np.linalg.norm(Ue - Uc, 2)), "norm": "operator 2-norm of exp(2i beta square) - cluster product",
                     "cluster_product_unitarity_error": float(np.abs(Uc.conj().T @ Uc - np.eye(256)).max())})
    vecs, w = isolated_plaquette_basis()
    assert vecs.shape[0] == gz.isolated_plaquette_count() == 50
    kappa2 = tg.kappa2_of(alpha, r)
    out1 = np.array([tg.apply_step(v, alpha, beta, kappa2, 1) for v in vecs])
    out2 = np.array([tg.apply_step(v, alpha, beta, kappa2, 2) for v in vecs])
    D = (out1 - out2).T                                      # 65536 x 50: (U_order1 - U_order2) restricted to the singlet space
    err = float(np.linalg.norm(D, 2))
    return {"cluster_product_vs_exact": rows,
            "trotter_order1_vs_order2": {"alpha": alpha, "beta": beta, "r": r, "kappa2": kappa2, "error": err,
                                         "space": "isolated_plaquette_singlets_50", "dim": int(vecs.shape[0]),
                                         "norm": "operator 2-norm of (U_order1 - U_order2) restricted to the space (no phase freedom)",
                                         "basis_gauss_residual": gauss_residual_dense(vecs),
                                         "basis_orthonormality_error": float(np.abs(vecs.conj() @ vecs.T - np.eye(vecs.shape[0])).max()),
                                         "gauss_residual_of_order1_outputs": gauss_residual_dense(out1),
                                         "gauss_residual_of_order2_outputs": gauss_residual_dense(out2),
                                         "spectral_gap_above_kernel": float(w[w > 1e-9].min())}}


def lean_summary() -> dict:
    """Static scan of lean/Su2Plaq/Fuzzy/*.lean (no build is run here): size, theorem count, code-level sorry/native_decide/axiom
    counts (comments stripped), whether the compiled .olean exists."""
    d = ROOT / "lean" / "Su2Plaq" / "Fuzzy"
    out = {"method": "static scan by scripts/m9_results.py; lake build / #print axioms are run by the Lean gate, not here", "files": {}}
    for f in sorted(d.glob("*.lean")):
        txt = f.read_text()
        code = re.sub(r"--[^\n]*", "", re.sub(r"/-.*?-/", "", txt, flags=re.S))
        olean = ROOT / "lean" / ".lake" / "build" / "lib" / "lean" / "Su2Plaq" / "Fuzzy" / (f.stem + ".olean")
        out["files"][f.name] = {"sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "lines": txt.count("\n"),
                                "theorems": len(re.findall(r"^\s*(?:theorem|lemma)\b", code, flags=re.M)),
                                "sorry": len(re.findall(r"\bsorry\b", code)), "native_decide": len(re.findall(r"native_decide", code)),
                                "axiom_declarations": len(re.findall(r"^\s*axiom\b", code, flags=re.M)),
                                "print_axioms_lines": len(re.findall(r"#print axioms", code)), "olean_built": olean.exists()}
    out["clean"] = bool(out["files"]) and all(v["sorry"] == 0 and v["native_decide"] == 0 and v["axiom_declarations"] == 0
                                              for v in out["files"].values())
    return out


# ---------------------------------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "results" / "fuzzy"))
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args(argv)
    snap = provenance(SEEDS)                                 # one snapshot (commit, dirty flag, versions) shared by all files
    snap["provenance_captured_at"] = snap["timestamp_utc"]
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    kappa2 = tg.kappa2_of(ALPHA, R)

    circuits = [("UE", 1), ("UK", 1), ("UB", 1), ("step", 1), ("step", 2)]
    row_specs = [(k, ALPHA, BETA, kappa2, o, e) for k, o in circuits for e in EPS]
    exact_specs = [(k, ALPHA, BETA, kappa2, o) for k, o in circuits]
    alt_specs = [(a, b, R) for a, b in ALTS] + [(ALPHA, BETA, 0.0)]
    with cf.ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futs_alt = [pool.submit(_task_alternate, s) for s in alt_specs]
        futs_row = [pool.submit(_task_row, s) for s in row_specs]
        futs_ex = [pool.submit(_task_exact, s) for s in exact_specs]
        fut_split = pool.submit(splitting_block)
        fut_outer = pool.submit(outer_row_block)
        exact = dict(f.result() for f in futs_ex)
        rows = dict(f.result() for f in futs_row)
        alts = dict(f.result() for f in futs_alt)
        splitting = fut_split.result()
        outer = fut_outer.result()

    def entry(kind, order):
        qc = _build(kind, ALPHA, BETA, kappa2, order)
        res = exact[(kind, ALPHA, BETA, kappa2, order)]
        trows = [rows[(kind, ALPHA, BETA, kappa2, order, e)] for e in EPS]
        lm = logical_metrics(qc)
        logical = {k: lm[k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}
        assert logical == res["logical"]
        name = {("step", 2): "step_order2"}.get((kind, order), kind)
        return {"verification": res["verification"], "seconds": res["seconds"],
                "metrics": {"logical": logical, "gates_lowered": lm["gates"], "t_table": trows, "macro_counts": dict(qc.count_ops())},
                "files": _save_circuit(qc, out, name)}

    ent = {(k, o): entry(k, o) for k, o in circuits}
    alt_json = [alts[s] for s in alt_specs]
    link_note = {"UE": "build_UE: four identical link_UE blocks on the inner links (the circuit is verified as one complete 16x16 "
                       "link unitary plus the check that the layer is four such blocks)",
                 "UK": "build_UK: four identical link_UK blocks (same verification)"}
    params = {"UE": {"alpha": ALPHA, "beta": None, "kappa2": None, "r": None, "order": 1},
              "UK": {"alpha": ALPHA, "beta": None, "kappa2": kappa2, "r": R, "order": 1},
              "UB": {"alpha": None, "beta": BETA, "kappa2": None, "r": None, "order": 1},
              "step": {"alpha": ALPHA, "beta": BETA, "kappa2": kappa2, "r": R, "order": 1}}
    for kind in ("UE", "UK", "UB"):
        e = ent[(kind, 1)]
        extra = {"verification_scope": SCOPE[kind], "order": 1, "alternates": [{"params": a["params"], **a[kind]} for a in alt_json if kind in a]}
        if kind in link_note:
            extra["note"] = link_note[kind]
            extra["per_link"] = {k: outer["per_link"][kind][k] for k in ("cx", "depth", "n_rot", "t_fixed", "qubits", "ancilla")}
        save_result(out / f"{kind}.json", encoding="fuzzy", circuit_id=kind, kind=kind, params=params[kind], verification=e["verification"],
                    metrics=e["metrics"], files=e["files"], seeds=SEEDS, provenance_snapshot=snap, extra=extra)
    s1, s2 = ent[("step", 1)], ent[("step", 2)]
    outer_summary = {k: outer[k] for k in ("n_outer_links", "totals", "consistency_with_build_step_with_outer")}
    outer_summary["file"] = "results/fuzzy/outer_row.json"
    step_extra = {"verification_scope": SCOPE["step"], "order": 1, "outer_row": outer_summary,
                  "order2": {"params": {"alpha": ALPHA, "beta": BETA, "kappa2": kappa2, "r": R, "order": 2}, **{k: s2[k] for k in ("verification", "metrics", "files")}},
                  "alternates": [{"params": a["params"], **{k: v for k, v in a.items() if k.startswith("step")}} for a in alt_json],
                  "trotter_order1_vs_order2_isolated_plaquette": splitting["trotter_order1_vs_order2"]["error"],
                  "verification_note": "UE/UK layers and the plaquette layer are taken from the circuit's own gates (UB layer: complete "
                                       "256x256 row block by the exact sparse simulator, weight outside the row space = leak); the composition is "
                                       "checked on seeded random product states and physical-state components against targets.apply_step; "
                                       "block_error = err - leak_amplitude.",
                  "lean": lean_summary(),
                  "seconds_total": time.time() - t_start}
    save_result(out / "step.json", encoding="fuzzy", circuit_id="step", kind="step", params=params["step"], verification=s1["verification"],
                metrics=s1["metrics"], files=s1["files"], seeds=SEEDS, provenance_snapshot=snap, extra=step_extra)
    doc = {"schema_version": 1, **outer, "provenance": dict(snap)}
    (out / "outer_row.json").write_text(json.dumps(doc, indent=2) + "\n")
    sdoc = {**splitting, "provenance": dict(snap)}
    (out / "splitting.json").write_text(json.dumps(sdoc, indent=2) + "\n")
    shared = ob.shared_table(ALPHA, BETA, prov=dict(snap))
    (out / "shared_observables.json").write_text(json.dumps(shared, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

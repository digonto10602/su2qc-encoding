"""Tester step 1.3: U_B physics. Independent assembly: the 433 physical vectors (28-qubit codes) are propagated through
build_UB(beta, with_outer=True) with the sparse simulator column by column, projected onto the physical basis, and compared
with enc.target('UB'); leak = ||Out - V M||_2 (everything outside the physical span incl. non-zero ancillas); Gauss via
explicit generators is in evaluate() (reported too).
Usage: PYTHONPATH=src python tests/independent/magnetic_1_3/check_ub_physics.py out.json"""
import sys, json, time, subprocess, warnings
import numpy as np, scipy.sparse as sp
warnings.filterwarnings("ignore")
from su2plaq.encodings.twelve import TwelveQubit
from su2plaq.circuits.twelve import build_UB, paulo_logical
from su2plaq.evaluate.sparse_sim import run_batch, encoded_block
from su2plaq.evaluate.evaluator import evaluate, inner_target
from su2plaq.metrics.logical import logical_metrics
from su2plaq.metrics.cliffordt import ct_compile
import json as _j

enc = TwelveQubit(); eb = enc.physical_vectors(); ns = len(eb.codes)
assert ns == 433
# physical vectors as sparse matrix over 28-bit keys
allc = np.unique(np.concatenate(eb.codes)); cidx = {int(c): i for i, c in enumerate(allc)}
rows = np.concatenate([[cidx[int(c)] for c in cs] for cs in eb.codes]); cols = np.concatenate([np.full(len(cs), s) for s, cs in enumerate(eb.codes)])
vals = np.concatenate(eb.amps)
A = sp.csr_matrix((vals, (rows, cols)), shape=(len(allc), ns))     # input expansion
VtV = (A.conj().T @ A).toarray(); gram_dev = float(np.abs(VtV - np.eye(ns)).max())

def physical_run(qc):
    b = run_batch(qc, allc.astype(np.int64))
    ok = np.unique(b.keys); ridx = np.searchsorted(ok, b.keys)
    B = sp.csr_matrix((b.amps, (ridx, b.cols)), shape=(len(ok), len(allc)))
    Out = B @ A                                                    # (out keys x 433)
    # V restricted to out keys: physical vector rows indexed by 28-bit code
    pos = np.searchsorted(ok, allc); hit = (pos < len(ok)) & (ok[np.minimum(pos, len(ok) - 1)] == allc)
    Vsub = sp.csr_matrix((np.ones(hit.sum()), (np.flatnonzero(hit), pos[hit])), shape=(len(allc), len(ok)))
    # M = A^dag P Out  with P picking rows of Out that are physical codes
    M = (A.conj().T @ (Vsub @ Out)).toarray()
    # residual R = Out - Vfull M (Vfull in out-key rows): build Vfull_out = P^T A
    Vout = Vsub.T @ A
    R = Out - Vout @ sp.csr_matrix(M)
    G = (R.conj().T @ R).toarray()
    leak = float(np.sqrt(max(np.linalg.eigvalsh((G + G.conj().T) / 2)[-1], 0)))
    return M, leak, b

def op_after_phase(M, T):
    ov = np.trace(T.conj().T @ M); ph = ov / abs(ov)
    return float(np.linalg.norm(M - ph * T, 2)), ph

out = dict(commit=subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip() + "+uncommitted", gram_dev=gram_dev, betas={})
print("Gram dev", gram_dev)
for beta in (0.4, 0.61, 1.0, 2.0):
    t0 = time.time()
    qc = build_UB(beta, with_outer=True)
    M, leak, b = physical_run(qc)
    T = enc.target("UB", None, beta)
    e, ph = op_after_phase(M, T)
    unit = float(np.abs(M.conj().T @ M - np.eye(ns)).max())
    ev = evaluate(qc, enc, T, method="physical", gauss=True)
    # inner-block (625 codes), the locked B1 check, independent
    qd = build_UB(beta); codes = enc.inner_codes()
    Mi, lk = encoded_block(run_batch(qd, codes), codes, len(codes), code_mask=(1 << 12) - 1)
    ei, _ = op_after_phase(Mi, inner_target(enc, "UB", None, beta))
    rec = dict(beta=beta, block_err=e, leak=leak, combined=e + leak, unit_dev=unit, phase=[ph.real, ph.imag], evaluate_ok=ev.ok, ev_op_norm=ev.op_norm_error, ev_block=ev.block_error,
               ev_leak_amp=ev.leak_amplitude, ev_gauss=ev.gauss_residual, ev_max_leak=ev.max_leak, ev_dirty=ev.dirty_ancilla, ev_outer_read=ev.outer_bits_read, ev_engine=ev.engine,
               inner625_err=ei, inner625_leak=float(lk.max()), dropped=float(b.dropped_max), seconds=time.time() - t0)
    # wrong targets must fail
    wrong = {}
    for nm, W in (("beta->-beta", enc.target("UB", None, -beta)), ("dagger", T.conj().T), ("complex_conj", T.conj()), ("beta*1.01", enc.target("UB", None, beta * 1.01)),
                  ("beta*1.0001", enc.target("UB", None, beta * 1.0001)), ("identity", np.eye(ns))):
        ew, _ = op_after_phase(M, W); evw = evaluate(qc, enc, W, method="physical", gauss=True)
        wrong[nm] = dict(err=ew, ev_ok=evw.ok, ev_err=evw.op_norm_error)
    rec["wrong"] = wrong
    out["betas"][str(beta)] = rec
    print(json.dumps({k: v for k, v in rec.items() if k != "wrong"}, default=float)); print("   wrong:", {k: (f"{v['err']:.3e}", v["ev_ok"]) for k, v in wrong.items()}, flush=True)

# composition: build_UB(0.3) then build_UB(0.31) vs target(0.61)
q1 = build_UB(0.3, with_outer=True); q2 = build_UB(0.31, with_outer=True); qc = q1.compose(q2)
M, leak, _ = physical_run(qc); e, _ = op_after_phase(M, enc.target("UB", None, 0.61))
qq = q1.compose(q1)  # 0.3+0.3=0.6 vs 0.61 must fail
M2, l2, _ = physical_run(qq); e2, _ = op_after_phase(M2, enc.target("UB", None, 0.61))
e3, _ = op_after_phase(M2, enc.target("UB", None, 0.6))
out["compose"] = dict(err_vs_0p61=e, leak=leak, wrong_0p6_vs_0p61=e2, ok_0p6_vs_0p6=e3, leak_0p3x2=l2, depth_gates=len(qc.data))
print("compose", out["compose"])

# Paulo logical
pl = paulo_logical(1.0); T1 = enc.target("UB", None, 1.0)
lm = logical_metrics(pl); out["paulo_logical_counts"] = {k: lm[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits", "ancilla")}
Mp, lp, _ = physical_run(pl) if False else (None, None, None)
codes = enc.inner_codes()
Mi, lk = encoded_block(run_batch(pl, codes), codes, len(codes), code_mask=(1 << 12) - 1)
out["paulo_logical_inner625"] = dict(err=op_after_phase(Mi, inner_target(enc, "UB", None, 1.0))[0], leak=float(lk.max()))
# paulo_logical vs build_UB: same block up to phase
Mb, lkb = encoded_block(run_batch(build_UB(1.0), codes), codes, len(codes), code_mask=(1 << 12) - 1)
out["paulo_logical_vs_build_UB_block"] = op_after_phase(Mi, Mb)[0]
evp = evaluate(pl, enc, T1)
out["paulo_logical_evaluate"] = dict(ok=evp.ok, op_norm=evp.op_norm_error, block=evp.block_error, leak=evp.leak_amplitude, gauss=evp.gauss_residual, engine=evp.engine)
t0 = time.time(); c, m = ct_compile(pl, 1e-6, level=3, seed=12345)
meta = _j.load(open("refs/paulo/SU2_plaquette_jmax_half_CT_metadata.json"))["resources"]
out["ct_compile_paulo_logical"] = dict(m, gates=dict(m["gates"]), meta_T=meta["T_count"], meta_cx=meta["CX_count"], meta_depth=meta["depth"], meta_gates=meta["gate_counts"], seconds=time.time() - t0)
print(out["paulo_logical_counts"], out["paulo_logical_inner625"], out["paulo_logical_vs_build_UB_block"], out["paulo_logical_evaluate"]); print(out["ct_compile_paulo_logical"])
json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)

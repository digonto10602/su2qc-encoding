"""pytest plugin (tester 223): in-process mutants of the det-layer code; nothing in src/ is edited.  MUT223=<name>."""
import os, subprocess

def _git_head_rejudge():
    # HEAD's _rejudge (before the NaN fix), compiled from `git show HEAD:...` source text
    src = subprocess.check_output(["git", "show", "HEAD:src/su2plaq/rishon/verify.py"], text=True, cwd="/home/digimonk/Projects/su2qc-encoding")
    a = src.index("def _rejudge"); b = src.index("\n\n\n", a)
    return src[a:b]

def pytest_configure(config):
    name = os.environ.get("MUT223", "")
    if not name:
        return
    from su2plaq.circuits import rishon as R
    orig_emit = R._emit_ud
    def emit(mutate):
        def f(qc, eta, n_links=4):
            for link in range(n_links):
                l1, l2, r1, r2 = 4 * link, 4 * link + 1, 4 * link + 2, 4 * link + 3
                mutate(qc, eta, link, n_links, l1, l2, r1, r2)
        return f
    def base(qc, eta, link, n_links, l1, l2, r1, r2, sign=1.0, rzf=2.0, skip_h=False, wiring=False, outer_flip=False):
        s = sign * (-1.0 if (outer_flip and link >= 4) else 1.0)
        qc.cx(l1, l2); qc.cx(r1, r2)
        qc.h(l1)
        if not skip_h: qc.h(r1)
        qc.cx(l1, r1); qc.rz(s * rzf * eta, r1)
        l2w = (4 * ((link + 1) % 4) + 1) if wiring else l2
        qc.cx(l2w, r1); qc.rz(s * rzf * eta, r1); qc.cx(l2w, r1)
        qc.cx(l1, r1); qc.h(l1); qc.h(r1)
        qc.cx(r1, r2); qc.cx(l1, l2)
    if name == "rz_sign":
        R._emit_ud = emit(lambda *a: base(*a, sign=-1.0))
    elif name == "rz_eta_not_2eta":
        R._emit_ud = emit(lambda *a: base(*a, rzf=1.0))
    elif name == "missing_H":
        R._emit_ud = emit(lambda *a: base(*a, skip_h=True))
    elif name == "wrong_link_wiring":
        R._emit_ud = emit(lambda *a: base(*a, wiring=True))
    elif name == "outer_sign_flip":
        R._emit_ud = emit(lambda *a: base(*a, outer_flip=True))
    elif name == "drop_last_link":
        R._emit_ud = lambda qc, eta, n_links=4: orig_emit(qc, eta, n_links - 1)
    elif name == "det_after_B":
        orig_step, orig_ub = R.build_step, R._emit_ub
        def build_step(alpha, beta, order=1, with_outer=False, ladder="ccx", eta=None):
            if eta is None:
                return orig_step(alpha, beta, order, with_outer, ladder)
            R._emit_ud = lambda *a, **k: None
            R._emit_ub = lambda qc, b, anc, lad: (lambda m: (orig_emit(qc, float(eta) if order == 1 else float(eta), 4), m)[1])(orig_ub(qc, b, anc, lad))
            try:
                return orig_step(alpha, beta, order, with_outer, ladder, eta)
            finally:
                R._emit_ud, R._emit_ub = orig_emit, orig_ub
        R.build_step = build_step
    elif name == "order2_full_angle":
        orig_step = R.build_step
        R.build_step = lambda alpha, beta, order=1, with_outer=False, ladder="ccx", eta=None: orig_step(alpha, beta, order, with_outer, ladder, None if eta is None else (eta * 2 if order == 2 else eta))
    elif name == "prepend_after":
        orig_pre = R.prepend_det_layer
        from qiskit import QuantumCircuit
        def pre(unit, eta):
            if not unit.qregs or unit.qregs[0].name != "d" or unit.qregs[0].size != 16:
                raise ValueError("first register")
            full = QuantumCircuit(*unit.qregs, *unit.cregs, name="mut")
            for inst in unit.data: full.append(inst.operation, list(inst.qubits), list(inst.clbits))
            orig_emit(full, float(eta)); full.metadata = {**(unit.metadata or {}), "eta": float(eta)}
            return full
        R.prepend_det_layer = pre
    elif name == "rejudge_old_nan":
        from su2plaq.rishon import verify as V
        ns = dict(V.__dict__); exec(_git_head_rejudge(), ns); V._rejudge = ns["_rejudge"]
    elif name == "outer_certify_wrong_target_sign":
        from su2plaq.rishon import results as RS
        o = RS.outer_det_certify
        RS.outer_det_certify = lambda qc, enc, eta, tol_err=1e-10: o(qc, enc, -eta, tol_err)
    else:
        raise RuntimeError("unknown mutant " + name)
    print(f"[mut223] mutant {name} active")

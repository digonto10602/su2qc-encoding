"""Certificate export / check for circuits (prompts/006 §4, §5; docs/METHODS.md §11.2).

`export_certificate` turns a Qiskit circuit into the JSON of `Su2PlaqCert` (gate list in program order from
`sparse_sim._translate`, exact physical states, exact block-diagonal target, unit phase `c = k z_alpha^a z_beta^b`),
`check_certificate` runs the compiled exact checker (`su2plaq_cert check`).  A circuit is certifiable iff every rotation
angle is a rational multiple (denominator <= 64) of alpha or beta (`non_linear_angle` otherwise), the gates are in
SIM_BASIS minus `u`/`unitary`, and it has <= 62 qubits.

Conventions of the JSON: little-endian qubits in the canonical frame data i -> i, outer j -> 12 + j (also when the circuit
has no outer register: the outer bits are then spectators), ancilla k -> 28 + k.  A gate angle is
`m_alpha * theta_alpha + m_beta * theta_beta` with `theta_alpha = alpha / d_alpha`, `theta_beta = beta / d_beta`; `rz`
uses the half angle, so its exponent vector is even by construction of the base.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import subprocess
import time
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from su2plaq._stub import todo
from su2plaq.lean import exact as E
from su2plaq.lean import project as P

ROOT = pathlib.Path(__file__).resolve().parents[3]
CERT_DIR = ROOT / "compress" / "lean" / "certs"
N_DATA, N_OUTER = 12, 16
_ANGLE_GATES = ("p", "cp", "rz")
_PLAIN_GATES = ("x", "z", "s", "sdg", "t", "tdg", "h", "sx", "cx", "cz", "swap", "ccx", "ccz")
_ENC = None


@dataclass
class LeanCert:
    status: str          # "certified" | "rejected" | "n_a" | "failed" | "not_run"
    reason: str
    cert_path: str | None
    seconds: float
    checker_sha256: str
    theorem_path: str | None = None
    axioms: list = field(default_factory=list)


# --------------------------------------------------------------------------------------------------------------------
# checker executable
_BUILT = False


def _checker_exe() -> pathlib.Path:
    """Path of the compiled checker; builds it (`lake build su2plaq_cert`, a no-op when up to date) once per process."""
    global _BUILT
    exe = P.LEAN_DIR / ".lake" / "build" / "bin" / "su2plaq_cert"
    if not _BUILT or not exe.exists():
        r = P.build("su2plaq_cert", timeout=1800)
        if not r["ok"]:
            raise RuntimeError("cannot build the Lean checker:\n" + r["stderr"][-2000:])
        _BUILT = True
    return exe


def checker_sha256() -> str:
    return hashlib.sha256(_checker_exe().read_bytes()).hexdigest()


def _run_checker(args: list[str], timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run([str(_checker_exe()), *args], capture_output=True, text=True, timeout=timeout)


# --------------------------------------------------------------------------------------------------------------------
# angle recognition
def _classify_angle(theta: float, alpha: float, beta: float):
    """(r_alpha, r_beta) Fractions with theta = r_alpha*alpha + r_beta*beta, exactly one of them nonzero (or both zero);
    None if theta is not a rational multiple (denominator <= 64) of alpha or beta.  At the nominal angles alpha/beta is
    itself a ratio of small integers, so an angle can be both; the smaller denominator wins."""
    ra = E.rational_multiple(theta, alpha)
    rb = E.rational_multiple(theta, beta)
    if ra is not None and ra == 0:
        return (Fraction(0), Fraction(0))
    cands = [(ra.denominator, 0, (ra, Fraction(0))) for ra in [ra] if ra is not None]
    cands += [(rb.denominator, 1, (Fraction(0), rb)) for rb in [rb] if rb is not None]
    if not cands:
        return None
    return min(cands)[2]


def _lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def _gate_records(ops, perm, alpha, beta, base_min=(1, 1)):
    """(gate records, base (d_alpha, d_beta), per-op exponent fractions) or a reason string (n_a)."""
    fr = []
    dA, dB = base_min
    for name, qs, payload in ops:
        if name in ("u", "unitary"):
            return "unitary_gate"
        if name in _ANGLE_GATES:
            theta = float(payload[0])
            r = _classify_angle(theta, alpha, beta)
            if r is None:
                return f"non_linear_angle:{name}:{theta!r}"
            fr.append(r)
            h = Fraction(1, 2) if name == "rz" else Fraction(1)
            dA = _lcm(dA, (r[0] * h).denominator)
            dB = _lcm(dB, (r[1] * h).denominator)
        elif name in _PLAIN_GATES:
            fr.append(None)
        else:
            return f"unsupported_gate:{name}"
    recs = []
    for (name, qs, payload), r in zip(ops, fr):
        rec = {"g": name, "q": [perm[q] for q in qs]}
        if r is not None:
            ma, mb = r[0] * dA, r[1] * dB
            assert ma.denominator == 1 and mb.denominator == 1
            if name == "rz":
                assert ma.numerator % 2 == 0 and mb.numerator % 2 == 0
            rec["m"] = [int(ma), int(mb)]
        recs.append(rec)
    return recs, (dA, dB), fr


def _perm_of(layout, n):
    perm = {q: i for i, q in enumerate(layout.data)}
    perm.update({q: N_DATA + j for j, q in enumerate(layout.outer)})
    perm.update({q: N_DATA + N_OUTER + k for k, q in enumerate(layout.ancilla)})
    if sorted(perm) != list(range(n)):
        raise ValueError("layout does not partition the circuit's qubits")
    return perm


def _encoding():
    global _ENC
    if _ENC is None:
        from su2plaq.encodings.twelve import TwelveQubit

        _ENC = TwelveQubit()
    return _ENC


def _git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 - provenance only
        return "unknown"


def _exporter_sha() -> str:
    h = hashlib.sha256()
    for f in ("certify.py", "exact.py"):
        h.update((pathlib.Path(__file__).parent / f).read_bytes())
    return h.hexdigest()


# --------------------------------------------------------------------------------------------------------------------
def export_raw_circuit(qc, out_path, *, alpha: float, beta: float) -> pathlib.Path | str:
    """Gates + base angles only (no states / target) for `checker_eval` semantics tests.  Qubits keep the circuit's own
    indices.  Returns the path, or an n_a reason string."""
    from su2plaq.evaluate import sparse_sim as ss

    n = qc.num_qubits
    if n > 62:
        return "too_many_qubits"
    try:
        ops, _gph = ss._translate(qc)
    except ValueError as exc:
        return f"disallowed_gate:{exc}"
    res = _gate_records(ops, {q: q for q in range(n)}, alpha, beta)
    if isinstance(res, str):
        return res
    recs, (dA, dB), _ = res
    cert = {"schema": "su2plaq-cert-1", "circuit_id": "raw-" + hashlib.sha256(json.dumps(recs).encode()).hexdigest()[:12],
            "n_qubits": n, "n_data": 0, "n_outer": 0, "base": {"d_alpha": dA, "d_beta": dB}, "gates": recs,
            "provenance": {"git_commit": _git_commit(), "exporter_sha256": _exporter_sha(),
                           "alpha_nominal": alpha, "beta_nominal": beta}}
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert))
    return out_path


def _scale_laurent(lp: E.Laurent, fa: int, fb: int) -> E.Laurent:
    return E.Laurent({(ea * fa, eb * fb): v for (ea, eb), v in lp.items()})


def _float_phase(ops_f, n, states, tgt_diag, ks_test, pair, dt):
    """Float estimate of c at the angle pair: <psi_k| U psi_k> / V_kk averaged over `ks_test`; ops_f have float payloads
    already substituted for this pair.  Returns (c, spread)."""
    from su2plaq.evaluate import sparse_sim as ss
    from su2plaq.evaluate.evaluator import _ops_to_circuit

    qcf = _ops_to_circuit(ops_f, 0.0, n)
    al, be = pair
    cs = []
    for k in ks_test:
        codes = np.asarray(states[k]["codes"], dtype=np.int64)
        amps = np.array([a.to_complex() for a in states[k]["amps"]])
        b = ss.run_batch(qcf, codes)
        out: dict[int, complex] = {}
        for key, col, a in zip(b.keys.tolist(), b.cols.tolist(), b.amps):
            out[key] = out.get(key, 0j) + amps[col] * a
        ov = sum(np.conj(amps[i]) * out.get(int(c), 0j) for i, c in enumerate(codes))
        v = tgt_diag[k].evaluate(al / dt[0], be / dt[1])
        cs.append(ov / v)
    cs = np.array(cs)
    c = complex(np.mean(cs))
    return c, float(np.max(np.abs(cs - c)))


def _fit_phase(cs, pairs, base, window=12):
    """(j, a, b) with c_i = omega^j z_alpha^a z_beta^b at every angle pair (theta = pair/base), or None."""
    dA, dB = base
    a = np.arange(-window * dA, window * dA + 1)[:, None, None]
    b = np.arange(-window * dB, window * dB + 1)[None, :, None]
    j = np.arange(8)[None, None, :]
    ok = np.ones((a.shape[0], b.shape[1], 8), dtype=bool)
    for c, (al, be) in zip(cs, pairs):
        model = np.exp(1j * (a * al / dA + b * be / dB + j * np.pi / 4))
        ok &= np.abs(model - c) < 1e-7
    idx = np.argwhere(ok)
    if len(idx) == 0:
        return None
    # smallest |a| + |b|, then smallest j
    best = min(idx.tolist(), key=lambda t: (abs(int(a[t[0], 0, 0])) + abs(int(b[0, t[1], 0])), t[2]))
    return int(best[2]), int(a[best[0], 0, 0]), int(b[0, best[1], 0])


def export_certificate(qc, enc, kind: str, alpha: float, beta: float, order: int, out_path, *,
                       verdict_phases: list[complex] | None = None) -> pathlib.Path | str:
    """Write the certificate JSON of `qc` against the exact target (kind, order) of the twelve-qubit encoding.  Returns the
    path or an n_a reason string (`non_linear_angle:<gate>:<theta>`, `unitary_gate`, `phase_not_in_K`, `too_many_qubits`, ...).
    `verdict_phases` (float evaluator phases at the nominal pair, global phase included) are only cross-checked."""
    from su2plaq.encodings.base import ALT_ANGLES
    from su2plaq.evaluate import sparse_sim as ss

    t0 = time.time()
    n = qc.num_qubits
    if n > 62:
        return "too_many_qubits"
    try:
        layout = enc.layout_of(qc)
        perm = _perm_of(layout, n)
    except ValueError as exc:
        return f"bad_layout:{exc}"
    n_cert = N_DATA + N_OUTER + len(layout.ancilla)
    if n_cert > 62:
        return "too_many_qubits"
    try:
        ops, gphase = ss._translate(qc)
    except ValueError as exc:
        return f"disallowed_gate:{exc}"
    t_base = E.target_base(kind, order)
    res = _gate_records(ops, perm, alpha, beta, base_min=t_base)
    if isinstance(res, str):
        return res
    recs, base, fr = res
    fa, fb = base[0] // t_base[0], base[1] // t_base[1]
    states = E.exact_encoded_states(enc)
    blocks = E.exact_target_blocks(kind, order)
    blocks = [{"ks": b["ks"], "entries": [(i, j, _scale_laurent(lp, fa, fb)) for i, j, lp in b["entries"]]} for b in blocks]
    # --- phase c = omega^j z_alpha^a z_beta^b, fitted from the float simulation at three angle pairs
    pairs = [(alpha, beta)] + [tuple(p) for p in ALT_ANGLES]
    diag = {}
    for b in blocks:
        for i, j, lp in b["entries"]:
            if i == j:
                diag[b["ks"][i]] = lp
    nom_mag = {k: abs(lp.evaluate(alpha / base[0], beta / base[1])) for k, lp in diag.items()}
    cand = [k for k in sorted(nom_mag, key=lambda k: (len(states[k]["codes"]), -nom_mag[k])) if nom_mag[k] > 0.5][:3]
    if not cand:
        return "phase_not_in_K"
    ops_canon = [(nm, tuple(perm[q] for q in qs), pl) for nm, qs, pl in ops]
    cs, spread = [], 0.0
    try:
        for (al, be) in pairs:
            ops_f = []
            for (nm, qs, pl), r in zip(ops_canon, fr):
                ops_f.append((nm, qs, (float(r[0]) * al + float(r[1]) * be,)) if r is not None else (nm, qs, pl))
            c, sp_ = _float_phase(ops_f, n_cert, states, diag, cand, (al, be), base)
            cs.append(c)
            spread = max(spread, sp_)
    except ss.SimCapExceeded:
        return "unsimulable"
    unit = all(abs(abs(c) - 1) < 1e-7 for c in cs) and spread < 1e-7
    fit = _fit_phase([c / abs(c) for c in cs], pairs, base) if unit else None
    if fit is None:
        if unit:
            return "phase_not_in_K"
        fit = (0, 0, 0)          # the circuit is not the target up to a phase: let the exact checker reject it
    j_, a_, b_ = fit
    residual = None
    if verdict_phases:
        residual = float(abs(cs[0] / abs(cs[0]) * np.exp(1j * gphase) - verdict_phases[0]))
    gates_hash = hashlib.sha256(json.dumps(recs).encode()).hexdigest()
    cert = {
        "schema": "su2plaq-cert-1", "circuit_id": f"{kind}-o{order}-{gates_hash[:12]}", "program_sha256": gates_hash,
        "n_qubits": n_cert, "n_data": N_DATA, "n_outer": N_OUTER, "base": {"d_alpha": base[0], "d_beta": base[1]},
        "gates": recs,
        "states": [{"k": k, "label": str(enc.basis.labels[k]),
                    "terms": [{"code": int(c), "c": a.to_json()} for c, a in zip(st["codes"], st["amps"])]}
                   for k, st in enumerate(states)],
        "target": {"kind": kind, "order": order,
                   "blocks": [{"ks": b["ks"], "entries": [[i, j, lp.to_json()] for i, j, lp in b["entries"]]}
                              for b in blocks]},
        "phase": {"k": E.omega_power(j_).to_json(), "m": [a_, b_]},
        "provenance": {"git_commit": _git_commit(), "exporter_sha256": _exporter_sha(), "alpha_nominal": alpha,
                       "beta_nominal": beta, "float_phase_spread": spread, "float_phase_cross_check": residual,
                       "export_seconds": time.time() - t0},
    }
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cert))
    return out_path


# --------------------------------------------------------------------------------------------------------------------
def check_certificate(path, timeout: float = 900.0) -> LeanCert:
    """`su2plaq_cert check <path>`: ACCEPT -> certified, REJECT <reason> -> rejected, anything else -> failed."""
    t0 = time.time()
    try:
        sha = checker_sha256()
        r = _run_checker(["check", str(path)], timeout)
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


def _certify(qc, enc, kind, alpha, beta, order, out_dir, timeout) -> LeanCert:
    t0 = time.time()
    out_dir = pathlib.Path(out_dir) if out_dir is not None else CERT_DIR
    tmp = out_dir / f"{kind}-o{order}-pending-{abs(hash(id(qc))) % 10**8}.json"
    try:
        res = export_certificate(qc, enc, kind, alpha, beta, order, tmp)
    except E.ExactError as exc:
        return LeanCert("failed", f"exact export failed: {exc}", None, time.time() - t0, "")
    if isinstance(res, str):
        return LeanCert("n_a", res, None, time.time() - t0, "")
    final = out_dir / (json.loads(res.read_text())["circuit_id"] + ".json")
    res.replace(final)
    cert = check_certificate(final, timeout=timeout)
    cert.seconds = time.time() - t0
    return cert


def certify_circuit_kind(qc, enc, kind: str, alpha: float, beta: float, order: int, out_dir=None,
                         timeout: float = 900.0) -> LeanCert:
    """Export + check against the target (kind, order) at the given nominal angles; the alternate angle pairs are
    `encodings.base.ALT_ANGLES` (the circuit is re-instantiated at them from its recognised angle exponents)."""
    return _certify(qc, enc, kind, alpha, beta, order, out_dir, timeout)


def certify_circuit(qc, spec, out_dir=None, timeout: float = 900.0) -> LeanCert:
    """`certify_circuit_kind` with kind / angles / order taken from a TaskSpec-like object."""
    enc = _encoding() if getattr(spec, "encoding", "twelve") == "twelve" else None
    if enc is None:
        return LeanCert("n_a", f"unsupported_encoding:{spec.encoding}", None, 0.0, "")
    return _certify(qc, enc, spec.kind, float(spec.alpha), float(spec.beta), int(spec.order), out_dir, timeout)


def write_theorem_file(cert_path, theorem_name: str, out_path) -> pathlib.Path:
    todo("lean.certify.write_theorem_file")      # step 2.L5


def checker_eval(cert_path, input_index: int, timeout: float = 900.0) -> list:
    """`su2plaq_cert eval <cert> <input_index>`: exact output of the gate list on one basis state, as
    [(basis integer, Laurent)]."""
    r = _run_checker(["eval", str(cert_path), str(int(input_index))], timeout)
    if r.returncode != 0:
        raise RuntimeError(f"checker eval failed: {r.stdout.strip()} {r.stderr.strip()}")
    data = json.loads(r.stdout)
    out = []
    for t in data["out"]:
        lp = E.Laurent()
        for ma, mb, k in t["terms"]:
            lp = lp + E.Laurent.mono((int(ma), int(mb)), E.KNum.from_json(k))
        out.append((int(t["key"]), lp))
    return out

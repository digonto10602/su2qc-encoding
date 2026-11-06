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
def _classify_angle(theta: float, alpha: float, beta: float, prefer: str = "ab"):
    """(r_alpha, r_beta) Fractions with theta = r_alpha*alpha + r_beta*beta, exactly one of them nonzero (or both zero);
    None if theta is not a rational multiple (denominator <= 64) of alpha or beta.  At special angle pairs alpha/beta is
    itself a ratio of small integers, so an angle can be both; `prefer` lists the variables of the target ("a" for U_E,
    "b" for U_B, "ab" for the step) and is tried first, the smaller denominator breaking ties inside a group."""
    ra = E.rational_multiple(theta, alpha)
    rb = E.rational_multiple(theta, beta)
    if ra is not None and ra == 0:
        return (Fraction(0), Fraction(0))
    cands = []
    if ra is not None:
        cands.append((0 if "a" in prefer else 1, ra.denominator, 0, (ra, Fraction(0))))
    if rb is not None:
        cands.append((0 if "b" in prefer else 1, rb.denominator, 1, (Fraction(0), rb)))
    return min(cands)[3] if cands else None


_PREFER = {"UE": "a", "UB": "b", "step": "ab"}


def _lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def _gate_records(ops, perm, alpha, beta, base_min=(1, 1), prefer: str = "ab"):
    """(gate records, base (d_alpha, d_beta), per-op exponent fractions) or a reason string (n_a)."""
    fr = []
    dA, dB = base_min
    for name, qs, payload in ops:
        if name in ("u", "unitary"):
            return "unitary_gate"
        if name in _ANGLE_GATES:
            theta = float(payload[0])
            r = _classify_angle(theta, alpha, beta, prefer)
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


def _h_matrix():
    from qiskit.circuit.library import HGate

    return np.asarray(HGate().to_matrix(), dtype=np.complex128)


def _lower_standard(op, qs):
    """Exact lowering (no global phase) of the standard rotation gates that `sparse_sim._translate` would turn into a matrix
    gate `u`: crx(t) = H_t crz(t) H_t, crz(t) = cx, rz(-t/2), cx, rz(t/2) (circuit order), rx(t) = H rz(t) H.  Returns the
    op list or None if `op` is not one of them."""
    name = op.name
    if name not in ("crx", "crz", "rx") or not ss_is_standard(op):
        return None
    th = float(op.params[0])
    Hm = _h_matrix()
    if name == "rx":
        (t,) = qs
        return [("h", (t,), Hm), ("rz", (t,), (th,)), ("h", (t,), Hm)]
    c, t = qs
    core = [("cx", (c, t), ()), ("rz", (t,), (-th / 2,)), ("cx", (c, t), ()), ("rz", (t,), (th / 2,))]
    return core if name == "crz" else [("h", (t,), Hm)] + core + [("h", (t,), Hm)]


def ss_is_standard(op) -> bool:
    from su2plaq.evaluate import sparse_sim as ss

    return ss.is_standard_gate(op)


def _translate_export(qc):
    """`sparse_sim._translate` with the exact lowering of crx / crz / rx (see `_lower_standard`) so that circuits using them
    stay certifiable; everything else is translated exactly as the simulator does (program order, level-0 decompositions)."""
    from su2plaq.evaluate import sparse_sim as ss

    ss._reject_wide_mcx(qc)
    ops: list = []
    phase = float(qc.global_phase)

    def emit(op, qs, depth):
        nonlocal phase
        name = op.name
        if ss._is_barrier(op):
            return
        low = _lower_standard(op, qs)
        if low is not None:
            ops.extend(low)
            return
        if name in ss.SIM_BASIS and ss.is_standard_gate(op):
            payload = (np.asarray(op.to_matrix(), dtype=np.complex128) if name in ss._BRANCH
                       else tuple(float(x) for x in op.params))
            ops.append((name, qs, payload))
        elif ss.is_standard_gate(op):
            local, ph = ss._decompose_local(op)
            ops.extend((nm, tuple(qs[k] for k in lq), pl) for nm, lq, pl in local)
            phase += ph
        else:
            d = getattr(op, "definition", None)
            if d is None or depth > 30:
                raise ValueError(f"custom gate {name!r} has no definition (or is nested too deeply)")
            phase += float(d.global_phase)
            for inst in d.data:
                sq = tuple(qs[d.find_bit(q).index] for q in inst.qubits)
                if inst.clbits or inst.operation.name in ("measure", "reset", "delay"):
                    raise ValueError(f"gate {inst.operation.name!r} cannot be simulated")
                emit(inst.operation, sq, depth + 1)

    for inst in qc.data:
        op = inst.operation
        if inst.clbits or op.name in ("measure", "reset", "delay") or op.name.startswith("if_") or op.name in (
                "for_loop", "while_loop", "switch_case"):
            raise ValueError(f"gate {op.name!r} cannot be simulated (measure/reset/classical control/unsupported)")
        emit(op, tuple(qc.find_bit(q).index for q in inst.qubits), 0)
    return ops, phase


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
        ops, _gph = _translate_export(qc)
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
    if kind not in _PREFER:
        raise ValueError(f"unknown kind {kind!r}")
    try:
        layout = enc.layout_of(qc)
        perm = _perm_of(layout, n)
    except ValueError as exc:
        return f"bad_layout:{exc}"
    n_cert = N_DATA + N_OUTER + len(layout.ancilla)
    if n_cert > 62:
        return "too_many_qubits"
    try:
        ops, gphase = _translate_export(qc)
    except ValueError as exc:
        return f"disallowed_gate:{exc}"
    t_base = E.target_base(kind, order)
    res = _gate_records(ops, perm, alpha, beta, base_min=t_base, prefer=_PREFER[kind])
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
    out_path.write_text(json.dumps(cert, separators=(",", ":")))
    return out_path


# --------------------------------------------------------------------------------------------------------------------
_ARITY = {"x": 1, "z": 1, "s": 1, "sdg": 1, "t": 1, "tdg": 1, "h": 1, "sx": 1, "rz": 1, "p": 1, "cx": 2, "cz": 2, "cp": 2,
          "swap": 2, "ccx": 3, "ccz": 3}


def _structure_problem(d: dict) -> str | None:
    """Purely structural checks of a twelve-qubit circuit certificate (the Lean checker repeats them; failing here gives the
    caller a reason before any Lean run): target kind, phase of the form omega^j z_alpha^a z_beta^b, positive base, gate list
    (names, arities, distinct in-range qubits, integer exponents, even for rz) and its recorded hash."""
    tgt = d.get("target")
    if not isinstance(tgt, dict) or tgt.get("kind") not in ("UE", "UB", "step"):
        return "target has no valid kind (UE, UB or step)"
    if tgt.get("order", 1) not in (1, 2):
        return "target order must be 1 or 2"
    ph = d.get("phase")
    if not isinstance(ph, dict) or not isinstance(ph.get("m"), list) or len(ph["m"]) != 2 or \
            not all(isinstance(x, int) and not isinstance(x, bool) for x in ph["m"]):
        return "bad phase: needs k and integer exponents m"
    if not any(E.KNum.from_json(ph["k"]) == E.omega_power(j) for j in range(8)):
        return "bad phase: k is not an eighth root of unity"
    base = d.get("base")
    if not isinstance(base, dict) or not all(isinstance(base.get(k), int) and base[k] > 0 for k in ("d_alpha", "d_beta")):
        return "base must have positive integer d_alpha and d_beta"
    n = d.get("n_qubits")
    if not isinstance(n, int) or not N_DATA + N_OUTER <= n <= 62:
        return "n_qubits must be between 28 and 62"
    gates = d.get("gates")
    if not isinstance(gates, list):
        return "no gate list"
    for i, g in enumerate(gates):
        name = g.get("g")
        if name not in _ARITY:
            return f"gate {i}: unsupported gate {name!r}"
        q = g.get("q")
        if not isinstance(q, list) or len(q) != _ARITY[name] or len(set(q)) != len(q) or \
                not all(isinstance(x, int) and 0 <= x < n for x in q):
            return f"gate {i} ({name}): bad qubits"
        m = g.get("m")
        if name in _ANGLE_GATES:
            if not isinstance(m, list) or len(m) != 2 or not all(isinstance(x, int) for x in m) or \
                    (name == "rz" and any(x % 2 for x in m)):
                return f"gate {i} ({name}): bad angle exponents"
        elif m is not None:
            return f"gate {i} ({name}): angle exponents on an angle-free gate"
    if d.get("program_sha256") != hashlib.sha256(json.dumps(gates).encode()).hexdigest():
        return "gate list does not match its recorded program_sha256"
    return None


def _exporter_mismatch(path) -> str | None:
    """Compare the trusted inputs of a twelve-qubit certificate -- the 433 states and the target blocks -- with the exact
    data of the exporter (`exact.py`, cross-checked against the float code), entry by entry, after the structural checks of
    `_structure_problem`.  Returns a reason or None.  (The Lean checker itself verifies count, indices, normalisation and
    orthogonality of the states and the SHA-256 pins; this refuses early and for the theorem-file writer.)"""
    try:
        d = json.loads(pathlib.Path(path).read_text())
        if not isinstance(d, dict) or d.get("n_data") != N_DATA or d.get("n_outer") != N_OUTER or "states" not in d:
            return "not a twelve-qubit circuit certificate with states (n_data 12, n_outer 16)"
        why = _structure_problem(d)
        if why is not None:
            return why
        got_states = d["states"]
        exp = E.exact_encoded_states(_encoding())
        if len(got_states) != len(exp):
            return f"certificate has {len(got_states)} states, the physical basis has {len(exp)}"
        seen = set()
        for st in got_states:
            k = st["k"]
            if k in seen or not 0 <= k < len(exp):
                return f"bad or duplicate state index {k}"
            seen.add(k)
            want = {int(c): a for c, a in zip(exp[k]["codes"], exp[k]["amps"])}
            have = {int(t["code"]): E.KNum.from_json(t["c"]) for t in st["terms"]}
            if len(have) != len(st["terms"]) or have != want:
                return f"state {k} differs from the exact physical basis"
        tgt = d["target"]
        kind, order = tgt["kind"], int(tgt.get("order", 1))
        t_base = E.target_base(kind, order)
        fa, fb = d["base"]["d_alpha"] // t_base[0], d["base"]["d_beta"] // t_base[1]
        if d["base"]["d_alpha"] != fa * t_base[0] or d["base"]["d_beta"] != fb * t_base[1]:
            return "base is not a multiple of the target's base"
        want_blocks = [{"ks": list(b["ks"]), "entries": {(i, j): _scale_laurent(lp, fa, fb) for i, j, lp in b["entries"]}}
                       for b in E.exact_target_blocks(kind, order)]
        have_blocks = [{"ks": list(b["ks"]), "entries": {(int(e[0]), int(e[1])): E.Laurent.from_json(e[2])
                                                          for e in b["entries"]}} for b in tgt["blocks"]]
        if want_blocks != have_blocks:
            return f"target blocks differ from the exact {kind} target"
    except E.ExactError as exc:
        return f"exporter data unavailable: {exc}"
    except (KeyError, TypeError, ValueError, AttributeError, IndexError, ZeroDivisionError, OverflowError) as exc:
        return f"malformed certificate: {type(exc).__name__}: {exc}"
    return None


def check_certificate(path, timeout: float = 900.0) -> LeanCert:
    """Pin the trusted inputs against the exporter's exact data, then `su2plaq_cert check <path>`: ACCEPT -> certified,
    REJECT <reason> -> rejected, anything else -> failed."""
    t0 = time.time()
    why = _exporter_mismatch(path)
    if why is not None:
        return LeanCert("rejected", why, str(path), time.time() - t0, "")
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
    """Write `import Su2PlaqCert` + the certificate JSON as a Lean string literal + `theorem <name> :
    Su2PlaqCert.checkJsonString certJson = true := by native_decide` + `#print axioms <name>` (standard axioms plus one
    per-theorem `native_decide` axiom: compiler trust).  Elaborate with `cd lean && lake env lean <out_path>`."""
    cert_path, out_path = pathlib.Path(cert_path), pathlib.Path(out_path)
    why = _exporter_mismatch(cert_path)
    if why is not None:
        raise ValueError(f"refusing to write a theorem file for a certificate that differs from the exporter's exact data: {why}")
    text = cert_path.read_text()
    d = json.loads(text)
    if not theorem_name.replace("_", "").isalnum() or len(theorem_name) > 13:
        # `#print axioms` prints one line only if the whole message fits in 120 columns: 92 + 2 * len(name)
        raise ValueError(f"bad theorem name {theorem_name!r} (alphanumeric/underscore, at most 13 characters)")
    lit = text.replace("\\", "\\\\").replace('"', '\\"')
    if "\n" in lit or "\r" in lit:
        raise ValueError("certificate JSON must be a single line")
    prov = d.get("provenance", {})
    head = (
        "import Su2PlaqCert\n\n"
        f"/-! Generated by `su2plaq.lean.certify.write_theorem_file` -- do not edit.\n"
        f"circuit_id {d.get('circuit_id')}; git {prov.get('git_commit')}; exporter {prov.get('exporter_sha256')};\n"
        f"certificate sha256 {hashlib.sha256(text.encode()).hexdigest()}; {len(d['gates'])} gates, {d['n_qubits']} qubits.\n"
        "`native_decide` runs the compiled checker `Su2PlaqCert.checkJsonString` (trust: Lean compiler + checker source). -/\n\n"
        "")
    body = (f'def certJson : String := "{lit}"\n\n'
            f"theorem {theorem_name} : Su2PlaqCert.checkJsonString certJson = true := by native_decide\n\n"
            f"#print axioms {theorem_name}\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(head + body)
    return out_path


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

"""The three Kogut-Susskind encodings (twelve, spinnet, LSH) side by side (prompts/009 §3.1, §5.1; docs/METHODS.md §13.1).

All three list the 433 physical states in the label order of `exact.physical.physical_basis(convention="cg")`; their Hamiltonians
differ by the real diagonal sign matrix D = `Encoding.gauge` (H_B^twelve = D H_B^enc D, D_twelve = 1).  Each encoding's operators
are built by THAT encoding's own code (twelve: route A `exact.operators`; spinnet: route B 6j; lsh: loop-string-hadron operators).

Cross-verdict (our label): the production evaluator's verdict for the circuit of one encoding against the target built by the code
of another encoding, moved by T_{s->d} = D_s D_d V_s D_d D_s.  This module decides no verdict by itself and writes nothing.
"""
from __future__ import annotations

import importlib
import pathlib

import numpy as np

KS_ENCODINGS = ("twelve", "spinnet", "lsh")


def _enc(name):
    from su2plaq.compress.spec import get_encoding

    if name not in KS_ENCODINGS:
        raise ValueError(f"not a Kogut-Susskind encoding: {name!r} (expected one of {KS_ENCODINGS})")
    return get_encoding(name)


def ks_operators(encoding) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(he_inner (433,), he_all (433,), HB (433, 433)) built by `encoding`'s own code, in its own sign convention, label order of
    physical_basis("cg").  he_* are the diagonal of H_E (sum of j(j+1) over the 4 inner / all 12 links)."""
    e = _enc(encoding)
    if encoding == "twelve":
        from su2plaq.exact.operators import h_electric_inner, h_electric_outer, h_magnetic_phys

        HB, _leak = h_magnetic_phys(e.basis)
        hi = np.asarray(h_electric_inner(e.basis), dtype=np.float64)
        ho = np.asarray(h_electric_outer(e.basis), dtype=np.float64)
        return hi.copy(), (hi + ho).copy(), np.asarray(HB, dtype=np.complex128).copy()
    return (np.asarray(e._HE_inner, dtype=np.float64).copy(), np.asarray(e._HE_all, dtype=np.float64).copy(),
            np.asarray(e._HB, dtype=np.complex128).copy())


def ks_hamiltonian(encoding, g2, include_outer_electric=True) -> np.ndarray:
    """(g2/2) diag(he) + HB / g2 (METHODS §2), he = he_all if `include_outer_electric` else he_inner."""
    hi, ha, HB = ks_operators(encoding)
    return 0.5 * g2 * np.diag(ha if include_outer_electric else hi) + HB / g2


def gauge_signs(encoding) -> np.ndarray:
    """(433,) of +-1.0 (`Encoding.gauge`); all +1 for twelve, the reference."""
    e = _enc(encoding)
    if encoding == "twelve":
        return np.ones(433)
    return np.asarray(e.gauge, dtype=np.float64).copy()


def transported_target(src, dst, kind, alpha, beta, order=1) -> np.ndarray:
    """T_{s->d} = D_s D_d V_s D_d D_s, V_s = get_encoding(src).target(kind, alpha, beta, order) (METHODS §13.1)."""
    V = np.asarray(_enc(src).target(kind, alpha, beta, order))
    s = gauge_signs(src) * gauge_signs(dst)
    return s[:, None] * V * s[None, :]


def step_circuit(encoding, which="general", alpha=0.37, beta=0.61, order=1, root=None):
    """-> (QuantumCircuit, info).  "general": `su2plaq.circuits.<encoding>.build_step(alpha, beta, order)`; "headline" (order 1 only):
    the program of `robust.headline(encoding, "step", compute=False)["id"]`, rebuilt by the stock worker at (alpha, beta).
    FileNotFoundError if no headline is cached; nothing is written.  `root`: project root holding results/compress and compress/archive
    (default: this checkout)."""
    _enc(encoding)
    if which == "general":
        mod = importlib.import_module(f"su2plaq.circuits.{encoding}")
        return mod.build_step(alpha, beta, order), {"which": "general", "entry": None}
    if which != "headline":
        raise ValueError(f"which must be 'general' or 'headline', got {which!r}")
    if order != 1:
        raise ValueError("headline circuits are first-order steps")
    from su2plaq.compress import archive as A
    from su2plaq.compress import evaluate as E
    from su2plaq.compress import robust as RB
    from su2plaq.compress.spec import ROOT, default_spec

    root = pathlib.Path(ROOT if root is None else root)
    h = RB.headline(encoding, "step", root=root, compute=False)
    if h is None or h.get("id") is None:
        raise FileNotFoundError(f"no cached headline for {encoding} (results/compress/{encoding}/robust.json)")
    hid = h["id"]
    spec = default_spec(encoding, "step")
    arch = A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles), strict=True)
    entry = next(x for x in arch.entries() if x.id == hid)
    circuits, _ = E._build_in_subprocess((root / entry.program_path).read_bytes(), [spec.with_angles(alpha, beta)], E.BUILD_TIMEOUT_S)
    return circuits[0], {"which": "headline", "entry": hid, "program_sha256": entry.program_sha256}


def cross_verdict(circuit_encoding, target_encoding, which="general", alpha=0.37, beta=0.61, order=1, root=None):
    """evaluator.evaluate(step_circuit(...)[0], get_encoding(circuit_encoding), transported_target(target_encoding, circuit_encoding,
    "step", alpha, beta, order))."""
    from su2plaq.evaluate.evaluator import evaluate

    qc, _info = step_circuit(circuit_encoding, which, alpha, beta, order, root=root)
    return evaluate(qc, _enc(circuit_encoding), transported_target(target_encoding, circuit_encoding, "step", alpha, beta, order))

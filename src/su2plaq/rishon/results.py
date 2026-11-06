"""Helpers of the M5 results script (prompts/200 §2.8, step 5.10): JSON blocks computed from the code, none typed in.

* `verdict_to_dict`      RishonVerdict -> the JSON `verification` block (nested `inner_verdict`).
* `physics_block`        {"dim","closed","u2_sector","inner_span_rank","bright_pairs"} + detail (U(1) sectors, kappa multiset).
* `register_rows`        48-qubit JW register, 36-qubit 3-per-link codeword variant (size row only), touched qubits.
* `outer_electric_check` sampled check of U_E with the outer electric row (writes/restores outer qubits, so `verify` is
                         not used): the circuit is diagonal in the computational basis, compared with the phase
                         exp(-i alpha (3/4) #Q) on seeded valid 48-bit codes.
* `observable_rows`      flatten `observables.observables_table()` into one row per (angle pair, n, theory).
"""
from __future__ import annotations

import collections
import math

import numpy as np

from su2plaq.evaluate import sparse_sim as ss
from su2plaq.rishon import operators as _ops
from su2plaq.rishon import physical as _phys
from su2plaq.rishon.verify import RishonVerdict

SEED = 20261104


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, (complex, np.complexfloating)):
        return [float(x.real), float(x.imag)]
    return x


def verdict_to_dict(v: RishonVerdict) -> dict:
    """All RishonVerdict fields (phase as [re, im]); `inner_verdict` is the nested laptop verdict block."""
    from su2plaq.results.store import verdict_to_dict as _laptop

    d = {k: getattr(v, k) for k in ("ok", "reason", "certified", "op_norm_error", "block_error", "leak_amplitude",
                                    "dropped_total", "max_leak", "dirty_ancilla", "phase", "gauss_residual", "gauss_states",
                                    "outer_bits_read", "method", "engine", "seconds", "tolerances")}
    d["failing_inputs"] = list(v.failing_inputs)
    d["inner_verdict"] = None if v.inner_verdict is None else _laptop(v.inner_verdict)
    d["extra"] = dict(v.extra)
    return _jsonable(d)


def physics_block(enc) -> tuple[dict, dict]:
    """(physics, detail).  `physics` has exactly the five keys of the plan (§2.8); `detail` carries the rest (U(1) sectors,
    the kappa multiset, the counts of the fusion route for comparison)."""
    b = enc.basis
    c = _phys.counts(b)
    f = _phys.count_by_fusion()
    pairs = _ops.bright_pairs()
    kappa = collections.Counter(round(float(k), 9) for _, _, k in pairs)
    physics = {"dim": int(c["dim"]), "closed": int(c["closed"]), "u2_sector": int(c["u2_sector"]),
               "inner_span_rank": int(_phys.inner_span(b).shape[1]), "bright_pairs": len(pairs)}
    detail = {"n_u1_sectors": int(c["n_u1_sectors"]), "type_patterns": int(c["type_patterns"]),
              "kappa_multiset": {f"{k:.9g}": int(n) for k, n in sorted(kappa.items())},
              "n_inner_codes": int(len(enc.inner_codes())), "n_dark_codes": int(len(_ops.dark_codes())),
              "inner_span_rank_by_corners": int(_phys.inner_span_rank_by_corners()),
              "counts_by_fusion": {k: int(v) for k, v in f.items() if isinstance(v, (int, np.integer))},
              "coo_entries": int(c["coo_entries"]), "max_components": int(c["max_components"])}
    return physics, detail


def touched_qubits(qc) -> list[int]:
    """Sorted register positions acted on by any gate of `qc`: position i < 16 is qubit i of the register `d`, 16 + i is
    qubit i of the register `o`; qubits of any other register (ancillas) are not counted."""
    offset = {"d": 0, "o": 16}
    s = set()
    for inst in qc.data:
        if inst.operation.name == "barrier":
            continue
        for q in inst.qubits:
            for reg, idx in qc.find_bit(q).registers:
                if reg.name in offset:
                    s.add(offset[reg.name] + idx)
    return sorted(s)


def register_rows(enc, circuits: dict) -> dict:
    """Register-size rows.  `circuits` maps a label to a built circuit (the step, U_E, U_B, ...).
    jw_4_per_link: 12 links x 4 modes (the built register); codeword_3_per_link: ceil(log2 6) qubits per link, a SIZE row
    only (no circuit is built for it); touched: the data qubits (below 16) acted on by the step circuit."""
    n_modes = len(enc.registers["link_b"])
    n_links = (enc.n_data + enc.n_outer) // n_modes
    n_states = 6
    bits = math.ceil(math.log2(n_states))
    touched = {name: touched_qubits(qc) for name, qc in circuits.items()}
    step_t = touched["step"]
    rows = {
        "jw_4_per_link": {"qubits": n_modes * n_links, "inner_qubits": enc.n_data, "outer_qubits": enc.n_outer,
                          "touched": len(step_t), "touched_qubits": step_t,
                          "note": "built: two fermionic rishon modes x two colours per link, Jordan-Wigner"},
        "codeword_3_per_link": {"qubits": bits * n_links, "inner_qubits": bits * (enc.n_data // n_modes), "touched": None,
                                "note": f"size row only: {n_states} link states -> {bits} qubits per link; no circuit built"},
    }
    return {"rows": rows, "touched_by_circuit": {k: {"n": len(v), "qubits": v} for k, v in touched.items()},
            "definitions": {"qubits": "size of the encoded register", "touched": "register qubits acted on by the step circuit "
                            "(ancillas excluded)"}}


def outer_electric_check(qc, enc, alpha: float, n_codes: int = 4000, seed: int = SEED, cap: int = 5_000_000) -> dict:
    """The circuit `qc` (48-qubit U_E with the outer electric row) against exp(-i alpha (3/4) #Q(code)) on up to `n_codes`
    seeded valid 48-bit codes (drawn from the keys of the 17 closed + 256 seeded physical states).  One global phase is
    fitted.  error = max over codes of the L2 norm of (output - phase * target) -- includes any leak to other codes.
    A sampled check, not a certificate."""
    sample = enc.physical_vectors("sample")
    codes = np.unique(np.concatenate([np.asarray(k, dtype=np.int64) for k in sample.codes]))
    rng = np.random.default_rng(seed)
    if len(codes) > n_codes:
        codes = np.sort(rng.choice(codes, size=n_codes, replace=False))
    nq = np.array([enc.decode(int(c)).count("Q") for c in codes], dtype=np.float64)
    tgt = np.exp(-0.75j * alpha * nq)
    batch = ss.run_batch(qc, codes, cap=cap)
    own = batch.keys == codes[batch.cols]
    a = np.zeros(len(codes), dtype=np.complex128)
    np.add.at(a, batch.cols[own], batch.amps[own])
    z = np.sum(a * np.conj(tgt))
    phase = z / abs(z) if abs(z) > 0 else 1.0 + 0j
    res = batch.amps.copy()
    res[own] -= (phase * tgt)[batch.cols[own]]
    err = np.sqrt(np.bincount(batch.cols, weights=np.abs(res) ** 2, minlength=len(codes)))
    return {"max_error": float(err.max()), "n_codes": int(len(codes)), "phase": phase, "seed": seed,
            "max_branches": int(np.bincount(batch.cols, minlength=len(codes)).max()),
            "target": "exp(-i alpha (3/4) #Q) per valid 48-bit code, #Q = number of type-Q links among the 12 (decoded "
                      "independently of the circuit)"}


def observable_rows(tab: dict) -> dict:
    """observables_table() -> {"angles", "rishon": [rows], "ks": [rows], ...}: one row {alpha, beta, n, E_link, P, echo} per
    (angle pair, n); closed forms and the deviation of the n = 1 rows from them are added."""
    out = {"angles": tab["angles"], "rishon": [], "ks": [], "closed_forms": tab["closed_forms"],
           "closed_spectra": tab["closed_spectra"], "definitions": tab["definitions"]}
    dev = 0.0
    for i, (alpha, beta) in enumerate(tab["angles"]):
        for th in ("rishon", "ks"):
            for n, v in tab[th][i].items():
                out[th].append({"alpha": alpha, "beta": beta, "n": int(n), **{k: float(x) + 0.0 for k, x in v.items()}})   # + 0.0: -0.0 -> 0.0
                if int(n) == 1:
                    dev = max(dev, *(abs(v[k] - tab["closed_forms"][i][th][k]) for k in ("E_link", "P", "echo")))
    out["closed_forms_max_dev_n1"] = float(dev)
    return out


def outer_electric_certify(qc, enc, alpha: float, tol_err: float = 1e-10) -> dict:
    """Exhaustive per-link certificate of the outer electric row (prompts/202 section 1 O1; step O1)."""
    raise NotImplementedError("prompts/202 step O1")

"""The three-layer step of the rishon track (prompts/204 sections 5, 6.1; METHODS-rishon R14, R16).

The compression loop works on the unit U_B(beta) U_E(alpha); the det layer U_D(eta) is added in FRONT of it, outside the loop:
U_B U_D U_E = [U_B U_E] U_D because [U_D, U_E] = 0 (M5-DT3).  This module holds the locked definitions (the three triples and the
eta set for the angle-averaged T count of the det layer), the laptop metrics of the det layer, and the verification of the headline
program with the det layer prepended.  NOT in RISHON_EVALUATOR_FILES: it decides no loop verdict.

  python -m su2plaq.rishon.compress.three_layer [--entry ID] [--kind step] [--root R] [--out PATH]
      -> results/compress/rishon/three-layer.json (+ "evaluator_sha256", "provenance"); run on a clean commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)

ENC = "rishon"
DET_TRIPLES = ((0.37, 0.61, 0.29), (0.91, 0.23, 0.53), (1.70, 1.00, 1.07))      # (alpha, beta, eta): nominal and the two alternates
ETA_SET_SEED, ETA_SET_N, ETA_SET_RANGE = 20261110, 20, (0.05, 1.2)
# separate generator from the (alpha, beta) set of robust.py (prompts/203 section 13 E3), whose sha stays unchanged
ETA_SET: tuple[float, ...] = tuple(float(x) for x in np.random.default_rng(ETA_SET_SEED).uniform(*ETA_SET_RANGE, ETA_SET_N))


def _spec(kind="step"):
    from su2plaq.rishon.compress.spec import rishon_spec

    return rishon_spec(kind)


def det_layer_metrics(eta: float = 0.29) -> dict:
    """Laptop `metrics(build_UD(eta, with_outer=True), spec, measured=True)` (48 qubits: the 32 outer qubits are in the register, as
    for every rishon circuit): "cx", "n_rot", "t_fixed", "t_eps" (T at 1e-6, pygridsynth), "depth_ct", "qubits", "key"; plus
    "t_eps_set" (T over ETA_SET), "t_sum", "t_mean" (angle average) and "eta"."""
    from su2plaq.circuits.rishon import build_UD
    from su2plaq.compress.metrics import key, metrics

    spec = _spec()
    m = metrics(build_UD(eta, with_outer=True), spec, measured=True)
    ts = [int(metrics(build_UD(e, with_outer=True), spec, measured=True)["t_eps"]) for e in ETA_SET]
    return {"eta": float(eta), "cx": m["cx"], "n_rot": m["n_rot"], "t_fixed": m["t_fixed"], "t_eps": m["t_eps"],
            "depth_ct": m["depth_ct"], "qubits": m["qubits"], "key": list(key(m)), "t_eps_set": ts, "t_sum": int(sum(ts)),
            "t_mean": float(sum(ts) / len(ts))}


def verify_three_layer(entry_id: str | None = None, kind: str = "step", root=None) -> dict:
    """The archive entry `entry_id` (default: the robust headline) rebuilt from its program at the three (alpha, beta) pairs, with the
    det layer prepended (`circuits.rishon.prepend_det_layer`), verified against the three-layer target on the 1296 inner codes
    (`rishon.verify.verify(..., eta=eta)`: ok and certified, Gauss sample, rishon prune cap).
    -> {"entry", "program_sha256", "triples", "verdicts" [{"ok","certified","reason","op_norm_error","block_error","leak_amplitude",
    "dropped_total","gauss_residual"} x3], "skeleton_equal", "ok", "unit_key", "det_key", "three_layer_key" (laptop key of the
    composite at the nominal triple), "unit_t_mean", "det_t_mean", "three_layer_t_mean", "outer_touched"}."""
    from su2plaq.circuits.rishon import prepend_det_layer
    from su2plaq.compress import archive as A
    from su2plaq.compress.metrics import key, metrics
    from su2plaq.compress.spec import ROOT
    from su2plaq.encodings.rishon import RishonEncoding
    from su2plaq.rishon.compress import evaluate as E
    from su2plaq.rishon.compress import robust
    from su2plaq.rishon.verify import verify

    root = pathlib.Path(root) if root is not None else ROOT
    spec = _spec(kind)
    arch = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True)
    head = robust.headline(kind, root=root)
    eid = entry_id or head["id"]
    if eid is None:
        raise ValueError("the rishon archive has no headline entry")
    entry = next((x for x in arch.entries() if x.id == eid), None)
    if entry is None or not entry.valid:
        raise ValueError(f"{eid!r} is not a valid entry of the rishon archive")
    row = next(r for r in head["ranking"] if r["id"] == eid)
    if row["t_mean"] is None:
        raise ValueError(f"{eid!r} has no robust metrics (circuit-valued row or changing skeleton)")
    src = robust._program_file(entry.program_path, root).read_bytes()
    sha = hashlib.sha256(src).hexdigest()
    if sha != entry.program_sha256:
        raise RuntimeError(f"program file of {eid} differs from the archived sha256")
    specs = [spec.with_angles(a, b) for a, b, _ in DET_TRIPLES]
    units, _ = E._build_in_subprocess(src, specs, E.BUILD_TIMEOUT_S)
    enc = RishonEncoding()
    verdicts, skels, fulls = [], [], []
    for (a, b, eta), unit in zip(DET_TRIPLES, units):
        full = prepend_det_layer(unit, eta)
        fulls.append(full)
        skels.append([tuple(x) for x in E.skeleton(full)])
        v = verify(full, enc, "step", a, b, 1, eta=eta)
        verdicts.append({"ok": bool(v.ok), "certified": bool(v.certified), "reason": v.reason, "op_norm_error": v.op_norm_error,
                         "block_error": v.block_error, "leak_amplitude": v.leak_amplitude, "dropped_total": v.dropped_total,
                         "gauss_residual": v.gauss_residual})
    touched = {fulls[0].find_bit(q).index for inst in fulls[0].data for q in inst.qubits}
    skeleton_equal = all(s == skels[0] for s in skels)
    mu, m3 = metrics(units[0], spec, measured=True), metrics(fulls[0], spec, measured=True)
    dm = det_layer_metrics(DET_TRIPLES[0][2])
    return {"entry": eid, "program_sha256": sha, "triples": [list(t) for t in DET_TRIPLES], "verdicts": verdicts,
            "skeleton_equal": bool(skeleton_equal), "ok": bool(skeleton_equal and all(x["ok"] and x["certified"] for x in verdicts)),
            "unit_key": [int(x) for x in key(mu)], "det_key": [int(x) for x in dm["key"]], "three_layer_key": [int(x) for x in key(m3)],
            "unit_t_mean": float(row["t_mean"]), "det_t_mean": dm["t_mean"], "three_layer_t_mean": float(row["t_mean"]) + dm["t_mean"],
            "outer_touched": bool(touched & set(range(16, 48)))}


def main(argv=None) -> int:
    from su2plaq.compress.spec import ROOT
    from su2plaq.metrics.provenance import provenance
    from su2plaq.rishon.compress import code_hash

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--entry", default=None, help="archive entry id (default: the robust headline)")
    ap.add_argument("--kind", default="step")
    ap.add_argument("--root", default=None)
    ap.add_argument("--out", default=None, help="default: <root>/results/compress/rishon/three-layer.json")
    a = ap.parse_args(argv)
    root = pathlib.Path(a.root) if a.root else ROOT
    snap = provenance({"eta_set": ETA_SET_SEED})
    res = verify_three_layer(a.entry, a.kind, root=root)
    res = {**res, "kind": a.kind, "encoding": ENC, "evaluator_sha256": code_hash(), "eta_set": {"seed": ETA_SET_SEED, "n": ETA_SET_N,
           "range": list(ETA_SET_RANGE)}, "provenance": snap}
    out = pathlib.Path(a.out) if a.out else root / "results" / "compress" / ENC / "three-layer.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps({k: res[k] for k in ("entry", "ok", "unit_key", "det_key", "three_layer_key")}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

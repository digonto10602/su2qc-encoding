"""Fuzzy inner step composed from the two unit HEADLINES (prompts/010 §4.3, step H.3).

`fuzzy.compress_hook.best_step` composes the step from the archive-best entry of each unit (locked by M10-G3 to `compressed_step.json`).
Here the units are the HEADLINE entries of the robust rule (`compress/robust.headline`, the smallest robust key over the 20 angle
pairs; cached, never computed here): fuzzy_ub `r10-F1-010` instead of the archive best `r12-F1-012`, fuzzy_link `r02-F2-001`.  The
composition itself is `compress_hook.compose_step` (via `entry_fn`); nothing of it is duplicated.

Not in `registry._FUZZY_FILES` (`fuzzy/compress_hook.py` is hashed and is not edited).  Command: `python scripts/m10_round.py headline-step`."""
from __future__ import annotations

import json
import pathlib

from su2plaq.compress.round import check_program_sha
from su2plaq.fuzzy import compress_hook as H

RULE = "headline"
OUT_NAME = "compressed_step_headline.json"


def _cached_unit(enc: str, root):
    """(archive entry, ranking row) of the cached headline of `enc`; FileNotFoundError if the headline is not cached."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import robust as RB
    from su2plaq.compress.spec import default_spec

    kind = H.UNITS[enc]
    h = RB.headline(enc, kind, root=root, compute=False)
    if h is None or h.get("id") is None:
        raise FileNotFoundError(f"no cached headline of {enc} under {H._root(root) / 'results' / 'compress' / enc / 'robust.json'} "
                                f"(run `python -m su2plaq.compress.robust --encoding {enc} --kind {kind}` first)")
    row = next(r for r in h["ranking"] if r["id"] == h["id"])
    spec = default_spec(enc, kind)
    arch = A.Archive.load(enc, root=H._root(root), n_alt=len(spec.alt_angles), strict=True)
    entry = next(e for e in arch.entries() if e.id == h["id"])
    if not str(entry.program_path).endswith(".circuit"):          # circuit-valued baselines have no file
        check_program_sha(entry.program_path, entry.program_sha256, root=H._root(root))      # audit 305 N3 (compress_hook.circuit_of_entry does not)
    return entry, row, spec


def _unit_fns(root):
    """({enc: unit callable}, {enc: {"entry", "key", "robust_key", "t_mean"}}, {enc: ranking row}) for the two headline units."""
    H.install()
    fns, units, rows = {}, {}, {}
    for enc in H.ENCODINGS:
        entry, row, spec = _cached_unit(enc, root)
        fns[enc] = H.entry_fn(entry, spec, root=root)
        units[enc] = {"entry": entry.id, "key": [float(x) for x in entry.key], "robust_key": [int(x) for x in row["robust_key"]],
                      "t_mean": float(row["t_mean"])}
        rows[enc] = row
    return fns, units, rows


def _compose(fns, order: int, with_outer: bool):
    return H.compose_step(fns["fuzzy_link"], fns["fuzzy_ub"], H.NOMINAL[0], H.NOMINAL[1], None, order, with_outer)


def headline_step(root=None, order: int = 1, with_outer: bool = True):
    """-> (composed circuit from the headline entry of each unit, {"units": {enc: {"entry", "key", "robust_key", "t_mean"}},
    "metrics": compress_hook._metrics_dict(qc)}).  FileNotFoundError if a headline is not cached (nothing is computed or written)."""
    fns, units, _ = _unit_fns(root)
    qc = _compose(fns, order, with_outer)
    return qc, {"units": units, "metrics": H._metrics_dict(qc)}


def write_headline_step(root=None, out=None, order: int = 1, with_outer: bool = True) -> dict:
    """Compose from the headline units, verify with `verify_step_samples` (the call of M10-G3), write
    results/fuzzy/compressed_step_headline.json (same provenance block as compressed_step.json)."""
    from su2plaq.fuzzy.verify import verify_step_samples
    from su2plaq.metrics.provenance import provenance

    root = H._root(root)
    fns, units, rows = _unit_fns(root)
    qc = _compose(fns, order, with_outer)
    composed = H._metrics_dict(qc)
    v = verify_step_samples(qc, H.NOMINAL[0], H.NOMINAL[1], 0.5 * H.NOMINAL[0], order, n_random=32, n_phys=8, seed=H.SEED)
    inner = composed if not with_outer else H._metrics_dict(_compose(fns, order, False))
    ub, lk = rows["fuzzy_ub"], rows["fuzzy_link"]
    inner_doc = {k: inner[k] for k in ("cx", "n_rot", "t_fixed", "depth", "qubits")}
    inner_doc["t_mean"] = units["fuzzy_ub"]["t_mean"] + 4 * units["fuzzy_link"]["t_mean"]          # U_B + the 4 inner link blocks
    inner_doc["t_nominal"] = int(ub["t_nominal"]) + 4 * int(lk["t_nominal"])
    gen = H.step_metrics(H.general_link_fn, H.general_ub_fn, with_outer, order)
    doc = {"rule": RULE, "order": order, "with_outer": with_outer, "units": units, "composed": composed, "inner": inner_doc, "general": gen,
           "verification": {"err": float(v["err"]), "gauss": float(v["gauss"]), "n_inputs": int(v["n_inputs"]), "seed": H.SEED,
                            "mode": v["mode"], "leak": float(v["leak"])},
           "provenance": provenance({"verify_seed": H.SEED})}
    path = pathlib.Path(out) if out is not None else root / "results" / "fuzzy" / OUT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, default=str))
    return doc

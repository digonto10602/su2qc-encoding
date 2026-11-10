"""The headline rule of the rishon track (prompts/203 section 13, erratum E3; mirrored from the spinnet erratum prompts/104 section 11 E3).

The laptop archive key (CX, T_1e-6, depth_CT, qubits) counts T at the single nominal angle pair, which rewards pygridsynth luck
(an exact rewrite Rz(theta) = Rz(theta +- pi/4) T^-+ costs +1 T at every angle and re-draws the Ross-Selinger remainder).  The track's
HEADLINE circuit (Report 6, `results/rishon/m6-compressed.json`, the Lean theorem file) is therefore the valid archive entry with the
smallest ROBUST key

    (CX, sum_i T_1e-6(angles_i), rho, sum_i depth_CT(angles_i), qubits),   i = 1..20 over the locked set `ANGLE_SET`,

lexicographic integers; full ties: the laptop key, then the id.  rho = 0 if every rotation angle of the nominal circuit is
(m_alpha alpha + m_beta beta + m_gamma sqrt2 beta)/d, d <= 64 (`lean_cert.recognise_angle`) and the fitted expression reproduces the
angle at all 20 pairs to 1e-9, else 1.  The archive (key, cells, elites, `Archive.best()`) is untouched; validity is the laptop's.
T counting needs only the rebuilt circuit and pygridsynth, never the 1296-code evaluation.

  python -m su2plaq.rishon.compress.robust (headline [--refresh] | report | metrics <program.py>) [--kind step] [--root R]

This module imports only numpy/hashlib at top level (the spec renderer and the brief import it); everything else is imported inside
the functions.  `render_spec` of `rishon.compress.spec` is wrapped in the package `__init__` (`with_headline_section`) instead of
being edited, because spec.py is part of `RISHON_EVALUATOR_FILES`: editing it would change the evaluator hash of every archived entry
(`test_M6_G1` compares the archive best's `evaluator_sha256` with the current hash).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import sys

import numpy as np

ENC = "rishon"
ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20
ANGLE_SET_RANGES = ((0.05, 2.0), (0.05, 1.2))
LINEAR_TOL = 1e-9                          # the fitted angle expression must reproduce every rotation angle at every pair to this
ROTATION_GATES = ("rz", "p", "crz", "crx", "cp")


def _make_angle_set() -> tuple[tuple[float, float], ...]:
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_SET_RANGES[0], ANGLE_SET_N)           # all alphas first ...
    b = rng.uniform(*ANGLE_SET_RANGES[1], ANGLE_SET_N)           # ... then all betas
    return tuple((float(x), float(y)) for x, y in zip(a, b))


ANGLE_SET: tuple[tuple[float, float], ...] = _make_angle_set()

HEADLINE_SECTION_TITLE = "## Headline rule (track R)"
HEADLINE_SECTION = HEADLINE_SECTION_TITLE + """

The archive key counts T at the nominal pair; the Report 6 headline and the Lean theorem file go to the smallest robust key (CX, T summed over 20 fixed random angle pairs, angle-linear first, depth, qubits). Offsetting a rotation by $\\pm\\pi/4$ with a compensating `t`/`tdg` costs +1 T at every angle and saves nothing on average: it will not count. Offsets that are multiples of $\\pi/2$ belong in separate `s`/`sdg`/`z` gates so that the rotation angle stays $(m_\\alpha\\alpha+m_\\beta\\beta+m_\\gamma\\sqrt2\\beta)/d$ (Lean-certifiable). Fewer CX, fewer rotations, smaller coefficients and shared rotations are what move the headline.
"""


def angle_set_sha256() -> str:
    """sha256 of the repr of the locked angle pairs (identifies the set in every cache and report)."""
    return hashlib.sha256(repr(ANGLE_SET).encode()).hexdigest()


def with_headline_section(render):
    """`render_spec` wrapped so that the headline section stands before `## Tools` (idempotent: a wrapped function is returned as is)."""
    if getattr(render, "_headline_wrapped", False):
        return render

    def render_spec(spec) -> str:
        text = render(spec)
        i = text.index("## Tools")
        return text[:i] + HEADLINE_SECTION + "\n" + text[i:]

    render_spec._headline_wrapped = True
    render_spec.__doc__ = render.__doc__
    return render_spec


def _root(root=None) -> pathlib.Path:
    from su2plaq.compress.spec import ROOT

    return pathlib.Path(root) if root is not None else ROOT


def _program_file(program_path, root=None) -> pathlib.Path:
    """Absolute path of a program: absolute as given, else under `root`, else under the repository root."""
    f = pathlib.Path(program_path)
    if f.is_absolute():
        return f
    r = _root(root)
    return r / f if (r / f).exists() else _root(None) / f


def _rotation_angles(qc) -> list:
    return [float(i.operation.params[0]) for i in qc.data if i.operation.name in ROTATION_GATES]


def robust_metrics(program_path, spec=None, root=None) -> dict:
    """Angle-averaged cost of a program.  Rebuilt through the rishon build worker at the nominal pair and the 20 pairs of `ANGLE_SET`
    in one call; the laptop `metrics(measured=True)` gives T(1e-6) and depth_CT at every pair.
    -> {"program_sha256", "angle_set_sha256", "skeleton_equal", "t_eps": [20 int], "depth_ct": [20 int], "t_sum", "depth_sum",
    "t_mean", "cx", "qubits", "angle_linear", "angle_fit": [(m_alpha, m_beta, m_gamma, d) | None per rotation of the nominal
    circuit], "robust_key": (cx, t_sum, 0|1, depth_sum, qubits) | None}.  `robust_key` is None when the gate skeleton changes
    over the 21 pairs (the laptop's no-fixed-angle-tricks rule extended to the set)."""
    from su2plaq.compress import metrics as M
    from su2plaq.compress.spec import default_spec
    from su2plaq.rishon.compress import evaluate as E
    from su2plaq.rishon.lean_cert import recognise_angle

    spec = spec if spec is not None else default_spec(ENC, "step")
    src = _program_file(program_path, root).read_bytes()
    specs = [spec.with_angles(a, b) for a, b in ANGLE_SET]
    circuits, _ = E._build_in_subprocess(src, [spec, *specs], E.BUILD_TIMEOUT_S)
    nominal, circuits = circuits[0], circuits[1:]
    skeleton_equal = len({tuple(map(tuple, E.skeleton(c))) for c in [nominal, *circuits]}) == 1
    ms = [M.metrics(c, s, measured=True) for c, s in zip(circuits, specs)]
    t_eps = [int(m["t_eps"]) for m in ms]
    depth_ct = [int(m["depth_ct"]) for m in ms]
    fits = [recognise_angle(th, spec.alpha, spec.beta) for th in _rotation_angles(nominal)]
    linear = skeleton_equal and all(f is not None for f in fits)
    if linear and fits:
        per_pair = [_rotation_angles(c) for c in circuits]
        sq2 = math.sqrt(2.0)
        for (a, b), angles in zip(ANGLE_SET, per_pair):
            for f, th in zip(fits, angles):
                ma, mb, mg, d = f
                if abs((ma * a + mb * b + mg * sq2 * b) / d - th) > LINEAR_TOL:
                    linear = False
    out = {"program_sha256": hashlib.sha256(src).hexdigest(), "angle_set_sha256": angle_set_sha256(), "skeleton_equal": skeleton_equal,
           "t_eps": t_eps, "depth_ct": depth_ct, "t_sum": sum(t_eps), "depth_sum": sum(depth_ct), "t_mean": sum(t_eps) / len(t_eps),
           "cx": int(ms[0]["cx"]), "qubits": int(ms[0]["qubits"]), "angle_linear": bool(linear),
           "angle_fit": [None if f is None else tuple(int(x) for x in f) for f in fits]}
    out["robust_key"] = ((out["cx"], out["t_sum"], 0 if linear else 1, out["depth_sum"], out["qubits"]) if skeleton_equal else None)
    return out


def _angle_set_record() -> dict:
    return {"seed": ANGLE_SET_SEED, "n": ANGLE_SET_N, "ranges": [list(r) for r in ANGLE_SET_RANGES],
            "pairs": [list(p) for p in ANGLE_SET], "sha256": angle_set_sha256()}


def _lean_status(entry):
    return entry.lean.get("status") if isinstance(entry.lean, dict) else None


def _has_program(e, root) -> bool:
    if str(e.program_path).endswith(".circuit"):
        return False
    return _program_file(e.program_path, root).exists()


def headline(kind="step", root=None, refresh: bool = False) -> dict:
    """The headline entry of the archive: among the valid entries, the smallest robust key (full ties: laptop key, then id).  Valid
    entries without a program file (circuit-valued rows) and entries whose skeleton changes over the angle set are ranked last with
    key None.  Per-entry `robust_metrics` are cached in <root>/results/compress/rishon/robust.json, keyed by (id, program_sha256,
    angle_set_sha256) and the rishon evaluator hash; a mismatch (or `refresh`) recomputes.
    -> {"id", "robust_key", "t_mean", "lean", "archive_best", "archive_best_robust_key", "ranking": [{"id", "robust_key", "t_mean",
    "lean", "laptop_key", "family", "round", "cx", "qubits", "t_nominal", "depth_mean", "angle_linear"}...]}, None keys last."""
    from su2plaq.compress import archive as A
    from su2plaq.compress.spec import default_spec
    from su2plaq.rishon.compress import code_hash

    root = _root(root)
    spec = default_spec(ENC, kind)
    arch = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True)
    valid = sorted((e for e in arch.entries() if e.valid), key=lambda e: e.id)
    best = arch.best()
    cache_file = root / "results" / "compress" / ENC / "robust.json"
    ev_sha, as_sha = code_hash(), angle_set_sha256()
    cached = {}
    if cache_file.exists() and not refresh:
        cache = json.loads(cache_file.read_text())
        if cache.get("evaluator_sha256") == ev_sha and cache.get("angle_set", {}).get("sha256") == as_sha:
            cached = cache.get("entries", {})
    store = {"angle_set": _angle_set_record(), "evaluator_sha256": ev_sha, "entries": {}}
    for e in valid:
        if not _has_program(e, root):
            continue
        rec = cached.get(e.id)
        if rec is None or rec.get("program_sha256") != e.program_sha256 or rec.get("angle_set_sha256") != as_sha:
            rec = robust_metrics(e.program_path, spec, root=root)
            rec["laptop_key"] = [int(x) for x in e.key]
            if rec["program_sha256"] != e.program_sha256:
                raise RuntimeError(f"program file of {e.id} ({e.program_path}) differs from the archived sha256")
            rec = json.loads(json.dumps(rec))          # the cached (JSON) shape, also for fresh entries
        store["entries"][e.id] = rec
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(store, indent=1))
        tmp.replace(cache_file)
    rows = []
    for e in valid:
        rec = store["entries"].get(e.id)
        base = {"id": e.id, "lean": _lean_status(e), "laptop_key": tuple(int(x) for x in e.key), "family": e.family, "round": e.round,
                "cx": int(e.key[0]), "qubits": int(e.key[3]), "t_nominal": int(e.key[1])}
        if rec is None or rec["robust_key"] is None:
            rows.append({**base, "robust_key": None, "t_mean": None, "depth_mean": None, "angle_linear": None})
        else:
            rows.append({**base, "robust_key": tuple(rec["robust_key"]), "t_mean": rec["t_mean"], "cx": rec["cx"], "qubits": rec["qubits"],
                         "depth_mean": rec["depth_sum"] / len(rec["depth_ct"]), "angle_linear": rec["angle_linear"]})
    rows.sort(key=lambda r: (r["robust_key"] is None, r["robust_key"] or (), r["laptop_key"], r["id"]))
    top = rows[0] if rows and rows[0]["robust_key"] is not None else None
    best_row = next((r for r in rows if best is not None and r["id"] == best.id), None)
    return {"id": top["id"] if top else None, "robust_key": top["robust_key"] if top else None,
            "t_mean": top["t_mean"] if top else None, "lean": top["lean"] if top else None,
            "archive_best": best.id if best else None,
            "archive_best_robust_key": best_row["robust_key"] if best_row else None, "ranking": rows}


_LEAN_WORDS = {"certified": "certified", "accepted": "certified", "failed": "failed", "rejected": "failed"}


def _lean_word(status) -> str:
    return "not_run" if status is None else _LEAN_WORDS.get(status, "n_a")


def report_table(kind="step", root=None) -> str:
    """Laptop `report.report_table("rishon", kind, root)` (also writes results/compress/rishon/summary.json) followed by the HEADLINE
    table of prompts/203 section 13 E3: GLOBAL BEST by the laptop key, HEADLINE by the robust key, best per family by the robust key;
    T_avg = T(1e-6) averaged over `ANGLE_SET`.  summary.json gains "headline" {id, robust_key, t_mean, angle_set_sha256}, "t_avg"
    {id: T_avg} and `t_avg` in every lineage item."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import report
    from su2plaq.compress.spec import default_spec

    root = _root(root)
    text = report.report_table(ENC, kind, root=root)
    h = headline(kind, root)
    arch = A.Archive.load(ENC, root=root, n_alt=len(default_spec(ENC, kind).alt_angles), strict=True)
    best = arch.best()
    by_id = {r["id"]: r for r in h["ranking"]}
    header = ["entry", "family", "round", "CX", "T nominal", "T_avg(1e-6)", "depth_CT avg", "qubits", "angle-linear", "Lean"]

    def row(label, i):
        r = by_id[i]
        if r["robust_key"] is None:
            return [f"{label}{i}", r["family"], r["round"], r["cx"], r["t_nominal"], "-", "-", r["qubits"], "-", _lean_word(r["lean"])]
        return [f"{label}{i}", r["family"], r["round"], r["cx"], r["t_nominal"], f"{r['t_mean']:.2f}", f"{r['depth_mean']:.1f}",
                r["qubits"], "yes" if r["angle_linear"] else "no", _lean_word(r["lean"])]

    rows = []
    if best is not None:
        rows.append(row("GLOBAL BEST (laptop key): ", best.id))
    if h["id"] is not None:
        rows.append(row("HEADLINE (robust key): ", h["id"]))
    fam_best = {}
    for r in h["ranking"]:
        if r["robust_key"] is not None:
            fam_best.setdefault(r["family"], r["id"])
    rows += [row(f"best of family {f} (robust key): ", fam_best[f]) for f in sorted(fam_best)]
    lines = ["", "### HEADLINE (angle-averaged T, prompts/203 §13 E3)", "", "| " + " | ".join(header) + " |",
             "|" + "|".join("---" for _ in header) + "|"] + ["| " + " | ".join(str(c) for c in rw) + " |" for rw in rows]
    lines += ["", "GLOBAL BEST is the archive's laptop-key minimum (CX, T(1e-6) at the nominal pair, depth_CT, qubits); HEADLINE is the "
              f"smallest robust key (CX, sum of T(1e-6) over the {ANGLE_SET_N} fixed random angle pairs of seed {ANGLE_SET_SEED}, "
              "angle-linear first, sum of depth_CT, qubits). T_avg = sum T / " + f"{ANGLE_SET_N}; angle set sha256 {angle_set_sha256()[:16]}."]
    unrank = [r["id"] for r in h["ranking"] if r["robust_key"] is None]
    if unrank:
        lines.append("No robust key (no program file, or the skeleton changes inside the angle set): " + ", ".join(unrank) + ".")
    summary_file = root / "results" / "compress" / ENC / "summary.json"
    summary = json.loads(summary_file.read_text())
    summary["headline"] = {"id": h["id"], "robust_key": list(h["robust_key"]) if h["robust_key"] else None, "t_mean": h["t_mean"],
                           "angle_set_sha256": angle_set_sha256()}
    summary["t_avg"] = {r["id"]: r["t_mean"] for r in h["ranking"] if r["robust_key"] is not None}
    for item in summary.get("lineage", []):
        item["t_avg"] = by_id[item["id"]]["t_mean"] if item["id"] in by_id else None
    summary_file.write_text(json.dumps(summary, indent=1))
    return text + "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.rishon.compress.robust")
    ap.add_argument("cmd", choices=["headline", "report", "metrics"])
    ap.add_argument("program", nargs="?", help="metrics: the program file")
    ap.add_argument("--kind", default="step", choices=["step", "UB", "UE"])
    ap.add_argument("--root")
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)
    import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)

    if a.cmd == "headline":
        print(json.dumps(headline(a.kind, a.root, refresh=a.refresh), indent=1, default=str))
    elif a.cmd == "report":
        print(report_table(a.kind, a.root))
    else:
        if not a.program:
            ap.error("metrics needs a program file")
        from su2plaq.compress.spec import default_spec

        print(json.dumps(robust_metrics(a.program, default_spec(ENC, a.kind), root=a.root), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

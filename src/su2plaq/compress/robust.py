"""The headline rule for every encoding (prompts/008 §6; METHODS §12): the robust key over one locked set of 20 angle pairs.

The archive key (CX, T_1e-6, depth_CT, qubits) counts T at the single nominal angle pair and is NOT changed (D1).  What is reported as
the result of a loop is the valid archive entry with the smallest ROBUST key

    (CX, sum_i T_1e-6(alpha_i, beta_i), rho, sum_i depth_CT(alpha_i, beta_i), qubits),     i = 1..20 over `ANGLE_SET`,

lexicographic integers; full ties: the archive key, then the id.  rho = 0 if the program is angle-linear, else 1: the encoding's
registered `angle_linear(circuit, spec) -> (bool, reason)` when there is one, otherwise the generic test (`generic_angle_linear`):
every rotation angle of the circuit equals c_alpha alpha + c_beta beta with coefficients fitted by least squares on the 20 pairs and a
residual of at most 1e-9 at the 20 pairs and at the nominal pair.  An entry whose gate skeleton changes over the 20 pairs or at the
nominal pair has no robust key (it is listed under `unrankable`).  Validity is the evaluator's; nothing here changes an archive.

Registry dispatch: `headline` delegates to the encoding's registered `headline(kind, root, refresh)` hook (spinnet: `loop.headline_for`,
rishon: `rishon.compress.robust.headline`; the tracks keep their own definitions of rho and caches); `robust_metrics` takes rho from
the registered `angle_linear` hook (twelve: the Lean exporter, `twelve_angle_linear`) or the generic fit (fuzzy_ub, fuzzy_link, lsh
has its own hook).  The fuzzy units use the generic fit; the constant terms it rejects are classified, for information only, by
`angle_offsets` (prompts/010 §3: a multiple of pi/2 on rz / p is a Clifford factor, costs no T and is not rewarded).

This module is NOT in a hash list: it decides no verdict and no archive metric (a robust key is a report quantity).  It imports only
numpy / hashlib at top level (the brief and the report import it); everything else is imported inside the functions.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np

ANGLE_SET_SEED, ANGLE_SET_N = 20261107, 20
ANGLE_SET_RANGES = ((0.05, 2.0), (0.05, 1.2))
GENERALITY_SEED = 20261110                # prompts/008 M2C-G4: further pairs, same ranges
LINEAR_TOL = 1e-9                         # a fitted angle expression must reproduce every rotation angle at every pair to this
OFFSET_TOL = 1e-9                         # prompts/010 §3: tolerance of the offset classification (the locked linearity value)
# smallest angle u for which a constant term k u on that gate is a Clifford factor (R_z(theta + k pi/2) = R_z(theta) S^k, cp(pi) = CZ,
# crz(pi) = S^dagger_control CZ); gates not listed have none, so a constant term on them is not Clifford
CLIFFORD_OFFSET_UNIT = {"rz": np.pi / 2, "p": np.pi / 2, "rx": np.pi / 2, "ry": np.pi / 2,
                        "crz": np.pi, "crx": np.pi, "cry": np.pi, "cp": np.pi}


def _make_angle_set() -> tuple[tuple[float, float], ...]:
    rng = np.random.default_rng(ANGLE_SET_SEED)
    a = rng.uniform(*ANGLE_SET_RANGES[0], ANGLE_SET_N)           # all alphas first ...
    b = rng.uniform(*ANGLE_SET_RANGES[1], ANGLE_SET_N)           # ... then all betas
    return tuple((float(x), float(y)) for x, y in zip(a, b))


ANGLE_SET: tuple[tuple[float, float], ...] = _make_angle_set()


def angle_set_sha256() -> str:
    """sha256 of the repr of the locked angle pairs (identifies the set in every cache and report)."""
    return hashlib.sha256(repr(ANGLE_SET).encode()).hexdigest()


def generality_points(encoding: str) -> tuple:
    """The pairs of M2C-G4 / M8-G4: two seeded pairs (seed 20261110, the ranges of `ANGLE_SET`) that no loop evaluation used, plus the
    two points (0.37, 0.0) and (0.37, 0.185) (kappa_2 = 0 and alpha/2) for the fuzzy link unit."""
    rng = np.random.default_rng(GENERALITY_SEED)
    a = rng.uniform(*ANGLE_SET_RANGES[0], 2)
    b = rng.uniform(*ANGLE_SET_RANGES[1], 2)
    pairs = [(float(x), float(y)) for x, y in zip(a, b)]
    return tuple(pairs + ([(0.37, 0.0), (0.37, 0.185)] if encoding == "fuzzy_link" else []))


HEADLINE_RULE_SECTION = """## Headline rule

The archive key counts T at the nominal angle pair; the number reported for this loop (the headline) is the valid entry with the smallest robust key (CX, T summed over 20 fixed random angle pairs, angle-linear first, depth_CT summed over the same pairs, qubits). Offsetting a rotation by $\\pm\\pi/4$ with a compensating `t`/`tdg` costs +1 T at every angle and saves nothing on average: it will not count. Offsets that are multiples of $\\pi/2$ belong in separate `s`/`sdg`/`z` gates so that every rotation angle stays a linear function of the two task angles alpha and beta (angle-linear programs rank first and can be certified for all angles). A program whose gate skeleton changes with the angles has no robust key. Fewer CX, fewer rotations, smaller rotation counts and shared rotations are what move the headline.
"""

HEADLINE_HEADER = ["entry", "family", "round", "CX", "T nominal", "T_avg(1e-6)", "depth_CT avg", "qubits", "angle-linear", "Lean"]
_LEAN_WORDS = {"certified": "certified", "accepted": "certified", "failed": "failed", "rejected": "failed"}


# ------------------------------------------------------------------------------------------------ helpers
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


def _has_program(entry, root) -> bool:
    """A real program file (circuit-valued baselines have none and cannot be rebuilt at other angles)."""
    return not str(entry.program_path).endswith(".circuit") and _program_file(entry.program_path, root).exists()


def _info(encoding: str):
    from su2plaq.encodings import registry

    return registry.lookup(encoding)


def _lean_status(entry):
    return entry.lean.get("status") if isinstance(entry.lean, dict) else None


def _lean_word(status) -> str:
    return "not_run" if status is None else _LEAN_WORDS.get(status, "n_a")


def rotation_angles(qc) -> list:
    """Every numeric gate parameter of the circuit, in program order (barriers skipped)."""
    return [float(p) for i in qc.data if i.operation.name != "barrier" for p in i.operation.params]


def generic_angle_linear(circuits, pairs) -> tuple:
    """The generic rho test.  `circuits`: one circuit per pair of `pairs` (equal skeletons), the 20 pairs of the set FIRST and the
    nominal circuit last (`pairs` the matching (alpha, beta) list).  Every rotation angle must be c_alpha alpha + c_beta beta with
    (c_alpha, c_beta) fitted by least squares on the first 20 pairs and a residual of at most 1e-9 at all pairs.
    -> (bool, "ok" | "non_linear_angle: gate parameter k ...")."""
    thetas = np.array([rotation_angles(c) for c in circuits], dtype=float)        # (pairs, n_params)
    if thetas.size == 0:
        return True, "ok"
    A = np.array(pairs, dtype=float)
    fit = A[:len(ANGLE_SET)]
    coef = np.linalg.lstsq(fit, thetas[:len(ANGLE_SET)], rcond=None)[0]            # (2, n_params)
    resid = np.abs(A @ coef - thetas)
    bad = np.flatnonzero(resid.max(axis=0) > LINEAR_TOL)
    if bad.size:
        return False, f"non_linear_angle: gate parameter {int(bad[0])} deviates by {float(resid.max(axis=0)[bad[0]]):.3e} from its linear fit"
    return True, "ok"


def angle_offsets(circuits, pairs) -> dict:
    """Classify the constant terms of the rotation angles of one program (prompts/010 §3; information only, no key uses it).
    `circuits` / `pairs` as in `generic_angle_linear` (equal skeletons, the 20 pairs of the set first, the nominal pair last).  Per gate
    parameter p, least squares on the first 20 pairs of theta_p ~ c_a alpha + c_b beta (linear) and ~ c_a alpha + c_b beta + c_0 (affine);
    r_lin, r_aff = the largest absolute residuals over all pairs and parameters; tau = OFFSET_TOL.
    "linear": r_lin <= tau (exactly the rho = 0 test); "non_affine": both residuals > tau; otherwise (affine) "clifford_offset" if every
    constant with |c_0| > tau is a multiple (within tau) of CLIFFORD_OFFSET_UNIT of its gate, else "non_clifford_offset".
    -> {"class", "affine_residual" (r_aff), "offsets" [c_0 per gate parameter, rad], "offset_units" [round(c_0 / (pi/2)) if c_0 is a
    multiple of pi/2 within tau, else None, per parameter], "gates" [gate name per parameter]}.  A circuit without parameters is "linear"."""
    thetas = np.array([rotation_angles(c) for c in circuits], dtype=float)         # (pairs, n_params)
    gates = [i.operation.name for i in circuits[0].data if i.operation.name != "barrier" for _ in i.operation.params] if len(circuits) else []
    if thetas.size == 0:
        return {"class": "linear", "affine_residual": 0.0, "offsets": [], "offset_units": [], "gates": []}
    A = np.array(pairs, dtype=float)
    n = len(ANGLE_SET)
    lin = np.linalg.lstsq(A[:n], thetas[:n], rcond=None)[0]
    r_lin = float(np.abs(A @ lin - thetas).max())
    Aff = np.hstack([A, np.ones((len(A), 1))])
    aff = np.linalg.lstsq(Aff[:n], thetas[:n], rcond=None)[0]                      # (3, n_params)
    r_aff = float(np.abs(Aff @ aff - thetas).max())
    c0 = aff[2]
    q = np.pi / 2
    units = [int(np.round(c / q)) if abs(c - q * np.round(c / q)) <= OFFSET_TOL else None for c in c0]

    def is_clifford(c, gate):
        u = CLIFFORD_OFFSET_UNIT.get(gate)
        return u is not None and abs(c - u * np.round(c / u)) <= OFFSET_TOL

    if r_lin <= OFFSET_TOL:
        cls = "linear"
    elif r_aff > OFFSET_TOL:
        cls = "non_affine"
    else:
        cls = "clifford_offset" if all(abs(c) <= OFFSET_TOL or is_clifford(c, g) for c, g in zip(c0, gates)) else "non_clifford_offset"
    return {"class": cls, "affine_residual": r_aff, "offsets": [float(c) for c in c0], "offset_units": units, "gates": gates}


# ------------------------------------------------------------------------------------------------ rho hooks
def twelve_angle_linear(circuit, spec) -> tuple:
    """Registry hook `angle_linear(circuit, spec)` of the twelve-qubit encoding (prompts/008 §6): rho = 0 unless the twelve-qubit Lean
    exporter answers `non_linear_angle:...` for the nominal circuit (as the spinnet track does with its own exporter; every other
    answer, an n_a reason or a certificate, counts as linear).  -> (bool, "ok" | the exporter's reason text)."""
    import tempfile

    from su2plaq.compress.spec import get_encoding
    from su2plaq.lean import certify as C

    with tempfile.TemporaryDirectory() as td:
        res = C.export_certificate(circuit, get_encoding(spec.encoding), spec.kind, spec.alpha, spec.beta, spec.order,
                                   pathlib.Path(td) / "angle-linearity.json")
    status = res if isinstance(res, str) else "ok"
    return (not status.startswith("non_linear_angle")), status


# ------------------------------------------------------------------------------------------------ one program
def robust_metrics(encoding, kind, program_path, root=None) -> dict:
    """Angle-averaged cost of a program (the keys of `spinnet.loop.robust_metrics`).  The program is rebuilt through the stock worker at
    the nominal pair and the 20 pairs of `ANGLE_SET` in one call; `compress.metrics.metrics(measured=True)` gives T(1e-6) and depth_CT
    at every pair of the set.
    -> {"program_sha256", "angle_set_sha256", "skeleton_equal", "t_eps": [20 int], "depth_ct": [20 int], "t_sum", "depth_sum",
    "t_mean", "cx", "qubits", "angle_linear", "export_status", "offset_class", "offset_units" (None when the skeleton changes),
    "robust_key": (cx, t_sum, 0|1, depth_sum, qubits) | None}.
    `robust_key` is None when the gate skeleton differs between any two of the 21 circuits (the nominal pair included: a program that
    differs only at the nominal pair has no robust key).  `export_status` is the reason text of the rho test ("ok" when linear)."""
    from su2plaq.compress import evaluate as E
    from su2plaq.compress import metrics as M
    from su2plaq.compress.spec import default_spec

    spec = default_spec(encoding, kind)
    src = _program_file(program_path, root).read_bytes()
    specs = [spec.with_angles(a, b) for a, b in ANGLE_SET]
    circuits, _ = E._build_in_subprocess(src, [*specs, spec], E.BUILD_TIMEOUT_S)
    nominal, circuits = circuits[-1], circuits[:-1]
    skeleton_equal = len({tuple(map(tuple, E.skeleton(c))) for c in [*circuits, nominal]}) == 1
    ms = [M.metrics(c, s, measured=True) for c, s in zip(circuits, specs)]
    t_eps = [int(m["t_eps"]) for m in ms]
    depth_ct = [int(m["depth_ct"]) for m in ms]
    info = _info(encoding)
    if not skeleton_equal:
        linear, why = False, "skeleton changes over the angle set"
    elif info is not None and info.angle_linear:
        from su2plaq.encodings import registry

        linear, why = registry.resolve(info.angle_linear)(nominal, spec)
    else:
        linear, why = generic_angle_linear([*circuits, nominal], [*ANGLE_SET, (spec.alpha, spec.beta)])
    out = {"program_sha256": hashlib.sha256(src).hexdigest(), "angle_set_sha256": angle_set_sha256(), "skeleton_equal": skeleton_equal,
           "t_eps": t_eps, "depth_ct": depth_ct, "t_sum": sum(t_eps), "depth_sum": sum(depth_ct), "t_mean": sum(t_eps) / len(t_eps),
           "cx": int(ms[0]["cx"]), "qubits": int(ms[0]["qubits"]), "angle_linear": bool(linear), "export_status": str(why)}
    if skeleton_equal:      # prompts/010 §4.1: informative, for every encoding; rho and the key above are not affected
        off = angle_offsets([*circuits, nominal], [*ANGLE_SET, (spec.alpha, spec.beta)])
        out["offset_class"], out["offset_units"] = off["class"], off["offset_units"]
    else:
        out["offset_class"], out["offset_units"] = None, None
    out["robust_key"] = ((out["cx"], out["t_sum"], 0 if linear else 1, out["depth_sum"], out["qubits"]) if skeleton_equal else None)
    return out


# ------------------------------------------------------------------------------------------------ the archive
def _angle_set_record() -> dict:
    return {"seed": ANGLE_SET_SEED, "n": ANGLE_SET_N, "ranges": [list(r) for r in ANGLE_SET_RANGES],
            "pairs": [list(p) for p in ANGLE_SET], "sha256": angle_set_sha256()}


# top-level cache keys that only a track's own headline function writes, and the function that gives the value they must equal
_HOOK_CODE_KEYS = {"spinnet_code_sha256": "su2plaq.spinnet.loop:code_hash"}


def _load_cache(cache_file: pathlib.Path, encoding: str, refresh: bool, hook: bool = False) -> dict:
    """The cached per-entry records, or {} when the file is missing, `refresh`, or keyed by another code / angle set.  `hook`: the file
    was written by the encoding's own `headline` hook (spinnet, rishon): its keys are `evaluator_sha256` (= `stamp_hash`), the angle
    set and, for spinnet, `spinnet_code_sha256`; a top-level `*_code_sha256` key this function does not know counts as stale."""
    from su2plaq.compress import provenance as P

    if refresh or not cache_file.exists():
        return {}
    cache = json.loads(cache_file.read_text())
    if cache.get("evaluator_sha256") != P.stamp_hash(encoding) or cache.get("angle_set", {}).get("sha256") != angle_set_sha256():
        return {}
    if hook:
        from su2plaq.encodings import registry

        for k in (k for k in cache if k.endswith("_code_sha256")):
            if k not in _HOOK_CODE_KEYS or registry.resolve(_HOOK_CODE_KEYS[k])() != cache[k]:
                return {}
    elif cache.get("encoding_sha256") != P.code_hash_for(encoding):
        return {}
    return cache.get("entries", {})


def headline(encoding, kind="step", root=None, refresh=False, compute=True) -> dict | None:
    """The headline of an archive: among the valid entries with a program file, the smallest robust key (full ties: the archive key,
    then the id).  Entries whose skeleton changes inside the set, and valid entries without a program file, are listed under
    "unrankable".  Per-entry `robust_metrics` are cached in <root>/results/compress/<encoding>/robust.json keyed by (id, program
    sha256, angle-set sha256) and the encoding's code hashes; a mismatch or `refresh` recomputes.  An encoding registered with a
    `headline` hook is served by it.  `summary.json` of the encoding (when it exists) gets "headline".
    `compute=False`: only cached records are used and nothing is built or written (also for an encoding with a `headline` hook, whose
    cache `robust.json` is then read here, in the shape of the generic rule); None if one is missing or stale.
    -> {"id", "robust_key", "t_mean", "lean", "archive_best", "archive_best_robust_key", "ranking": [{"id", "robust_key", "t_mean",
    "lean", "laptop_key", "family", "round", "cx", "qubits", "t_nominal", "depth_mean", "angle_linear"}...] sorted, "unrankable": [ids]}."""
    info = _info(encoding)
    hook = info is not None and bool(info.headline)
    if hook and compute:
        from su2plaq.encodings import registry

        h = registry.resolve(info.headline)(kind, root, refresh)
        h.setdefault("unrankable", sorted(r["id"] for r in h.get("ranking", []) if r["robust_key"] is None))
        for r in h.get("ranking", []):          # the track's own cache has no offset classes (prompts/010 §4.1)
            r.setdefault("offset_class", None)
        if compute and h.get("robust_key") is not None:
            _write_summary_headline(encoding, _root(root), h)
        return h
    from su2plaq.compress import archive as A
    from su2plaq.compress import provenance as P
    from su2plaq.compress.spec import default_spec

    root = _root(root)
    spec = default_spec(encoding, kind)
    arch = A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles), strict=True)
    valid = sorted((e for e in arch.entries() if e.valid), key=lambda e: e.id)
    best = arch.best()
    cache_file = root / "results" / "compress" / encoding / "robust.json"
    cached = _load_cache(cache_file, encoding, refresh, hook=hook)
    as_sha = angle_set_sha256()
    store = {"angle_set": _angle_set_record(), "evaluator_sha256": P.stamp_hash(encoding), "encoding_sha256": P.code_hash_for(encoding),
             "entries": {}}
    unrankable, rows = [], []
    for e in valid:
        if not _has_program(e, root):
            unrankable.append(e.id)
            continue
        rec = cached.get(e.id)
        if (rec is None or rec.get("program_sha256") != e.program_sha256 or rec.get("angle_set_sha256") != as_sha
                or (not hook and "offset_class" not in rec)):          # prompts/010 §4.1: a record without the class counts as missing
            if not compute:
                return None
            rec = robust_metrics(encoding, kind, _program_file(e.program_path, root), root=root)
            rec["laptop_key"] = [int(x) for x in e.key]
            if rec["program_sha256"] != e.program_sha256:
                raise RuntimeError(f"program file of {e.id} ({e.program_path}) differs from the archived sha256")
            rec = json.loads(json.dumps(rec))                 # the cached (JSON) shape, also for fresh entries
        store["entries"][e.id] = rec
        if compute:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(store, indent=1))
            tmp.replace(cache_file)
        if rec["robust_key"] is None:
            unrankable.append(e.id)
            continue
        rows.append({"id": e.id, "robust_key": tuple(rec["robust_key"]), "t_mean": rec["t_mean"], "lean": _lean_status(e),
                     "laptop_key": tuple(int(x) for x in e.key), "family": e.family, "round": e.round, "cx": rec["cx"],
                     "qubits": rec["qubits"], "t_nominal": int(e.key[1]), "depth_mean": rec["depth_sum"] / len(rec["depth_ct"]),
                     "angle_linear": rec["angle_linear"], "offset_class": rec.get("offset_class")})
    rows.sort(key=lambda r: (r["robust_key"], r["laptop_key"], r["id"]))
    top = rows[0] if rows else None
    best_row = next((r for r in rows if best is not None and r["id"] == best.id), None)
    h = {"id": top["id"] if top else None, "robust_key": top["robust_key"] if top else None, "t_mean": top["t_mean"] if top else None,
         "lean": top["lean"] if top else None, "archive_best": best.id if best else None,
         "archive_best_robust_key": best_row["robust_key"] if best_row else None, "ranking": rows, "unrankable": sorted(unrankable)}
    if compute:
        _write_summary_headline(encoding, root, h)
    return h


def summary_headline(h: dict) -> dict:
    """The "headline" block of summary.json (the spinnet format)."""
    return {"id": h["id"], "robust_key": list(h["robust_key"]) if h["robust_key"] else None, "t_mean": h["t_mean"],
            "angle_set_sha256": angle_set_sha256()}


def _write_summary_headline(encoding: str, root: pathlib.Path, h: dict) -> None:
    f = root / "results" / "compress" / encoding / "summary.json"
    if not f.exists():
        return
    summary = json.loads(f.read_text())
    block = summary_headline(h)
    if summary.get("headline") != block:
        summary["headline"] = block
        f.write_text(json.dumps(summary, indent=1))


def report_rows(encoding, kind, root=None, h=None) -> list:
    """Rows (cells as `HEADLINE_HEADER`) for the report: GLOBAL BEST (archive key), HEADLINE (robust key) and the best entry of each
    family by the robust key.  `h` = `headline(...)` of the archive; None -> the cached headline (an empty list if it is not cached).
    A row of an entry without a robust key has "-" in the averaged columns."""
    from su2plaq.compress import archive as A
    from su2plaq.compress.spec import default_spec

    h = headline(encoding, kind, root=root, compute=False) if h is None else h
    if h is None:
        return []
    root = _root(root)
    arch = A.Archive.load(encoding, root=root, n_alt=len(default_spec(encoding, kind).alt_angles), strict=True)
    best = arch.best()
    by_id = {r["id"]: r for r in h["ranking"]}
    entries = {e.id: e for e in arch.entries()}

    def row(label, i):
        r = by_id.get(i)
        if r is None:
            e = entries[i]
            return [f"{label}{i}", e.family, e.round, int(e.key[0]), int(e.key[1]), "-", "-", int(e.key[3]), "-", _lean_word(_lean_status(e))]
        lin = "yes" if r["angle_linear"] else ("no (Clifford offsets)" if r.get("offset_class") == "clifford_offset" else "no")
        return [f"{label}{i}", r["family"], r["round"], r["cx"], r["t_nominal"], f"{r['t_mean']:.2f}", f"{r['depth_mean']:.1f}", r["qubits"],
                lin, _lean_word(r["lean"])]

    rows = []
    if best is not None:
        rows.append(row("GLOBAL BEST (archive key): ", best.id))
    if h["id"] is not None:
        rows.append(row("HEADLINE (robust key): ", h["id"]))
    fam_best = {}
    for r in h["ranking"]:
        fam_best.setdefault(r["family"], r["id"])
    rows += [row(f"best of family {f} (robust key): ", fam_best[f]) for f in sorted(fam_best)]
    return rows


def headline_note(h: dict) -> str:
    """The sentence under the report table that explains the two rows."""
    text = ("GLOBAL BEST is the archive's minimum (CX, T(1e-6) at the nominal pair, depth_CT, qubits); HEADLINE is the smallest robust key "
            f"(CX, sum of T(1e-6) over the {ANGLE_SET_N} fixed random angle pairs of seed {ANGLE_SET_SEED}, angle-linear first, sum of "
            f"depth_CT, qubits). T_avg = sum T / {ANGLE_SET_N}; angle set sha256 {angle_set_sha256()[:16]}.")
    if any(r.get("offset_class") == "clifford_offset" for r in h["ranking"]):
        text += (" Entries marked 'no (Clifford offsets)' differ from an angle-linear program only by R_z(theta + k pi/2) = R_z(theta) S^k; "
                 "this costs no T gate and is not rewarded.")
    if h["unrankable"]:
        text += " No robust key (no program file, or the skeleton changes inside the angle set): " + ", ".join(h["unrankable"]) + "."
    return text


def main(argv=None) -> int:
    """`python -m su2plaq.compress.robust --encoding E [--kind K] [--refresh] [--root R]`: compute (or reuse) the headline of an archive,
    write its cache and the `headline` block of its summary.json, print id, robust key and T mean.  This is the refresh command named
    by the NOTE of `compress.report`."""
    import argparse
    import sys

    ap = argparse.ArgumentParser(prog="python -m su2plaq.compress.robust")
    ap.add_argument("--encoding", required=True)
    ap.add_argument("--kind", default=None, help="default: the registry's loop kind")
    ap.add_argument("--root")
    ap.add_argument("--refresh", action="store_true", help="recompute every entry (default: reuse a cache that is still valid)")
    a = ap.parse_args(argv)
    from su2plaq.encodings import registry

    kind = a.kind or registry.info(a.encoding).loop_kind
    h = headline(a.encoding, kind, root=a.root, refresh=a.refresh)
    print(json.dumps({"encoding": a.encoding, "kind": kind, "id": h["id"], "robust_key": h["robust_key"], "t_mean": h["t_mean"],
                      "archive_best": h["archive_best"], "unrankable": h["unrankable"]}))
    return 0 if h["id"] is not None else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())

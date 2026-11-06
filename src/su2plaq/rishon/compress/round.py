"""One round of the rishon compression loop (prompts/203 sections 2, 3.1; the laptop `su2plaq.compress.round` for the encoding rishon).

  python -m su2plaq.rishon.compress.round --kind step --seed                   # round 0: the seeds
  python -m su2plaq.rishon.compress.round --kind step --round r --evaluate [--dry-run] [--no-lean] [--root R]
  python -m su2plaq.rishon.compress.round --kind step --certify-best

Same protocol and the same files as the laptop round (archive `compress/archive/rishon/`, `results/compress/rishon/round-rrr.json`
with the laptop record schema so that `su2plaq.compress.report` reads it, `results/compress/rishon/feedback/<id>.json`,
`compress/attempts/rishon.jsonl`, `compress/discoveries/rishon.md`), instantiated with the rishon evaluator
(`su2plaq.rishon.compress.evaluate`: inner-block verdict, rishon build worker, rishon code hash) and the rishon baselines.  The pure
file helpers of the laptop round (`_rel`, `_log_attempt`, `_seen_shas`, `_proposals`, `_store_lean`) are reused unchanged; nothing of
the laptop module is patched.

Round 0 = seeds: `general`, `general+polish`, `qiskit_l3` and (kinds with U_B) `general-rccx`, `general-mcx`; the external rows are
`qiskit_l3_whole` (counts only) and the four sources of `baselines.import_seed` with their reason strings.  Round r >= 1 = the
proposers' programs.  Valid results go into the archive; the round's best entry gets its Clifford+T re-verification
(`evaluate.verify_synthesised`) and, with `lean=True`, its Lean certificate (`lean_cert.certify_circuit`; informative only, never
changes validity).  `dry_run`: no cache; this module never touches git.  `root` may be a temporary directory.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)
from su2plaq.compress import archive as A
from su2plaq.compress import baselines as LB
from su2plaq.compress import round as LR
from su2plaq.compress.spec import ROOT, default_spec
from su2plaq.metrics.provenance import provenance
from su2plaq.rishon.compress import baselines as BL
from su2plaq.rishon.compress import code_hash
from su2plaq.rishon.compress import evaluate as E

ENC = "rishon"
SEED_FAMILY = LB.SEED_FAMILY
_SOURCES = ("paulo34", "lean22", "lean22_v2", "spinnet15")


def _has_ub(spec) -> bool:
    return spec.kind in ("UB", "step")


# ----------------------------------------------------------------------------------------------- round 0
def _program_for(fn, spec, summary: str):
    """Source of an angle-linear program rebuilding `fn(spec)`, or None.  Tried in order: the laptop `program_source` (fit at
    (0,0), (1,0), (0,1)), then the fit at generic angle pairs (`baselines.linear_in_angles`); a circuit whose angles are not linear
    homogeneous in (alpha, beta) (e.g. Qiskit merged a Clifford phase into a rotation) has no program and is evaluated as a circuit."""
    for make in (lambda: fn, lambda: BL.linear_in_angles(fn, spec)):
        try:
            return LB.program_source(make(), spec, summary=summary)
        except ValueError:
            continue
    return None


def _seed_candidates(spec, root: pathlib.Path):
    """[(label, program_path_or_None, circuit_fn_or_None)] of round 0.  Programs are written under `root` (immutable once written);
    circuit-valued baselines without an angle-linear program are evaluated as circuits and are not parents."""
    d = root / "compress" / "programs" / ENC / SEED_FAMILY
    d.mkdir(parents=True, exist_ok=True)

    def ladder_program(ladder):
        gp = BL.general_program_path(spec, ladder)
        if root.resolve() != ROOT.resolve():          # keep temporary roots self-contained
            (d / gp.name).write_text(gp.read_text())
            gp = d / gp.name
        return gp

    out = [("general", ladder_program("ccx"), None)]
    for num, label, fn, summary in ((10, "general+polish", lambda s: BL.general_polished(s)[0],
                                     "the reference circuit after the deterministic polish passes."),
                                    (11, "qiskit_l3", lambda s: BL.qiskit_l3(s, seed=12345),
                                     f"Qiskit level-3 transpile (windows of {LB.L3_WINDOW}) of the reference circuit.")):
        f = d / f"{num:03d}-{label.replace('+', '_')}.py"
        if not f.exists():
            src = _program_for(fn, spec, summary)
            if src is None:
                f = None
            else:
                f.write_text(src)
        out.append((label, f, fn))
    if _has_ub(spec):
        for ladder in ("rccx", "mcx"):
            out.append((f"general-{ladder}", ladder_program(ladder), None))
    return out


def _external_rows(spec) -> list:
    from su2plaq.compress.metrics import metrics

    rows = []
    try:
        rows.append({"source": "qiskit_l3_whole", "valid": False,
                     "reason": "unverifiable: Qiskit's whole-circuit level-3 transpile hoists Hadamards (more than 1e6 amplitudes per "
                               "input), beyond the exact sparse engine",
                     "metrics": metrics(BL.qiskit_l3_whole(spec), spec, measured=False)})
    except (ValueError, RuntimeError) as exc:
        rows.append({"source": "qiskit_l3_whole", "valid": False, "reason": f"counts unavailable: {exc}"})
    rows += [{"source": s, "reason": BL.import_seed(spec, s)} for s in _SOURCES]
    return rows


# ----------------------------------------------------------------------------------------------- helpers
def _record(label, e, r, parent_known=True) -> dict:
    """The laptop candidate record, whose "verdict" subset also carries `dropped_total` (the prune-cap quantity)."""
    rec = LR._record(label, e, r, parent_known)
    v = e.verdict_nominal or {}
    rec["verdict"]["dropped_total"] = v.get("dropped_total")
    return rec


def _circuit_of(spec, program_path, label, fn, root):
    """(nominal circuit of an evaluated candidate, None) or (None, error text).  Programs are rebuilt in the rishon build worker,
    circuit-valued seeds from their function; failures are returned, never swallowed."""
    try:
        if fn is not None and (program_path is None or str(program_path).endswith(".circuit")):
            return fn(spec), None
        f = pathlib.Path(program_path)
        f = f if f.is_absolute() else (root / f if (root / f).exists() else ROOT / f)
        if not f.exists():
            return None, f"program file {program_path} not found"
        circuits, _ = E._build_in_subprocess(f.read_bytes(), [spec], E.BUILD_TIMEOUT_S)
        return circuits[0], None
    except (E.ContractError, RuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _certify(circ, spec):
    """(asdict(LeanCert) or a status dict, seconds).  Lean never changes validity; a failure or an unbuilt checker is recorded."""
    t0 = time.time()
    try:
        from dataclasses import asdict

        from su2plaq.rishon import lean_cert

        return asdict(lean_cert.certify_circuit(circ, spec, timeout=1200.0)), time.time() - t0
    except NotImplementedError as exc:
        return {"status": "not_run", "reason": f"Lean certification not available: {exc}"}, time.time() - t0
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, time.time() - t0


# ----------------------------------------------------------------------------------------------- the round
def run_round(kind: str, round: int, evaluate: bool, dry_run: bool = False, root=None, proposals: list | None = None,
              lean: bool = True) -> dict:
    """-> {"round","n_valid","n_invalid","best_key","entries":[ids],"lean_seconds"} and the files of the module docstring.
    `proposals=None` and round 0: the seeds; round r >= 1: every unseen program under compress/programs/rishon/<family>/ (not seed)."""
    root = pathlib.Path(root) if root is not None else ROOT
    spec = default_spec(ENC, kind)
    archive = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True)
    t0 = time.time()
    results = []          # (label, ProgramResult, program path (relative), family, circuit_fn or None, declared parent)
    external = []
    if round == 0 and proposals is None:
        if evaluate:
            for label, path, fn in _seed_candidates(spec, root):
                if path is not None:
                    r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                    pp = LR._rel(path, root)
                else:     # circuit-valued baseline without a program: rebuilt at the alternate angles too
                    alts = [fn(spec.with_angles(a, b)) for a, b in spec.alt_angles]
                    r = E.evaluate_circuit(fn(spec), spec, "full", alt_circuits=alts)
                    pp = f"compress/programs/{ENC}/seed/{label}.circuit"
                results.append((label, r, pp, SEED_FAMILY, fn, None))
            external = _external_rows(spec)
    else:
        paths = proposals if proposals is not None else LR._proposals(spec, root, archive)
        if evaluate:
            for path in paths:
                r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                try:
                    hdr = E.B.parse_program_header(pathlib.Path(path).read_text())
                    fam, par = hdr["family"], hdr["parent"]
                except (E.B.BuilderError, OSError, UnicodeDecodeError):
                    fam, par = "unknown", None      # the failed contract is already in r.reason
                results.append((pathlib.Path(path).stem, r, LR._rel(path, root), fam, None, par))
    ids, n_valid, n_invalid, invalid, records = [], 0, 0, [], []
    fdir = root / "results" / "compress" / ENC / "feedback"
    fdir.mkdir(parents=True, exist_ok=True)
    known_ids = {x.id for x in archive.entries()}
    for label, r, pp, fam, fn, par in results:
        e = A.entry_from_result(r, program_path=pp, family=fam, round=round, parent=par)
        e.evaluator_sha256 = code_hash()
        parent_known = par is None or par in known_ids
        if pp.endswith(".circuit"):          # a circuit-valued baseline without a program file is named after its label
            e.id = f"r{round:02d}-{fam}-{label.replace('+', '_')}"
        if e.id in {x.id for x in archive.entries()}:
            e.id = f"{e.id}-{r.program_sha256[:6] or int(time.time())}"
        (fdir / f"{e.id}.json").write_text(json.dumps(E.LE.result_to_dict(r), indent=1))
        LR._log_attempt(root, ENC, {"id": e.id, "round": round, "family": fam, "valid": r.valid, "reason": r.reason,
                                    "key": list(e.key), "summary": r.summary, "written_utc": e.written_utc,
                                    "program_sha256": r.program_sha256, "parent": par, "parent_known": parent_known},
                        r.discoveries, e.id)
        if archive.insert(e):
            ids.append(e.id)
            n_valid += 1
        else:
            n_invalid += 1
            invalid.append({"id": e.id, "label": label, "reason": r.reason, "message": r.message})
        records.append((_record(label, e, r, parent_known), r, pp, label, fn))
        if any(x.id == e.id for x in archive.entries()):
            known_ids.add(e.id)
    best = archive.best()
    synth_check, lean_seconds = None, 0.0
    best_here = next((x for x in records if best is not None and x[0]["id"] == best.id), None)
    if best_here is not None and evaluate:
        # the round's global best: Clifford+T re-verification (and, on request, the Lean certificate)
        _rec, r, pp, label, fn = best_here
        circ, err = _circuit_of(spec, pp, label, fn, root)
        if circ is None:
            synth_check = {"entry": best.id, "ok": None, "error": err}
        else:
            sv = E.verify_synthesised(circ, spec)
            synth_check = {"entry": best.id, "ok": sv["ok"], "eps": sv["eps"], "n_rot": sv["n_rot"], "t_total": sv["t_total"],
                           "tolerances": sv["tolerances"], "op_norm_error": sv["verdict"].op_norm_error,
                           "certified": sv["verdict"].certified, "reason": sv["verdict"].reason}
            if lean:
                new_lean, lean_seconds = _certify(circ, spec)
                LR._store_lean(best, new_lean, root, ENC, f"round {round}")
    archive.save()
    for rec, *_ in records:               # records carry the final lean status
        e = next((x for x in archive.entries() if x.id == rec["id"]), None)
        if e is not None:
            rec["lean"] = e.lean
    info = {"round": round, "n_valid": n_valid, "n_invalid": n_invalid, "best_key": list(best.key) if best else None,
            "entries": ids, "lean_seconds": lean_seconds}
    out = {**info, "encoding": ENC, "kind": kind, "provenance": provenance({"trial_seed": spec.trial_seed}),
           "evaluator_sha256": code_hash(), "spec_sha256": spec.sha256(), "invalid": invalid, "external": external,
           "n_pruning_bound": sum(1 for x in invalid if x["reason"] == "pruning_bound"),
           "candidates": [x[0] for x in records], "synthesis_verification": synth_check, "wall_s": time.time() - t0,
           "written_utc": LR._utc()}
    rdir = root / "results" / "compress" / ENC
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / f"round-{round:03d}.json").write_text(json.dumps(out, indent=1, default=str))
    return info


def certify_best(kind="step", root=None) -> dict:
    """Lean-certify the archive's current global best (rebuilt from its program file) and store the certificate on the entry
    (`Entry.lean`).  Never changes validity; a failure is recorded, not hidden.  -> {"entry","lean","seconds"}."""
    root = pathlib.Path(root) if root is not None else ROOT
    spec = default_spec(ENC, kind)
    archive = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True)
    best = archive.best()
    if best is None:
        return {"entry": None, "lean": None, "seconds": 0.0}
    circ, err = _circuit_of(spec, best.program_path, best.id, None, root)
    if circ is None:
        new, sec = {"status": "failed", "reason": f"cannot rebuild the best circuit: {err}"}, 0.0
    else:
        new, sec = _certify(circ, spec)
    before = best.lean
    LR._store_lean(best, new, root, ENC, "certify_best")
    archive.save()
    return {"entry": best.id, "lean": best.lean, "attempt": new, "kept_previous": before is not None and best.lean is before,
            "seconds": sec}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.rishon.compress.round")
    ap.add_argument("--kind", default="step", choices=["step", "UB", "UE"])
    ap.add_argument("--seed", action="store_true", help="round 0: evaluate the seeds")
    ap.add_argument("--round", type=int)
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lean", dest="lean", action="store_true", default=True,
                    help="(default) certify the round's new global best with the rishon three-angle Lean checker")
    ap.add_argument("--no-lean", dest="lean", action="store_false", help="skip the Lean certificate")
    ap.add_argument("--root")
    ap.add_argument("--certify-best", action="store_true", help="Lean-certify the archive's current best and store it")
    a = ap.parse_args(argv)
    if a.certify_best:
        print(json.dumps(certify_best(a.kind, a.root), indent=1, default=str))
        return 0
    if a.seed == (a.round is not None):
        ap.error("give exactly one of --seed and --round r")
    rnd = 0 if a.seed else a.round
    info = run_round(a.kind, rnd, evaluate=a.seed or a.evaluate, dry_run=a.dry_run, root=a.root, lean=a.lean)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""One round of the compression loop (prompts/002 §5, rows 2.5 and 2.6).

  python -m su2plaq.compress.round --encoding twelve --kind step --seed             # round 0: the seeds
  python -m su2plaq.compress.round --encoding twelve --kind step --round r --evaluate [--dry-run]

Round 0 evaluates (full mode) the general program, general + polish, the Qiskit level-3 baseline and the external seeds
(lean22_v2, lean22 as parent-able seeds; paulo34 as a fixed-angle comparison row that is never archived); round r >= 1
evaluates the proposers' programs (default: every `compress/programs/<encoding>/<family>/NNN-*.py` not seen before).  Valid
results go into the archive; everything is logged (`results/compress/<enc>/round-rrr.json`, `compress/attempts/<enc>.jsonl`,
`compress/discoveries/<enc>.md`).  The best valid entry of a round gets its Clifford+T re-verification
(`baselines.verify_synthesised`).  `dry_run`: no git interaction (this module never touches git); `root` may be a temporary
directory, in which case seed programs are written under it.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import subprocess
import sys
import time

from su2plaq.compress import archive as A
from su2plaq.compress import baselines as BL
from su2plaq.compress import evaluate as E
from su2plaq.compress import provenance as P
from su2plaq.compress.spec import ROOT, TaskSpec, default_spec
from su2plaq.metrics.provenance import provenance


def _utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path, root: pathlib.Path) -> str:
    """Path relative to `root` (else to the repository root), absolute only if it is in neither: archives stay relocatable."""
    p = pathlib.Path(path).resolve()
    for base in (root.resolve(), ROOT.resolve()):
        try:
            return str(p.relative_to(base))
        except ValueError:
            continue
    return str(p)


def _seed_candidates(spec: TaskSpec, root: pathlib.Path):
    """[(label, program_path_or_None, circuit_fn_or_None)] for round 0.  Programs are written under `root`; circuit-valued
    baselines get a generated program too (so that they can be parents) unless their skeleton depends on the angles."""
    out = []
    d = root / "compress" / "programs" / spec.encoding / BL.SEED_FAMILY
    d.mkdir(parents=True, exist_ok=True)
    gp = BL.general_program_path(spec)
    if root.resolve() != ROOT.resolve():      # keep temporary roots self-contained
        (d / gp.name).write_text(gp.read_text())
        gp = d / gp.name
    out.append(("general", gp, None))
    for num, label, fn, summary in ((10, "general+polish", lambda s: BL.general_polished(s)[0],
                                     "the reference circuit after the deterministic polish passes."),
                                    (11, "qiskit_l3", lambda s: BL.qiskit_l3(s, seed=12345),
                                     f"Qiskit level-3 transpile (windows of {BL.L3_WINDOW}) of the reference circuit.")):
        f = d / f"{num:03d}-{label.replace('+', '_')}.py"
        if not f.exists():
            try:
                f.write_text(BL.program_source(fn, spec, summary=summary))
            except ValueError:
                f = None          # angle-dependent skeleton: evaluated as a circuit, no parent-able program
        out.append((label, f, fn))
    for k, src in enumerate(("lean22_v2", "lean22"), start=1):
        seed = BL.import_seed(spec, src)
        if isinstance(seed, str):
            continue
        f = d / f"00{k}-{src}.py"
        if not f.exists():
            f.write_text(BL.seed_program_source(spec, src))
        out.append((src, f, None))
    return out


def _log_attempt(root, encoding, rec: dict, discoveries: list, ident: str):
    adir = root / "compress" / "attempts"
    adir.mkdir(parents=True, exist_ok=True)
    with open(adir / f"{encoding}.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    if discoveries:
        ddir = root / "compress" / "discoveries"
        ddir.mkdir(parents=True, exist_ok=True)
        with open(ddir / f"{encoding}.md", "a") as fh:
            for line in discoveries:
                fh.write(f"- {ident}: {line}\n")


def _seen_shas(root: pathlib.Path, encoding: str, archive: A.Archive) -> set:
    """sha256 of every program already evaluated: archived ones and the attempts log (valid or not), so that a rejected program is
    recorded once and not re-evaluated every round."""
    seen = {e.program_sha256 for e in archive.entries()}
    f = root / "compress" / "attempts" / f"{encoding}.jsonl"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line).get("program_sha256"))
    return seen


def _proposals(spec: TaskSpec, root: pathlib.Path, archive: A.Archive) -> list[str]:
    seen = _seen_shas(root, spec.encoding, archive)
    out = []
    base = root / "compress" / "programs" / spec.encoding
    if base.is_dir():
        for fam in sorted(p for p in base.iterdir() if p.is_dir() and p.name != BL.SEED_FAMILY):
            for f in sorted(fam.glob("*.py")):
                if E.hashlib.sha256(f.read_bytes()).hexdigest() not in seen:
                    out.append(str(f))
    return out


def _record(label, e, r, parent_known=True) -> dict:
    """One candidate as plain data (everything `report.py` shows comes from here)."""
    v = e.verdict_nominal or {}
    return {"label": label, "id": e.id, "family": e.family, "program_sha256": e.program_sha256, "program_path": e.program_path, "valid": e.valid, "reason": e.reason,
            "key": list(e.key) if e.valid else None, "cell": list(e.cell) if e.cell else None, "metrics": e.metrics_raw,
            "verdict": {k: v.get(k) for k in ("ok", "op_norm_error", "block_error", "leak_amplitude", "gauss_residual", "certified",
                                              "engine", "method")},
            "alt_ok": [bool(a.get("ok")) for a in e.verdicts_alt], "skeleton_equal": e.skeleton_equal, "parent": e.parent, "parent_known": parent_known,
            "git_commit": e.git_commit, "summary": e.summary, "lean": e.lean, "round": e.round, "mode": e.mode}


def run_round(encoding, kind, round: int, evaluate: bool, dry_run: bool = False, root=None,
              proposals: list[str] | None = None, lean: bool = True) -> dict:
    """-> {"round","n_valid","n_invalid","best_key","entries":[ids],"lean_seconds"} (and writes the files listed in the module
    docstring).  `lean=True` (default, prompts/006 §5): certify the round's new global best with Lean (`su2plaq.lean.certify`)
    and check the `NNN-slug.lean` lemma files shipped next to evaluated programs (at most 5 per round, 120 s each); both are
    informative, never change validity, and their wall time is `lean_seconds`.  `lean=False` skips them."""
    root = pathlib.Path(root) if root is not None else ROOT
    spec = default_spec(encoding, kind)
    archive = A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles), strict=True)
    t0 = time.time()
    results = []          # (label, ProgramResult, program_path (relative), family, circuit_fn or None)
    external = []
    if round == 0 and proposals is None:
        cands = _seed_candidates(spec, root)
        if evaluate:
            for label, path, fn in cands:
                if path is not None:
                    r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                    pp = _rel(path, root)
                else:     # circuit-valued baseline without a program: rebuilt at the alternate angles too
                    alts = [fn(spec.with_angles(a, b)) for a, b in spec.alt_angles]
                    r = E.evaluate_circuit(fn(spec), spec, "full", alt_circuits=alts)
                    pp = f"compress/programs/{encoding}/seed/{label}.circuit"
                results.append((label, r, pp, BL.SEED_FAMILY, fn, None))
            try:      # the whole-circuit L3 transpile: counts only (the sparse engine cannot verify it)
                from su2plaq.compress.metrics import metrics

                external.append({"source": "qiskit_l3_whole", "valid": False, "reason": "unverifiable: Qiskit's whole-circuit level-3 "
                                 "transpile hoists Hadamards (more than 1e6 amplitudes per input), beyond the exact sparse engine",
                                 "metrics": metrics(BL.qiskit_l3_whole(spec), spec, measured=False)})
            except (ValueError, RuntimeError) as exc:
                external.append({"source": "qiskit_l3_whole", "valid": False, "reason": f"counts unavailable: {exc}"})
            seed = BL.import_seed(spec, "paulo34")
            if not isinstance(seed, str):
                rs = BL.evaluate_seed(spec, seed, "full")
                external.append({"source": "paulo34", "fixed_angle": True, "kind": seed.kind, "valid": rs.valid, "reason": rs.reason,
                                 "metrics": rs.metrics, "op_norm_error": getattr(rs.verdict, "op_norm_error", None),
                                 "certified": getattr(rs.verdict, "certified", None), "message": rs.message})
            external.append({"source": "spinnet15", "reason": BL.import_seed(spec, "spinnet15")})
    else:
        paths = proposals if proposals is not None else _proposals(spec, root, archive)
        if evaluate:
            for path in paths:
                r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                try:
                    hdr = E.B.parse_program_header(pathlib.Path(path).read_text())
                    fam, par = hdr["family"], hdr["parent"]
                except (E.B.BuilderError, OSError, UnicodeDecodeError):
                    fam, par = "unknown", None      # the failed contract is already in r.reason
                results.append((pathlib.Path(path).stem, r, _rel(path, root), fam, None, par))
    ids, n_valid, n_invalid, invalid, records = [], 0, 0, [], []
    lemma_seconds, n_lemma_files = 0.0, 0
    fdir = root / "results" / "compress" / encoding / "feedback"
    fdir.mkdir(parents=True, exist_ok=True)
    known_ids = {x.id for x in archive.entries()}
    for label, r, pp, fam, fn, par in results:
        # PARENT of the program header: recorded as declared; `parent_known` says whether it names an existing entry
        e = A.entry_from_result(r, program_path=pp, family=fam, round=round, parent=par)
        parent_known = par is None or par in known_ids
        if pp.endswith(".circuit"):          # a circuit-valued baseline without a program file is named after its label
            e.id = f"r{round:02d}-{fam}-{label.replace('+', '_')}"
        if e.id in {x.id for x in archive.entries()}:
            e.id = f"{e.id}-{r.program_sha256[:6] or int(time.time())}"
        (fdir / f"{e.id}.json").write_text(json.dumps(E.result_to_dict(r), indent=1))
        _log_attempt(root, encoding, {"id": e.id, "round": round, "family": fam, "valid": r.valid, "reason": r.reason,
                                      "key": list(e.key), "summary": r.summary, "written_utc": e.written_utc, "program_sha256": r.program_sha256,
                                      "parent": par, "parent_known": parent_known}, r.discoveries, e.id)
        if archive.insert(e):
            ids.append(e.id)
            n_valid += 1
        else:
            n_invalid += 1
            invalid.append({"id": e.id, "label": label, "reason": r.reason, "message": r.message})
        records.append((_record(label, e, r, parent_known), r, pp, label, fn))
        if lean and evaluate and not pp.endswith(".circuit") and n_lemma_files < MAX_LEMMA_FILES:
            lem, lsec = _check_lemmas(pp, root)
            if lem is not None:
                n_lemma_files += 1
                records[-1][0]["lean_lemmas"] = lem
                lemma_seconds += lsec
        if archive.entries() and any(x.id == e.id for x in archive.entries()):
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
            sv = BL.verify_synthesised(circ, spec)
            synth_check = {"entry": best.id, "ok": sv["ok"], "eps": sv["eps"], "n_rot": sv["n_rot"], "t_total": sv["t_total"],
                           "tolerances": sv["tolerances"], "op_norm_error": sv["verdict"].op_norm_error,
                           "certified": sv["verdict"].certified, "reason": sv["verdict"].reason}
            if lean:
                best.lean, lean_seconds = _certify(circ, spec)
    archive.save()
    for rec, *_ in records:               # records carry the final lean status
        e = next((x for x in archive.entries() if x.id == rec["id"]), None)
        if e is not None:
            rec["lean"] = e.lean
    lean_seconds += lemma_seconds
    info = {"round": round, "n_valid": n_valid, "n_invalid": n_invalid, "best_key": list(best.key) if best else None,
            "entries": ids, "lean_seconds": lean_seconds}
    out = {**info, "encoding": encoding, "kind": kind, "provenance": provenance({"trial_seed": spec.trial_seed}),
           "evaluator_sha256": P.code_hash(), "spec_sha256": spec.sha256(), "invalid": invalid, "external": external,
           "candidates": [x[0] for x in records], "synthesis_verification": synth_check, "wall_s": time.time() - t0,
           "written_utc": _utc()}
    rdir = root / "results" / "compress" / encoding
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / f"round-{round:03d}.json").write_text(json.dumps(out, indent=1, default=str))
    return info


MAX_LEMMA_FILES = 5


def _check_lemmas(program_path, root):
    """(lemma-check dict, seconds) for the `.lean` file next to a program, or (None, 0.0) when there is none.  Informative only."""
    f = pathlib.Path(program_path)
    f = f if f.is_absolute() else (root / f if (root / f).exists() else ROOT / f)
    t0 = time.time()
    try:
        from su2plaq.lean import lemmas

        if lemmas.lemma_file_for(f) is None:
            return None, 0.0
        return lemmas.check_program_lemmas(f, timeout=120.0), time.time() - t0
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return {"status": "failed", "message": f"{type(exc).__name__}: {exc}"}, time.time() - t0


def _certify(circ, spec):
    """(asdict(LeanCert) or a status dict, seconds).  Lean never changes validity; a failure is recorded, not hidden."""
    t0 = time.time()
    try:
        from dataclasses import asdict

        from su2plaq.lean import certify

        return asdict(certify.certify_circuit(circ, spec, timeout=1200.0)), time.time() - t0
    except NotImplementedError as exc:
        return {"status": "not_run", "reason": f"Lean certification not available: {exc}"}, time.time() - t0
    except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}, time.time() - t0


def _circuit_of(spec, program_path, label, fn, root):
    """(nominal circuit of an evaluated candidate, None) or (None, error text).  Programs are rebuilt in the sandboxed worker, circuit-valued
    seeds from their function; failures are returned, never swallowed."""
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


def certify_best(encoding="twelve", kind="step", root=None) -> dict:
    """Step 2.L8: Lean-certify the archive's current global best (rebuilt from its program file) and store the certificate on
    the entry (`Entry.lean`).  Never changes validity; a failure is recorded, not hidden.  -> {"entry","lean","seconds"}."""
    root = pathlib.Path(root) if root is not None else ROOT
    spec = default_spec(encoding, kind)
    archive = A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles), strict=True)
    best = archive.best()
    if best is None:
        return {"entry": None, "lean": None, "seconds": 0.0}
    circ, err = _circuit_of(spec, best.program_path, best.id, None, root)
    if circ is None:
        best.lean, sec = {"status": "failed", "reason": f"cannot rebuild the best circuit: {err}"}, 0.0
    else:
        best.lean, sec = _certify(circ, spec)
    archive.save()
    return {"entry": best.id, "lean": best.lean, "seconds": sec}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.compress.round")
    ap.add_argument("--encoding", default="twelve")
    ap.add_argument("--kind", default="step")
    ap.add_argument("--seed", action="store_true", help="round 0: evaluate the seeds")
    ap.add_argument("--round", type=int)
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lean", dest="lean", action="store_true", default=True,
                    help="(default) certify the round's new global best with Lean and check shipped lemma files")
    ap.add_argument("--no-lean", dest="lean", action="store_false", help="skip the Lean certificate and lemma checks")
    ap.add_argument("--root")
    ap.add_argument("--certify-best", action="store_true", help="Lean-certify the archive's current best and store it (step 2.L8)")
    a = ap.parse_args(argv)
    if a.certify_best:
        print(json.dumps(certify_best(a.encoding, a.kind, a.root), indent=1, default=str))
        return 0
    if a.seed == (a.round is not None):
        ap.error("give exactly one of --seed and --round r")
    rnd = 0 if a.seed else a.round
    info = run_round(a.encoding, a.kind, rnd, evaluate=a.seed or a.evaluate, dry_run=a.dry_run, root=a.root, lean=a.lean)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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


def _seed_candidates(spec: TaskSpec, root: pathlib.Path):
    """[(label, family, program_path_or_None, circuit_or_None, kind)] for round 0.  Programs are written under `root`."""
    out = []
    gp = BL.general_program_path(spec)
    if root != ROOT:      # keep temporary roots self-contained
        dst = root / "compress" / "programs" / spec.encoding / BL.SEED_FAMILY / gp.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(gp.read_text())
        gp = dst
    out.append(("general", gp, None))
    out.append(("general+polish", None, lambda s: BL.general_polished(s)[0]))
    out.append(("qiskit_l3", None, lambda s: BL.qiskit_l3(s, seed=12345)))
    for k, src in enumerate(("lean22_v2", "lean22"), start=1):
        seed = BL.import_seed(spec, src)
        if isinstance(seed, str):
            continue
        d = root / "compress" / "programs" / spec.encoding / BL.SEED_FAMILY
        d.mkdir(parents=True, exist_ok=True)
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


def _proposals(spec: TaskSpec, root: pathlib.Path, archive: A.Archive) -> list[str]:
    seen = {e.program_sha256 for e in archive.entries()}
    out = []
    base = root / "compress" / "programs" / spec.encoding
    if base.is_dir():
        for fam in sorted(p for p in base.iterdir() if p.is_dir() and p.name != BL.SEED_FAMILY):
            for f in sorted(fam.glob("*.py")):
                if E.hashlib.sha256(f.read_bytes()).hexdigest() not in seen:
                    out.append(str(f))
    return out


def run_round(encoding, kind, round: int, evaluate: bool, dry_run: bool = False, root=None,
              proposals: list[str] | None = None) -> dict:
    """-> {"round","n_valid","n_invalid","best_key","entries":[ids]} (and writes the files listed in the module docstring)."""
    root = pathlib.Path(root) if root is not None else ROOT
    spec = default_spec(encoding, kind)
    archive = A.Archive.load(encoding, root=root, n_alt=len(spec.alt_angles))
    t0 = time.time()
    results = []          # (label, ProgramResult, program_path, family)
    external = []
    if round == 0 and proposals is None:
        cands = _seed_candidates(spec, root)
        if evaluate:
            for label, path, circ in cands:
                if path is not None:
                    r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                    pp = str(path)
                else:     # circuit-valued baselines are rebuilt at the alternate angles too (verified at every pair)
                    alts = [circ(spec.with_angles(a, b)) for a, b in spec.alt_angles]
                    r = E.evaluate_circuit(circ(spec), spec, "full", alt_circuits=alts)
                    pp = f"compress/programs/{encoding}/seed/{label}.circuit"
                results.append((label, r, pp, BL.SEED_FAMILY))
            for src in ("paulo34",):
                seed = BL.import_seed(spec, src)
                if not isinstance(seed, str):
                    rs = BL.evaluate_seed(spec, seed, "full")
                    external.append({"source": src, "fixed_angle": True, "kind": seed.kind, "valid": rs.valid, "reason": rs.reason,
                                     "metrics": rs.metrics, "op_norm_error": getattr(rs.verdict, "op_norm_error", None),
                                     "message": rs.message})
            reason = BL.import_seed(spec, "spinnet15")
            external.append({"source": "spinnet15", "reason": reason})
    else:
        paths = proposals if proposals is not None else _proposals(spec, root, archive)
        if evaluate:
            for path in paths:
                r = E.evaluate_program(path, spec, "full", cache=not dry_run, root=root)
                try:
                    fam = E.B.parse_program_header(pathlib.Path(path).read_text())["family"]
                except Exception:  # noqa: BLE001 - an unreadable header is already a failed result
                    fam = "unknown"
                results.append((pathlib.Path(path).stem, r, str(path), fam))
    ids, n_valid, n_invalid, invalid = [], 0, 0, []
    for label, r, pp, fam in results:
        e = A.entry_from_result(r, program_path=pp, family=fam, round=round, parent=None)
        if label in ("general+polish", "qiskit_l3"):
            e.id = f"r{round:02d}-{fam}-{label}"
        if e.id in {x.id for x in archive.entries()}:
            e.id = f"{e.id}-{r.program_sha256[:6] or int(time.time())}"
        _log_attempt(root, encoding, {"id": e.id, "round": round, "family": fam, "valid": r.valid, "reason": r.reason,
                                      "key": list(e.key), "summary": r.summary, "written_utc": e.written_utc}, r.discoveries, e.id)
        if archive.insert(e):
            ids.append(e.id)
            n_valid += 1
        else:
            n_invalid += 1
            invalid.append({"id": e.id, "label": label, "reason": r.reason, "message": r.message})
    archive.save()
    best = archive.best()
    synth_check = None
    if best is not None and evaluate and results:
        # Clifford+T re-verification of the best valid circuit of the archive (when it was produced this round)
        for label, r, pp, fam in results:
            if best.id.startswith(f"r{round:02d}") and (best.program_sha256 == r.program_sha256):
                circ = _circuit_of(spec, pp, label)
                if circ is not None:
                    sv = BL.verify_synthesised(circ, spec)
                    synth_check = {"entry": best.id, "ok": sv["ok"], "eps": sv["eps"], "n_rot": sv["n_rot"], "t_total": sv["t_total"],
                                   "tolerances": sv["tolerances"], "op_norm_error": sv["verdict"].op_norm_error,
                                   "certified": sv["verdict"].certified, "reason": sv["verdict"].reason}
                break
    info = {"round": round, "n_valid": n_valid, "n_invalid": n_invalid, "best_key": list(best.key) if best else None, "entries": ids}
    out = {**info, "encoding": encoding, "kind": kind, "provenance": provenance({"trial_seed": spec.trial_seed}),
           "evaluator_sha256": P.code_hash(), "spec_sha256": spec.sha256(), "invalid": invalid, "external": external,
           "synthesis_verification": synth_check, "wall_s": time.time() - t0, "written_utc": _utc()}
    rdir = root / "results" / "compress" / encoding
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / f"round-{round:03d}.json").write_text(json.dumps(out, indent=1, default=str))
    return info


def _circuit_of(spec, program_path, label):
    """The nominal circuit of an evaluated candidate (program in a subprocess; seed circuits rebuilt)."""
    try:
        if label == "general+polish":
            return BL.general_polished(spec)[0]
        if label == "qiskit_l3":
            return BL.qiskit_l3(spec)
        f = pathlib.Path(program_path)
        if f.exists():
            circuits, _ = E._build_in_subprocess(f.read_bytes(), [spec], E.BUILD_TIMEOUT_S)
            return circuits[0]
    except Exception:  # noqa: BLE001 - a missing synthesis check must not hide the round result
        return None
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.compress.round")
    ap.add_argument("--encoding", default="twelve")
    ap.add_argument("--kind", default="step")
    ap.add_argument("--seed", action="store_true", help="round 0: evaluate the seeds")
    ap.add_argument("--round", type=int)
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    if a.seed == (a.round is not None):
        ap.error("give exactly one of --seed and --round r")
    rnd = 0 if a.seed else a.round
    info = run_round(a.encoding, a.kind, rnd, evaluate=a.seed or a.evaluate, dry_run=a.dry_run, root=a.root)
    print(json.dumps(info, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

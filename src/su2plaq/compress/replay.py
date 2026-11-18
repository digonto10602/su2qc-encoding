"""Replay of the recorded rounds of any encoding's archive under the current code (prompts/008 section 7; prompts/204 section 6.2).

Needed whenever a hashed file changes: the archive entries and round files carry the old `evaluator_sha256`, and the gate (M2C-G1)
requires the current one.  The programs are NOT changed; every recorded round is re-run in order with its recorded program list
(round 0: the encoding's seeds), a replay is not a new attempt (stop-rule counters, proposer sessions and MAX_ROUNDS bookkeeping
are untouched).  Nothing is deleted: the old round files, feedback, robust cache and summary go to results/compress/<enc>/pre-<tag>/
and the old archive to compress/archive/<enc>-pre-<tag>/; the attempts log and the discoveries file (appended to by the round
function) are restored byte for byte; the `lean` record of an old entry is carried over to the new entry of the same program
(same sha256) unless the new entry already has a certified one.

  python -m su2plaq.compress.replay --encoding E --kind K --tag T [--root R] [--lean]

Writes results/compress/<enc>/replay-<tag>.json (schema of prompts/204 section 6.2 step 6, plus `encoding_sha256` and
`written_utc`).  Refuses (ValueError, nothing touched) if that file or a pre-<tag> folder exists, if round files are missing / not
contiguous from 0, belong to another encoding or kind, or list a candidate without a program_path or a program_path twice in one
round.  RuntimeError after the rounds ran if a replayed round does not list the recorded (program_path, label) pairs in the recorded order.  Exit code 1 of the CLI when a key changed, a valid entry was lost, or an entry of the old archive was refused by the loader
(or was produced by no recorded round); the entry is named on stderr.
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import json
import pathlib
import shutil
import sys
import time


def _read(p: pathlib.Path):
    return p.read_bytes() if p.exists() else None


def _restore(p: pathlib.Path, data) -> bool:
    """Put `data` (bytes or None = file did not exist) back; True iff the file now equals the original."""
    if data is None:
        if p.exists():
            p.unlink()
        return True
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p.read_bytes() == data


def _key(c) -> list | None:
    return [int(x) for x in c["key"]] if c.get("key") else None


def _side(c) -> dict:
    v = c.get("verdict") or {}
    return {"valid": bool(c["valid"]), "reason": c["reason"], "key": _key(c), "dropped_total": v.get("dropped_total")}


def _candidate_mismatch(old: list, new: list) -> str:
    """'' iff the replayed candidates of a round are the recorded ones: the same (program_path, label) pairs in the same order (the
    replay feeds the recorded program paths in recorded order; round 0 re-runs the same seed list).  The program path identifies a
    candidate; the label (the program's file stem) need not be unique in a round (twelve round 4, fuzzy_ub round 5: families F2/F4
    and F1/F3 wrote files with the same stem), so a match by label alone is ambiguous.  Else a description of the first difference."""
    po = [(c.get("program_path"), c.get("label")) for c in old]
    pn = [(c.get("program_path"), c.get("label")) for c in new]
    if po == pn:
        return ""
    if len(po) != len(pn):
        return f"{len(po)} recorded vs {len(pn)} replayed; missing {sorted(set(po) - set(pn))}, extra {sorted(set(pn) - set(po))}"
    i = next(k for k, (a, b) in enumerate(zip(po, pn)) if a != b)
    return f"position {i}: recorded {po[i]}, replayed {pn[i]}"


def _utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# the encoding's own round function when it has one: "module:attr" and whether it takes (encoding, kind) / (kind) / () first
_OWN_ROUND = {"spinnet": ("su2plaq.spinnet.loop:run_round", ()), "rishon": ("su2plaq.rishon.compress.round:run_round", ("kind",))}


def _round_fn(encoding: str, kind: str):
    """-> callable(r, proposals, root, lean) running one round of `encoding` through its own round function, else the shared one."""
    if encoding in _OWN_ROUND:
        spec, lead = _OWN_ROUND[encoding]
        mod, attr = spec.split(":")
        fn = getattr(importlib.import_module(mod), attr)
        pre = (kind,) if lead == ("kind",) else ()
        return lambda r, proposals, root, lean: fn(*pre, r, evaluate=True, dry_run=False, root=root, proposals=proposals, lean=lean)
    from su2plaq.compress.round import run_round

    return lambda r, proposals, root, lean: run_round(encoding, kind, r, evaluate=True, dry_run=False, root=root, proposals=proposals, lean=lean)


def replay(encoding: str, kind: str, root=None, tag: str = "008", lean: bool = False, extra: dict | None = None) -> dict:
    """Re-run every recorded round of (`encoding`, `kind`) under the current code; -> the record written to
    results/compress/<enc>/replay-<tag>.json.  `extra`: fields added to the record right after `kind` (the rishon wrapper adds
    `prune_fraction`)."""
    from su2plaq.compress import archive as A
    from su2plaq.compress import provenance as P
    from su2plaq.compress.spec import ROOT, default_spec
    from su2plaq.metrics.provenance import provenance

    root = pathlib.Path(root) if root is not None else ROOT
    rdir = root / "results" / "compress" / encoding
    adir = root / "compress" / "archive" / encoding
    out_json, pre = rdir / f"replay-{tag}.json", rdir / f"pre-{tag}"
    apre = root / "compress" / "archive" / f"{encoding}-pre-{tag}"
    for p in (out_json, pre, apre):
        if p.exists():
            raise ValueError(f"{p} already exists: a replay with tag {tag!r} was done (or started); use a new tag after a new edit")
    files = sorted(rdir.glob("round-*.json"))
    if not files:
        raise ValueError(f"no round files under {rdir}")
    old_rounds = [json.loads(f.read_text()) for f in files]
    nums = [int(f.stem.split("-")[1]) for f in files]
    if nums != list(range(len(nums))):
        raise ValueError(f"round files are not contiguous from 0: {nums}")
    if any(r.get("kind") != kind or r.get("encoding", encoding) != encoding for r in old_rounds):
        raise ValueError(f"round files do not all belong to ({encoding!r}, {kind!r})")
    for r, old in enumerate(old_rounds):       # the program path is a candidate's identity in a round (its label, the file stem, is not:
        pps = [c.get("program_path") for c in old["candidates"]]          # two families may use the same stem, prompts/008 C1)
        if None in pps or len(set(pps)) != len(pps):
            raise ValueError(f"round {r}: recorded candidates without a program_path or with a repeated one: {pps}")
    spec = default_spec(encoding, kind)
    n_alt = len(spec.alt_angles)
    old_arch = A.Archive.load(encoding, root=root, n_alt=n_alt, strict=True)
    old_best_e = old_arch.best()
    # an entry file the loader refuses (tampered key, failed re-validation, name != id) or an archived entry that no recorded round
    # produced cannot be replayed: it is a problem of the old archive, not a silent omission (prompts/008 B7-fix N2)
    recorded_ids = {c["id"] for r in old_rounds for c in r["candidates"]}
    refused = [{"file": f, "reason": why} for f, why in old_arch.rejected]
    unreplayed = sorted(e.id for e in old_arch.entries() if e.id not in recorded_ids)
    best_old = {"id": old_best_e.id if old_best_e else None, "key": [int(x) for x in old_best_e.key] if old_best_e else None}
    old_lean = {}                                  # entry id -> (program sha256, lean dict) of the old archive
    for f in sorted((adir / "entries").glob("*.json")) if (adir / "entries").is_dir() else []:
        d = json.loads(f.read_text())
        if isinstance(d.get("lean"), dict) and d["lean"]:
            old_lean[d["id"]] = (d.get("program_sha256"), d["lean"])
    attempts_p = root / "compress" / "attempts" / f"{encoding}.jsonl"
    disc_p = root / "compress" / "discoveries" / f"{encoding}.md"
    attempts0, disc0 = _read(attempts_p), _read(disc_p)
    old_hashes = list(dict.fromkeys(r["evaluator_sha256"] for r in old_rounds))
    run = _round_fn(encoding, kind)

    backup = []
    pre.mkdir(parents=True)
    for name in [f.name for f in files] + ["feedback", "robust.json", "summary.json"]:
        src = rdir / name
        if src.exists():
            shutil.move(str(src), str(pre / name))
            backup.append(str(pre.relative_to(root) / name))
    if adir.exists():
        shutil.move(str(adir), str(apre))
        backup.append(str(apre.relative_to(root)))
    t0 = time.time()
    new_rounds = []
    try:
        for r, old in enumerate(old_rounds):
            props = None if r == 0 else [str(root / c["program_path"]) for c in old["candidates"]]
            run(r, props, root, lean)
            new_rounds.append(json.loads((rdir / f"round-{r:03d}.json").read_text()))
    finally:         # a replay is not an attempt: the append-only logs go back to their bytes even if a round failed
        attempts_ok, disc_ok = _restore(attempts_p, attempts0), _restore(disc_p, disc0)

    entries, newly, lost, id_map = [], [], [], {}
    for r, (old, new) in enumerate(zip(old_rounds, new_rounds)):
        diff = _candidate_mismatch(old["candidates"], new["candidates"])
        if diff:
            raise RuntimeError(f"round {r}: the replayed candidates differ from the recorded ones: {diff}")
        for oc, nc in zip(old["candidates"], new["candidates"]):
            o, n = _side(oc), _side(nc)
            id_map[nc["id"]] = oc["id"]
            if o["valid"] and not n["valid"]:
                lost.append(nc["id"])
            if n["valid"] and not o["valid"]:
                newly.append(nc["id"])
            entries.append({"id": nc["id"], "old_id": oc["id"], "round": r, "label": oc["label"], "program_path": oc["program_path"],
                            "program_sha256": nc["program_sha256"], "old": o, "new": n,
                            "key_equal": (o["key"] == n["key"]) if (o["valid"] and n["valid"]) else None})

    # Lean records of unchanged programs go over to the new entries (a replay must not erase a certificate)
    arch = A.Archive.load(encoding, root=root, n_alt=n_alt, strict=True)
    carried = []
    for e in arch.entries():
        prev = old_lean.get(id_map.get(e.id))
        if prev is None or prev[0] != e.program_sha256:
            continue
        if isinstance(e.lean, dict) and e.lean.get("status") == "certified":
            continue
        e.lean = prev[1]
        carried.append(e.id)
    if carried:
        arch.save()
        for r, new in enumerate(new_rounds):
            changed = False
            for c in new["candidates"]:
                if c["id"] in carried:
                    c["lean"] = next(x.lean for x in arch.entries() if x.id == c["id"])
                    changed = True
            if changed:
                (rdir / f"round-{r:03d}.json").write_text(json.dumps(new, indent=1, default=str))
    best_new_e = arch.best()
    res = {"tag": tag, "encoding": encoding, "kind": kind, **(extra or {}), "rounds": list(range(len(new_rounds))),
           "evaluator_sha256": P.stamp_hash(encoding), "encoding_sha256": P.code_hash_for(encoding), "evaluator_sha256_old": old_hashes,
           "entries": entries, "newly_valid": newly, "lost": lost, "best_old": best_old,
           "best_new": {"id": best_new_e.id if best_new_e else None, "key": [int(x) for x in best_new_e.key] if best_new_e else None},
           "old_archive_refused": refused, "old_archive_unreplayed": unreplayed,
           "attempts_unchanged": bool(attempts_ok), "discoveries_unchanged": bool(disc_ok), "backup": backup, "lean": bool(lean),
           "lean_carried": carried, "wall_s": time.time() - t0, "round_wall_s": [x["wall_s"] for x in new_rounds],
           "provenance": provenance({"replay_tag": tag}), "written_utc": _utc()}
    out_json.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return res


def _stamp(f: pathlib.Path, d: dict) -> float:
    """Sort key of a replay record: `written_utc` (epoch seconds), file modification time for a record without that field."""
    w = d.get("written_utc")
    if w:
        try:
            return datetime.datetime.strptime(w, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
        except ValueError:
            pass
    return f.stat().st_mtime


def latest_record(encoding: str, root=None) -> dict | None:
    """The `replay-*.json` of `encoding` with the latest `written_utc` (modification time for a record without that field), or None."""
    from su2plaq.compress.spec import ROOT

    root = pathlib.Path(root) if root is not None else ROOT
    best = None
    for f in sorted((root / "results" / "compress" / encoding).glob("replay-*.json")):
        d = json.loads(f.read_text())
        k = (_stamp(f, d), f.stat().st_mtime, f.name)
        if best is None or k > best[0]:
            best = (k, d)
    return best[1] if best else None


def problems(res: dict) -> dict:
    """What prompts/204 section 12 says to stop on: entries valid before and after whose key changed (`key_equal` is False) and
    entries that were valid and are not any more (`lost`); also (B7-fix N2) the entry files of the OLD archive that the loader refused and
    the old archived entries that no recorded round produced (`refused`: file names / ids; records without those fields count none).
    -> {"key_changed": [ids], "lost": [ids], "refused": [names]}."""
    return {"key_changed": [e["id"] for e in res["entries"] if e["key_equal"] is False], "lost": list(res["lost"]),
            "refused": [x["file"] for x in res.get("old_archive_refused", [])] + list(res.get("old_archive_unreplayed", []))}


def report(res: dict, out=None, err=None) -> int:
    """Print the one-line summary; 1 (and a message on `err`) when a key changed or a valid entry was lost, else 0."""
    out, err = out or sys.stdout, err or sys.stderr
    bad = problems(res)
    print(json.dumps({"tag": res["tag"], "rounds": res["rounds"], "newly_valid": res["newly_valid"], "lost": res["lost"],
                      "key_changed": bad["key_changed"], "refused": bad["refused"], "best_old": res["best_old"], "best_new": res["best_new"],
                      "wall_s": round(res["wall_s"])}), file=out)
    if bad["key_changed"] or bad["lost"] or bad["refused"]:
        print(f"REPLAY PROBLEM: key changed for {bad['key_changed']}; lost (valid before, invalid now): {bad['lost']}; "
              f"old archive entries refused by the loader or never produced by a recorded round: {bad['refused']}", file=err)
        return 1
    return 0


def main(argv=None) -> int:
    from su2plaq.encodings import registry

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--encoding", required=True)
    ap.add_argument("--kind", default=None, help="default: the registry's loop kind of the encoding")
    ap.add_argument("--root", default=None)
    ap.add_argument("--tag", default="008")
    ap.add_argument("--lean", action="store_true", help="also Lean-certify each round's best (default: no; the old records are carried over)")
    a = ap.parse_args(argv)
    kind = a.kind or registry.info(a.encoding).loop_kind
    return report(replay(a.encoding, kind, root=a.root, tag=a.tag, lean=a.lean))


if __name__ == "__main__":
    sys.exit(main())

"""Replay of the rishon loop's rounds 0..R under a new evaluator hash (prompts/204 section 6.2; METHODS-rishon R15).

Needed after the rishon prune cap moved from 1 % to 10 % of tol_err (and the det code touched further hashed rishon files): the archive
entries carry the old `evaluator_sha256`, and `test_M6_G1` requires the best entry's hash to equal the current one.  The programs
are NOT changed; every recorded round is re-run in order with the same programs (`round.run_round(kind, r, evaluate=True,
proposals=<that round's program paths in recorded order>, lean=lean)`), a replay is not a new attempt (stop-rule counter, proposer
sessions and MAX_ROUNDS bookkeeping are untouched).  Nothing is deleted: the old round files, feedback, robust cache and summary go to
results/compress/rishon/pre-<tag>/ and the old archive to compress/archive/rishon-pre-<tag>/; the attempts log and the discoveries file
(appended to by `run_round`) are restored byte for byte.  Any later edit of a file in RISHON_EVALUATOR_FILES needs a new replay with a
new tag before test_M6_G1 / G5 can pass.

  python -m su2plaq.rishon.compress.replay [--kind step] [--root R] [--tag 204] [--lean]

Writes results/compress/rishon/replay-<tag>.json (schema: section 6.2 step 6 of prompts/204).  Refuses (ValueError, nothing touched) if
that file or a pre-<tag> folder exists, if round files are missing / not contiguous from 0, or belong to another kind.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time

ENC = "rishon"
TAG = "204"


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


def replay(kind: str = "step", root=None, tag: str = TAG, lean: bool = False) -> dict:
    from su2plaq.compress import archive as A
    from su2plaq.compress.spec import ROOT, default_spec
    from su2plaq.metrics.provenance import provenance
    from su2plaq.rishon.compress import code_hash
    from su2plaq.rishon.compress.round import run_round
    from su2plaq.rishon.verify import RISHON_PRUNE_FRACTION

    root = pathlib.Path(root) if root is not None else ROOT
    rdir = root / "results" / "compress" / ENC
    adir = root / "compress" / "archive" / ENC
    out_json, pre = rdir / f"replay-{tag}.json", rdir / f"pre-{tag}"
    apre = root / "compress" / "archive" / f"{ENC}-pre-{tag}"
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
    if any(r.get("kind") != kind or r.get("encoding") != ENC for r in old_rounds):
        raise ValueError(f"round files do not all belong to ({ENC!r}, {kind!r})")
    spec = default_spec(ENC, kind)
    old_best_e = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True).best()
    best_old = {"id": old_best_e.id if old_best_e else None, "key": [int(x) for x in old_best_e.key] if old_best_e else None}
    attempts_p, disc_p = root / "compress" / "attempts" / f"{ENC}.jsonl", root / "compress" / "discoveries" / f"{ENC}.md"
    attempts0, disc0 = _read(attempts_p), _read(disc_p)
    old_hashes = list(dict.fromkeys(r["evaluator_sha256"] for r in old_rounds))

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
    new_rounds, infos = [], []
    try:
        for r, old in enumerate(old_rounds):
            props = None if r == 0 else [str(root / c["program_path"]) for c in old["candidates"]]
            infos.append(run_round(kind, r, evaluate=True, dry_run=False, root=root, proposals=props, lean=lean))
            new_rounds.append(json.loads((rdir / f"round-{r:03d}.json").read_text()))
    finally:         # a replay is not an attempt: the append-only logs go back to their bytes even if a round failed
        attempts_ok, disc_ok = _restore(attempts_p, attempts0), _restore(disc_p, disc0)

    entries, newly, lost = [], [], []
    for r, (old, new) in enumerate(zip(old_rounds, new_rounds)):
        nmap = {c["label"]: c for c in new["candidates"]}
        if len(nmap) != len(new["candidates"]) or {c["label"] for c in old["candidates"]} != set(nmap):
            raise RuntimeError(f"round {r}: the replayed candidates differ from the recorded ones")
        for oc in old["candidates"]:
            nc = nmap[oc["label"]]
            o, n = _side(oc), _side(nc)
            if o["valid"] and not n["valid"]:
                lost.append(nc["id"])
            if n["valid"] and not o["valid"]:
                newly.append(nc["id"])
            entries.append({"id": nc["id"], "old_id": oc["id"], "round": r, "label": oc["label"], "program_path": oc["program_path"],
                            "program_sha256": nc["program_sha256"], "old": o, "new": n,
                            "key_equal": (o["key"] == n["key"]) if (o["valid"] and n["valid"]) else None})
    best_new_e = A.Archive.load(ENC, root=root, n_alt=len(spec.alt_angles), strict=True).best()
    res = {"tag": tag, "encoding": ENC, "kind": kind, "prune_fraction": RISHON_PRUNE_FRACTION, "rounds": list(range(len(new_rounds))),
           "evaluator_sha256": code_hash(), "evaluator_sha256_old": old_hashes, "entries": entries, "newly_valid": newly, "lost": lost,
           "best_old": best_old,
           "best_new": {"id": best_new_e.id if best_new_e else None, "key": [int(x) for x in best_new_e.key] if best_new_e else None},
           "attempts_unchanged": bool(attempts_ok), "discoveries_unchanged": bool(disc_ok), "backup": backup, "lean": bool(lean),
           "wall_s": time.time() - t0, "round_wall_s": [x["wall_s"] for x in new_rounds],
           "provenance": provenance({"replay_tag": tag})}
    out_json.write_text(json.dumps(res, indent=1, default=str) + "\n")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kind", default="step")
    ap.add_argument("--root", default=None)
    ap.add_argument("--tag", default=TAG)
    ap.add_argument("--lean", action="store_true", help="also Lean-certify each round's best (default: no; C4 handles Lean)")
    a = ap.parse_args(argv)
    res = replay(a.kind, root=a.root, tag=a.tag, lean=a.lean)
    print(json.dumps({"tag": res["tag"], "rounds": res["rounds"], "newly_valid": res["newly_valid"], "lost": res["lost"],
                      "best_old": res["best_old"], "best_new": res["best_new"], "wall_s": round(res["wall_s"])}))
    return 0 if not res["lost"] else 1


if __name__ == "__main__":
    sys.exit(main())

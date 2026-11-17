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

Since prompts/008 step B7 this module is a thin wrapper: `replay(kind, root, tag="204", lean=False)` is
`su2plaq.compress.replay.replay("rishon", ...)` plus the record field `prune_fraction` (RISHON_PRUNE_FRACTION); the generic
procedure (and `problems`) live in su2plaq/compress/replay.py.  Rishon's own `round.run_round` is used for every round.

Writes results/compress/rishon/replay-<tag>.json (schema: section 6.2 step 6 of prompts/204).  Refuses (ValueError, nothing touched) if
that file or a pre-<tag> folder exists, if round files are missing / not contiguous from 0, or belong to another kind.
"""
from __future__ import annotations

import argparse
import sys

from su2plaq.compress import replay as _G
from su2plaq.compress.replay import problems  # noqa: F401  (re-exported: the CLI and the unit tests use it from here)

ENC = "rishon"
TAG = "204"


def replay(kind: str = "step", root=None, tag: str = TAG, lean: bool = False) -> dict:
    from su2plaq.rishon.verify import RISHON_PRUNE_FRACTION

    return _G.replay(ENC, kind, root=root, tag=tag, lean=lean, extra={"prune_fraction": RISHON_PRUNE_FRACTION})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kind", default="step")
    ap.add_argument("--root", default=None)
    ap.add_argument("--tag", default=TAG)
    ap.add_argument("--lean", action="store_true", help="also Lean-certify each round's best (default: no; C4 handles Lean)")
    a = ap.parse_args(argv)
    return _G.report(replay(a.kind, root=a.root, tag=a.tag, lean=a.lean))


if __name__ == "__main__":
    sys.exit(main())

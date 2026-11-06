#!/usr/bin/env python
"""M10 driver: the laptop compression loop on the fuzzy units, through the hook (plan 302 §3; METHODS-fuzzy F9).

  python scripts/m10_round.py seed       --encoding fuzzy_ub|fuzzy_link [round-options]
  python scripts/m10_round.py round      --encoding E --round r --evaluate [--programs P ...] [--no-lean]
  python scripts/m10_round.py candidate  <program.py> --encoding E [--kind K] --trial|--full [--json out]
  python scripts/m10_round.py oracle     --encoding E [oracle options]
  python scripts/m10_round.py brief      --encoding E --round r --family F
  python scripts/m10_round.py ideation   --encoding E
  python scripts/m10_round.py report     --encoding E [--out path]
  python scripts/m10_round.py best-step  [--order 1|2] [--no-outer] [--root R] [--out path]   # results/fuzzy/compressed_step.json

The hook (`su2plaq.fuzzy.compress_hook.install()`) is installed before anything else; `--kind` defaults to the unit's kind."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from su2plaq.fuzzy import compress_hook as H  # noqa: E402

SUBS = ("seed", "round", "candidate", "oracle", "brief", "ideation", "report", "best-step")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in SUBS:
        print(__doc__)
        return 2
    sub, rest = argv[0], argv[1:]
    H.install()
    ap = argparse.ArgumentParser(prog=f"m10_round.py {sub}", add_help=False)
    ap.add_argument("--encoding", choices=H.ENCODINGS)
    ap.add_argument("--kind")
    ap.add_argument("--round", type=int)
    ap.add_argument("--family")
    ap.add_argument("--programs", nargs="*")
    ap.add_argument("--evaluate", action="store_true")
    ap.add_argument("--no-lean", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--root")
    ap.add_argument("--out")
    ap.add_argument("--order", type=int, default=1)
    ap.add_argument("--no-outer", action="store_true")
    a, extra = ap.parse_known_args(rest)
    if sub == "best-step":
        doc = H.write_compressed_step(root=a.root, out=a.out, order=a.order, with_outer=not a.no_outer)
        print(json.dumps({k: doc[k] for k in ("units", "composed", "general", "verification")}, indent=1, default=str))
        return 0
    if a.encoding is None:
        ap.error("--encoding is required")
    enc, kind = a.encoding, a.kind or H.UNITS[a.encoding]
    if sub == "seed":
        from su2plaq.compress import round as R

        return R.main(["--encoding", enc, "--kind", kind, "--seed", *(["--no-lean"] if a.no_lean else []),
                       *(["--dry-run"] if a.dry_run else []), *(["--root", a.root] if a.root else [])])
    if sub == "round":
        from su2plaq.compress import round as R

        if a.round is None:
            ap.error("--round is required")
        if a.programs:
            info = R.run_round(enc, kind, a.round, evaluate=True, dry_run=a.dry_run, root=a.root, proposals=a.programs,
                               lean=not a.no_lean)
            print(json.dumps(info, indent=1))
            return 0
        return R.main(["--encoding", enc, "--kind", kind, "--round", str(a.round), *(["--evaluate"] if a.evaluate else []),
                       *(["--no-lean"] if a.no_lean else []), *(["--dry-run"] if a.dry_run else []),
                       *(["--root", a.root] if a.root else [])])
    if sub == "candidate":
        from su2plaq.compress import run_candidate as RC

        prog = [x for x in extra if not x.startswith("--")][:1]
        flags = [x for x in extra if x.startswith("--")] + (["--json", a.out] if a.out else [])
        if not prog:
            ap.error("candidate needs a program path")
        return RC.main([prog[0], "--encoding", enc, "--kind", kind, *flags])
    if sub == "oracle":
        from su2plaq.compress import oracle as OR

        return OR.main(["--encoding", enc, "--kind", kind, *extra])
    if sub in ("brief", "ideation"):
        from su2plaq.compress import brief as BR

        if sub == "ideation":
            print(BR.make_ideation_brief(enc, kind, root=a.root))
            return 0
        if a.round is None or not a.family:
            ap.error("brief needs --round and --family")
        print(BR.make_brief(enc, kind, a.round, a.family, root=a.root))
        return 0
    if sub == "report":
        from su2plaq.compress import report as RP

        return RP.main(["--encoding", enc, "--kind", kind, *(["--out", a.out] if a.out else []), *(["--root", a.root] if a.root else [])])
    return 2


if __name__ == "__main__":
    sys.exit(main())

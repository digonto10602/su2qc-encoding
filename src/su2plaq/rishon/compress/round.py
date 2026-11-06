"""Rishon compression rounds (prompts/203 section 3.1).  STUBS (step 6.4)."""
from __future__ import annotations

from su2plaq.rishon.compress._pending import pending


def run_round(kind: str, round: int, evaluate: bool, dry_run: bool = False, root=None, proposals: list | None = None,
              lean: bool = True) -> dict:
    raise pending("round.run_round", "6.4")


def certify_best(kind="step", root=None) -> dict:
    raise pending("round.certify_best", "6.4")


def main(argv=None) -> int:
    raise pending("round.main", "6.4")


if __name__ == "__main__":
    raise SystemExit(main())

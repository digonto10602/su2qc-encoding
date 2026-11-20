"""Run the cross-encoding results of milestone M11 (prompts/009 §5.4): spectra.json, gate-table.json, tradeoff.pdf, tables.md.

    PYTHONPATH=src python scripts/m11_results.py [--no-headline] [--root R]

Writes under <root>/results/crosscheck/ (root default: this checkout).  Every number comes from a source file or a production function;
headlines that are not cached are recorded as pending with the reason (never guessed).  `--no-headline` skips the headline
cross-verdicts (the slow part).  Provenance records the command line.  About 4-5 minutes.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-headline", action="store_true", help="skip the headline cross-verdicts")
    ap.add_argument("--root", default=None, help="project root holding results/ and compress/ (default: this checkout)")
    a = ap.parse_args(argv)
    from su2plaq.crosscheck import report as R

    root = pathlib.Path(a.root) if a.root else None
    command = "python scripts/m11_results.py" + (" --no-headline" if a.no_headline else "") + (f" --root {a.root}" if a.root else "")
    git = R.git_snapshot()          # once, before any output file is written (the first write would otherwise dirty the tree for the second)
    s = R.spectra_results(root=root, headline=not a.no_headline, command=command, git=git)
    t = R.gate_table(root=root, command=command, git=git)
    fig = R.tradeoff_figure(root=root)
    text = R.render(root=root)
    md = pathlib.Path(fig).with_name("tables.md")
    md.write_text(text)
    print(f"spectra.json: {len(s['ks']['cross_verdicts'])} cross-verdicts, {len(s['ks']['headline_skipped'])} headline cross-verdicts skipped")
    for r in t["rows"]:
        print(f"gate-table.json: {r['encoding']:8s} {r['status'][:150]}")
    print(f"wrote {pathlib.Path(fig).parent}/{{spectra.json,gate-table.json,tradeoff.pdf,tables.md}}")


if __name__ == "__main__":
    main()

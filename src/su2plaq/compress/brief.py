"""Briefs for the proposer sessions (prompts/002 §5 row 2.6; design B §3; prompts/006).

A brief points at files (paths relative to the repository root), it does not paste their content: the task specification, the
parent program and its feedback JSON, a few archive alternatives with their costs, the last attempts of the family, the DISCOVERY
notes (at most 30 lines) and the Lean structure facts.  The session writes ONE program to `compress/programs/<E>/<family>/NNN-*.py`.
"""
from __future__ import annotations

import json
import pathlib

from su2plaq.compress import archive as A
from su2plaq.compress.spec import ROOT, default_spec

TASK_LINE = "Rewrite the parent to improve the key; return the complete program"
MAX_DISCOVERY_LINES = 30


def _root(root):
    return pathlib.Path(root) if root is not None else ROOT


def _rel(p, root: pathlib.Path) -> str:
    p = pathlib.Path(p)
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return str(p)


def _spec_file(encoding, kind, root: pathlib.Path) -> pathlib.Path:
    spec = default_spec(encoding, kind)
    return spec.write(root / "compress" / "specs" / f"{encoding}-{kind}.md")


def _cost(e: A.Entry) -> str:
    return f"CX {e.key[0]:g}, T_eps {e.key[1]:g}, depth_CT {e.key[2]:g}, qubits {e.key[3]:g}"


def _attempts(root: pathlib.Path, encoding: str, family: str, n: int = 5) -> list[dict]:
    f = root / "compress" / "attempts" / f"{encoding}.jsonl"
    if not f.exists():
        return []
    recs = [json.loads(x) for x in f.read_text().splitlines() if x.strip()]
    return [r for r in recs if r.get("family") == family][-n:]


def _discoveries(root: pathlib.Path, encoding: str) -> list[str]:
    f = root / "compress" / "discoveries" / f"{encoding}.md"
    if not f.exists():
        return []
    return [ln for ln in f.read_text().splitlines() if ln.strip()][-MAX_DISCOVERY_LINES:]


def _next_number(root: pathlib.Path, encoding: str, family: str) -> int:
    d = root / "compress" / "programs" / encoding / family
    nums = [int(p.name[:3]) for p in d.glob("[0-9][0-9][0-9]-*.py")] if d.is_dir() else []
    return max(nums, default=0) + 1


def _structure_pointer(root: pathlib.Path) -> str:
    f = root / "compress" / "lean" / "structure.json"
    return (f"`{_rel(f, root)}` (machine-proved facts about the problem; the same facts are in the section 'Proved structure (Lean)' "
            "of the specification)" if f.exists() else "pending: `compress/lean/structure.json` has not been generated yet")


def make_ideation_brief(encoding, kind, root=None) -> pathlib.Path:
    """Ideation session: the specification only (no seeds, as in Gu et al.); output `compress/ideation/<encoding>.md` with at most
    5 families, each one datapath idea."""
    root = _root(root)
    spec = _spec_file(encoding, kind, root)
    out = root / "compress" / "briefs" / encoding / "ideation.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# Ideation brief: `{encoding}` / `{kind}`\n\n"
        f"Read the task specification `{_rel(spec, root)}` and nothing else about previous solutions (no seeds, no archive).\n"
        f"Proved structure (Lean): {_structure_pointer(root)}.\n\n"
        f"Write `compress/ideation/{encoding}.md`: at most 5 families, one datapath idea each (what the registers hold, which gates carry "
        "the weight, why it should beat a generic circuit), most promising first. Use the oracle "
        f"(`python -m su2plaq.compress.oracle --encoding {encoding} --kind {kind} ...`) to look at the target; write scratch files only "
        "under `scratch/proposer/`. Do not write programs in this session.\n")
    return out


def make_brief(encoding, kind, round: int, family: str, root=None) -> pathlib.Path:
    """`compress/briefs/<encoding>/round-rrr-<family>.md` for one proposer session (see the module docstring)."""
    root = _root(root)
    spec = _spec_file(encoding, kind, root)
    arch = A.Archive.load(encoding, root=root, n_alt=len(default_spec(encoding, kind).alt_angles), strict=True)
    parent = arch.family_best(family) if family != "seed" else None
    elites = [e for e in sorted(arch.elites().values(), key=lambda x: (tuple(x.key), x.id)) if parent is None or e.id != parent.id]
    elites = [e for e in elites if (root / e.program_path).exists() or (ROOT / e.program_path).exists()]   # real program files only
    alts = elites[:3]
    gb = arch.best()
    if round % 3 == 0 and gb is not None and gb not in alts and (parent is None or gb.id != parent.id):
        alts = alts[:2] + [gb]          # migration: every third round the global best is offered as an alternative
    lines = [f"# Brief: `{encoding}` / `{kind}`, round {round}, family `{family}`\n",
             f"**Task.** {TASK_LINE}.\n",
             f"- Task specification: `{_rel(spec, root)}`",
             f"- Proved structure (Lean): {_structure_pointer(root)}",
             f"- Check a draft: `python -m su2plaq.compress.run_candidate <program.py> --encoding {encoding} --kind {kind} --trial` "
             "(seconds), `--full` before you finish; the oracle: `python -m su2plaq.compress.oracle ...`"]
    if parent is not None:
        lines += ["", "## Parent", f"- program: `{parent.program_path}` (entry `{parent.id}`, sha256 {parent.program_sha256[:12]})",
                  f"- feedback: `results/compress/{encoding}/feedback/{parent.id}.json`", f"- cost: {_cost(parent)}",
                  f"- summary: {parent.summary}"]
    else:
        lines += ["", "## Parent", "none: write a fresh program for this family (the seeds below are alternatives, not parents)."]
    lines += ["", "## Archive alternatives (paths and costs only)"]
    lines += [f"- `{e.program_path}` (entry `{e.id}`, family `{e.family}`): {_cost(e)}; {e.summary}" for e in alts] or ["- (none yet)"]
    att = _attempts(root, encoding, family)
    lines += ["", f"## Last {len(att) or 0} attempts of family `{family}`"]
    lines += [f"- `{a['id']}`: {'valid' if a['valid'] else 'invalid (' + a['reason'] + ')'}"
              f"{', key ' + str(a['key']) if a.get('valid') else ''}; {a.get('summary', '')}" for a in att] or ["- (none yet)"]
    disc = _discoveries(root, encoding)
    lines += ["", f"## DISCOVERY notes of all programs (last {len(disc)} of at most {MAX_DISCOVERY_LINES} lines)"]
    lines += disc or ["- (none yet)"]
    n = _next_number(root, encoding, family)
    lines += ["", "## Output", f"Write ONE program to `compress/programs/{encoding}/{family}/{n:03d}-<slug>.py` (docstring starting with "
              "`SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under "
              "`scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.", ""]
    out = root / "compress" / "briefs" / encoding / f"round-{round:03d}-{family}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return out

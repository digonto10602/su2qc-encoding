"""Briefs for the rishon proposer sessions (prompts/203 section 3.1; the laptop `su2plaq.compress.brief` for the encoding rishon).

A brief points at files (paths relative to the repository root), it does not paste their content: the task specification
(`compress/specs/rishon-<kind>.md`, rendered by `rishon.compress.spec.render_spec`), the structure facts, the parent program and its
feedback JSON, a few archive alternatives with their costs, the last attempts of the family and the DISCOVERY notes.  The laptop
proposer agent file (`~/.claude/agents/proposer.md`) names the `twelve` commands and says outer qubits may be read; it is not edited,
so every brief starts with an explicit "rishon overrides" block that names the commands of THIS package and the rishon rules.

  python -m su2plaq.rishon.compress.brief (--ideation | --round r --family F) [--kind step] [--root R]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import su2plaq.rishon.compress  # noqa: F401  (registers the encoding)
from su2plaq.compress import archive as A
from su2plaq.compress import brief as LBR
from su2plaq.compress.spec import ROOT, default_spec
from su2plaq.rishon.compress import robust as RB
from su2plaq.rishon.compress import spec as S

ENC = "rishon"
TASK_LINE = LBR.TASK_LINE
MAX_DISCOVERY_LINES = LBR.MAX_DISCOVERY_LINES


def _root(root):
    return pathlib.Path(root) if root is not None else ROOT


def _spec_files(kind: str, root: pathlib.Path):
    """(spec markdown, structure json), both (re)written under `root`/compress/specs/ from the production renderer."""
    spec = default_spec(ENC, kind)
    d = root / "compress" / "specs"
    return S.write_spec(spec, d / f"{ENC}-{kind}.md"), S.write_structure_json(d / f"{ENC}-structure.json")


def _commands(kind: str) -> str:
    return (f"`python -m su2plaq.rishon.compress.run_candidate <program.py> --kind {kind} --trial` (seconds) and `--full` (all inner "
            f"codes, three angle pairs, Gauss sample); the oracle: `python -m su2plaq.rishon.compress.oracle --kind {kind} "
            "[--column j] [--element i j] [--codec [--state k]] [--pairs [--closed]] [--block]`")


def _overrides(kind: str) -> list:
    """The rishon rules that differ from the laptop proposer agent file (and from the twelve brief)."""
    return [
        "## Rishon overrides (these win over `~/.claude/agents/proposer.md`, which describes the `twelve` encoding)",
        f"- Commands: {_commands(kind)}. Do NOT use `su2plaq.compress.run_candidate` / `su2plaq.compress.oracle` with `--encoding`.",
        "- **Outer qubits `o[16..47]` may be neither read nor written** (a gate on them is `outer_read_unsupported` / `writes_outer`, "
        "invalid). The target acts on the 16 data qubits; the outer register only counts in the key's qubit component.",
        "- **A `--trial` result is not a validity verdict.** Trial checks only a seeded subset of the inner codes at the nominal angles "
        "with no Gauss sample; a wrong controlled rotation acting on few codes can pass it (reports/tests/215: most single-gate errors passed it). "
        "Only `--full` decides validity (all codes, three angle pairs with an identical skeleton, Gauss sample, prune cap): run it "
        "before you finish, and never conclude a design is correct from a trial `valid`.",
        "- The prune cap (`dropped_total` <= 1e-12) is part of validity: see the Correctness section of the specification "
        "(prune budget: see Correctness); a program that is exact but over the cap is recorded as `pruning_bound` (invalid).",
        "- Programs import only numpy / maths modules / qiskit / `su2plaq.compress.{oracle,builder,spec}` (`get_encoding(\"rishon\")` "
        "gives the pairs, targets and codes); never `su2plaq.rishon.*`. Do not ship `.lean` lemma files (not checked for rishon).",
        "- Structure facts (what Lean proved and what is only numerical): `compress/specs/rishon-structure.json` and the section "
        "'Proved structure (Lean)' of the specification.",
    ]


def make_ideation_brief(kind="step", root=None) -> pathlib.Path:
    """Ideation session: the specification only (no seeds, as in Gu et al.); output `compress/ideation/rishon.md` with at most 5
    families, each one datapath idea.  -> compress/briefs/rishon/ideation.md"""
    root = _root(root)
    spec, structure = _spec_files(kind, root)
    out = root / "compress" / "briefs" / ENC / "ideation.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"# Ideation brief: `{ENC}` / `{kind}`\n\n"
        f"Read the task specification `{LBR._rel(spec, root)}` and the structure facts `{LBR._rel(structure, root)}`; nothing else "
        "about previous solutions (no seeds, no archive).\n\n"
        f"Write `compress/ideation/{ENC}.md`: at most 5 families (`## F1`, ... headings), one datapath idea each (what the registers "
        "hold, which gates carry the weight, why it should beat a generic circuit), most promising first. "
        "Write scratch files only under `scratch/proposer/`. Do not write programs in this session.\n\n"
        + "\n".join(_overrides(kind)) + "\n")
    return out


def make_brief(kind, round: int, family: str, root=None) -> pathlib.Path:
    """`compress/briefs/rishon/round-rrr-<family>.md` for one proposer session (see the module docstring)."""
    root = _root(root)
    spec, structure = _spec_files(kind, root)
    arch = A.Archive.load(ENC, root=root, n_alt=len(default_spec(ENC, kind).alt_angles), strict=True)
    parent = arch.family_best(family) if family != "seed" else None
    has_file = lambda e: (root / e.program_path).exists() or (ROOT / e.program_path).exists()    # real program files only
    ranked = [e for e in sorted(arch.elites().values(), key=lambda x: (tuple(x.key), x.id))
              if (parent is None or e.id != parent.id) and has_file(e)]
    alts = LBR._diverse(ranked, parent.family if parent is not None else family)
    gb = arch.best()
    if round % 3 == 0 and gb is not None and has_file(gb) and (parent is None or gb.id != parent.id) and gb not in alts:
        alts = (alts[:2] if len(alts) >= 3 else alts) + [gb]          # migration: every third round the global best is offered
    lines = [f"# Brief: `{ENC}` / `{kind}`, round {round}, family `{family}`\n",
             f"**Task.** {TASK_LINE}.\n",
             f"- Task specification: `{LBR._rel(spec, root)}`",
             f"- Structure facts: `{LBR._rel(structure, root)}`", ""] + _overrides(kind)
    if parent is not None:
        lines += ["", "## Parent", f"- program: `{parent.program_path}` (entry `{parent.id}`, sha256 {parent.program_sha256[:12]})",
                  f"- feedback: `results/compress/{ENC}/feedback/{parent.id}.json`", f"- cost: {LBR._cost(parent)}",
                  f"- summary: {parent.summary}"]
    else:
        lines += ["", "## Parent", "none: write a fresh program for this family (the seeds below are alternatives, not parents)."]
    lines += ["", "## Archive alternatives (paths and costs only)"]
    lines += [f"- `{e.program_path}` (entry `{e.id}`, family `{e.family}`): {LBR._cost(e)}; {e.summary}" for e in alts] or ["- (none yet)"]
    att = LBR._attempts(root, ENC, family)
    lines += ["", f"## Last {len(att) or 0} attempts of family `{family}`"]
    lines += [f"- `{a['id']}`: {'valid' if a['valid'] else 'invalid (' + a['reason'] + ')'}"
              f"{', key ' + str(a['key']) if a.get('valid') else ''}; {a.get('summary', '')}" for a in att] or ["- (none yet)"]
    disc = LBR._discoveries(root, ENC)
    lines += ["", f"## DISCOVERY notes of all programs (last {len(disc)} of at most {MAX_DISCOVERY_LINES} lines)"]
    lines += disc or ["- (none yet)"]
    n = LBR._next_number(root, ENC, family)
    lines += ["", RB.HEADLINE_SECTION.rstrip("\n")]          # prompts/203 section 13 E3
    lines += ["", "## Output", f"Write ONE program to `compress/programs/{ENC}/{family}/{n:03d}-<slug>.py` (docstring starting with "
              "`SUMMARY:`, at most 3 `DISCOVERY:` lines, `FAMILY`, `PARENT`, `def build(spec) -> Builder`); scratch files only under "
              "`scratch/proposer/`. The file is immutable once evaluated; a change needs a new number.", ""]
    out = root / "compress" / "briefs" / ENC / f"round-{round:03d}-{family}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m su2plaq.rishon.compress.brief")
    ap.add_argument("--kind", default="step", choices=["step", "UB", "UE"])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ideation", action="store_true")
    g.add_argument("--round", type=int)
    ap.add_argument("--family")
    ap.add_argument("--root")
    a = ap.parse_args(argv)
    if a.ideation:
        print(make_ideation_brief(a.kind, a.root))
        return 0
    if not a.family:
        ap.error("--round needs --family")
    print(make_brief(a.kind, a.round, a.family, a.root))
    return 0


if __name__ == "__main__":
    sys.exit(main())

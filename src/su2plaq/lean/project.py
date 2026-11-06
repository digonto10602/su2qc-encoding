"""Lean project handle: paths, pins, building, axiom audit, sorry scan (prompts/006 §2, §5).

All Lean work runs as a subprocess of `lake` inside `lean/` with `~/.elan/bin` on PATH.  Nothing here is part of the
numerical validity verdict.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import time

LEAN_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parents[3] / "lean"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
MATHLIB_REV = "v4.35.0"
STANDARD_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})

# LOCKED names (tests/acceptance/m2/test_lean_formal.py, test_lean_structure.py; prompts/006 §3).
GENERIC_THEOREMS: tuple[str, ...] = (
    "Su2Plaq.norm_sum_sq_of_pairwise_orth", "Su2Plaq.opNorm_add_three_le_of_orth", "Su2Plaq.rss_le_sum",
    "Su2Plaq.pruning_triangle", "Su2Plaq.opNorm_le_of_blockdiag", "Su2Plaq.verdict_sound",
    "Su2Plaq.gauss_max_ge", "Su2Plaq.span_leak_le_four_gauss",
    "Su2Plaq.cs_block_bound",
    "Su2Plaq.norm_list_prod_le_one", "Su2Plaq.prod_sub_prod_le", "Su2Plaq.synth_bound",
    "Su2Plaq.ctrl_mulVec_e", "Su2Plaq.mono_mulVec_e", "Su2Plaq.mono_conjTranspose_mul", "Su2Plaq.sandwich",
    "Su2Plaq.rccx_crx_rccx_eq_ccrx", "Su2Plaq.h_z_h", "Su2Plaq.h_rz_h",
    "Su2Plaq.cx_involutive", "Su2Plaq.perm_conj_diagonal", "Su2Plaq.cx_comm_diagonal_of_indep", "Su2Plaq.cx_comm_cx",
    "Su2Plaq.ccz_circuit",
    "Su2Plaq.kron_disjoint_comm", "Su2Plaq.outer_electric_commutes",
)
COUNT_THEOREMS: tuple[str, ...] = (
    "Su2Plaq.card_physical", "Su2Plaq.card_link_patterns", "Su2Plaq.card_two_or_more", "Su2Plaq.card_closed",
    "Su2Plaq.far_end_weighted", "Su2Plaq.card_supported_outer", "Su2Plaq.max_states_per_outer",
    "Su2Plaq.dont_care_codes",
)

_NATIVE_RE = re.compile(r"\._native\.native_decide\.ax_\d+(_\d+)*$")


def _env() -> dict:
    env = dict(os.environ)
    env["PATH"] = str(pathlib.Path.home() / ".elan" / "bin") + os.pathsep + env.get("PATH", "")
    return env


def lake(args: list[str], timeout: float = 1800.0) -> subprocess.CompletedProcess:
    """Run `lake <args>` with cwd = LEAN_DIR and ~/.elan/bin on PATH; returns the CompletedProcess (text mode)."""
    return subprocess.run(["lake", *args], cwd=LEAN_DIR, env=_env(), capture_output=True, text=True, timeout=timeout)


def build(target: str | None = None, timeout: float = 1800.0) -> dict:
    """`lake build [target]`.  Returns {"ok", "seconds", "stdout", "stderr"}; a timeout gives ok=False."""
    args = ["build"] + ([target] if target else [])
    t0 = time.time()
    try:
        r = lake(args, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {"ok": False, "seconds": time.time() - t0, "stdout": out, "stderr": err + f"\nTIMEOUT after {timeout}s"}
    return {"ok": r.returncode == 0, "seconds": time.time() - t0, "stdout": r.stdout, "stderr": r.stderr}


def is_native_axiom(ax: str) -> bool:
    """True for the per-theorem `native_decide` axioms (compiler trust) and `Lean.ofReduceBool`."""
    return ax == "Lean.ofReduceBool" or bool(_NATIVE_RE.search(ax))


_DEPENDS_RE = re.compile(r"'([^']+)' depends on axioms:\s*\[(.*?)\]", re.S)
_NONE_RE = re.compile(r"'([^']+)' does not depend on any axioms")
_ERR_RE = re.compile(r"AxiomCheck\w*\.lean:(\d+):\d+: error")


def print_axioms(names: list[str], timeout: float = 600.0) -> dict[str, frozenset[str]]:
    """Axioms of each named constant: writes lean/AxiomCheck.lean (`import Su2Plaq` + one `#print axioms` per name) and
    runs `lake env lean`.  A constant that does not exist (or any elaboration error on its line) maps to {"<unknown>"}."""
    names = list(names)
    if not names:
        return {}
    lines = ["import Su2Plaq", ""] + [f"#print axioms {n}" for n in names]
    # lean/AxiomCheck.lean (gitignored); the pid suffix keeps parallel (xdist) callers from overwriting each other.
    fname = f"AxiomCheck_{os.getpid()}.lean"
    (LEAN_DIR / fname).write_text("\n".join(lines) + "\n")
    try:
        r = lake(["env", "lean", fname], timeout=timeout)
    finally:
        (LEAN_DIR / fname).unlink(missing_ok=True)
    text = r.stdout + "\n" + r.stderr
    out: dict[str, frozenset[str]] = {}
    for m in _DEPENDS_RE.finditer(text):
        out[m.group(1)] = frozenset(a.strip() for a in m.group(2).replace("\n", " ").split(",") if a.strip())
    for m in _NONE_RE.finditer(text):
        out[m.group(1)] = frozenset()
    for m in _ERR_RE.finditer(text):          # error on line L (1-based); names start at line 3
        idx = int(m.group(1)) - 3
        if 0 <= idx < len(names) and names[idx] not in out:
            out[names[idx]] = frozenset({"<unknown>"})
    for n in names:                           # anything unaccounted for (e.g. import failure) is unknown
        out.setdefault(n, frozenset({"<unknown>"}))
    return out


def _strip_lean_comments(text: str) -> list[str]:
    """Return the source lines with `-- ...` and (nested) `/- ... -/` comments and string literals blanked out."""
    out, depth, in_str, i, n = [], 0, False, 0, len(text)
    cur: list[str] = []
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        if c == "\n":
            out.append("".join(cur)); cur = []; i += 1; continue
        if depth > 0:
            if two == "/-":
                depth += 1; i += 2
            elif two == "-/":
                depth -= 1; i += 2
            else:
                i += 1
            continue
        if in_str:
            if c == "\\":
                i += 2
            else:
                if c == '"':
                    in_str = False
                i += 1
            continue
        if two == "/-":
            depth = 1; i += 2
        elif two == "--":
            while i < n and text[i] != "\n":
                i += 1
        elif c == '"':
            in_str = True; i += 1
        elif c == "'" and not (cur and (cur[-1].isalnum() or cur[-1] in "_'.!?")):
            # char literal ('x', '"', '\\n', '\\'', '\\x41', '\\u{..}'); a `'` after an identifier char is part of the name
            if text[i + 1:i + 2] == "\\":
                j = text.find("'", i + 3)
                i = n if j < 0 else j + 1
            elif text[i + 2:i + 3] == "'":
                i += 3
            else:
                cur.append(c); i += 1
        else:
            cur.append(c); i += 1
    out.append("".join(cur))
    return out


_SORRY_RE = re.compile(r"(?<![\w.'])(sorry|admit)(?![\w'])")


def no_sorry(paths: list[pathlib.Path] | None = None) -> list[str]:
    """Lines containing `sorry`/`admit` outside comments and strings, as "file:line: text"; [] when clean.
    Default scope: *.lean under lean/Su2Plaq, lean/Su2PlaqCert, lean/certs, plus the two root files."""
    if paths is None:
        paths = []
        for sub in ("Su2Plaq", "Su2PlaqCert", "certs"):
            paths += sorted((LEAN_DIR / sub).rglob("*.lean"))
        paths += [LEAN_DIR / "Su2Plaq.lean", LEAN_DIR / "Su2PlaqCert.lean"]
    hits: list[str] = []
    for p in paths:
        p = pathlib.Path(p)
        if p.is_dir():
            files = sorted(p.rglob("*.lean"))
        elif p.exists():
            files = [p]
        else:
            continue
        for f in files:
            raw = f.read_text().splitlines()
            for k, line in enumerate(_strip_lean_comments(f.read_text())):
                if _SORRY_RE.search(line):
                    hits.append(f"{f}:{k + 1}: {raw[k].strip() if k < len(raw) else line.strip()}")
    return hits

"""Per-program Lean lemma files (prompts/006 §5, docs/METHODS.md §11.4).

A proposer may ship `NNN-slug.lean` next to `NNN-slug.py`.  It is checked with `lake env lean` (cwd `lean/`, 120 s budget) and
its theorems must depend on the standard axioms only.  Informative: the result never enters validity, ranking or the archive
key.  Allowed imports: `Su2Plaq*`, `Su2PlaqCert*`, `Mathlib*`; `sorry`, `admit` and `native_decide` are refused.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import time

from su2plaq.lean import project as P

_THEOREM_RE = re.compile(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+)?(?:theorem|lemma)\s+([A-Za-z_][\w.'!?]*)", re.M)
_IMPORT_RE = re.compile(r"^\s*import\s+(\S+)", re.M)
_ALLOWED_IMPORT = re.compile(r"^(Su2Plaq|Su2PlaqCert|Mathlib)(\.[\w.]+)?$")
_NATIVE_RE = re.compile(r"\b(native_decide|implemented_by|extern|unsafe|opaque|axiom)\b|Lean\.ofReduceBool")


def lemma_file_for(program_path) -> pathlib.Path | None:
    """`<program>.lean` next to the program, if it exists."""
    f = pathlib.Path(program_path).with_suffix(".lean")
    return f if f.is_file() else None


def _result(status, f, theorems=(), axioms_ok=False, seconds=0.0, message=""):
    return {"status": status, "file": str(f) if f else None, "theorems": list(theorems), "axioms_ok": bool(axioms_ok),
            "seconds": seconds, "message": message}


def check_program_lemmas(program_path, timeout: float = 120.0) -> dict:
    """-> {"status": "none"|"proved"|"failed", "file", "theorems", "axioms_ok", "seconds", "message"}."""
    f = lemma_file_for(program_path)
    if f is None:
        return _result("none", None)
    t0 = time.time()
    text = f.read_text()
    bad_imports = [m for m in _IMPORT_RE.findall(text) if not _ALLOWED_IMPORT.match(m)]
    if bad_imports:
        return _result("failed", f, seconds=time.time() - t0, message=f"disallowed import(s): {bad_imports}")
    if P.no_sorry([f]):
        return _result("failed", f, seconds=time.time() - t0, message="the file contains sorry / admit")
    stripped = "\n".join(P._strip_lean_comments(text))
    if _NATIVE_RE.search(stripped):
        return _result("failed", f, seconds=time.time() - t0,
                       message="native_decide / axiom / unsafe / extern constructs are not accepted in lemma files")
    names = _THEOREM_RE.findall(stripped)
    # elaborate a copy with `#print axioms` appended (inside lean/, so that `import Su2Plaq` resolves)
    tmp = P.LEAN_DIR / f"Lemma_{os.getpid()}_{abs(hash(str(f))) % 10**8}.lean"
    tmp.write_text(text.rstrip() + "\n\n" + "".join(f"#print axioms {n}\n" for n in names))
    try:
        try:
            r = P.lake(["env", "lean", tmp.name], timeout=timeout)
        except subprocess.TimeoutExpired:
            return _result("failed", f, names, seconds=time.time() - t0, message=f"timeout after {timeout} s")
    finally:
        tmp.unlink(missing_ok=True)
    out = r.stdout + "\n" + r.stderr
    if r.returncode != 0 or re.search(r"\berror\b", out):
        return _result("failed", f, names, seconds=time.time() - t0, message=out.strip()[-1500:])
    ax: dict[str, frozenset] = {}
    for m in re.finditer(r"'([^']+)' depends on axioms:\s*\[(.*?)\]", out, re.S):
        ax[m.group(1)] = frozenset(a.strip() for a in m.group(2).replace("\n", " ").split(",") if a.strip())
    for m in re.finditer(r"'([^']+)' does not depend on any axioms", out):
        ax[m.group(1)] = frozenset()
    short = {n.split(".")[-1]: v for n, v in ax.items()}
    ok = all(n in ax or n in short for n in names) and all((ax.get(n) or short.get(n, frozenset())) <= P.STANDARD_AXIOMS for n in names)
    if not ok:
        return _result("failed", f, names, False, time.time() - t0, "a theorem depends on a non-standard axiom or its axioms are unknown")
    if "sorry" in out:
        return _result("failed", f, names, False, time.time() - t0, "declaration uses sorry")
    return _result("proved", f, names, True, time.time() - t0, "")

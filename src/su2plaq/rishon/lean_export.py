"""Lean export for the rishon track (prompts/200 §2.9; METHODS-rishon R8).

* `RISHON_COUNT_THEOREMS`, `RISHON_JW_THEOREMS`: locked theorem names of the kernel-checked files (5.L1, 5.L2).
* `export_hb_certificate` / `write_hb_lean` / `check_hb` (5.L3): the exact bright-pair structure of `H_B^in` as a
  native-decide certificate.  Numbers are integer pairs `[a, b]` meaning `a + b*sqrt(2)`; every value is computed from
  `su2plaq.rishon.operators` (link matrices, bright pairs, kappa) and converted exactly -- nothing is typed in.
  The checker is `lean/Su2PlaqCert/Rishon/HB.lean` (Mathlib-free, computable).
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import subprocess
import time

import numpy as np

from su2plaq.lean import project
from su2plaq.rishon import operators as _ops

RISHON_COUNT_THEOREMS = ("Su2Plaq.card_rishon_physical", "Su2Plaq.card_rishon_closed")
RISHON_JW_THEOREMS = (
    "Su2Plaq.Rishon.car_4", "Su2Plaq.Rishon.car_8", "Su2Plaq.Rishon.bilinear_string_free_8",
    "Su2Plaq.Rishon.sector_card", "Su2Plaq.Rishon.u_ladder", "Su2Plaq.Rishon.det_u_sector",
    "Su2Plaq.Rishon.end_bilinear_local",
)

HB_SCHEMA = "su2plaq-rishon-hb/1"
HB_THEOREM = "Su2PlaqCert.Rishon.rishon_hb_structure"
_N_CODES = 1296
_LINK_OP_NAMES = ("U00", "U01", "U10", "U11", "Ud00", "Ud01", "Ud10", "Ud11")
_SQRT2 = math.sqrt(2.0)


def _zs(x: float, tol: float = 1e-9) -> list[int]:
    """Exact integer pair [a, b] with x = a + b*sqrt(2) (|a|, |b| <= 64); ValueError if x is not such a number."""
    for b in range(-64, 65):
        a = round(x - b * _SQRT2)
        if abs(a + b * _SQRT2 - x) < tol:
            return [int(a), int(b)]
    raise ValueError(f"{x!r} is not an integer combination a + b*sqrt(2)")


def _int(x: complex, tol: float = 1e-12) -> int:
    if abs(x.imag) > tol or abs(x.real - round(x.real)) > tol:
        raise ValueError(f"link-matrix entry {x!r} is not an integer")
    return int(round(x.real))


def _sparse_vec(x: np.ndarray) -> list[list[int]]:
    """Sparse [index, a, b] list of 4*x (exact Z[sqrt2] pairs)."""
    return [[int(i)] + _zs(4.0 * float(x[i])) for i in np.flatnonzero(x)]


def export_hb_certificate(out_path) -> pathlib.Path:
    """Write the JSON certificate (schema `su2plaq-rishon-hb/1`) and return its path.

    Fields: `n_codes` (1296), `link_ops` (8 sparse 6x6 integer matrices `U00..Ud11` as [row, col, value]),
    `pairs` (81 dicts `{"kappa": [a, b], "u": [[idx, a, b], ...], "v": [...]}` with the vectors 4u_p, 4v_p).
    """
    ops = _ops._sector_ops()
    link_ops = []
    for kind in ("U", "Ud"):
        for i in range(2):
            for j in range(2):
                M = ops[kind][i][j]
                link_ops.append({"name": f"{kind}{i}{j}",
                                 "entries": [[int(r), int(c), _int(M[r, c])] for r, c in np.argwhere(np.abs(M) > 1e-12)]})
    pairs = [{"kappa": _zs(k), "u": _sparse_vec(u), "v": _sparse_vec(v)} for u, v, k in _ops.bright_pairs()]
    cert = {
        "schema": HB_SCHEMA,
        "source": "su2plaq.rishon.operators (_sector_ops, bright_pairs)",
        "n_codes": _N_CODES,
        "code_index": "sum_l s_l * 6^l, s_l = position of the link state in the sorted two-rishon sector",
        "link_ops": link_ops,
        "pairs": pairs,
    }
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cert))
    return out


# --- exact pure-Python mirror of the Lean checker (used by the unit tests; not part of the trust chain) ------------------
def _zmul(x, y):
    return (x[0] * y[0] + 2 * x[1] * y[1], x[0] * y[1] + x[1] * y[0])


def check_hb_python(cert: dict) -> dict:
    """Same five claims as `checkHB` in HB.lean, in exact integer arithmetic.  Returns {part: bool}."""
    N = cert["n_codes"]
    cols = [[[] for _ in range(6)] for _ in range(8)]
    for o, op in enumerate(cert["link_ops"]):
        for r, c, v in op["entries"]:
            cols[o][c].append((r, v))
    lhs: dict[tuple[int, int], list[int]] = {}
    for code in range(N):
        s = [(code // 6 ** l) % 6 for l in range(4)]
        for a in range(2):
            for b in range(2):
                for c in range(2):
                    for d in range(2):
                        for (r0, v0) in cols[2 * a + b][s[0]]:
                            for (r1, v1) in cols[2 * b + c][s[1]]:
                                for (r2, v2) in cols[4 + 2 * d + c][s[2]]:
                                    for (r3, v3) in cols[4 + 2 * a + d][s[3]]:
                                        row = r0 + 6 * r1 + 36 * r2 + 216 * r3
                                        v = 16 * v0 * v1 * v2 * v3
                                        for key in ((row, code), (code, row)):
                                            lhs.setdefault(key, [0, 0])[0] += v
    lhs = {k: tuple(v) for k, v in lhs.items() if v != [0, 0]}
    rhs: dict[tuple[int, int], list[int]] = {}
    vecs, seen = [], set()
    for p in cert["pairs"]:
        k = tuple(p["kappa"])
        for i, xa, xb in p["u"]:
            for j, ya, yb in p["v"]:
                z = _zmul(k, _zmul((xa, xb), (ya, yb)))
                for key in ((i, j), (j, i)):
                    e = rhs.setdefault(key, [0, 0])
                    e[0] += z[0]
                    e[1] += z[1]
        for side in ("u", "v"):
            vecs.append({i: (a, b) for i, a, b in p[side]})
            seen.update(i for i, _, _ in p[side])
    rhs = {k: tuple(v) for k, v in rhs.items() if v != [0, 0]}
    ortho = True
    for i, x in enumerate(vecs):
        for j, y in enumerate(vecs):
            s = [0, 0]
            for idx, z in x.items():
                if idx in y:
                    m = _zmul(z, y[idx])
                    s[0] += m[0]
                    s[1] += m[1]
            if tuple(s) != ((16, 0) if i == j else (0, 0)):
                ortho = False
    kappas = [tuple(p["kappa"]) for p in cert["pairs"]]
    return {
        "identity": lhs == rhs,
        "ortho": ortho,
        "kappa": (len(kappas) == 81 and kappas.count((1, 0)) == 32 and kappas.count((2, 0)) == 48
                  and kappas.count((0, 4)) == 1),
        "dark": N - len(seen) == 990,
    }


# --- Lean text generation --------------------------------------------------------------------------------------------
def _lit(n: int) -> str:
    return f"({n})" if n < 0 else str(n)


def _zs_lit(a: int, b: int) -> str:
    return f"⟨{_lit(a)}, {_lit(b)}⟩"


def _svec_lit(v) -> str:
    return "[" + ", ".join(f"({i}, {_zs_lit(a, b)})" for i, a, b in v) + "]"


def _data_def(cert: dict) -> str:
    if not str(cert.get("schema", "")).startswith("su2plaq-rishon-hb"):
        raise ValueError("not a rishon H_B certificate")
    ops = ",\n    ".join("[" + ", ".join(f"({r}, {c}, {_lit(v)})" for r, c, v in op["entries"]) + "]"
                         for op in cert["link_ops"])
    pairs = ",\n    ".join(f"⟨{_zs_lit(*p['kappa'])}, {_svec_lit(p['u'])}, {_svec_lit(p['v'])}⟩" for p in cert["pairs"])
    return ("def rishonHBCert : HBCert where\n"
            f"  nCodes := {int(cert['n_codes'])}\n"
            f"  linkOps := [\n    {ops}]\n"
            f"  pairs := [\n    {pairs}]\n")


_HEADER = ("-- GENERATED by su2plaq.rishon.lean_export.write_hb_lean (prompts/200 step 5.L3); do not edit by hand.\n"
           "-- Certificate: exact bright-pair structure of H_B^in (integer pairs a + b*sqrt2).\n")
_THEOREM = ("\ntheorem rishon_hb_structure : checkHB rishonHBCert = true := by native_decide\n"
            "\n#print axioms rishon_hb_structure\n")


def write_hb_lean(cert_path, out_path, data_path=None) -> pathlib.Path:
    """Generate the theorem file `out_path` from the JSON certificate (`import Su2PlaqCert.Rishon.HB`, the data,
    `theorem rishon_hb_structure : checkHB rishonHBCert = true := by native_decide`, `#print axioms`).

    With `data_path=None` the data are inlined, so the file is self-contained (used for tampered certificates);
    otherwise the data go to `data_path` (module `Su2PlaqCert.Rishon.HBData`) and the theorem file imports it."""
    cert = json.loads(pathlib.Path(cert_path).read_text())
    data = _data_def(cert)
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if data_path is None:
        text = (_HEADER + "import Su2PlaqCert.Rishon.HB\n\nnamespace Su2PlaqCert.Rishon\n\n" + data + _THEOREM
                + "\nend Su2PlaqCert.Rishon\n")
    else:
        dp = pathlib.Path(data_path)
        dp.parent.mkdir(parents=True, exist_ok=True)
        dp.write_text(_HEADER + "import Su2PlaqCert.Rishon.HB\n\nnamespace Su2PlaqCert.Rishon\n\n" + data
                      + "\nend Su2PlaqCert.Rishon\n")
        text = (_HEADER + "import Su2PlaqCert.Rishon.HB\nimport Su2PlaqCert.Rishon.HBData\n\n"
                "namespace Su2PlaqCert.Rishon\n" + _THEOREM + "\nend Su2PlaqCert.Rishon\n")
    out.write_text(text)
    return out


def write_repo_hb_files(tmp_json=None) -> tuple[pathlib.Path, pathlib.Path]:
    """Regenerate `lean/Su2PlaqCert/Rishon/HBData.lean` and `lean/certs/rishon-hb-structure.lean` from the code."""
    root = project.LEAN_DIR
    cert = export_hb_certificate(tmp_json or (root.parent / "scratch" / "rishon-hb-cert.json"))
    out = write_hb_lean(cert, root / "certs" / "rishon-hb-structure.lean", data_path=root / "Su2PlaqCert" / "Rishon" / "HBData.lean")
    return root / "Su2PlaqCert" / "Rishon" / "HBData.lean", out


_DEPENDS_RE = re.compile(r"'([^']+)' depends on axioms:\s*\[(.*?)\]", re.S)
_NONE_RE = re.compile(r"'([^']+)' does not depend on any axioms")


def check_hb(lean_file, timeout=900) -> dict:
    """Run `lake env lean <lean_file>` (after building the checker module `Su2PlaqCert.Rishon.HB`).

    Returns {"status": "certified" | "rejected" | "error", "axioms": set[str], "seconds": float, "detail": str}.
    certified = Lean exit 0 with no error and a `#print axioms` line; rejected = `native_decide` evaluated the
    statement to false; error = anything else (build failure, timeout, elaboration error)."""
    t0 = time.time()
    path = pathlib.Path(lean_file).resolve()
    mods = ["Su2PlaqCert.Rishon.HB"] + [m for m in re.findall(r"^import\s+(Su2PlaqCert\.[\w.]+)", path.read_text(), re.M)
                                      if m != "Su2PlaqCert.Rishon.HB"]
    for mod in dict.fromkeys(mods):           # checker module + any other project module the file imports (e.g. HBData)
        b = project.build("+" + mod, timeout=max(1.0, timeout - (time.time() - t0)))
        if not b["ok"]:
            return {"status": "error", "axioms": set(), "seconds": time.time() - t0,
                    "detail": f"build of {mod} failed: " + (b["stdout"] + b["stderr"])[-1500:]}
    try:
        r = project.lake(["env", "lean", str(path)], timeout=max(1.0, timeout - (time.time() - t0)))
    except subprocess.TimeoutExpired:
        return {"status": "error", "axioms": set(), "seconds": time.time() - t0, "detail": f"TIMEOUT after {timeout}s"}
    text = r.stdout + "\n" + r.stderr
    axioms: set[str] = set()
    found = False
    for m in _DEPENDS_RE.finditer(text):
        found = True
        axioms |= {a.strip() for a in m.group(2).replace("\n", " ").split(",") if a.strip()}
    if _NONE_RE.search(text):
        found = True
    has_error = r.returncode != 0 or ": error" in text
    if has_error:
        rejected = "evaluated that the proposition" in text and "is false" in text
        return {"status": "rejected" if rejected else "error", "axioms": axioms, "seconds": time.time() - t0,
                "detail": text[-1500:]}
    if not found:
        return {"status": "error", "axioms": axioms, "seconds": time.time() - t0, "detail": "no #print axioms output\n" + text[-1500:]}
    return {"status": "certified", "axioms": axioms, "seconds": time.time() - t0, "detail": text[-500:]}


# --- M5x (prompts/202 section 3): exact statements of the rishon encoding.  Stubs until steps W2/W3 build them. ----------
RISHON_M5X_THEOREMS = (
    "Su2Plaq.Rishon.hb_link_ops_from_jw", "Su2Plaq.Rishon.hb_link_ops_count", "Su2Plaq.Rishon.det_u_identity",
    "Su2Plaq.Rishon.u_commute", "Su2Plaq.Rishon.corner_kernel_dims", "Su2Plaq.Rishon.card_inner_codes",
    "Su2Plaq.Rishon.ue_gadget_sector", "Su2Plaq.Rishon.ue_gates_structure", "Su2Plaq.Rishon.ue_outer_gates_structure",
    "Su2Plaq.Rishon.ue_exact_all_codes", "Su2Plaq.Rishon.corner_count_agree")
_RISHON_LEAN_DIR = project.LEAN_DIR / "Su2Plaq" / "Rishon"
HBLINK_LEAN: pathlib.Path = _RISHON_LEAN_DIR / "HBLink.lean"
CORNER_KERNEL_LEAN: pathlib.Path = _RISHON_LEAN_DIR / "CornerKernel.lean"
UE_SEMANTICS_LEAN: pathlib.Path = _RISHON_LEAN_DIR / "UESemantics.lean"
BRIDGE_LEAN: pathlib.Path = _RISHON_LEAN_DIR / "Bridge.lean"
UE_GATE_NAMES = ("x", "cx", "p")


def ue_gate_ints(qc) -> list[tuple]:
    """Program-order gate list of a build_UE circuit: ("x", q) | ("cx", c, t) | ("p", q, a), a = angle / (alpha/4) (step W3)."""
    raise NotImplementedError("prompts/202 step W3")


def ue_gate_literal(qc) -> str:
    """Lean literal "[.cx 0 1, .p 1 (-3), ...]" of ue_gate_ints(qc) (step W3)."""
    raise NotImplementedError("prompts/202 step W3")


def write_lean_ue_gates(path=None) -> pathlib.Path:
    """Regenerate the generated block of UESemantics.lean (step W3)."""
    raise NotImplementedError("prompts/202 step W3")


def lean_eval(body: str, imports: tuple[str, ...] = ("Su2Plaq.Rishon.UESemantics",), timeout: float = 300.0) -> str:
    """Run `lake env lean` on imports + body and return stdout (step W2)."""
    raise NotImplementedError("prompts/202 step W2")


def lean_ue_gate_images(gate: tuple, n_qubits: int, alpha: float) -> np.ndarray:
    """Complex (2^n, 2^n) matrix of one gate from the Lean semantics evaluated at z = exp(i alpha/4) (step W3)."""
    raise NotImplementedError("prompts/202 step W3")


def lean_corner_kernel_dims() -> list[int]:
    """kerDim for the 81 corner end configurations, evaluated in Lean (step W2)."""
    raise NotImplementedError("prompts/202 step W2")


if __name__ == "__main__":      # python -m su2plaq.rishon.lean_export : regenerate the repo's generated Lean files
    for p in write_repo_hb_files():
        print(p)

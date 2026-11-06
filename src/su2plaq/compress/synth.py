"""T-count of a rotation (pygridsynth, disk-cached) and the MAP-Elites key / cell (prompts/002 §2.10)."""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

from su2plaq.metrics.cliffordt import pygridsynth_word

ROOT = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = ROOT / "compress" / "cache" / "gridsynth"
INVALID_KEY = (float("inf"), float("inf"), float("inf"), float("inf"))


_ALPHABET = set("HSTXW")


def _checksum(version: str, theta: float, eps: float, word: str) -> str:
    return hashlib.sha256(f"{version}|{float(theta)!r}|{float(eps)!r}|{word}".encode()).hexdigest()


def _read_valid(f: pathlib.Path, version: str, theta: float, eps: float):
    """The cached word, or None if the entry is missing, malformed, from another (version, theta, eps), fails its checksum, has a
    letter outside H S T X W, or does not approximate rz(theta) within eps (recomputed from the word, not trusted)."""
    from su2plaq.metrics.cliffordt import word_error

    try:
        d = json.loads(f.read_text())
        w = d["word"]
        if (d["version"] != version or d["theta"] != repr(float(theta)) or d["eps"] != repr(float(eps))
                or d["sha256"] != _checksum(version, theta, eps, w)):
            return None
        if not isinstance(w, str) or not set(w) <= _ALPHABET or word_error(w, float(theta)) > float(eps):
            return None
        return w
    except (OSError, ValueError, KeyError, TypeError):
        return None


def gridsynth_word(theta: float, eps: float) -> str:
    """pygridsynth word for rz(theta) within eps, cached on disk under compress/cache/gridsynth/.  An entry is JSON
    {version, theta, eps, word, sha256}; it is used only if the checksum matches AND the word really approximates rz(theta)
    within eps (alphabet and error are re-checked on every read); anything else is recomputed and overwritten."""
    from importlib.metadata import version as _version

    ver = _version("pygridsynth")
    f = CACHE_DIR / (hashlib.sha256(f"{ver}|{float(theta)!r}|{float(eps)!r}".encode()).hexdigest() + ".json")
    w = _read_valid(f, ver, theta, eps) if f.exists() else None
    if w is not None:
        return w
    w = pygridsynth_word(theta, eps)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version": ver, "theta": repr(float(theta)), "eps": repr(float(eps)), "word": w,
                                   "sha256": _checksum(ver, theta, eps, w)}))
        tmp.replace(f)
    except OSError:
        pass          # a read-only cache directory only costs time
    return w


def gridsynth_T(theta: float, eps: float) -> int:
    """T-count of the pygridsynth word (= metrics.cliffordt.pygridsynth_tcount), disk-cached."""
    return gridsynth_word(theta, eps).count("T")


def key(m: dict) -> tuple:
    """Lexicographic cost key (CX, T_eps, depth_CT, qubits)."""
    return (m["cx"], m["t_eps"], m["depth_ct"], m["qubits"])


def cell(m: dict, k: int = 8) -> tuple:
    """MAP-Elites cell (floor(k log2(CX+1)), floor(k log2(T_eps+1)))."""
    return (int(math.floor(k * math.log2(m["cx"] + 1))), int(math.floor(k * math.log2(m["t_eps"] + 1))))

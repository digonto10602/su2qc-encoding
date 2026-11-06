"""MAP-Elites archive of valid candidate programs (prompts/002 §2.10, design B §3).

Cost key (lexicographic): (CX, T_eps, depth_CT, qubits).  Cell: (floor(k log2(CX+1)), floor(k log2(T_eps+1))), k = 8.  The elite of a
cell is its entry with the smallest key.  Only VALID entries (verdict ok, certified, skeleton equal at the alternate angles) are
ever inserted: invalid, unverified and infinite-key entries are refused.  Storage under <root>/compress/archive/<encoding>/:
index.json plus entries/<id>.json (atomic writes).  Every entry carries its provenance (program / evaluator-code / spec hashes,
commit and dirty flag, versions, seeds, machine, wall time).
"""
from __future__ import annotations

import datetime
import json
import logging
import math
import numbers
import pathlib
import re
from dataclasses import asdict, dataclass, field

from su2plaq.compress import provenance as P
from su2plaq.compress.synth import INVALID_KEY, cell as _cell, key as _key

ROOT = P.ROOT


@dataclass
class Entry:
    id: str
    program_path: str
    program_sha256: str
    parent: str | None
    family: str
    round: int
    valid: bool
    reason: str
    key: tuple
    cell: tuple | None
    metrics_raw: dict
    metrics_polished: dict | None
    verdict_nominal: dict
    verdicts_alt: list
    skeleton_equal: bool
    discoveries: list
    summary: str
    evaluator_sha256: str
    spec_sha256: str
    git_commit: str
    versions: dict
    seeds: dict
    machine: str
    wall_s: float
    written_utc: str
    git_dirty: bool = False
    synthesis: dict | None = None      # pygridsynth details of the key's T_eps (eps, measured, error bound)
    lean: dict | None = None           # asdict(LeanCert) once the Lean certificate was tried (prompts/006); None = not run
    mode: str = "full"

    def to_dict(self) -> dict:
        from su2plaq.results.store import _jsonable

        d = asdict(self)
        d["key"] = list(self.key)
        d["cell"] = None if self.cell is None else list(self.cell)
        return _jsonable(d)               # numpy scalars -> plain numbers

    @staticmethod
    def from_dict(d: dict) -> "Entry":
        d = dict(d)
        d["key"] = tuple(d["key"])
        d["cell"] = None if d.get("cell") is None else tuple(d["cell"])
        fields = set(Entry.__dataclass_fields__)
        return Entry(**{k: v for k, v in d.items() if k in fields})


_ID_RE = re.compile(r"^r\d{2,3}-[A-Za-z0-9_+]+(?:[-.][A-Za-z0-9_+]+)*$")
_METRIC_KEYS = ("cx", "t_eps", "depth_ct", "qubits")
log = logging.getLogger(__name__)


def _finite_key(k) -> bool:
    return len(k) == 4 and all(isinstance(x, numbers.Real) and not isinstance(x, bool) and math.isfinite(float(x)) for x in k)


def entry_problem(e: "Entry", n_alt: int = 0, k: int = 8) -> str | None:
    """Why `e` may not enter the archive, or None.  Rules (prompts/002 §2.10): a sane id (no path characters); a FULL-mode
    result; valid with reason ok; verdict ok and certified at the nominal angles and at every alternate pair that is present
    (exactly `n_alt` of them when n_alt > 0); skeleton equal; key and cell equal to the ones recomputed from the metrics, finite."""
    from su2plaq.compress.synth import cell as _c, key as _k

    if not isinstance(e.id, str) or len(e.id) > 100 or not _ID_RE.match(e.id):
        return "bad id"
    if e.mode != "full":
        return f"mode {e.mode!r} is not 'full'"
    if not e.valid or e.reason != "ok":
        return "not valid"
    if not e.skeleton_equal:
        return "skeleton differs between the angle pairs"
    vn = e.verdict_nominal
    if not isinstance(vn, dict) or not vn or vn.get("ok") is not True or vn.get("certified") is False:
        return "nominal verdict empty, not ok, or not certified"
    if n_alt and len(e.verdicts_alt) != n_alt:
        return f"expected {n_alt} alternate-angle verdicts, got {len(e.verdicts_alt)}"
    for va in e.verdicts_alt:
        if not isinstance(va, dict) or va.get("ok") is not True or va.get("certified") is False:
            return "an alternate-angle verdict is empty, not ok, or not certified"
    m = e.metrics_raw
    if not isinstance(m, dict) or any(x not in m for x in _METRIC_KEYS):
        return "metrics incomplete"
    try:
        key, cell = _k(m), _c(m, k)
    except (TypeError, ValueError, OverflowError):
        return "metrics not numeric or not finite"
    if not _finite_key(key) or not _finite_key(e.key) or e.cell is None:
        return "key not finite"
    if tuple(float(x) for x in e.key) != tuple(float(x) for x in key) or tuple(int(x) for x in e.cell) != tuple(cell):
        return "key / cell do not match the metrics"
    return None


class Archive:
    def __init__(self, encoding: str, root=None, entries=None, n_alt: int = 0):
        self.encoding = encoding
        self.root = pathlib.Path(root) if root is not None else ROOT
        self.n_alt = n_alt                      # required number of alternate-angle verdicts (0: whatever is present is checked)
        self._entries: dict[str, Entry] = dict(entries or {})
        self.rejected: list[tuple[str, str]] = []   # (file or id, reason) of entries refused on load / insert

    # ------------------------------------------------------------------ persistence
    @property
    def directory(self) -> pathlib.Path:
        return self.root / "compress" / "archive" / self.encoding

    @classmethod
    def load(cls, encoding, root=None, n_alt: int = 0) -> "Archive":
        """Load the archive; every stored entry is re-validated with the insert rules and refused (logged, listed in
        `.rejected`) if it fails or if its file name does not match its id."""
        arch = cls(encoding, root, n_alt=n_alt)
        d = arch.directory / "entries"
        if d.is_dir():
            for f in sorted(d.glob("*.json")):
                try:
                    e = Entry.from_dict(json.loads(f.read_text()))
                    why = entry_problem(e, n_alt) if f.stem == e.id else "file name does not match the entry id"
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    why = f"unreadable entry ({type(exc).__name__}: {exc})"
                if why is not None:
                    arch.rejected.append((f.name, why))
                    log.warning("archive %s: refusing %s: %s", encoding, f.name, why)
                    continue
                arch._entries[e.id] = e
        return arch

    def save(self):
        d = self.directory
        edir = (d / "entries")
        edir.mkdir(parents=True, exist_ok=True)
        for e in self._entries.values():
            why = entry_problem(e, self.n_alt)
            if why is not None:
                raise ValueError(f"entry {e.id!r} no longer satisfies the archive rules ({why})")
            target = (edir / f"{e.id}.json")
            if target.resolve().parent != edir.resolve():
                raise ValueError(f"entry id {e.id!r} would be written outside the archive")
            self._write(target, e.to_dict())
        best = self.best()
        index = {"encoding": self.encoding, "n_entries": len(self._entries),
                 "families": {f: {"best": self.family_best(f).id} for f in sorted({e.family for e in self._entries.values()})},
                 "elites": {f"{c[0]},{c[1]}": e.id for c, e in sorted(self.elites().items())},
                 "best": best.id if best else None, "written_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        self._write(d / "index.json", index)

    @staticmethod
    def _write(path: pathlib.Path, obj):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=1))
        tmp.replace(path)

    # ------------------------------------------------------------------ content
    def insert(self, entry: Entry) -> bool:
        """Add an entry that satisfies `entry_problem`; returns False (archive untouched, the reason is appended to `.rejected`)
        otherwise: not a full-mode result, not ok AND certified at the nominal and alternate angles, skeleton differs, key / cell
        not equal to the ones recomputed from the metrics, non-finite key, unsafe id.  A duplicate id is an error."""
        why = entry_problem(entry, self.n_alt)
        if why is not None:
            self.rejected.append((str(entry.id), why))
            return False
        if entry.id in self._entries:
            raise ValueError(f"entry id {entry.id!r} already in the archive")
        self._entries[entry.id] = entry
        return True

    def entries(self) -> list[Entry]:
        return list(self._entries.values())

    def elites(self) -> dict[tuple, Entry]:
        """cell -> entry with the smallest key in that cell (ties: the earlier id)."""
        out: dict[tuple, Entry] = {}
        for e in sorted(self._entries.values(), key=lambda x: (tuple(x.key), x.id)):
            out.setdefault(tuple(e.cell), e)
        return out

    def best(self) -> Entry | None:
        return min(self._entries.values(), key=lambda x: (tuple(x.key), x.id), default=None)

    def family_best(self, f) -> Entry | None:
        return min((e for e in self._entries.values() if e.family == f), key=lambda x: (tuple(x.key), x.id), default=None)


def _nnn(program_path: str) -> str:
    m = re.match(r"(\d+)", pathlib.Path(program_path).stem)
    return f"{int(m.group(1)):03d}" if m else "000"


def entry_from_result(result, *, program_path: str, family: str, round: int, parent: str | None, k: int = 8) -> Entry:
    """Archive entry from a `ProgramResult` with full provenance.  The id is r<round>-<family>-<NNN> (NNN = the leading number
    of the program file name)."""
    from datetime import datetime, timezone

    from su2plaq.metrics.provenance import provenance
    from su2plaq.results.store import _jsonable, verdict_to_dict

    prov = provenance(result.seeds or None)
    met = result.metrics
    has_cost = bool(result.valid and met)
    key = _key(met) if has_cost else INVALID_KEY
    cell = _cell(met, k) if has_cost else None
    return Entry(
        id=f"r{round:02d}-{family}-{_nnn(program_path)}", program_path=str(program_path), program_sha256=result.program_sha256,
        parent=parent, family=family, round=round, valid=bool(result.valid), reason=result.reason, key=tuple(key), cell=cell,
        metrics_raw=_jsonable(met or {}), metrics_polished=None,
        verdict_nominal=verdict_to_dict(result.verdict) if result.verdict is not None else {},
        verdicts_alt=[verdict_to_dict(v) for v in result.verdicts_alt], skeleton_equal=bool(result.skeleton_equal),
        discoveries=list(result.discoveries), summary=result.summary, evaluator_sha256=P.code_hash(),
        spec_sha256=result.spec_sha256, git_commit=prov["git_commit"], versions=prov["versions"], seeds=dict(result.seeds),
        machine=P.machine(), wall_s=float(result.wall_s), written_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_dirty=bool(prov["git_dirty"]), synthesis=({"measured": bool(met.get("measured")), "synth_error_bound": met.get("synth_error_bound")}
                                                      if met else None),
        mode=result.mode)

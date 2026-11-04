"""MAP-Elites archive (prompts/002 §2.10). Stubs (step 0.1)."""
from __future__ import annotations

from dataclasses import dataclass

from su2plaq._stub import todo


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
    cell: tuple
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


class Archive:
    @classmethod
    def load(cls, encoding, root=None) -> "Archive":
        todo("Archive.load")

    def insert(self, entry) -> bool:
        todo("Archive.insert")

    def elites(self) -> dict:
        todo("Archive.elites")

    def best(self):
        todo("Archive.best")

    def family_best(self, f):
        todo("Archive.family_best")

    def save(self):
        todo("Archive.save")

    def entries(self) -> list:
        todo("Archive.entries")


def entry_from_result(result, *, program_path: str, family: str, round: int, parent: str | None) -> Entry:
    todo("entry_from_result")

"""Verify locked acceptance files against tests/acceptance/LOCK.json (sha256)."""
import hashlib
import json
import pathlib
import sys


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check(root: pathlib.Path) -> list[str]:
    lock_file = root / "tests" / "acceptance" / "LOCK.json"
    if not lock_file.exists():
        return ["LOCK.json missing"]
    lock = json.loads(lock_file.read_text())
    problems = []
    for rel, digest in lock["files"].items():
        f = root / rel
        if not f.exists():
            problems.append(f"missing: {rel}")
        elif sha(f) != digest:
            problems.append(f"changed: {rel}")
    for ms in lock["milestones"]:
        for f in sorted((root / "tests" / "acceptance" / ms).rglob("*.py")):
            rel = f.relative_to(root).as_posix()
            if rel not in lock["files"]:
                problems.append(f"unlocked file in locked milestone: {rel}")
    return problems


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[1]
    p = check(root)
    print("LOCK OK" if not p else "LOCK BROKEN:\n  " + "\n  ".join(p))
    sys.exit(1 if p else 0)

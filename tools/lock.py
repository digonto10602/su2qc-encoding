"""Lock NEW milestones' acceptance tests: python3 tools/lock.py m0 m1 m2
Refuses to re-lock a milestone that is already locked (re-locking needs Digonto's approval
and is done by hand). Also hashes the shared files (SHARED) only on first creation of LOCK.json."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.check_lock import sha  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = ROOT / "tests" / "acceptance" / "LOCK.json"
SHARED = ["tests/acceptance/conftest.py", "tests/acceptance/_api.py",
          "tools/check_lock.py", "tools/lock.py"]


def main(milestones):
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {"milestones": [], "files": {}}
    if not LOCK.exists():
        for rel in SHARED:
            lock["files"][rel] = sha(ROOT / rel)
    for ms in milestones:
        if ms in lock["milestones"]:
            sys.exit(f"{ms} is already locked; ask Digonto before changing locked tests")
        files = sorted((ROOT / "tests" / "acceptance" / ms).rglob("*.py"))
        if not files:
            sys.exit(f"no test files in tests/acceptance/{ms}")
        for f in files:
            lock["files"][f.relative_to(ROOT).as_posix()] = sha(f)
        lock["milestones"].append(ms)
        print(f"locked {ms}: {len(files)} files")
    LOCK.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])

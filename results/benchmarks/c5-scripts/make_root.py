"""usage: make_root.py <src_tree> <dst> <encoding> <round>   scratch copy of compress/ + results/compress/<enc> with round <round> entries removed
(as results/benchmarks/spinnet-m4-scripts/make_root.sh of report 301; evaluation cache emptied, gridsynth cache kept)."""
import sys, json, shutil, pathlib, re
src, dst, enc, rnd = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
if dst.exists(): shutil.rmtree(dst)
(dst / "compress").mkdir(parents=True); (dst / "results" / "compress").mkdir(parents=True)
for d in ("archive", "attempts", "briefs", "discoveries", "ideation", "lean", "programs", "specs"):
    if (src / "compress" / d).exists(): shutil.copytree(src / "compress" / d, dst / "compress" / d)
(dst / "compress" / "cache").mkdir()
if (src / "compress/cache/gridsynth").exists(): shutil.copytree(src / "compress/cache/gridsynth", dst / "compress/cache/gridsynth")
shutil.copytree(src / "results/compress" / enc, dst / "results/compress" / enc)
for f in (dst / "compress/archive" / enc / "entries").glob(f"r{rnd:02d}-*.json"): f.unlink()
f = dst / "compress/attempts" / f"{enc}.jsonl"
keep = [l for l in f.read_text().splitlines() if l.strip() and json.loads(l).get("round") != rnd]
f.write_text("\n".join(keep) + "\n"); print("attempts kept", len(keep))

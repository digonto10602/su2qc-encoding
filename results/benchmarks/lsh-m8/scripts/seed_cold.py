"""Run `su2plaq.lsh.loop seed --root R` with the pygridsynth disk cache redirected to an empty scratch directory (cold cache).
usage: seed_cold.py <root> <cache_dir> [--no-lean]   (module attribute assignment in this process only; the repository is untouched)"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
import su2plaq.compress.synth as S
S.CACHE_DIR = pathlib.Path(sys.argv[2]); S.CACHE_DIR.mkdir(parents=True, exist_ok=True)
from su2plaq.lsh.loop import main
raise SystemExit(main(["seed", "--root", sys.argv[1]] + sys.argv[3:]))

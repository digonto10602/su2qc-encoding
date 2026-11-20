"""`python -m su2plaq.lsh.loop <args>` with the pygridsynth disk cache redirected to an empty scratch dir (cold cache).
usage: loop_cold.py <cache_dir> <loop args...>   (module attribute assignment in this process only; the repository is untouched)"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
import su2plaq.compress.synth as S
S.CACHE_DIR = pathlib.Path(sys.argv[1]); S.CACHE_DIR.mkdir(parents=True, exist_ok=True)
from su2plaq.lsh.loop import main
raise SystemExit(main(sys.argv[2:]))

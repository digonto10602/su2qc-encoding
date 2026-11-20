import sys, os, cProfile, pstats, time, io
sys.path.insert(0, os.environ["BENCH_ROOT"] + "/src")
from su2plaq.crosscheck import report as R
pr = cProfile.Profile(); t = time.perf_counter(); pr.enable(); R.spectra_results(out=False, headline=False); pr.disable()
print("wall under cProfile", time.perf_counter() - t)
s = io.StringIO(); pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(28); print(s.getvalue()[:5500])

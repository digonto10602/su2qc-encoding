"""time -v substitute: tv.py <cmd...> ; prints wall and peak RSS (children) to stderr."""
import sys, subprocess, resource, time
t=time.time(); r=subprocess.call(sys.argv[1:]); u=resource.getrusage(resource.RUSAGE_CHILDREN)
print(f"TV wall_s={time.time()-t:.1f} peak_rss_gb={u.ru_maxrss/1048576:.3f} rc={r}", file=sys.stderr); sys.exit(r)

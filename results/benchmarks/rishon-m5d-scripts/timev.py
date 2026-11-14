"""Minimal stand-in for GNU /usr/bin/time (not installed on omnicommander): timev.py [-v] [-f FMT] -o FILE cmd...
Writes wall seconds, max RSS (largest descendant, KB) and the exit code to FILE; FMT tokens %e %M %x as in GNU time."""
import sys, subprocess, time, resource
a = sys.argv[1:]; fmt = None; out = None
while a and a[0].startswith("-"):
    if a[0] == "-v": a = a[1:]
    elif a[0] == "-f": fmt = a[1]; a = a[2:]
    elif a[0] == "-o": out = a[1]; a = a[2:]
    else: raise SystemExit("bad option " + a[0])
t0 = time.time(); p = subprocess.run(a); wall = time.time() - t0
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
if fmt:
    s = fmt.replace("%e", f"{wall:.2f}").replace("%M", str(rss)).replace("%x", str(p.returncode))
else:
    s = f"Elapsed (wall clock) time (seconds): {wall:.2f}\nMaximum resident set size (kbytes): {rss}\nExit status: {p.returncode}"
open(out, "w").write(s + "\n")
sys.exit(p.returncode)

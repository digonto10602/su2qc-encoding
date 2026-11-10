"""Tester 221: run a command, print wall seconds and peak RSS (children) to stderr as one line. usage: tester-221-timed.py cmd..."""
import subprocess, sys, time, resource
t = time.time(); rc = subprocess.call(sys.argv[1:])
print("TIMED wall_s=%.1f maxrss_MB=%.0f rc=%d" % (time.time() - t, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, rc), file=sys.stderr)
sys.exit(rc)

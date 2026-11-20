"""Run a command, print wall time and the peak of the summed RSS (and PSS if available) over the process tree, sampled every 0.2 s."""
import subprocess, sys, time, psutil, json
t0=time.time(); p=subprocess.Popen(sys.argv[1:]); ps=psutil.Process(p.pid); peak=0; peak_pss=0
while p.poll() is None:
    try:
        tree=[ps]+ps.children(recursive=True); r=0; pss=0
        for c in tree:
            try:
                r+=c.memory_info().rss
                try: pss+=c.memory_full_info().pss
                except Exception: pass
            except psutil.Error: pass
        peak=max(peak,r); peak_pss=max(peak_pss,pss)
    except psutil.Error: pass
    time.sleep(0.2)
print(json.dumps({"rc":p.returncode,"wall_s":round(time.time()-t0,1),"peak_sum_rss_GiB":round(peak/2**30,3),"peak_sum_pss_GiB":round(peak_pss/2**30,3)}))
sys.exit(p.returncode)

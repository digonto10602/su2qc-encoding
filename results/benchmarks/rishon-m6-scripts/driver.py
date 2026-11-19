"""usage: driver.py <jobs-json> <out.jsonl>  -- runs jobs (fresh process each, pinned with taskset), records wall (perf_counter),
child CPU user/sys + maxrss (wait4), loadavg before/after, per-CPU foreign busy fraction on the pinned CPU + SMT sibling."""
import sys, json, os, time, subprocess, resource, pathlib
def cpu_stat():
    r = {}
    for l in open("/proc/stat"):
        if l.startswith("cpu") and l[3].isdigit():
            f = l.split(); v = list(map(int, f[1:])); r[int(f[0][3:])] = (sum(v), v[3] + v[4])
    return r
def load(): return os.getloadavg()
jobs = json.load(open(sys.argv[1])); outp = pathlib.Path(sys.argv[2])
for j in jobs:
    cpus = j["cpus"]; cmd = ["taskset", "-c", cpus] + j["cmd"]
    s0 = cpu_stat(); l0 = load(); t0 = time.perf_counter(); ts = time.strftime("%H:%M:%S")
    env = dict(os.environ); env.update(j.get("env", {}))
    stdout = open(j["log"], "w") if j.get("log") else subprocess.PIPE
    p = subprocess.Popen(cmd, cwd=j["cwd"], env=env, stdout=stdout, stderr=subprocess.STDOUT)
    _, status, ru = os.wait4(p.pid, 0)
    t1 = time.perf_counter(); s1 = cpu_stat(); l1 = load()
    ncpu = [int(x) for x in cpus.replace("-", ",").split(",")] if "-" not in cpus else list(range(int(cpus.split("-")[0]), int(cpus.split("-")[1]) + 1))
    cpuset = sorted(set(ncpu))
    busy = {c: round(1 - (s1[c][1] - s0[c][1]) / max(1, s1[c][0] - s0[c][0]), 3) for c in cpuset}
    sib = {}
    for c in cpuset:
        try: sib[c] = [int(x) for x in open(f"/sys/devices/system/cpu/cpu{c}/topology/thread_siblings_list").read().strip().replace("-", ",").split(",")]
        except Exception: pass
    sibs = sorted({x for v in sib.values() for x in v} - set(cpuset))
    busy_sib = {c: round(1 - (s1[c][1] - s0[c][1]) / max(1, s1[c][0] - s0[c][0]), 3) for c in sibs}
    rec = {"name": j["name"], "rep": j.get("rep"), "cmd": j["cmd"], "cpus": cpus, "start": ts, "wall_s": t1 - t0,
           "user_s": ru.ru_utime, "sys_s": ru.ru_stime, "maxrss_mb": ru.ru_maxrss / 1024, "rc": os.waitstatus_to_exitcode(status),
           "load_before": l0, "load_after": l1, "cpu_busy_frac": busy, "sibling_cpu_busy_frac": busy_sib}
    if j.get("log"): stdout.close(); rec["log"] = j["log"]
    with open(outp, "a") as f: f.write(json.dumps(rec) + "\n")
    print(j["name"], j.get("rep"), f"{rec['wall_s']:.2f}s cpu {ru.ru_utime+ru.ru_stime:.1f}s rc {rec['rc']} load {l0[0]:.1f}->{l1[0]:.1f} busy {busy} sib {busy_sib}", flush=True)

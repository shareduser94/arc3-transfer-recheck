"""Rudakov graph explorer, offline baseline: 3 seeds with the re-initialisation fix + 1 seed as-is, all 25 games."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

jobs = [("", s) for s in (0, 1, 2)] + [("--as-is", 0)]
env = dict(os.environ, PYTHONHASHSEED="0")

def run(job):
    flag, s = job
    tag = "_asis" if flag else ""
    t0 = time.time()
    with open(f"run_rudakov{tag}_s{s}.log", "w") as out:
        cmd = [sys.executable, "rudakov_runner.py", "--seed", str(s), "--budget", "10000"] + (["--tag", tag, flag] if flag else [])
        rc = subprocess.call(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    print(f"rudakov{tag} s{s} rc={rc} {time.time() - t0:.0f}s", flush=True)
    return rc

with ThreadPoolExecutor(4) as ex:
    rcs = list(ex.map(run, jobs))
print("DONE", sum(r != 0 for r in rcs), "failures", flush=True)

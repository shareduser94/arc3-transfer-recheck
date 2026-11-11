"""Step E: combined agent, reset + transfer x 3 seeds, all 25 games, 6 processes."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

jobs = [(m, s) for s in (0, 1, 2) for m in ("reset", "transfer")]
env = dict(os.environ, PYTHONHASHSEED="0")

def run(job):
    m, s = job
    t0 = time.time()
    with open(f"run_hyb_{m}_s{s}.log", "w") as out:
        rc = subprocess.call([sys.executable, "rule_agent.py", "--hybrid", "--mode", m, "--seed", str(s), "--budget", "10000"],
                             stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    print(f"hyb_{m} s{s} rc={rc} {time.time() - t0:.0f}s", flush=True)
    return rc

with ThreadPoolExecutor(6) as ex:
    rcs = list(ex.map(run, jobs))
print("DONE", sum(r != 0 for r in rcs), "failures", flush=True)

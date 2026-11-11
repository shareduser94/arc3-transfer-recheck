"""Step L: confirmation on fresh seeds 10-19, our original agent (no --hybrid), 4 modes x 10 seeds x 6 games."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

GAMES = "cd82,dc22,lf52,lp85,tu93,vc33"
MODES = ["reset", "transfer", "selective", "effthin"]
jobs = [(m, s) for s in range(10, 20) for m in MODES]
env = dict(os.environ, PYTHONHASHSEED="0")

def run(job):
    m, s = job
    t0 = time.time()
    with open(f"run_l_{m}_s{s}.log", "w") as out:
        rc = subprocess.call([sys.executable, "rule_agent.py", "--mode", m, "--seed", str(s),
                              "--budget", "10000", "--games", GAMES, "--tag", "_c6"],
                             stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    print(f"{m} s{s} rc={rc} {time.time() - t0:.0f}s", flush=True)
    return rc

with ThreadPoolExecutor(6) as ex:
    rcs = list(ex.map(run, jobs))
print("DONE", sum(r != 0 for r in rcs), "failures", flush=True)

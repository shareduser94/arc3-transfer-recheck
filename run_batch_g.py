"""Step G: VOI re-check, 10 seeds x 6 games, on the combined agent and on our original agent (6 processes)."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

GAMES = "cd82,dc22,lf52,lp85,tu93,vc33"
jobs = [(h, s) for s in range(10) for h in (True, False)]
env = dict(os.environ, PYTHONHASHSEED="0")

def run(job):
    hyb, s = job
    name = f"{'hyb_' if hyb else ''}voi_s{s}"
    t0 = time.time()
    with open(f"run_g_{name}.log", "w") as out:
        cmd = [sys.executable, "rule_agent.py", "--mode", "voi", "--seed", str(s), "--budget", "10000",
               "--games", GAMES, "--tag", "_c6"] + (["--hybrid"] if hyb else [])
        rc = subprocess.call(cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
    print(f"{name} rc={rc} {time.time() - t0:.0f}s", flush=True)
    return rc

with ThreadPoolExecutor(6) as ex:
    rcs = list(ex.map(run, jobs))
print("DONE", sum(r != 0 for r in rcs), "failures", flush=True)

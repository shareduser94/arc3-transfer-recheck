"""Step C batch: 5 modes x 10 seeds on the 6 level-2 games, at most 6 processes at once."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

GAMES = "cd82,dc22,lf52,lp85,tu93,vc33"
MODES = ["reset", "transfer", "surprise", "droponly", "selective"]
jobs = [(m, s) for s in range(10) for m in MODES]

def run(job):
    m, s = job
    t0 = time.time()
    with open(f"run_c6_{m}_s{s}.log", "w") as out:
        rc = subprocess.call([sys.executable, "rule_agent.py", "--mode", m, "--seed", str(s),
                              "--budget", "10000", "--games", GAMES, "--tag", "_c6"],
                             stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    print(f"{m} s{s} rc={rc} {time.time() - t0:.0f}s", flush=True)
    return rc

with ThreadPoolExecutor(6) as ex:
    rcs = list(ex.map(run, jobs))
print("DONE", sum(r != 0 for r in rcs), "failures", flush=True)

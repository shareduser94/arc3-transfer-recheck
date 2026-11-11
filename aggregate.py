import json, glob, statistics as st
from collections import defaultdict
import logging; logging.disable(logging.INFO)
from agents import game_score

runs = defaultdict(list)
for f in sorted(glob.glob("results/*_s[0-9].json")):
    agent = f.split("\\")[-1].split("/")[-1].split("_s")[0]
    run = json.load(open(f))
    for r in run:                      # rescore with the official formula (fixed cap)
        r["score"] = game_score(r["level_actions"], r["baselines"])
    runs[agent].append(run)

for agent, rs in runs.items():
    means = [sum(r["score"] for r in run) / len(run) for run in rs]
    lvl1 = [sum(r["levels"] > 0 for r in run) for run in rs]
    lvl2 = [sum(r["levels"] > 1 for r in run) for run in rs]
    print(f"{agent:9s} runs={len(rs)} games/run={[len(r) for r in rs]} "
          f"mean score {st.mean(means):.4f} (per seed {[round(m,4) for m in means]}) "
          f"games>=1 level {lvl1}  games>=2 levels {lvl2}")

print("\nper game (levels per seed | mean score | explorer states at last level / actions there):")
games = sorted({r["game"] for rs in runs.values() for run in rs for r in run})
for g in games:
    line = f"{g:15s}"
    for agent, rs in runs.items():
        rr = [r for run in rs for r in run if r["game"] == g]
        line += f" | {agent[:4]} lv {[r['levels'] for r in rr]} sc {st.mean(r['score'] for r in rr):.3f}"
        if agent == "explorer":
            ratio = [round(r["states_per_level"][-1] / max(1, r["actions"] - sum(r["level_actions"])), 2) for r in rr]
            line += f" st/act {ratio} fb {[r['fallbacks'] for r in rr]}"
    print(line)

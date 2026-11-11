"""Step D baseline: Rudakov graph explorer (offline) vs our agents, 25 games, 10,000 actions."""
import json, os, statistics as st, logging
logging.disable(logging.INFO)
from agents import game_score

def load(name):
    return {r["game"][:4]: r for r in json.load(open(f"results/{name}.json"))}

runs = {"explorer": [load(f"explorer_s{s}") for s in range(3)],
        "reset": [load(f"reset_s{s}") for s in range(3)],
        "transfer": [load(f"transfer_s{s}") for s in range(3)],
        "rudakov": [load(f"rudakov_s{s}") for s in range(3) if os.path.exists(f"results/rudakov_s{s}.json")],
        "rudakov as-is": [load("rudakov_s0_asis")] if os.path.exists("results/rudakov_s0_asis.json") else []}
games = sorted(runs["reset"][0])
print("=== overall (per seed) ===")
for name, rs in runs.items():
    if not rs: continue
    sc = [st.mean(game_score(r[g]["level_actions"], r[g]["baselines"]) for g in games if g in r) for r in rs]
    l1 = [sum(r[g]["levels"] >= 1 for g in games if g in r) for r in rs]
    l2 = [sum(r[g]["levels"] >= 2 for g in games if g in r) for r in rs]
    lv = [sum(r[g]["levels"] for g in games if g in r) for r in rs]
    n = [len([g for g in games if g in r]) for r in rs]
    extra = ""
    if "rudakov" in name:
        extra = f" errors/game median {[int(st.median(r[g]['errors'] for g in games if g in r)) for r in rs]}"
    print(f"{name:14s} games {n} score {[round(x, 3) for x in sc]} mean {st.mean(sc):.3f} lvl>=1 {l1} lvl>=2 {l2} levels {lv}{extra}")

print("\n=== per game: levels per seed | level-1 actions (median over seeds that cleared it) ===")
for g in games:
    line = f"{g}"
    for name in ("reset", "transfer", "rudakov", "rudakov as-is"):
        rs = [r for r in runs[name] if g in r]
        if not rs: continue
        lv = [r[g]["levels"] for r in rs]
        a1 = [r[g]["level_actions"][0] for r in rs if r[g]["level_actions"]]
        line += f" | {name[:8]} lv {lv} a1 {int(st.median(a1)) if a1 else '-'}"
    print(line)

"""Step F analysis (copy of compare_c6.py for the combined agent): 5 modes x 10 seeds on 6 games; paired level-2 comparisons vs RESET; C1-C4."""
import json, math, statistics as st, logging
from math import comb
logging.disable(logging.INFO)
from agents import game_score

SEEDS = range(10)
MODES = ["reset", "transfer", "surprise", "droponly", "selective"]
D = {m: {s: {r["game"][:4]: r for r in json.load(open(f"results/hyb_{m}_s{s}_c6.json"))} for s in SEEDS} for m in MODES}
games = sorted(D["reset"][0])
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None

def sign_p(k, n):  # one-sided P(X >= k), X ~ Bin(n, 0.5)
    return sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0

# regression check vs the earlier full runs (seeds 0-2)
bad = 0
for m in ("reset", "transfer"):
    for s in range(3):
        full = {r["game"][:4]: r for r in json.load(open(f"results/hyb_{m}_s{s}.json"))}
        for g in games:
            if full[g]["level_actions"] != D[m][s][g]["level_actions"]:
                bad += 1
print(f"regression vs earlier runs (must be 0): {bad}")
mism = sum(D[m][s][g]["level_actions"][:1] != D["reset"][s][g]["level_actions"][:1]
           for m in MODES for s in SEEDS for g in games)
print(f"level-1 pairing mismatches (must be 0): {mism}")

pairs = [(g, s) for g in games for s in SEEDS if D["reset"][s][g]["level_actions"]]
print(f"game-seeds with level 1 cleared: {len(pairs)}")

print("\n=== level 2 vs RESET ===")
print(f"{'mode':10s} {'cleared':>7s} {'both':>5s} {'fewer':>5s} {'more':>5s} {'p(fewer)':>8s} {'median':>7s} {'geo':>6s} score")
for m in MODES:
    cl = sum(l2(D[m][s][g]) is not None for g, s in pairs)
    both = [(g, s) for g, s in pairs if l2(D[m][s][g]) is not None and l2(D["reset"][s][g]) is not None]
    fewer = sum(l2(D[m][s][g]) < l2(D["reset"][s][g]) for g, s in both)
    more = sum(l2(D[m][s][g]) > l2(D["reset"][s][g]) for g, s in both)
    lr = [math.log(l2(D[m][s][g]) / l2(D["reset"][s][g])) for g, s in both]
    sc = st.mean(game_score(D[m][s][g]["level_actions"], D[m][s][g]["baselines"]) for g in games for s in SEEDS)
    print(f"{m:10s} {cl:7d} {len(both):5d} {fewer:5d} {more:5d} {sign_p(fewer, fewer + more):8.3f} "
          f"{math.exp(st.median(lr)) if lr else float('nan'):7.3f} {math.exp(st.mean(lr)) if lr else float('nan'):6.3f} {sc:.3f}")

print("\n=== per game: level 2 cleared (of 10) / median level-2 actions among cleared ===")
for g in games:
    line = f"{g}:"
    for m in MODES:
        v = [l2(D[m][s][g]) for s in SEEDS if D[m][s][g]["level_actions"]]
        c = [x for x in v if x is not None]
        line += f"  {m[:5]} {len(c)}/{len(v)} med {int(st.median(c)) if c else '-'}"
    print(line)

print("\n=== C2: lp85 level-2 actions per seed (transfer vs selective) ===")
t = [l2(D["transfer"][s]["lp85"]) for s in SEEDS]; se = [l2(D["selective"][s]["lp85"]) for s in SEEDS]
print("  transfer ", t); print("  selective", se)
d = [a - b for a, b in zip(se, t) if a is not None and b is not None]
print(f"  median (selective - transfer): {st.median(d) if d else None}")

print("\n=== C4: surprise events on level 2 (selective) ===")
for g in games:
    ev = [D["selective"][s][g]["surprise_per_level"][1] for s in SEEDS if len(D["selective"][s][g]["surprise_per_level"]) > 1]
    print(f"  {g}: median {st.median(ev) if ev else None}  {ev}")

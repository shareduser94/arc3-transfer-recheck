"""Step A analysis: paired TRANSFER vs RESET, plus counter-mask effect vs EXPLORER."""
import json, statistics as st, logging
logging.disable(logging.INFO)
from agents import game_score

def load(name, s):
    return {r["game"]: r for r in json.load(open(f"results/{name}_s{s}.json"))}

SEEDS = [0, 1, 2]
T = {s: load("transfer", s) for s in SEEDS}
R = {s: load("reset", s) for s in SEEDS}
E = {s: load("explorer", s) for s in SEEDS}
games = sorted(T[0])

print("=== overall ===")
for name, D in (("explorer", E), ("reset", R), ("transfer", T)):
    means = [st.mean(game_score(r["level_actions"], r["baselines"]) for r in D[s].values()) for s in SEEDS]
    l1 = [sum(r["levels"] >= 1 for r in D[s].values()) for s in SEEDS]
    l2 = [sum(r["levels"] >= 2 for r in D[s].values()) for s in SEEDS]
    l3 = [sum(r["levels"] >= 3 for r in D[s].values()) for s in SEEDS]
    lv = [sum(r["levels"] for r in D[s].values()) for s in SEEDS]
    print(f"{name:9s} mean score {st.mean(means):.4f} per seed {[round(m, 4) for m in means]} "
          f"games>=1 lvl {l1} >=2 {l2} >=3 {l3} total levels {lv}")

print("\n=== A3: paired level-2 actions (only game-seeds where level 1 was cleared) ===")
pairs, mism = [], 0
for s in SEEDS:
    for g in games:
        t, r = T[s][g], R[s][g]
        if not t["level_actions"]:
            continue
        if t["level_actions"][0] != r["level_actions"][0]:
            mism += 1
        def l2(x):  # actions on level 2, or a lower bound (budget left) if unfinished
            if len(x["level_actions"]) >= 2:
                return x["level_actions"][1], True
            return x["actions"] - x["level_actions"][0], False
        (ta, td), (ra, rd) = l2(t), l2(r)
        pairs.append((g[:4], s, ta, td, ra, rd, t["levels"], r["levels"]))
print(f"pairs {len(pairs)}  level-1 mismatches (must be 0): {mism}")
for p in pairs:
    print(f"  {p[0]} s{p[1]}  transfer {p[2]:5d}{'' if p[3] else '+'}  reset {p[4]:5d}{'' if p[5] else '+'}  "
          f"levels T{p[6]} R{p[7]}")
both = [p for p in pairs if p[3] and p[5]]
print(f"both cleared level 2: {len(both)}")
if both:
    print(f"  median level-2 actions transfer {st.median(p[2] for p in both)} reset {st.median(p[4] for p in both)}")
    print(f"  transfer fewer on {sum(p[2] < p[4] for p in both)}, more on {sum(p[2] > p[4] for p in both)}, equal {sum(p[2] == p[4] for p in both)}")
print(f"level 2 cleared: transfer {sum(p[3] for p in pairs)}  reset {sum(p[5] for p in pairs)}")
print(f"median incl. censored (+ = lower bound): transfer {st.median(p[2] for p in pairs)} reset {st.median(p[4] for p in pairs)}")
neg = [p for p in pairs if (p[3] and p[5] and p[2] > 1.3 * p[4]) or (p[5] and not p[3])]
print(f"A5 negative-transfer cases: {[(p[0], p[1]) for p in neg]}")
print(f"total levels on these pairs: transfer {sum(p[6] for p in pairs)} reset {sum(p[7] for p in pairs)}")

print("\n=== A1: new states per action at the last level reached (mean over seeds) ===")
def ratio(r):
    left = max(1, r["actions"] - sum(r["level_actions"]))
    return r["states_per_level"][-1] / left
HOT = ["cd82", "cn04", "ka59", "r11l", "re86", "sp80", "tn36", "tr87", "vc33", "wa30"]
halved = 0
for g in games:
    if g[:4] not in HOT:
        continue
    e = st.mean(ratio(E[s][g]) for s in SEEDS); t = st.mean(ratio(R[s][g]) for s in SEEDS)
    halved += t <= e / 2
    masks = sorted({(tuple(R[s][g]["mask_rows"]), tuple(R[s][g]["mask_cols"])) for s in SEEDS})
    print(f"  {g[:4]} explorer {e:.2f}  rule(reset) {t:.2f}  {'HALVED' if t <= e / 2 else ''}  mask {masks}")
print(f"halved on {halved}/10")

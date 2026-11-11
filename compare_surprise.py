"""Step B analysis: SURPRISE vs RESET / TRANSFER (paired), predictions B1-B5."""
import json, math, statistics as st, logging
logging.disable(logging.INFO)
from agents import game_score

SEEDS = [0, 1, 2]
load = lambda name, s: {r["game"]: r for r in json.load(open(f"results/{name}_s{s}.json"))}
M = {name: {s: load(name, s) for s in SEEDS} for name in ("explorer", "reset", "transfer", "surprise")}
games = sorted(M["reset"][0])

print("=== overall ===")
for name, D in M.items():
    means = [st.mean(game_score(r["level_actions"], r["baselines"]) for r in D[s].values()) for s in SEEDS]
    l1 = [sum(r["levels"] >= 1 for r in D[s].values()) for s in SEEDS]
    l2 = [sum(r["levels"] >= 2 for r in D[s].values()) for s in SEEDS]
    lv = [sum(r["levels"] for r in D[s].values()) for s in SEEDS]
    print(f"{name:9s} mean {st.mean(means):.4f} per seed {[round(m, 4) for m in means]} >=1 lvl {l1} >=2 {l2} total levels {lv}")

R, T, S = M["reset"], M["transfer"], M["surprise"]
mism = sum(1 for s in SEEDS for g in games
           if S[s][g]["level_actions"][:1] != R[s][g]["level_actions"][:1])
print(f"\nlevel-1 pairing mismatches surprise vs reset (must be 0): {mism}")

l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None
pairs = [(g, s) for s in SEEDS for g in games if R[s][g]["level_actions"]]
print(f"game-seeds with level 1 cleared: {len(pairs)}")

print("\n=== B1: lf52 level 2 (actions, None = not cleared) ===")
for s in SEEDS:
    g = [x for x in games if x.startswith("lf52")][0]
    print(f"  s{s}: reset {l2(R[s][g])} transfer {l2(T[s][g])} surprise {l2(S[s][g])}")

print("\n=== B2 ===")
for name, D in (("reset", R), ("transfer", T), ("surprise", S)):
    print(f"  level 2 cleared by {name}: {sum(l2(D[s][g]) is not None for g, s in pairs)}")
for other_name, O in (("reset", R), ("transfer", T)):
    both = [(g, s) for g, s in pairs if l2(S[s][g]) is not None and l2(O[s][g]) is not None]
    fewer = sum(l2(S[s][g]) < l2(O[s][g]) for g, s in both)
    more = sum(l2(S[s][g]) > l2(O[s][g]) for g, s in both)
    lr = [math.log(l2(S[s][g]) / l2(O[s][g])) for g, s in both]
    print(f"  surprise vs {other_name}: both cleared {len(both)}, surprise fewer {fewer}, more {more}, "
          f"equal {len(both) - fewer - more}, median ratio {math.exp(st.median(lr)):.3f}, geo-mean {math.exp(st.mean(lr)):.3f}")
print("  per pair (level-2 actions R / T / S):")
for g, s in pairs:
    v = [l2(D[s][g]) for D in (R, T, S)]
    if any(x is not None for x in v):
        ev = S[s][g]["surprise_per_level"]
        print(f"    {g[:4]} s{s}: {v}  surprise events per level {ev} switches {S[s][g]['level_switches']}")

print("\n=== B3: surprise events on level 2 ===")
def lvl2_events(r):
    ev = r["surprise_per_level"]
    return ev[1] if len(ev) > 1 else None
allv = [(g, s, lvl2_events(S[s][g])) for g, s in pairs if lvl2_events(S[s][g]) is not None]
hurt = [("lf52", 0), ("lf52", 1), ("lf52", 2), ("cd82", 1)]
med = st.median(v for _, _, v in allv)
print(f"  median over {len(allv)} game-seeds reaching level 2: {med}")
for g, s, v in allv:
    if (g[:4], s) in hurt:
        print(f"  hurt case {g[:4]} s{s}: {v}  {'ABOVE median' if v > med else 'not above'}")
print("  all:", sorted(((g[:4], s, v) for g, s, v in allv), key=lambda x: -x[2]))

print("\n=== B4 ===")
mean = lambda D: st.mean(game_score(r["level_actions"], r["baselines"]) for s in SEEDS for r in D[s].values())
print(f"  surprise {mean(S):.4f} transfer {mean(T):.4f} diff {mean(S) - mean(T):+.4f}")

print("\n=== B5: lp85 level-2 saving vs reset ===")
g = [x for x in games if x.startswith("lp85")][0]
for s in SEEDS:
    print(f"  s{s}: transfer saves {l2(R[s][g]) - l2(T[s][g])}, surprise saves {l2(R[s][g]) - l2(S[s][g])}")

"""Step E: combined agent vs ours vs Rudakov; predictions E1-E5."""
import json, statistics as st, logging
logging.disable(logging.INFO)
from agents import game_score

def load(name):
    return {r["game"][:4]: r for r in json.load(open(f"results/{name}.json"))}

M = {n: [load(f"{n}_s{s}") for s in range(3)] for n in ("reset", "transfer", "rudakov", "hyb_reset", "hyb_transfer")}
games = sorted(M["reset"][0])
print("=== overall ===")
for n, rs in M.items():
    sc = [st.mean(game_score(r[g]["level_actions"], r[g]["baselines"]) for g in games) for r in rs]
    l1 = [sum(r[g]["levels"] >= 1 for g in games) for r in rs]
    l2 = [sum(r[g]["levels"] >= 2 for g in games) for r in rs]
    lv = [sum(r[g]["levels"] for g in games) for r in rs]
    print(f"{n:13s} score {[round(x, 3) for x in sc]} mean {st.mean(sc):.3f}  lvl>=1 {l1}  lvl>=2 {l2}  levels {lv}")

OURS_ONLY = ["dc22", "g50t", "lf52", "ls20", "su15", "tn36", "tu93"]
print("\nE3: level 1 cleared on our-only games (per seed):")
for n in ("hyb_reset", "hyb_transfer"):
    print(f"  {n}: {[sum(r[g]['levels'] >= 1 for g in OURS_ONLY) for r in M[n]]} of 7")
print("\nE5: sp80 level-1 actions:", {n: [r['sp80']['level_actions'][:1] for r in M[n]] for n in ("reset", "rudakov", "hyb_reset", "hyb_transfer")})

print("\n=== per game: levels per seed | median level-1 actions ===")
for g in games:
    line = f"{g}"
    for n in ("reset", "rudakov", "hyb_reset", "hyb_transfer"):
        a1 = [r[g]["level_actions"][0] for r in M[n] if r[g]["level_actions"]]
        line += f" | {n[:9]} {[r[g]['levels'] for r in M[n]]} a1 {int(st.median(a1)) if a1 else '-'}"
    print(line)

print("\n=== transfer vs reset inside the combined agent (level 2, paired) ===")
pairs = [(g, s) for s in range(3) for g in games if M["hyb_reset"][s][g]["level_actions"]]
mism = sum(M["hyb_reset"][s][g]["level_actions"][:1] != M["hyb_transfer"][s][g]["level_actions"][:1] for g, s in pairs)
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) > 1 else None
both = [(g, s) for g, s in pairs if l2(M["hyb_reset"][s][g]) and l2(M["hyb_transfer"][s][g])]
fewer = sum(l2(M["hyb_transfer"][s][g]) < l2(M["hyb_reset"][s][g]) for g, s in both)
print(f"pairs with level 1: {len(pairs)}, level-1 mismatches {mism}; both cleared level 2: {len(both)}, transfer fewer on {fewer}")
print(f"level 2 cleared: reset {sum(l2(M['hyb_reset'][s][g]) is not None for g, s in pairs)}, transfer {sum(l2(M['hyb_transfer'][s][g]) is not None for g, s in pairs)}")

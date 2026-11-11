"""Step K analysis on the Step J games (copy of compare_dense.py): dense layout, k up to 64, 100 games per cell."""
import json, statistics as st
from collections import defaultdict
import gen_env as G
MODES = ["reset", "transfer", "selective", "effthin"]
D = {m: {r["game"]: r for r in json.load(open(f"results/gen_{m}_dense.json"))} for m in MODES}
games = list(D["reset"])
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None
mism = sum(D[m][g]["level_actions"][:1] != D["reset"][g]["level_actions"][:1] for m in MODES for g in games)
print(f"games {len(games)}; pairing mismatches {mism}; level 2 not cleared: { {m: sum(l2(D[m][g]) is None for g in games) for m in MODES} }")
cells = defaultdict(list)
for g in games:
    cells[(G.parse(g)[1], G.parse_noise(g))].append(g)
print(f"\n{'condition':14s} {'k':>3s} | {'RESET med':>9s} | " + " | ".join(f"{m:>9s} slower/faster ratio" for m in MODES[1:]))
for cond in ("stable", "promoted_half"):
    for k in (0, 16, 32, 48, 64):
        gs = cells[(cond, k)]
        parts = []
        for m in MODES[1:]:
            pr = [(l2(D[m][g]), l2(D["reset"][g])) for g in gs if l2(D[m][g]) and l2(D["reset"][g])]
            parts.append(f"{m:>9s} {sum(a > b for a, b in pr):2d}/{sum(a < b for a, b in pr):2d} {st.median(a / b for a, b in pr):5.2f}")
        print(f"{cond:14s} {k:3d} | {st.median(l2(D['reset'][g]) for g in gs):9.0f} | " + " | ".join(parts))
print("\n(slower/faster = games where the mode needed more / fewer level-2 actions than RESET; ratio = median mode/RESET)")

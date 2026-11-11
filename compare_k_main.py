"""Step H analysis: generated games, level-2 actions of each mode vs RESET (paired), per condition x decoys."""
import json, math, statistics as st, sys
from math import comb
from collections import defaultdict
import gen_env as G

tag = sys.argv[1] if len(sys.argv) > 1 else ""
MODES = ["reset", "transfer", "selective", "effthin"]
D = {m: {r["game"]: r for r in json.load(open(f"results/gen_{m}{tag}.json"))} for m in MODES}
games = list(D["reset"])
sign_p = lambda k, n: sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None

mism = sum(D[m][g]["level_actions"][:1] != D["reset"][g]["level_actions"][:1] for m in MODES for g in games)
unsolved = {m: sum(l2(D[m][g]) is None for g in games) for m in MODES}
print(f"games {len(games)}; level-1 pairing mismatches {mism}; level 2 not cleared: {unsolved}")
cells = defaultdict(list)
for g in games:
    _, cond, nd = G.parse(g); cells[(cond, nd)].append(g)
print(f"\n{'condition':15s} {'dec':>3s} | {'RESET med':>9s} | " + " | ".join(f"{m:>9s} more/fewer  ratio" for m in MODES[1:]))
for cond in G.CONDITIONS:
    for nd in (0, 6):
        gs = cells[(cond, nd)]
        line = f"{cond:15s} {nd:3d} | {st.median(l2(D['reset'][g]) for g in gs):9.0f} | "
        parts = []
        for m in MODES[1:]:
            pr = [(l2(D[m][g]), l2(D["reset"][g])) for g in gs if l2(D[m][g]) and l2(D["reset"][g])]
            more = sum(a > b for a, b in pr); fewer = sum(a < b for a, b in pr)
            ratio = st.median(a / b for a, b in pr)
            parts.append(f"{m:>9s} {more:2d}/{fewer:2d} {ratio:6.2f}")
        print(line + " | ".join(parts))
print("\n(more/fewer = games where the mode needed more / fewer level-2 actions than RESET; ratio = median mode/RESET)")

"""Step L: EFFTHIN confirmation on fresh seeds 10-19 (original agent). Same measures as Steps C/K."""
import json, math, statistics as st, logging
from math import comb
logging.disable(logging.INFO)
SEEDS = range(10, 20)
MODES = ("reset", "transfer", "selective", "effthin")
D = {m: {s: {r["game"][:4]: r for r in json.load(open(f"results/{m}_s{s}_c6.json"))} for s in SEEDS} for m in MODES}
games = sorted(D["reset"][10])
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None
sign_p = lambda k, n: sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0
mism = sum(D[m][s][g]["level_actions"][:1] != D["reset"][s][g]["level_actions"][:1] for m in MODES for s in SEEDS for g in games)
pairs = [(g, s) for g in games for s in SEEDS if D["reset"][s][g]["level_actions"]]
print(f"seeds 10-19; level-1 pairing mismatches {mism}; game-seeds with level 1: {len(pairs)}")
print(f"{'mode':10s} {'L2 clr':>6s} {'fewer':>5s} {'more':>5s} {'share':>6s} {'p':>6s} {'median':>7s} {'geo':>6s} {'lf52':>5s}")
for m in MODES:
    cl = sum(l2(D[m][s][g]) is not None for g, s in pairs)
    both = [(g, s) for g, s in pairs if l2(D[m][s][g]) is not None and l2(D["reset"][s][g]) is not None]
    f = sum(l2(D[m][s][g]) < l2(D["reset"][s][g]) for g, s in both)
    mo = sum(l2(D[m][s][g]) > l2(D["reset"][s][g]) for g, s in both)
    lr = [math.log(l2(D[m][s][g]) / l2(D["reset"][s][g])) for g, s in both]
    lf = sum(l2(D[m][s]["lf52"]) is not None for s in SEEDS)
    share = f / (f + mo) if f + mo else float("nan")
    print(f"{m:10s} {cl:6d} {f:5d} {mo:5d} {share:6.2f} {sign_p(f, f + mo):6.3f} {math.exp(st.median(lr)):7.3f} {math.exp(st.mean(lr)):6.3f} {lf:5d}")
t = [l2(D["transfer"][s]["lp85"]) for s in SEEDS]; e = [l2(D["effthin"][s]["lp85"]) for s in SEEDS]
d = [a - b for a, b in zip(e, t) if a is not None and b is not None]
print(f"lp85 level-2 actions, EFFTHIN minus TRANSFER: median {st.median(d) if d else None} {d}")
print("per game level 2 cleared (of 10) / median level-2 actions:")
for g in games:
    line = f"  {g}:"
    for m in MODES:
        c = [l2(D[m][s][g]) for s in SEEDS if l2(D[m][s][g]) is not None]
        line += f"  {m[:5]} {len(c)}/10 med {int(st.median(c)) if c else '-'}"
    print(line)

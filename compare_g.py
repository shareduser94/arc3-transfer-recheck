"""Step G: VOI re-check vs RESET / TRANSFER / SELECTIVE, on the combined agent and on our original agent."""
import json, math, statistics as st, logging
from math import comb
logging.disable(logging.INFO)

SEEDS = range(10)
def load(prefix, m):
    return {s: {r["game"][:4]: r for r in json.load(open(f"results/{prefix}{m}_s{s}_c6.json"))} for s in SEEDS}
l2 = lambda r: r["level_actions"][1] if len(r["level_actions"]) >= 2 else None
sign_p = lambda k, n: sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0

for label, prefix in (("COMBINED AGENT", "hyb_"), ("OUR ORIGINAL AGENT", "")):
    D = {m: load(prefix, m) for m in ("reset", "transfer", "selective", "surprise", "voi")}
    games = sorted(D["reset"][0])
    mism = sum(D["voi"][s][g]["level_actions"][:1] != D["reset"][s][g]["level_actions"][:1] for s in SEEDS for g in games)
    pairs = [(g, s) for g in games for s in SEEDS if D["reset"][s][g]["level_actions"]]
    print(f"\n===== {label} =====  level-1 pairing mismatches VOI vs RESET: {mism}; game-seeds with level 1: {len(pairs)}")
    print(f"{'mode':10s} {'L2 clr':>6s} {'fewer':>5s} {'more':>5s} {'share':>6s} {'p':>6s} {'median':>7s} {'geo':>6s} {'lf52':>5s}")
    for m in ("reset", "transfer", "selective", "surprise", "voi"):
        cl = sum(l2(D[m][s][g]) is not None for g, s in pairs)
        both = [(g, s) for g, s in pairs if l2(D[m][s][g]) is not None and l2(D["reset"][s][g]) is not None]
        f = sum(l2(D[m][s][g]) < l2(D["reset"][s][g]) for g, s in both)
        mo = sum(l2(D[m][s][g]) > l2(D["reset"][s][g]) for g, s in both)
        lr = [math.log(l2(D[m][s][g]) / l2(D["reset"][s][g])) for g, s in both]
        lf = sum(l2(D[m][s]["lf52"]) is not None for s in SEEDS)
        share = f / (f + mo) if f + mo else float("nan")
        print(f"{m:10s} {cl:6d} {f:5d} {mo:5d} {share:6.2f} {sign_p(f, f + mo):6.3f} {math.exp(st.median(lr)):7.3f} {math.exp(st.mean(lr)):6.3f} {lf:5d}")
    t = [l2(D["transfer"][s]["lp85"]) for s in SEEDS]; v = [l2(D["voi"][s]["lp85"]) for s in SEEDS]
    d = [a - b for a, b in zip(v, t) if a is not None and b is not None]
    print(f"lp85 level-2 actions, VOI minus TRANSFER: median {st.median(d) if d else None}  {d}")
    print("VOI re-checks per game (median over seeds):", {g: int(st.median(D['voi'][s][g]['voi_rechecks'] for s in SEEDS)) for g in games})
    print("per game level 2 cleared (of 10) / median level-2 actions:")
    for g in games:
        line = f"  {g}:"
        for m in ("reset", "transfer", "selective", "voi"):
            c = [l2(D[m][s][g]) for s in SEEDS if l2(D[m][s][g]) is not None]
            line += f"  {m[:5]} {len(c)}/10 med {int(st.median(c)) if c else '-'}"
        print(line)

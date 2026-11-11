"""Step H runner: the rule agent (unchanged) on the generated games. Writes results/gen_<mode><tag>.json."""
import argparse, json, os, time, logging
logging.disable(logging.INFO)
import gen_env as G
from rule_agent import RuleAgent, run_game


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True)
    ap.add_argument("--budget", type=int, default=3000)
    ap.add_argument("--only", default="")
    ap.add_argument("--set", default="main", choices=["main", "noise", "dense"])
    ap.add_argument("--hybrid", action="store_true")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    arc = G.GenArcade()
    ids = args.only.split(",") if args.only else (G.game_ids_noise() if args.set == "noise" else G.game_ids_dense() if args.set == "dense" else G.game_ids())
    os.makedirs("results", exist_ok=True)
    out = f"results/gen_{'hyb_' if args.hybrid else ''}{args.mode}{args.tag}.json"
    res, t0 = [], time.time()
    for i, gid in enumerate(ids):
        idx = G.parse(gid)[0]
        agent = RuleAgent(idx, args.mode, hybrid=args.hybrid)       # agent seed = game index: paired across modes
        r = run_game(arc, gid, agent, args.budget, [1, 1])
        res.append(r)
        if args.only:
            print(f"{gid} levels {r['levels']} level_actions {r['level_actions']} actions {r['actions']} {r['secs']}s", flush=True)
        if i % 20 == 19 or i == len(ids) - 1:
            json.dump(res, open(out, "w"), indent=1)
            print(f"{i + 1}/{len(ids)} games, {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

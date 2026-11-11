"""Run Rudakov, Shock & Cowley's graph explorer (arXiv 2512.24156) offline on the arc-agi 0.9.9 toolkit.

Their code is used unmodified, from ../rudakov (MIT licence). Only the plumbing around it is new:
- their package __init__ pulls in LLM frameworks we do not need, so the three modules their agent
  imports from it are provided here: a minimal Agent base class, a no-op tracing decorator, and their
  own structs.py loaded straight from file;
- their per-step sleep (0.31 s, an API rate limit) is set to 0 and their time-based seed is replaced
  by --seed, so runs are reproducible (run with PYTHONHASHSEED=0: their graph iterates over sets of strings);
- the main loop mirrors their Agent.main(): level-up when the score rises, re-initialise on an exception.
RESETs after GAME_OVER are not counted as actions (same convention as our own runners).
One documented deviation (off with --as-is): in their Agent.main(), an exception sets level_up = True so the next
call re-initialises the graph ("re-initializing the GraphExplorer"), but the same loop sets level_up = False again
right after the step, so the re-initialisation never happens. Offline, where a reset after GAME_OVER can make a
tested action look different, that leaves the agent repeating one action forever (thousands of errors per game).
By default the runner keeps level_up = True for the call after an exception, which is what their message says.

Usage: python rudakov_runner.py --seed 0 --budget 10000 [--games ls20,ft09] [--tag _x]
Writes results/rudakov_s<seed><tag>.json
"""
import argparse, importlib.util, json, os, random, sys, time, types, logging
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction as EnvAction, GameState as EnvState
from agents import game_score

logging.disable(logging.INFO)
FIX_REINIT = True
RUDAKOV = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rudakov"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- shims for the three modules their agent imports from its package ----
pkg = types.ModuleType("agents_rd"); pkg.__path__ = []
sys.modules["agents_rd"] = pkg


class _Agent:                                  # minimal stand-in for their API-bound Agent base class
    def __init__(self, *args, **kwargs):
        self.game_id = kwargs.get("game_id", args[0] if args else "")
        self.action_counter = 0


agent_mod = types.ModuleType("agents.agent"); agent_mod.Agent = _Agent
tracing_mod = types.ModuleType("agents.tracing"); tracing_mod.trace_agent_session = lambda f: f
agents_pkg = types.ModuleType("agents"); agents_pkg.__path__ = []
sys.modules.update({"agents.agent": agent_mod, "agents.tracing": tracing_mod})
# our own agents.py (scorer) was imported above as "agents"; keep a handle and swap the package in
_our_agents = sys.modules["agents"]
sys.modules["agents"] = agents_pkg
structs = _load("agents.structs", os.path.join(RUDAKOV, "agents", "structs.py"))
sys.path.insert(0, RUDAKOV)                    # for "from graph_explorer import GraphExplorer"
heur = _load("agents.heuristic_agent", os.path.join(RUDAKOV, "agents", "heuristic_agent.py"))
sys.modules["agents"] = _our_agents
RGameState, RGameAction = structs.GameState, structs.GameAction


class Frame:                                   # what their choose_action reads from a frame
    def __init__(self, fd):
        self.frame = [np.asarray(f) for f in fd.frame]
        self.state = RGameState[fd.state.name]
        self.available_actions = list(fd.available_actions)
        self.score = fd.levels_completed


def make_agent(gid, seed):
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        ag = heur.HeuristicAgent(game_id=gid)
    ag.minimal_step_time = 0.0
    random.seed(seed); np.random.seed(seed)
    return ag


def run_game(arc, gid, seed, budget, baselines):
    import io, contextlib
    env = arc.make(gid, seed=0)
    fd = env.reset()
    ag = make_agent(gid, seed)
    win_levels = fd.win_levels
    level_actions, since, n, overs, resets, errors = [], 0, 0, 0, 0, 0
    score = best = fd.levels_completed
    sink = io.StringIO()
    reinit = False
    t0 = time.time()
    while n < budget:
        lf = Frame(fd)
        try:
            with contextlib.redirect_stdout(sink):
                action = ag.choose_action([lf], lf)
        except Exception:
            ag.failed = True; ag.level_up = True; errors += 1
            action = ag.last_action_object
            reinit = True
        sink.seek(0); sink.truncate()
        if action.value == 0:
            fd2 = env.reset(); resets += 1
        else:
            data = {"x": int(action.action_data.x), "y": int(action.action_data.y)} if action.value == 6 else None
            fd2 = env.step(EnvAction.from_id(action.value), data=data)
            n += 1; since += 1
        if fd2 is None:
            break
        new_score = fd2.levels_completed
        if new_score > score:
            ag.level_up = True; ag.status_bar_mask = None
        elif reinit and FIX_REINIT:
            reinit = False                     # keep level_up so the next call really re-initialises (see header)
        elif ag.status_bar_mask is not None:
            ag.level_up = False
        score = new_score
        if new_score > best:
            for _ in range(new_score - best):
                level_actions.append(since); since = 0
            best = new_score
        if fd2.state == EnvState.WIN:
            break
        if fd2.state == EnvState.GAME_OVER:
            overs += 1
        fd = fd2
    return {"game": gid, "win_levels": win_levels, "levels": best, "level_actions": level_actions,
            "baselines": baselines, "score": game_score(level_actions, baselines), "actions": n,
            "game_overs": overs, "resets": resets, "errors": errors, "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--games", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--as-is", action="store_true", help="their loop exactly: no re-initialisation fix")
    args = ap.parse_args()
    global FIX_REINIT
    FIX_REINIT = not args.as_is
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    infos = {e.game_id: e for e in arc.get_environments()}
    gids = sorted(infos) if not args.games else [g for g in sorted(infos) if g.split("-")[0] in args.games.split(",")]
    os.makedirs("results", exist_ok=True)
    out = f"results/rudakov_s{args.seed}{args.tag}.json"
    res = []
    for gid in gids:
        meta = json.load(open(os.path.join(infos[gid].local_dir, "metadata.json")))
        r = run_game(arc, gid, args.seed, args.budget, meta["baseline_actions"])
        res.append(r)
        print(f"{gid} levels {r['levels']}/{r['win_levels']} score {r['score']:.3f} level_actions {r['level_actions']} "
              f"overs {r['game_overs']} errors {r['errors']} {r['secs']}s", flush=True)
        json.dump(res, open(out, "w"), indent=1)
    print("MEAN SCORE", round(sum(r["score"] for r in res) / len(res), 4),
          "games with >=1 level", sum(r["levels"] > 0 for r in res), flush=True)


if __name__ == "__main__":
    main()

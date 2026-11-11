"""ARC-AGI-3 baselines: RANDOM and EXPLORER (graph exploration, no learning across games).

Usage: python agents.py --agent random|explorer --seed 0 --budget 10000 [--games ls20,ft09]
Writes results/<agent>_s<seed>.json
"""
import argparse, json, os, random, time, hashlib, logging
from collections import deque
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState

logging.disable(logging.INFO)


# ---------------- scoring (same formula as arc_agi.scorecard.EnvironmentScoreCalculator) -------------
def game_score(level_actions, baselines):
    """level_actions[i] = actions used to finish level i+1 (None if unfinished)."""
    tot, wsum, wdone = 0.0, 0, 0
    for i, b in enumerate(baselines):
        w = i + 1
        a = level_actions[i] if i < len(level_actions) else None
        s = min(115.0, 100.0 * (b / a) ** 2) if a else 0.0
        tot += s * w
        wsum += w
        wdone += w if s > 0 else 0
    return min(tot / wsum, wdone / wsum * 100.0) if wsum else 0.0


# ---------------- frame utilities ----------------
def last_frame(fd):
    return np.asarray(fd.frame[-1], dtype=np.uint8)


def key_of(fr):
    return hashlib.blake2b(fr.tobytes(), digest_size=12).digest()


def object_clicks(fr, max_objs=80):
    """Centre pixel of each 4-connected same-colour region, background colour excluded."""
    vals, counts = np.unique(fr, return_counts=True)
    bg = vals[np.argmax(counts)]
    seen = np.zeros(fr.shape, dtype=bool)
    seen[fr == bg] = True
    H, W = fr.shape
    objs = []
    for y0 in range(H):
        for x0 in range(W):
            if seen[y0, x0]:
                continue
            c = fr[y0, x0]
            q = [(y0, x0)]; seen[y0, x0] = True; pix = []
            while q:
                y, x = q.pop(); pix.append((y, x))
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy, xx] and fr[yy, xx] == c:
                        seen[yy, xx] = True; q.append((yy, xx))
            pix.sort()
            y, x = pix[len(pix) // 2]          # a pixel that is inside the region
            objs.append((len(pix), x, y))
    objs.sort()                                 # small objects first (buttons are usually small)
    return [(x, y) for _, x, y in objs[:max_objs]]


# ---------------- agents ----------------
class RandomAgent:
    def __init__(self, seed):
        self.rng = random.Random(seed)

    def new_level(self):
        pass

    def act(self, fd, fr):
        a = self.rng.choice([x for x in fd.available_actions if x != 0])
        if a == 6:
            return (6, self.rng.randrange(64), self.rng.randrange(64))
        return (a,)

    def observe(self, s, a, s2, dead):
        pass


class ExplorerAgent:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.new_level()
        self.click_cache = {}

    def new_level(self):
        self.adj = {}        # state -> {action: next_state}
        self.untried = {}    # state -> [actions]
        self.dead = set()    # (state, action) that led to GAME_OVER
        self.plan = deque()  # [(action, expected_state)]
        self.fallbacks = 0

    def _init_state(self, s, fd, fr):
        acts = [(a,) for a in fd.available_actions if a not in (0, 6)]
        if 6 in fd.available_actions:
            if s not in self.click_cache:
                self.click_cache[s] = object_clicks(fr)
            acts += [(6, x, y) for x, y in self.click_cache[s]]
        self.rng.shuffle(acts)
        self.untried[s] = acts
        self.adj[s] = {}

    def _bfs(self, start):
        prev = {start: None}
        q = deque([start])
        while q:
            u = q.popleft()
            if u != start and self.untried.get(u):
                path = []
                while prev[u] is not None:
                    p, a = prev[u]; path.append((a, u)); u = p
                return list(reversed(path))
            for a, v in self.adj.get(u, {}).items():
                if v not in prev and (u, a) not in self.dead:
                    prev[v] = (u, a); q.append(v)
        return None

    def act(self, fd, fr):
        s = key_of(fr)
        if s not in self.untried:
            self._init_state(s, fd, fr)
        if self.untried[s]:
            self.plan.clear()
            return self.untried[s].pop()
        if not self.plan:
            path = self._bfs(s)
            if path:
                self.plan.extend(path)
        if self.plan:
            a, _ = self.plan[0]
            return a
        self.fallbacks += 1                       # graph exhausted: random action
        a = self.rng.choice([x for x in fd.available_actions if x != 0])
        return (6, self.rng.randrange(64), self.rng.randrange(64)) if a == 6 else (a,)

    def observe(self, s, a, s2, dead):
        if dead:
            self.dead.add((s, a)); self.plan.clear(); return
        if s in self.adj:
            self.adj[s][a] = s2
        if self.plan:
            pa, exp = self.plan.popleft()
            if pa != a or exp != s2:
                self.plan.clear()                 # world did not do what the graph predicted


# ---------------- runner ----------------
def run_game(arc, gid, agent, budget, baselines):
    env = arc.make(gid, seed=0)
    fd = env.reset()
    win_levels = fd.win_levels
    level_actions = []          # actions spent on each newly completed level
    since = 0                   # actions since last new level
    best = fd.levels_completed
    n = overs = 0
    states = set()
    states_per_level = []
    t0 = time.time()
    while n < budget:
        fr = last_frame(fd)
        s = key_of(fr); states.add(s)
        a = agent.act(fd, fr)
        act = GameAction.from_id(a[0])
        fd2 = env.step(act, data={"x": a[1], "y": a[2]} if a[0] == 6 else None)
        n += 1; since += 1
        if fd2 is None:
            break
        dead = fd2.state == GameState.GAME_OVER
        agent.observe(s, a, key_of(last_frame(fd2)), dead)
        if fd2.levels_completed > best:
            for _ in range(fd2.levels_completed - best):
                level_actions.append(since); since = 0
            best = fd2.levels_completed
            states_per_level.append(len(states)); states = set()
            agent.new_level()
        if fd2.state == GameState.WIN:
            break
        if dead:
            overs += 1
            fd2 = env.reset()
        fd = fd2
    states_per_level.append(len(states))
    return {
        "game": gid, "win_levels": win_levels, "levels": best,
        "level_actions": level_actions, "baselines": baselines,
        "score": game_score(level_actions, baselines),
        "actions": n, "game_overs": overs,
        "states_per_level": states_per_level,
        "fallbacks": getattr(agent, "fallbacks", None),
        "secs": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True, choices=["random", "explorer"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--games", default="")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    infos = {e.game_id: e for e in arc.get_environments()}
    gids = sorted(infos) if not args.games else [g for g in sorted(infos) if g.split("-")[0] in args.games.split(",")]
    os.makedirs("results", exist_ok=True)
    out = f"results/{args.agent}_s{args.seed}{args.tag}.json"
    res = []
    for gid in gids:
        meta = json.load(open(os.path.join(infos[gid].local_dir, "metadata.json")))
        agent = RandomAgent(args.seed) if args.agent == "random" else ExplorerAgent(args.seed)
        r = run_game(arc, gid, agent, args.budget, meta["baseline_actions"])
        res.append(r)
        print(f"{gid} levels {r['levels']}/{r['win_levels']} score {r['score']:.3f} "
              f"level_actions {r['level_actions']} overs {r['game_overs']} "
              f"states {r['states_per_level'][-1]} fallbacks {r['fallbacks']} {r['secs']}s", flush=True)
        json.dump(res, open(out, "w"), indent=1)
    print("MEAN SCORE", round(sum(r["score"] for r in res) / len(res), 4),
          "games with >=1 level", sum(r["levels"] > 0 for r in res), flush=True)


if __name__ == "__main__":
    main()

import os, time, json, random
import numpy as np
import arc_agi
from arcengine import GameAction, GameState

arc = arc_agi.Arcade()
envs = arc.get_environments()
print("N environments:", len(envs))
out = []
for e in envs:
    d = e.model_dump() if hasattr(e, "model_dump") else vars(e)
    out.append({k: (str(v) if not isinstance(v, (int, float, str, bool, type(None), list)) else v) for k, v in d.items()})
print(json.dumps(out[:2], indent=1, default=str))
print("IDs:", [o.get("game_id") for o in out])

rows = []
for o in out:
    gid = o["game_id"]
    try:
        env = arc.make(gid, seed=0)
        fd = env.reset()
        fr = fd.frame
        shapes = [np.asarray(f).shape for f in fr]
        acts = list(fd.available_actions)
        rng = random.Random(0)
        t0 = time.time(); n = 0; wins = 0; overs = 0; maxlev = 0; multi = 0
        while n < 2000:
            a = GameAction.from_id(rng.choice(acts))
            data = {"x": rng.randrange(64), "y": rng.randrange(64)} if a.is_complex() else None
            fd = env.step(a, data=data)
            n += 1
            if fd is None:
                print(gid, "step returned None"); break
            if len(fd.frame) > 1: multi += 1
            maxlev = max(maxlev, fd.levels_completed)
            if fd.state == GameState.GAME_OVER:
                overs += 1; fd = env.reset()
            elif fd.state == GameState.WIN:
                wins += 1; fd = env.reset()
        dt = time.time() - t0
        rows.append((gid, shapes[:2], acts, fd.win_levels, maxlev, overs, wins, multi, round(n/dt)))
        print(gid, "frames", shapes[:2], "acts", acts, "win_levels", fd.win_levels,
              "maxlev", maxlev, "game_overs", overs, "wins", wins, "multi-frame steps", multi, "steps/s", round(n/dt), flush=True)
    except Exception as ex:
        print(gid, "ERROR", repr(ex), flush=True)

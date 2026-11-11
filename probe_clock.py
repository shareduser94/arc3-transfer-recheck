"""Probe: where are the tiny per-step changes (suspected step counters)?"""
import random, logging, sys
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
logging.disable(logging.INFO)
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
infos = {e.game_id: e for e in arc.get_environments()}
for gid in sorted(infos):
    env = arc.make(gid, seed=0); fd = env.reset(); rng = random.Random(1)
    acts = [a for a in fd.available_actions if a != 0]
    pts = []; tinyn = 0; n = 0
    for t in range(200):
        fr = np.asarray(fd.frame[-1]); a = rng.choice(acts)
        fd2 = env.step(GameAction.from_id(a), data={"x": rng.randrange(64), "y": rng.randrange(64)} if a == 6 else None)
        if fd2 is None: break
        if fd2.state == GameState.GAME_OVER: fd = env.reset(); continue
        if fd2.levels_completed != fd.levels_completed: fd = fd2; continue
        d = np.argwhere(fr != np.asarray(fd2.frame[-1])); n += 1
        if 0 < len(d) <= 4:
            tinyn += 1; pts += [tuple(p) for p in d]
        fd = fd2
    if pts:
        P = np.array(pts)
        rows = sorted(set(P[:, 0].tolist())); cols = sorted(set(P[:, 1].tolist()))
        print(f"{gid[:4]} tiny-diff steps {tinyn}/{n} distinct px {len(set(pts))} rows {rows[:6]}{'..' if len(rows)>6 else ''} cols {cols[:3]}..{cols[-3:]} ({len(cols)} cols)")
    else:
        print(f"{gid[:4]} no tiny diffs ({n} steps)")

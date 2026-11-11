"""Probe: what changes in the frame per action? Looks for action-independent (clock) changes."""
import json, os, random, logging, sys
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
logging.disable(logging.INFO)

arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
infos = {e.game_id: e for e in arc.get_environments()}
games = sys.argv[1].split(",") if len(sys.argv) > 1 else None
for gid in sorted(infos):
    if games and gid.split("-")[0] not in games:
        continue
    env = arc.make(gid, seed=0); fd = env.reset()
    rng = random.Random(0)
    H = W = 64
    cnt = np.zeros((H, W), int); steps = 0
    nchg = []
    acts = [a for a in fd.available_actions if a != 0]
    per_act = {}
    for t in range(300):
        fr = np.asarray(fd.frame[-1])
        a = rng.choice(acts)
        fd2 = env.step(GameAction.from_id(a), data={"x": rng.randrange(64), "y": rng.randrange(64)} if a == 6 else None)
        if fd2 is None: break
        fr2 = np.asarray(fd2.frame[-1])
        d = fr != fr2
        if fd2.state == GameState.GAME_OVER or fd2.levels_completed != fd.levels_completed:
            fd = env.reset() if fd2.state == GameState.GAME_OVER else fd2; continue
        cnt += d; steps += 1; nchg.append(int(d.sum()))
        per_act.setdefault(a, []).append(int(d.sum()))
        fd = fd2
    frac = cnt / max(1, steps)
    hot = np.argwhere(frac > 0.5)
    zero_steps = sum(1 for n in nchg if n == 0)
    print(f"{gid.split('-')[0]} acts {acts} steps {steps} no-change steps {zero_steps} "
          f"median changed px {int(np.median(nchg)) if nchg else -1} "
          f"px changing >50% of steps {len(hot)} "
          f"bbox {(hot.min(0).tolist(), hot.max(0).tolist()) if len(hot) else None} "
          f"per-action median {{{', '.join(f'{k}:{int(np.median(v))}' for k, v in sorted(per_act.items()))}}}", flush=True)

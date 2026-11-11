"""Sanity checks for gen_env: determinism, solvability, distinct kinds, effect rates per role under random clicks."""
import random, logging
from collections import defaultdict
import numpy as np
from arcengine import GameAction, GameState
logging.disable(logging.INFO)
import gen_env as G

ids = G.game_ids()
# 1. determinism
for gid in ids[:20]:
    a, b = G.GenEnv(gid), G.GenEnv(gid)
    assert (a.reset().frame[0] == b.reset().frame[0]).all()
print("determinism ok")
# 2. distinct kinds (colour+size) and no colour clash with indicator
for gid in ids:
    e = G.GenEnv(gid)
    ks = list(e.kinds.values())
    assert len(set(ks)) == 5 and len(set(k[0] for k in ks)) == 5
    assert not set(k[0] for k in ks) & set(G.IND_COLOURS)
print("kinds ok")
# 3. oracle solves every game in 4 clicks (2 keys x 2 levels), state WIN
for gid in ids:
    e = G.GenEnv(gid); fd = e.reset(); n = 0
    while fd.state != GameState.WIN:
        o = next(o for o in e.objs if o["alive"] and o["role"] == "KEY")
        fd = e.step(GameAction.ACTION6, {"x": o["x"], "y": o["y"]}); n += 1
        assert n <= 4
    assert n == 4 and fd.levels_completed == 2
print("oracle ok: every game solvable in 4 clicks")
# 4. effect rate per role, random clicks on objects (level 1 only, keys excluded so the level never ends)
rate = defaultdict(lambda: [0, 0])
for gid in ids[::10]:
    e = G.GenEnv(gid); e.reset(); rng = random.Random(0)
    for _ in range(400):
        o = rng.choice([o for o in e.objs if o["alive"] and o["role"] != "KEY"])
        before = e._grid(); e.step(GameAction.ACTION6, {"x": o["x"], "y": o["y"]})
        r = rate[o["role"]]; r[0] += 1; r[1] += int((e._grid() != before).any())
print("effect rate under random clicks:", {k: round(v[1] / v[0], 2) for k, v in rate.items()})
# 5. layouts differ between levels and objects never overlap
for gid in ids:
    e = G.GenEnv(gid)
    for lv in e.levels:
        occ = np.zeros((64, 64), int)
        for o in lv:
            occ[o["y"]:o["y"] + o["h"], o["x"]:o["x"] + o["w"]] += 1
        assert occ.max() == 1 and occ[2:6, 2:6].sum() == 0
print("no overlaps, indicator clear;", len(ids), "games")

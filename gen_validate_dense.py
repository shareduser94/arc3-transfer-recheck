"""Step J checks: dense games solvable, non-overlapping, same-colour objects never touch, k distinct noise kinds."""
import numpy as np, logging
from arcengine import GameAction, GameState
logging.disable(logging.INFO)
import gen_env as G
ids = G.game_ids_dense()
for gid in ids:
    e = G.GenEnv(gid); k = G.parse_noise(gid)
    assert len(e.kinds) == 5 + k and len(set(e.kinds.values())) == 5 + k
    for lv in e.levels:
        occ = np.zeros((64, 64), int)
        for o in lv:
            assert o["y"] + o["h"] <= 64 and o["x"] + o["w"] <= 64
            occ[max(0, o["y"] - 1):o["y"] + o["h"] + 1, max(0, o["x"] - 1):o["x"] + o["w"] + 1] += 1   # 1-cell halo
        assert occ.max() == 1, gid                 # halos never overlap -> objects never touch
        assert sum(o["role"] == "NOISE" for o in lv) == k
    fd = e.reset(); n = 0
    while fd.state != GameState.WIN:
        o = next(o for o in e.objs if o["alive"] and o["role"] == "KEY")
        fd = e.step(GameAction.ACTION6, {"x": o["x"], "y": o["y"]}); n += 1
    assert n == 4
print("dense games ok:", len(ids), "games; k values", sorted({G.parse_noise(g) for g in ids}))
